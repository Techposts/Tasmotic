import React, { createContext, useContext, useEffect, useState } from 'react'
import { Device } from '../types'
import { apiService } from '../services/api'
import { useSocket } from './SocketContext'
import { useSnackbar } from 'notistack'

interface DeviceContextType {
  devices: Record<string, Device>
  loading: boolean
  devicesLoading: boolean
  error: string | null
  refreshDevices: () => Promise<void>
  getDevice: (deviceId: string) => Device | undefined
  sendCommand: (deviceId: string, command: string, params?: Record<string, any>) => Promise<boolean>
}

const DeviceContext = createContext<DeviceContextType>({
  devices: {},
  loading: false,
  devicesLoading: false,
  error: null,
  refreshDevices: async () => {},
  getDevice: () => undefined,
  sendCommand: async () => false,
})

export const useDevices = () => {
  const context = useContext(DeviceContext)
  if (!context) {
    throw new Error('useDevices must be used within a DeviceProvider')
  }
  return context
}

interface DeviceProviderProps {
  children: React.ReactNode
}

export const DeviceProvider: React.FC<DeviceProviderProps> = ({ children }) => {
  const [devices, setDevices] = useState<Record<string, Device>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { socket } = useSocket()
  const { enqueueSnackbar } = useSnackbar()

  const refreshDevices = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await apiService.getDevices()
      if (response.data) {
        setDevices(response.data.devices)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load devices'
      setError(errorMessage)
      enqueueSnackbar(errorMessage, { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const getDevice = (deviceId: string): Device | undefined => {
    return devices[deviceId]
  }

  const sendCommand = async (deviceId: string, command: string, params?: Record<string, any>): Promise<boolean> => {
    try {
      const response = await apiService.sendDeviceCommand(deviceId, command, params)
      if (response.data?.success) {
        enqueueSnackbar(`Command sent successfully: ${command}`, { variant: 'success' })
        return true
      } else {
        enqueueSnackbar(`Command failed: ${response.data?.error || 'Unknown error'}`, { variant: 'error' })
        return false
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send command'
      enqueueSnackbar(errorMessage, { variant: 'error' })
      return false
    }
  }

  // Socket event handlers
  useEffect(() => {
    if (!socket) return

    const handleDeviceUpdate = (data: { device_id: string; device: Device }) => {
      setDevices(prev => ({
        ...prev,
        [data.device_id]: data.device
      }))
    }

    const handleDeviceDiscovered = (data: { device: Device }) => {
      setDevices(prev => ({
        ...prev,
        [data.device.id]: data.device
      }))
      enqueueSnackbar(`New device discovered: ${data.device.name}`, { variant: 'info' })
    }

    socket.on('device_update', handleDeviceUpdate)
    socket.on('device_discovered', handleDeviceDiscovered)

    return () => {
      socket.off('device_update', handleDeviceUpdate)
      socket.off('device_discovered', handleDeviceDiscovered)
    }
  }, [socket, enqueueSnackbar])

  // Load devices on mount
  useEffect(() => {
    refreshDevices()
  }, [])

  return (
    <DeviceContext.Provider value={{
      devices,
      loading,
      devicesLoading: loading,
      error,
      refreshDevices,
      getDevice,
      sendCommand,
    }}>
      {children}
    </DeviceContext.Provider>
  )
}