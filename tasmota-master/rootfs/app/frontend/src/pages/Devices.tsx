import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Grid,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  IconButton,
  Menu,
  Tooltip,
  Badge,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Fab,
  Divider
} from '@mui/material'
import {
  MoreVert as MoreIcon,
  PowerSettingsNew as PowerIcon,
  Settings as SettingsIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Router as RouterIcon,
  Wifi as WifiIcon,
  Memory as MemoryIcon,
  Schedule as ScheduleIcon,
  Add as AddIcon,
  Search as SearchIcon,
  Tune as ConfigureIcon
} from '@mui/icons-material'
import { useDevices } from '../contexts/DeviceContext'
import { useSocket } from '../contexts/SocketContext'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

interface Device {
  id: string
  name: string
  hostname: string
  ip: string
  mac: string
  online: boolean
  firmware_version: string
  hardware: string
  template: string
  last_seen: string
  uptime: number
  rssi: number
  free_memory: number
  status: Record<string, any>
}

const Devices: React.FC = () => {
  const { devices, devicesLoading, refreshDevices } = useDevices()
  const deviceArray = Object.values(devices)
  const { socket } = useSocket()
  const navigate = useNavigate()
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null)
  const [deviceDetailOpen, setDeviceDetailOpen] = useState(false)
  const [commandDialogOpen, setCommandDialogOpen] = useState(false)
  const [command, setCommand] = useState('')
  const [commandParams, setCommandParams] = useState('')
  const [commandLoading, setCommandLoading] = useState(false)
  const [commandResult, setCommandResult] = useState<any>(null)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [menuDevice, setMenuDevice] = useState<Device | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingDevice, setEditingDevice] = useState<Partial<Device>>({})

  useEffect(() => {
    // Listen for real-time device updates
    if (socket) {
      socket.on('device_update', (data: { device_id: string; device: Device }) => {
        console.log('Device updated:', data)
        refreshDevices()
      })

      socket.on('device_discovered', (data: { device: Device }) => {
        console.log('New device discovered:', data)
        refreshDevices()
      })

      return () => {
        socket.off('device_update')
        socket.off('device_discovered')
      }
    }
  }, [socket, refreshDevices])

  const handleDeviceClick = (device: Device) => {
    setSelectedDevice(device)
    setDeviceDetailOpen(true)
  }

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, device: Device) => {
    event.stopPropagation()
    setAnchorEl(event.currentTarget)
    setMenuDevice(device)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    setMenuDevice(null)
  }

  const handleSendCommand = async () => {
    if (!selectedDevice || !command) return

    setCommandLoading(true)
    try {
      const params = commandParams ? JSON.parse(commandParams) : {}
      const response = await api.post(`/devices/${selectedDevice.id}/command`, {
        command,
        params
      })
      setCommandResult(response.data)
    } catch (error: any) {
      setCommandResult({ success: false, error: error.message })
    } finally {
      setCommandLoading(false)
    }
  }

  const handleToggleDevice = async (device: Device) => {
    try {
      await api.post(`/devices/${device.id}/command`, {
        command: 'Power',
        params: { toggle: true }
      })
      refreshDevices()
    } catch (error) {
      console.error('Failed to toggle device:', error)
    }
    handleMenuClose()
  }

  const handleRestartDevice = async (device: Device) => {
    try {
      await api.post(`/devices/${device.id}/command`, {
        command: 'Restart',
        params: {}
      })
      refreshDevices()
    } catch (error) {
      console.error('Failed to restart device:', error)
    }
    handleMenuClose()
  }

  const handleEditDevice = (device: Device) => {
    setEditingDevice(device)
    setEditDialogOpen(true)
    handleMenuClose()
  }

  const handleSaveDevice = async () => {
    if (!editingDevice.id) return

    try {
      // API call to update device would go here
      console.log('Saving device:', editingDevice)
      setEditDialogOpen(false)
      refreshDevices()
    } catch (error) {
      console.error('Failed to save device:', error)
    }
  }

  const getStatusColor = (online: boolean) => {
    return online ? 'success' : 'default'
  }

  const getSignalStrength = (rssi: number) => {
    if (rssi > -50) return { strength: 'Excellent', color: 'success' }
    if (rssi > -60) return { strength: 'Good', color: 'info' }
    if (rssi > -70) return { strength: 'Fair', color: 'warning' }
    return { strength: 'Poor', color: 'error' }
  }

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (days > 0) return `${days}d ${hours}h`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          Devices
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={refreshDevices}
            disabled={devicesLoading}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<SearchIcon />}
            href="/discovery"
          >
            Discover
          </Button>
        </Box>
      </Box>

      {devicesLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : deviceArray.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <RouterIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No devices found
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Start device discovery to find Tasmota devices on your network
            </Typography>
            <Button variant="contained" href="/discovery" startIcon={<SearchIcon />}>
              Start Discovery
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {deviceArray.map((device) => (
            <Grid item xs={12} sm={6} md={4} key={device.id}>
              <Card 
                sx={{ 
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: 4
                  }
                }}
                onClick={() => handleDeviceClick(device)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="h6" noWrap>
                        {device.name || device.hostname}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" fontFamily="monospace">
                        {device.ip}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={device.online ? 'Online' : 'Offline'}
                        color={getStatusColor(device.online)}
                        size="small"
                      />
                      <IconButton
                        size="small"
                        onClick={(e) => handleMenuClick(e, device)}
                      >
                        <MoreIcon />
                      </IconButton>
                    </Box>
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">
                        Firmware:
                      </Typography>
                      <Typography variant="body2">
                        {device.firmware_version || 'Unknown'}
                      </Typography>
                    </Box>

                    {device.rssi && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="text.secondary">
                          Signal:
                        </Typography>
                        <Chip
                          label={`${device.rssi}dBm`}
                          color={getSignalStrength(device.rssi).color as any}
                          size="small"
                          icon={<WifiIcon />}
                        />
                      </Box>
                    )}

                    {device.uptime && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="text.secondary">
                          Uptime:
                        </Typography>
                        <Typography variant="body2">
                          {formatUptime(device.uptime)}
                        </Typography>
                      </Box>
                    )}

                    {device.free_memory && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="text.secondary">
                          Free Memory:
                        </Typography>
                        <Typography variant="body2">
                          {Math.round(device.free_memory / 1024)}KB
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </CardContent>

                <CardActions>
                  <Button
                    size="small"
                    startIcon={<InfoIcon />}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeviceClick(device)
                    }}
                  >
                    Details
                  </Button>
                  <Button
                    size="small"
                    startIcon={<SettingsIcon />}
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedDevice(device)
                      setCommandDialogOpen(true)
                    }}
                  >
                    Control
                  </Button>
                  <Button
                    size="small"
                    startIcon={<ConfigureIcon />}
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/devices/${device.id}/config`)
                    }}
                  >
                    Configure
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Device Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => menuDevice && handleToggleDevice(menuDevice)}>
          <PowerIcon sx={{ mr: 1 }} />
          Toggle Power
        </MenuItem>
        <MenuItem onClick={() => menuDevice && handleEditDevice(menuDevice)}>
          <EditIcon sx={{ mr: 1 }} />
          Edit Device
        </MenuItem>
        <MenuItem onClick={() => menuDevice && handleRestartDevice(menuDevice)}>
          <RefreshIcon sx={{ mr: 1 }} />
          Restart
        </MenuItem>
        <MenuItem onClick={() => {
          if (menuDevice) {
            navigate(`/devices/${menuDevice.id}/config`)
            handleMenuClose()
          }
        }}>
          <ConfigureIcon sx={{ mr: 1 }} />
          Configure Device
        </MenuItem>
      </Menu>

      {/* Device Detail Dialog */}
      <Dialog
        open={deviceDetailOpen}
        onClose={() => setDeviceDetailOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Device Details: {selectedDevice?.name || selectedDevice?.hostname}
        </DialogTitle>
        <DialogContent>
          {selectedDevice && (
            <Box sx={{ pt: 1 }}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Name"
                    value={selectedDevice.name || ''}
                    fullWidth
                    disabled
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="IP Address"
                    value={selectedDevice.ip}
                    fullWidth
                    disabled
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="MAC Address"
                    value={selectedDevice.mac || 'Unknown'}
                    fullWidth
                    disabled
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Firmware Version"
                    value={selectedDevice.firmware_version || 'Unknown'}
                    fullWidth
                    disabled
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Hardware"
                    value={selectedDevice.hardware || 'Unknown'}
                    fullWidth
                    disabled
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Template"
                    value={selectedDevice.template || 'None'}
                    fullWidth
                    disabled
                    variant="outlined"
                  />
                </Grid>
              </Grid>

              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Status Information
                </Typography>
                <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
                  <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(selectedDevice.status || {}, null, 2)}
                  </pre>
                </Paper>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeviceDetailOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              setDeviceDetailOpen(false)
              setCommandDialogOpen(true)
            }}
          >
            Send Command
          </Button>
        </DialogActions>
      </Dialog>

      {/* Command Dialog */}
      <Dialog
        open={commandDialogOpen}
        onClose={() => setCommandDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Send Command: {selectedDevice?.name || selectedDevice?.hostname}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              label="Command"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              fullWidth
              margin="normal"
              placeholder="e.g., Power, Status, Restart"
            />
            <TextField
              label="Parameters (JSON)"
              value={commandParams}
              onChange={(e) => setCommandParams(e.target.value)}
              fullWidth
              multiline
              rows={3}
              margin="normal"
              placeholder='e.g., {"toggle": true}'
            />

            {commandResult && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Result:
                </Typography>
                <Paper sx={{ p: 2, backgroundColor: commandResult.success ? 'success.light' : 'error.light' }}>
                  <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(commandResult, null, 2)}
                  </pre>
                </Paper>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommandDialogOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={handleSendCommand}
            disabled={commandLoading || !command}
          >
            {commandLoading ? <CircularProgress size={20} /> : 'Send Command'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Device Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Device</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              label="Device Name"
              value={editingDevice.name || ''}
              onChange={(e) => setEditingDevice({ ...editingDevice, name: e.target.value })}
              fullWidth
              margin="normal"
            />
            <TextField
              label="Hostname"
              value={editingDevice.hostname || ''}
              onChange={(e) => setEditingDevice({ ...editingDevice, hostname: e.target.value })}
              fullWidth
              margin="normal"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveDevice}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Devices