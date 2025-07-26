import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Tab,
  Switch,
  FormControlLabel
} from '@mui/material'
import {
  Usb as UsbIcon,
  CloudDownload as DownloadIcon,
  FlashOn as FlashIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon,
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Settings as SettingsIcon,
  Help as HelpIcon,
  Wifi as WifiIcon,
  Memory as MemoryIcon
} from '@mui/icons-material'
import { useDropzone } from 'react-dropzone'
import api from '../services/api'
import { webSerialService, WebSerialService, SerialDevice, FlashProgress } from '../services/webserial'

interface FlashDevice {
  port: string
  description: string
  hwid: string
  vid: string
  pid: string
  serial: string
  manufacturer: string
  product: string
  connected: boolean
}

interface Firmware {
  id: string
  name: string
  version: string
  chip_type: string
  size: number
  download_url: string
  verified: boolean
  release_notes?: string
}

interface FlashStep {
  id: string
  label: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'error'
  progress?: number
  message?: string
}

const Flashing: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0)
  const [flashDevices, setFlashDevices] = useState<FlashDevice[]>([])
  const [selectedDevice, setSelectedDevice] = useState<string>('')
  const [selectedFirmware, setSelectedFirmware] = useState<string>('')
  const [firmwareList, setFirmwareList] = useState<Firmware[]>([])
  const [customFirmware, setCustomFirmware] = useState<File | null>(null)
  const [webSerialSupported, setWebSerialSupported] = useState(false)
  const [serialDevice, setSerialDevice] = useState<SerialDevice | null>(null)
  const [webSerialProgress, setWebSerialProgress] = useState<FlashProgress | null>(null)
  const [flashSteps, setFlashSteps] = useState<FlashStep[]>([
    { id: 'prepare', label: 'Prepare Device', description: 'Put device in flash mode', status: 'pending' },
    { id: 'erase', label: 'Erase Flash', description: 'Clear existing firmware', status: 'pending' },
    { id: 'flash', label: 'Flash Firmware', description: 'Write new firmware', status: 'pending' },
    { id: 'verify', label: 'Verify', description: 'Verify flash success', status: 'pending' },
    { id: 'reboot', label: 'Reboot Device', description: 'Start with new firmware', status: 'pending' }
  ])
  const [flashProgress, setFlashProgress] = useState(0)
  const [isFlashing, setIsFlashing] = useState(false)
  const [currentTab, setCurrentTab] = useState(0)
  const [flashSettings, setFlashSettings] = useState({
    erase_flash: true,
    verify_flash: true,
    auto_reboot: true,
    baud_rate: 115200,
    flash_mode: 'dout',
    flash_freq: '40m',
    flash_size: 'detect'
  })
  const [helpDialogOpen, setHelpDialogOpen] = useState(false)
  const [devicesLoading, setDevicesLoading] = useState(true)
  const [firmwareLoading, setFirmwareLoading] = useState(true)

  useEffect(() => {
    fetchFlashDevices()
    fetchFirmwareList()
    checkWebSerialSupport()
    
    // Refresh devices every 5 seconds
    const interval = setInterval(fetchFlashDevices, 5000)
    return () => clearInterval(interval)
  }, [])

  const checkWebSerialSupport = async () => {
    const supported = await WebSerialService.isSupported()
    setWebSerialSupported(supported)
    
    // Set progress callback
    webSerialService.setProgressCallback(setWebSerialProgress)
  }

  const fetchFlashDevices = async () => {
    try {
      const response = await api.get('/flash/devices')
      setFlashDevices(response.data.devices || [])
    } catch (error) {
      console.error('Failed to fetch flash devices:', error)
    } finally {
      setDevicesLoading(false)
    }
  }

  const fetchFirmwareList = async () => {
    try {
      const response = await api.get('/firmware')
      setFirmwareList(response.data.firmware || [])
    } catch (error) {
      console.error('Failed to fetch firmware list:', error)
    } finally {
      setFirmwareLoading(false)
    }
  }

  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setCustomFirmware(acceptedFiles[0])
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/octet-stream': ['.bin'],
      'application/x-binary': ['.bin']
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024 // 10MB
  })

  const handleRequestSerialPort = async () => {
    try {
      const device = await webSerialService.requestPort()
      setSerialDevice(device)
      setSelectedDevice('webserial')
    } catch (error) {
      console.error('Failed to request serial port:', error)
    }
  }

  const handleWebSerialFlash = async () => {
    if (!serialDevice || (!selectedFirmware && !customFirmware)) {
      return
    }

    setIsFlashing(true)
    setFlashProgress(0)
    setWebSerialProgress(null)

    try {
      // Connect to device
      await webSerialService.connect(flashSettings.baud_rate)
      
      // Enter bootloader mode
      await webSerialService.enterBootloader()
      await webSerialService.syncDevice()

      // Get firmware data
      let firmwareData: ArrayBuffer
      
      if (customFirmware) {
        firmwareData = await customFirmware.arrayBuffer()
      } else {
        // Download selected firmware
        const response = await api.downloadFirmware(selectedFirmware)
        firmwareData = await response.arrayBuffer()
      }

      // Flash firmware
      await webSerialService.flashFirmware(firmwareData, (written, total) => {
        const progress = Math.round((written / total) * 100)
        setFlashProgress(progress)
      })

    } catch (error) {
      console.error('WebSerial flash error:', error)
      setWebSerialProgress({
        stage: 'error',
        progress: 0,
        message: `Flash failed: ${error}`
      })
    } finally {
      setIsFlashing(false)
      await webSerialService.disconnect()
    }
  }

  const handleStartFlash = async () => {
    if (!selectedDevice || (!selectedFirmware && !customFirmware)) {
      return
    }

    // Use WebSerial if selected
    if (selectedDevice === 'webserial' && webSerialSupported) {
      return handleWebSerialFlash()
    }

    setIsFlashing(true)
    setFlashProgress(0)
    
    // Reset all steps
    setFlashSteps(prev => prev.map(step => ({ ...step, status: 'pending', progress: 0, message: '' })))

    try {
      // Simulate flashing process for USB devices
      for (let i = 0; i < flashSteps.length; i++) {
        const step = flashSteps[i]
        
        // Mark current step as running
        setFlashSteps(prev => prev.map((s, idx) => 
          idx === i ? { ...s, status: 'running', progress: 0 } : s
        ))

        // Simulate step progress
        for (let progress = 0; progress <= 100; progress += 10) {
          setFlashSteps(prev => prev.map((s, idx) => 
            idx === i ? { ...s, progress } : s
          ))
          setFlashProgress((i * 100 + progress) / flashSteps.length)
          await new Promise(resolve => setTimeout(resolve, 200))
        }

        // Mark step as completed
        setFlashSteps(prev => prev.map((s, idx) => 
          idx === i ? { ...s, status: 'completed', progress: 100 } : s
        ))
      }

      setActiveStep(flashSteps.length)
    } catch (error) {
      console.error('Flash error:', error)
      // Mark current step as error
      setFlashSteps(prev => prev.map((s, idx) => 
        s.status === 'running' ? { ...s, status: 'error', message: 'Flash failed' } : s
      ))
    } finally {
      setIsFlashing(false)
    }
  }

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <SuccessIcon color="success" />
      case 'running':
        return <FlashIcon color="primary" />
      case 'error':
        return <ErrorIcon color="error" />
      default:
        return <InfoIcon color="disabled" />
    }
  }

  const renderDeviceSelection = () => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Select Device</Typography>
          <Button
            variant="outlined"
            size="small"
            startIcon={<RefreshIcon />}
            onClick={fetchFlashDevices}
            disabled={devicesLoading}
          >
            Refresh
          </Button>
        </Box>

        {webSerialSupported && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2" fontWeight="bold">
              WebSerial API Supported! 
            </Typography>
            <Typography variant="body2">
              You can flash devices directly from your browser without backend USB access.
            </Typography>
          </Alert>
        )}

        {devicesLoading ? (
          <LinearProgress />
        ) : (
          <FormControl fullWidth>
            <InputLabel>Flash Method</InputLabel>
            <Select
              value={selectedDevice}
              onChange={(e) => setSelectedDevice(e.target.value)}
              label="Flash Method"
            >
              {webSerialSupported && (
                <MenuItem value="webserial">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <UsbIcon color="primary" />
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        WebSerial API (Browser)
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Direct browser-to-device flashing
                      </Typography>
                    </Box>
                  </Box>
                </MenuItem>
              )}
              {flashDevices.map((device) => (
                <MenuItem key={device.port} value={device.port}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <UsbIcon />
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {device.port} - {device.description}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {device.manufacturer} {device.product}
                      </Typography>
                    </Box>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        {selectedDevice === 'webserial' && !serialDevice && (
          <Box sx={{ mt: 2 }}>
            <Button
              variant="outlined"
              startIcon={<UsbIcon />}
              onClick={handleRequestSerialPort}
              fullWidth
            >
              Select Serial Device
            </Button>
          </Box>
        )}

        {selectedDevice === 'webserial' && serialDevice && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>WebSerial Device Ready:</strong> 
              USB Vendor: {serialDevice.info.usbVendorId?.toString(16)}, 
              Product: {serialDevice.info.usbProductId?.toString(16)}
            </Typography>
            <Typography variant="caption">
              Make sure your device is in flash mode (GPIO0 connected to GND on boot).
            </Typography>
          </Alert>
        )}

        {flashDevices.length === 0 && !webSerialSupported && (
          <Alert severity="warning">
            No USB devices detected and WebSerial API not supported. 
            Please connect your ESP device and put it in flash mode, or use a WebSerial-compatible browser.
          </Alert>
        )}

        {selectedDevice && (
          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Selected:</strong> {flashDevices.find(d => d.port === selectedDevice)?.description}
            </Typography>
            <Typography variant="caption">
              Make sure your device is in flash mode (GPIO0 connected to GND on boot).
            </Typography>
          </Alert>
        )}
      </CardContent>
    </Card>
  )

  const renderFirmwareSelection = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>Select Firmware</Typography>
        
        <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)} sx={{ mb: 2 }}>
          <Tab label="Official Firmware" />
          <Tab label="Custom Firmware" />
        </Tabs>

        {currentTab === 0 && (
          <Box>
            {firmwareLoading ? (
              <LinearProgress />
            ) : (
              <FormControl fullWidth>
                <InputLabel>Firmware Version</InputLabel>
                <Select
                  value={selectedFirmware}
                  onChange={(e) => setSelectedFirmware(e.target.value)}
                  label="Firmware Version"
                >
                  {firmwareList.map((firmware) => (
                    <MenuItem key={firmware.id} value={firmware.id}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {firmware.name} v{firmware.version}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {firmware.chip_type} • {Math.round(firmware.size / 1024)}KB
                          </Typography>
                        </Box>
                        {firmware.verified && (
                          <Chip label="Verified" size="small" color="success" />
                        )}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Box>
        )}

        {currentTab === 1 && (
          <Box>
            <Paper
              {...getRootProps()}
              sx={{
                p: 3,
                border: '2px dashed',
                borderColor: isDragActive ? 'primary.main' : 'grey.300',
                backgroundColor: isDragActive ? 'action.hover' : 'background.default',
                cursor: 'pointer',
                textAlign: 'center'
              }}
            >
              <input {...getInputProps()} />
              <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
              {customFirmware ? (
                <Box>
                  <Typography variant="body1" fontWeight="bold">
                    {customFirmware.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {Math.round(customFirmware.size / 1024)}KB
                  </Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<DeleteIcon />}
                    onClick={(e) => {
                      e.stopPropagation()
                      setCustomFirmware(null)
                    }}
                    sx={{ mt: 1 }}
                  >
                    Remove
                  </Button>
                </Box>
              ) : (
                <Box>
                  <Typography variant="body1">
                    {isDragActive ? 'Drop the firmware file here' : 'Drag & drop a .bin file here'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    or click to select a file
                  </Typography>
                </Box>
              )}
            </Paper>
            
            {customFirmware && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                Custom firmware is not verified. Flash at your own risk.
              </Alert>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  )

  const renderFlashSettings = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>Flash Settings</Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={flashSettings.erase_flash}
                  onChange={(e) => setFlashSettings(prev => ({ ...prev, erase_flash: e.target.checked }))}
                />
              }
              label="Erase Flash"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={flashSettings.verify_flash}
                  onChange={(e) => setFlashSettings(prev => ({ ...prev, verify_flash: e.target.checked }))}
                />
              }
              label="Verify Flash"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={flashSettings.auto_reboot}
                  onChange={(e) => setFlashSettings(prev => ({ ...prev, auto_reboot: e.target.checked }))}
                />
              }
              label="Auto Reboot"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth>
              <InputLabel>Baud Rate</InputLabel>
              <Select
                value={flashSettings.baud_rate}
                onChange={(e) => setFlashSettings(prev => ({ ...prev, baud_rate: e.target.value as number }))}
                label="Baud Rate"
              >
                <MenuItem value={115200}>115200</MenuItem>
                <MenuItem value={460800}>460800</MenuItem>
                <MenuItem value={921600}>921600</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  )

  const renderFlashProgress = () => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Flash Progress</Typography>
          <Typography variant="body2" color="text.secondary">
            {Math.round(flashProgress)}%
          </Typography>
        </Box>
        
        <LinearProgress variant="determinate" value={flashProgress} sx={{ mb: 3, height: 8, borderRadius: 4 }} />

        {selectedDevice === 'webserial' && webSerialProgress ? (
          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" gutterBottom>
              {webSerialProgress.message}
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={webSerialProgress.progress} 
              sx={{ height: 8, borderRadius: 4 }}
              color={webSerialProgress.stage === 'error' ? 'error' : 'primary'}
            />
            {webSerialProgress.bytesWritten && webSerialProgress.totalBytes && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                {Math.round(webSerialProgress.bytesWritten / 1024)}KB / {Math.round(webSerialProgress.totalBytes / 1024)}KB
              </Typography>
            )}
          </Box>
        ) : (
          <List>
            {flashSteps.map((step, index) => (
              <ListItem key={step.id} sx={{ pl: 0 }}>
                <ListItemIcon>
                  {getStepIcon(step.status)}
                </ListItemIcon>
                <ListItemText
                  primary={step.label}
                  secondary={
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        {step.description}
                      </Typography>
                      {step.status === 'running' && step.progress !== undefined && (
                        <LinearProgress
                          variant="determinate"
                          value={step.progress}
                          sx={{ mt: 1, height: 4, borderRadius: 2 }}
                        />
                      )}
                      {step.message && (
                        <Typography variant="caption" color={step.status === 'error' ? 'error' : 'text.secondary'}>
                          {step.message}
                        </Typography>
                      )}
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}

        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
          <Button
            variant="contained"
            startIcon={isFlashing ? <StopIcon /> : <StartIcon />}
            onClick={isFlashing ? () => setIsFlashing(false) : handleStartFlash}
            disabled={!selectedDevice || (!selectedFirmware && !customFirmware)}
            color={isFlashing ? 'error' : 'primary'}
          >
            {isFlashing ? 'Stop Flash' : 'Start Flash'}
          </Button>
          
          {flashSteps.every(step => step.status === 'completed') && (
            <Button
              variant="outlined"
              startIcon={<WifiIcon />}
              onClick={() => {
                // Navigate to discovery or devices page
                window.location.href = '/devices'
              }}
            >
              Find Device
            </Button>
          )}
        </Box>
      </CardContent>
    </Card>
  )

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          Device Flashing
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<HelpIcon />}
            onClick={() => setHelpDialogOpen(true)}
          >
            Help
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          {renderDeviceSelection()}
        </Grid>
        <Grid item xs={12} md={6}>
          {renderFlashSettings()}
        </Grid>
        <Grid item xs={12}>
          {renderFirmwareSelection()}
        </Grid>
        <Grid item xs={12}>
          {renderFlashProgress()}
        </Grid>
      </Grid>

      {/* Help Dialog */}
      <Dialog
        open={helpDialogOpen}
        onClose={() => setHelpDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Flashing Help</DialogTitle>
        <DialogContent>
          <Typography variant="h6" gutterBottom>
            How to Flash Tasmota Firmware
          </Typography>
          
          <Typography variant="body2" paragraph>
            <strong>Step 1: Prepare Your Device</strong>
          </Typography>
          <Typography variant="body2" paragraph>
            • Power off your ESP device
            • Connect GPIO0 to GND (ground)
            • Connect your device to USB
            • Power on the device (it should enter flash mode)
          </Typography>
          
          <Typography variant="body2" paragraph>
            <strong>Step 2: Select Firmware</strong>
          </Typography>
          <Typography variant="body2" paragraph>
            • Choose official Tasmota firmware for your chip type (ESP8266/ESP32)
            • Or upload a custom .bin file
            • Verified firmware is recommended for stability
          </Typography>
          
          <Typography variant="body2" paragraph>
            <strong>Step 3: Flash Settings</strong>
          </Typography>
          <Typography variant="body2" paragraph>
            • Erase Flash: Recommended for clean installation
            • Verify Flash: Ensures firmware was written correctly
            • Auto Reboot: Automatically restarts device after flashing
          </Typography>
          
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Warning:</strong> Flashing firmware can brick your device if done incorrectly. 
              Make sure you have the correct firmware for your device model.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHelpDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Flashing