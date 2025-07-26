import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Divider,
  Paper
} from '@mui/material'
import {
  Search as SearchIcon,
  Stop as StopIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
  DeviceHub as DeviceIcon,
  NetworkWifi as NetworkIcon,
  Router as RouterIcon,
  CheckCircle as FoundIcon,
  Error as ErrorIcon,
  Settings as SettingsIcon
} from '@mui/icons-material'
import { useSocket } from '../contexts/SocketContext'
import { useDevices } from '../contexts/DeviceContext'
import api from '../services/api'

interface DiscoverableDevice {
  ip: string
  hostname: string
  mac?: string
  manufacturer?: string
  model?: string
  firmware_version?: string
  services: string[]
  discovered_at: string
  status: 'new' | 'existing' | 'added'
}

interface DiscoveryStats {
  devices_found: number
  scan_progress: number
  current_subnet: string
  time_elapsed: number
  estimated_remaining: number
}

const Discovery: React.FC = () => {
  const { socket } = useSocket()
  const { refreshDevices } = useDevices()
  const [discoveryActive, setDiscoveryActive] = useState(false)
  const [discoveredDevices, setDiscoveredDevices] = useState<DiscoverableDevice[]>([])
  const [discoveryStats, setDiscoveryStats] = useState<DiscoveryStats>({
    devices_found: 0,
    scan_progress: 0,
    current_subnet: '',
    time_elapsed: 0,
    estimated_remaining: 0
  })
  const [selectedDevice, setSelectedDevice] = useState<DiscoverableDevice | null>(null)
  const [addDeviceOpen, setAddDeviceOpen] = useState(false)
  const [manualAddOpen, setManualAddOpen] = useState(false)
  const [deviceName, setDeviceName] = useState('')
  const [deviceIp, setDeviceIp] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [discoverySettings, setDiscoverySettings] = useState({
    scan_subnets: ['192.168.1.0/24', '192.168.0.0/24'],
    scan_ports: [80, 8080, 8081],
    timeout: 5000,
    concurrent_scans: 50
  })

  useEffect(() => {
    // Check initial discovery status
    checkDiscoveryStatus()

    // Listen for real-time discovery updates
    if (socket) {
      socket.on('discovery_status', handleDiscoveryStatus)
      socket.on('device_discovered', handleDeviceDiscovered)
      socket.on('discovery_progress', handleDiscoveryProgress)

      return () => {
        socket.off('discovery_status')
        socket.off('device_discovered')
        socket.off('discovery_progress')
      }
    }
  }, [socket])

  const checkDiscoveryStatus = async () => {
    try {
      const response = await api.get('/health')
      setDiscoveryActive(response.data.services?.discovery || false)
    } catch (error) {
      console.error('Failed to check discovery status:', error)
    }
  }

  const handleDiscoveryStatus = (data: { active: boolean }) => {
    setDiscoveryActive(data.active)
    if (!data.active) {
      setDiscoveryStats(prev => ({ ...prev, scan_progress: 0 }))
    }
  }

  const handleDeviceDiscovered = (data: { device: DiscoverableDevice }) => {
    setDiscoveredDevices(prev => {
      const existing = prev.find(d => d.ip === data.device.ip)
      if (existing) {
        return prev.map(d => d.ip === data.device.ip ? { ...data.device, status: 'existing' } : d)
      }
      return [...prev, { ...data.device, status: 'new' }]
    })

    if (autoRefresh) {
      refreshDevices()
    }
  }

  const handleDiscoveryProgress = (data: DiscoveryStats) => {
    setDiscoveryStats(data)
  }

  const startDiscovery = async () => {
    try {
      await api.post('/discovery/start')
      setDiscoveredDevices([])
      setDiscoveryStats({
        devices_found: 0,
        scan_progress: 0,
        current_subnet: '',
        time_elapsed: 0,
        estimated_remaining: 0
      })
    } catch (error) {
      console.error('Failed to start discovery:', error)
    }
  }

  const stopDiscovery = async () => {
    try {
      await api.post('/discovery/stop')
    } catch (error) {
      console.error('Failed to stop discovery:', error)
    }
  }

  const addDevice = async (device: DiscoverableDevice) => {
    try {
      const response = await api.post('/devices', {
        ip: device.ip,
        hostname: device.hostname,
        name: deviceName || device.hostname,
        mac: device.mac
      })

      if (response.data.success) {
        setDiscoveredDevices(prev =>
          prev.map(d => d.ip === device.ip ? { ...d, status: 'added' } : d)
        )
        setAddDeviceOpen(false)
        setDeviceName('')
        refreshDevices()
      }
    } catch (error) {
      console.error('Failed to add device:', error)
    }
  }

  const addManualDevice = async () => {
    try {
      const response = await api.post('/devices', {
        ip: deviceIp,
        name: deviceName,
        manual: true
      })

      if (response.data.success) {
        setManualAddOpen(false)
        setDeviceName('')
        setDeviceIp('')
        refreshDevices()
      }
    } catch (error) {
      console.error('Failed to add manual device:', error)
    }
  }

  const formatTimeRemaining = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
  }

  const getDeviceStatusColor = (status: string) => {
    switch (status) {
      case 'new': return 'primary'
      case 'existing': return 'default'
      case 'added': return 'success'
      default: return 'default'
    }
  }

  const getDeviceIcon = (device: DiscoverableDevice) => {
    if (device.services.includes('tasmota')) return <RouterIcon />
    if (device.services.includes('http')) return <NetworkIcon />
    return <DeviceIcon />
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          Device Discovery
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
            }
            label="Auto Refresh"
          />
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => setManualAddOpen(true)}
          >
            Add Manually
          </Button>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => {/* Open settings dialog */}}
          >
            Settings
          </Button>
        </Box>
      </Box>

      {/* Discovery Control */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Network Scan</Typography>
                <Chip
                  label={discoveryActive ? 'Active' : 'Stopped'}
                  color={discoveryActive ? 'success' : 'default'}
                  icon={discoveryActive ? <SearchIcon /> : <StopIcon />}
                />
              </Box>

              {discoveryActive && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">
                      Scanning: {discoveryStats.current_subnet}
                    </Typography>
                    <Typography variant="body2">
                      {discoveryStats.scan_progress.toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={discoveryStats.scan_progress} 
                    sx={{ mb: 1 }}
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">
                      Found: {discoveryStats.devices_found} devices
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      ETA: {formatTimeRemaining(discoveryStats.estimated_remaining)}
                    </Typography>
                  </Box>
                </Box>
              )}

              <Box sx={{ display: 'flex', gap: 2 }}>
                {!discoveryActive ? (
                  <Button
                    variant="contained"
                    startIcon={<SearchIcon />}
                    onClick={startDiscovery}
                    size="large"
                  >
                    Start Discovery
                  </Button>
                ) : (
                  <Button
                    variant="outlined"
                    startIcon={<StopIcon />}
                    onClick={stopDiscovery}
                    size="large"
                  >
                    Stop Discovery
                  </Button>
                )}
                <Button
                  variant="outlined"
                  startIcon={<RefreshIcon />}
                  onClick={refreshDevices}
                >
                  Refresh Devices
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Discovery Statistics
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>Total Found:</Typography>
                  <Typography fontWeight="bold">{discoveredDevices.length}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>New Devices:</Typography>
                  <Typography fontWeight="bold" color="primary.main">
                    {discoveredDevices.filter(d => d.status === 'new').length}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>Added:</Typography>
                  <Typography fontWeight="bold" color="success.main">
                    {discoveredDevices.filter(d => d.status === 'added').length}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>Time Elapsed:</Typography>
                  <Typography>{formatTimeRemaining(discoveryStats.time_elapsed)}</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Discovered Devices */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Discovered Devices ({discoveredDevices.length})
          </Typography>

          {discoveredDevices.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              {discoveryActive ? (
                <Box>
                  <CircularProgress sx={{ mb: 2 }} />
                  <Typography color="text.secondary">
                    Scanning network for devices...
                  </Typography>
                </Box>
              ) : (
                <Box>
                  <SearchIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography color="text.secondary">
                    No devices discovered yet. Start a network scan to find Tasmota devices.
                  </Typography>
                </Box>
              )}
            </Box>
          ) : (
            <List>
              {discoveredDevices.map((device, index) => (
                <React.Fragment key={device.ip}>
                  <ListItem>
                    <ListItemIcon>
                      {getDeviceIcon(device)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body1" fontWeight="bold">
                            {device.hostname || 'Unknown Device'}
                          </Typography>
                          <Chip
                            label={device.status}
                            size="small"
                            color={getDeviceStatusColor(device.status)}
                          />
                          {device.services.includes('tasmota') && (
                            <Chip
                              label="Tasmota"
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            IP: {device.ip} {device.mac && `• MAC: ${device.mac}`}
                          </Typography>
                          {device.firmware_version && (
                            <Typography variant="body2" color="text.secondary">
                              Firmware: {device.firmware_version}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary">
                            Discovered: {new Date(device.discovered_at).toLocaleString()}
                          </Typography>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      {device.status === 'new' && (
                        <Button
                          variant="contained"
                          size="small"
                          startIcon={<AddIcon />}
                          onClick={() => {
                            setSelectedDevice(device)
                            setAddDeviceOpen(true)
                          }}
                        >
                          Add
                        </Button>
                      )}
                      {device.status === 'added' && (
                        <Chip
                          label="Added"
                          color="success"
                          icon={<FoundIcon />}
                          size="small"
                        />
                      )}
                      {device.status === 'existing' && (
                        <Chip
                          label="Existing"
                          color="default"
                          size="small"
                        />
                      )}
                    </ListItemSecondaryAction>
                  </ListItem>
                  {index < discoveredDevices.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Add Device Dialog */}
      <Dialog
        open={addDeviceOpen}
        onClose={() => setAddDeviceOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Device</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              Adding device: {selectedDevice?.ip} ({selectedDevice?.hostname})
            </Alert>
            <TextField
              label="Device Name"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              fullWidth
              margin="normal"
              placeholder={selectedDevice?.hostname || 'Enter device name'}
              helperText="Leave empty to use hostname as name"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDeviceOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => selectedDevice && addDevice(selectedDevice)}
          >
            Add Device
          </Button>
        </DialogActions>
      </Dialog>

      {/* Manual Add Dialog */}
      <Dialog
        open={manualAddOpen}
        onClose={() => setManualAddOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Device Manually</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              label="Device IP Address"
              value={deviceIp}
              onChange={(e) => setDeviceIp(e.target.value)}
              fullWidth
              margin="normal"
              placeholder="192.168.1.100"
              required
            />
            <TextField
              label="Device Name"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              fullWidth
              margin="normal"
              placeholder="My Tasmota Device"
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setManualAddOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={addManualDevice}
            disabled={!deviceIp || !deviceName}
          >
            Add Device
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Discovery