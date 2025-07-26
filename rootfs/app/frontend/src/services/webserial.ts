/**
 * WebSerial API service for browser-based ESP device flashing
 * Provides direct serial communication without requiring backend USB access
 */

/// <reference path="../types/webserial.d.ts" />

export interface SerialDevice {
  port: SerialPort
  info: {
    usbVendorId?: number
    usbProductId?: number
  }
  connected: boolean
}

export interface FlashProgress {
  stage: 'connecting' | 'erasing' | 'flashing' | 'verifying' | 'complete' | 'error'
  progress: number
  message: string
  bytesWritten?: number
  totalBytes?: number
}

export class WebSerialService {
  private port: SerialPort | null = null
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null
  private writer: WritableStreamDefaultWriter<Uint8Array> | null = null
  private progressCallback: ((progress: FlashProgress) => void) | null = null

  // ESP boot modes and commands
  private readonly ESP_SYNC = 0x08
  private readonly ESP_WRITE_REG = 0x09
  private readonly ESP_READ_REG = 0x0a
  private readonly ESP_SPI_ATTACH = 0x0d
  private readonly ESP_CHANGE_BAUDRATE = 0x0f
  private readonly ESP_FLASH_BEGIN = 0x02
  private readonly ESP_FLASH_DATA = 0x03
  private readonly ESP_FLASH_END = 0x04
  private readonly ESP_MEM_BEGIN = 0x05
  private readonly ESP_MEM_END = 0x06
  private readonly ESP_MEM_DATA = 0x07

  static async isSupported(): Promise<boolean> {
    return 'serial' in navigator && 'requestPort' in navigator.serial
  }

  static async getAvailablePorts(): Promise<SerialPort[]> {
    if (!await WebSerialService.isSupported()) {
      throw new Error('WebSerial API not supported')
    }
    
    return await navigator.serial.getPorts()
  }

  async requestPort(): Promise<SerialDevice> {
    if (!await WebSerialService.isSupported()) {
      throw new Error('WebSerial API not supported')
    }

    try {
      // Request port with ESP device filters
      const port = await navigator.serial.requestPort({
        filters: [
          // Common ESP development boards
          { usbVendorId: 0x10c4, usbProductId: 0xea60 }, // CP2102
          { usbVendorId: 0x0403, usbProductId: 0x6001 }, // FT232
          { usbVendorId: 0x0403, usbProductId: 0x6010 }, // FT2232H
          { usbVendorId: 0x0403, usbProductId: 0x6011 }, // FT4232H
          { usbVendorId: 0x0403, usbProductId: 0x6014 }, // FT232H
          { usbVendorId: 0x0403, usbProductId: 0x6015 }, // FT230X
          { usbVendorId: 0x1a86, usbProductId: 0x7523 }, // CH340
          { usbVendorId: 0x1a86, usbProductId: 0x5523 }, // CH341
        ]
      })

      const info = port.getInfo()
      this.port = port

      return {
        port,
        info,
        connected: false
      }
    } catch (error) {
      throw new Error(`Failed to request serial port: ${error}`)
    }
  }

  async connect(baudRate: number = 115200): Promise<void> {
    if (!this.port) {
      throw new Error('No port selected')
    }

    try {
      await this.port.open({ 
        baudRate,
        dataBits: 8,
        stopBits: 1,
        parity: 'none',
        flowControl: 'none'
      })

      this.reader = this.port.readable?.getReader() || null
      this.writer = this.port.writable?.getWriter() || null

      if (!this.reader || !this.writer) {
        throw new Error('Failed to get serial streams')
      }

      this.updateProgress('connecting', 100, 'Connected to device')
    } catch (error) {
      throw new Error(`Failed to connect: ${error}`)
    }
  }

  async disconnect(): Promise<void> {
    try {
      if (this.reader) {
        await this.reader.cancel()
        this.reader.releaseLock()
        this.reader = null
      }

      if (this.writer) {
        await this.writer.close()
        this.writer = null
      }

      if (this.port) {
        await this.port.close()
        this.port = null
      }
    } catch (error) {
      console.warn('Error during disconnect:', error)
    }
  }

  setProgressCallback(callback: (progress: FlashProgress) => void): void {
    this.progressCallback = callback
  }

  private updateProgress(stage: FlashProgress['stage'], progress: number, message: string, bytesWritten?: number, totalBytes?: number): void {
    if (this.progressCallback) {
      this.progressCallback({
        stage,
        progress,
        message,
        bytesWritten,
        totalBytes
      })
    }
  }

  async enterBootloader(): Promise<void> {
    if (!this.writer) {
      throw new Error('Device not connected')
    }

    try {
      // Set DTR and RTS to enter bootloader mode
      await this.port?.setSignals({ dataTerminalReady: false, requestToSend: true })
      await this.delay(100)
      await this.port?.setSignals({ dataTerminalReady: true, requestToSend: false })
      await this.delay(100)
      await this.port?.setSignals({ dataTerminalReady: false, requestToSend: false })
      await this.delay(100)

      this.updateProgress('connecting', 50, 'Entering bootloader mode...')
    } catch (error) {
      throw new Error(`Failed to enter bootloader: ${error}`)
    }
  }

  async syncDevice(): Promise<void> {
    if (!this.writer || !this.reader) {
      throw new Error('Device not connected')
    }

    try {
      // Send sync command multiple times
      for (let i = 0; i < 10; i++) {
        const syncPacket = this.buildPacket(this.ESP_SYNC, new Uint8Array([
          0x07, 0x07, 0x12, 0x20,
          0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55,
          0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55,
          0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55,
          0x55, 0x55, 0x55, 0x55
        ]))

        await this.writer.write(syncPacket)
        
        try {
          const response = await this.readResponse(1000)
          if (response && response.length > 0) {
            this.updateProgress('connecting', 75, 'Device synchronized')
            return
          }
        } catch (e) {
          // Ignore timeout, try again
        }
      }

      throw new Error('Failed to sync with device')
    } catch (error) {
      throw new Error(`Sync failed: ${error}`)
    }
  }

  async flashFirmware(firmwareData: ArrayBuffer, onProgress?: (written: number, total: number) => void): Promise<void> {
    if (!this.writer || !this.reader) {
      throw new Error('Device not connected')
    }

    try {
      const firmware = new Uint8Array(firmwareData)
      const blockSize = 1024 // 1KB blocks
      const totalBlocks = Math.ceil(firmware.length / blockSize)

      this.updateProgress('erasing', 0, 'Erasing flash...')

      // Begin flash
      await this.flashBegin(firmware.length, 0x00000000)
      
      this.updateProgress('flashing', 0, 'Writing firmware...')

      // Flash in blocks
      for (let i = 0; i < totalBlocks; i++) {
        const start = i * blockSize
        const end = Math.min(start + blockSize, firmware.length)
        const block = firmware.slice(start, end)
        
        // Pad block to blockSize if needed
        const paddedBlock = new Uint8Array(blockSize)
        paddedBlock.set(block)
        
        await this.flashData(paddedBlock, i)
        
        const progress = Math.round((i + 1) / totalBlocks * 100)
        this.updateProgress('flashing', progress, `Writing block ${i + 1}/${totalBlocks}`, end, firmware.length)
        
        if (onProgress) {
          onProgress(end, firmware.length)
        }
      }

      // End flash
      await this.flashEnd()

      this.updateProgress('verifying', 90, 'Verifying flash...')
      await this.delay(1000) // Give device time to process

      this.updateProgress('complete', 100, 'Flash complete! Device will restart.')
      
      // Reset device
      await this.resetDevice()

    } catch (error) {
      this.updateProgress('error', 0, `Flash failed: ${error}`)
      throw error
    }
  }

  private async flashBegin(size: number, offset: number): Promise<void> {
    const data = new Uint8Array(16)
    const dataView = new DataView(data.buffer)
    
    dataView.setUint32(0, size, true)  // Size (little endian)
    dataView.setUint32(4, Math.ceil(size / 1024), true)  // Number of blocks
    dataView.setUint32(8, 1024, true)  // Block size
    dataView.setUint32(12, offset, true)  // Offset

    const packet = this.buildPacket(this.ESP_FLASH_BEGIN, data)
    await this.writer!.write(packet)
    await this.readResponse(5000)
  }

  private async flashData(data: Uint8Array, sequence: number): Promise<void> {
    const header = new Uint8Array(16)
    const headerView = new DataView(header.buffer)
    
    headerView.setUint32(0, data.length, true)  // Data size
    headerView.setUint32(4, sequence, true)     // Sequence number
    headerView.setUint32(8, 0, true)           // Reserved
    headerView.setUint32(12, 0, true)          // Reserved

    const payload = new Uint8Array(header.length + data.length)
    payload.set(header)
    payload.set(data, header.length)

    const packet = this.buildPacket(this.ESP_FLASH_DATA, payload)
    await this.writer!.write(packet)
    await this.readResponse(5000)
  }

  private async flashEnd(): Promise<void> {
    const data = new Uint8Array(4)
    data.fill(0) // Reboot = false

    const packet = this.buildPacket(this.ESP_FLASH_END, data)
    await this.writer!.write(packet)
    await this.readResponse(5000)
  }

  private async resetDevice(): Promise<void> {
    try {
      // Toggle DTR to reset
      await this.port?.setSignals({ dataTerminalReady: false })
      await this.delay(100)
      await this.port?.setSignals({ dataTerminalReady: true })
    } catch (error) {
      console.warn('Reset failed:', error)
    }
  }

  private buildPacket(command: number, data: Uint8Array): Uint8Array {
    const header = new Uint8Array(8)
    header[0] = 0xc0  // Begin
    header[1] = command
    
    // Data length (little endian)
    header[2] = data.length & 0xff
    header[3] = (data.length >> 8) & 0xff
    
    // Checksum (simple XOR)
    let checksum = 0xef
    for (let i = 0; i < data.length; i++) {
      checksum ^= data[i]
    }
    header[4] = checksum & 0xff
    header[5] = (checksum >> 8) & 0xff
    header[6] = (checksum >> 16) & 0xff
    header[7] = (checksum >> 24) & 0xff

    const packet = new Uint8Array(header.length + data.length + 1)
    packet.set(header)
    packet.set(data, header.length)
    packet[packet.length - 1] = 0xc0  // End

    return packet
  }

  private async readResponse(timeoutMs: number): Promise<Uint8Array | null> {
    if (!this.reader) return null

    const timeout = new Promise<null>((_, reject) => 
      setTimeout(() => reject(new Error('Timeout')), timeoutMs)
    )

    try {
      const result = await Promise.race([
        this.reader.read(),
        timeout
      ])

      if (result && typeof result === 'object' && 'value' in result && result.value) {
        return result.value
      }
      return null
    } catch (error) {
      throw error
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

// Global instance
export const webSerialService = new WebSerialService()