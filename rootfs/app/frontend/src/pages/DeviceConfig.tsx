import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Switch,
  FormControlLabel,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  Chip,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material'
import {
  Wifi as WifiIcon,
  Router as RouterIcon,
  Settings as SettingsIcon,
  Save as SaveIcon,
  Backup as BackupIcon,
  Restore as RestoreIcon,
  Terminal as TerminalIcon,
  Memory as MemoryIcon,
  NetworkCheck as NetworkIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon
} from '@mui/icons-material'
import { useParams } from 'react-router-dom'
import api from '../services/api'

interface DeviceInfo {
  ip: string
  device_name: string
  friendly_name: string
  firmware_version: string
  hardware: string
  wifi_ssid: string
  wifi_rssi: number
  uptime: string
  heap_free: number
  online: boolean
}

interface DeviceTemplate {
  name: string
  gpio: number[]
  flag: number
  base: number
}

const DeviceConfig: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>()
  const [currentTab, setCurrentTab] = useState(0)
  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [saveLoading, setSaveLoading] = useState(false)
  const [templates, setTemplates] = useState<Record<string, DeviceTemplate>>({})
  const [commandResult, setCommandResult] = useState<any>(null)
  
  // Configuration states
  const [wifiConfig, setWifiConfig] = useState({
    ssid: '',
    password: '',
    ap_ssid: '',
    ap_password: ''
  })
  
  const [mqttConfig, setMqttConfig] = useState({
    mqtt_host: 'core-mosquitto',
    mqtt_port: 1883,
    mqtt_user: '',
    mqtt_pass: '',
    topic: ''
  })
  
  const [deviceNameConfig, setDeviceNameConfig] = useState({
    device_name: '',
    friendly_name: ''
  })
  
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [rawCommand, setRawCommand] = useState('')
  
  useEffect(() => {
    if (deviceId) {
      loadDeviceInfo()
      loadTemplates()
    }
  }, [deviceId])

  const loadDeviceInfo = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/devices/${deviceId}/config/info`)
      
      if (response.data?.success) {
        const info = response.data.device_info
        setDeviceInfo(info)
        
        // Pre-populate forms
        setWifiConfig(prev => ({
          ...prev,
          ssid: info.wifi_ssid || ''
        }))
        
        setDeviceNameConfig({
          device_name: info.device_name || '',
          friendly_name: info.friendly_name || ''
        })
        
        setMqttConfig(prev => ({
          ...prev,
          topic: info.device_name || ''
        }))
      }
    } catch (error) {
      console.error('Failed to load device info:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTemplates = async () => {
    try {
      const response = await api.get('/config/templates')
      if (response.data?.success) {
        setTemplates(response.data.templates)
      }
    } catch (error) {
      console.error('Failed to load templates:', error)
    }
  }

  const handleWifiSave = async () => {
    try {
      setSaveLoading(true)
      const response = await api.post(`/devices/${deviceId}/config/wifi`, wifiConfig)
      setCommandResult(response.data)
    } catch (error: any) {
      setCommandResult({ success: false, error: error.message })
    } finally {
      setSaveLoading(false)
    }
  }

  const handleMqttSave = async () => {
    try {
      setSaveLoading(true)
      const response = await api.post(`/devices/${deviceId}/config/mqtt`, mqttConfig)
      setCommandResult(response.data)
    } catch (error: any) {
      setCommandResult({ success: false, error: error.message })
    } finally {
      setSaveLoading(false)
    }
  }

  const handleNameSave = async () => {
    try {
      setSaveLoading(true)
      const response = await api.post(`/devices/${deviceId}/config/name`, deviceNameConfig)
      setCommandResult(response.data)
    } catch (error: any) {
      setCommandResult({ success: false, error: error.message })
    } finally {
      setSaveLoading(false)
    }
  }

  const handleTemplateApply = async () => {
    if (!selectedTemplate) return
    
    try {
      setSaveLoading(true)
      const response = await api.post(`/devices/${deviceId}/config/template`, {
        template_name: selectedTemplate
      })
      setCommandResult(response.data)
    } catch (error: any) {
      setCommandResult({ success: false, error: error.message })
    } finally {
      setSaveLoading(false)
    }
  }

  const handleRawCommand = async () => {
    if (!rawCommand) return
    
    try {
      setSaveLoading(true)
      const response = await api.post(`/devices/${deviceId}/config/command`, {
        command: rawCommand
      })
      setCommandResult(response.data)
    } catch (error: any) {
      setCommandResult({ success: false, error: error.message })
    } finally {
      setSaveLoading(false)
    }
  }

  const handleBackup = async () => {
    try {
      setSaveLoading(true)
      const response = await api.get(`/devices/${deviceId}/config/backup`)
      
      if (response.data?.success) {
        // Download backup as JSON file
        const backup = response.data.backup_data
        const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `tasmota-backup-${deviceInfo?.device_name || deviceId}-${new Date().toISOString().split('T')[0]}.json`
        a.click()
        URL.revokeObjectURL(url)
        
        setCommandResult({ success: true, messages: ['Configuration backup downloaded'] })
      }
    } catch (error: any) {
      setCommandResult({ success: false, error: error.message })
    } finally {
      setSaveLoading(false)
    }
  }

  const renderDeviceInfoCard = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Device Information
        </Typography>
        
        {deviceInfo ? (
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Device Name"
                value={deviceInfo.device_name}
                fullWidth
                disabled
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="IP Address"
                value={deviceInfo.ip}
                fullWidth
                disabled
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Firmware Version"
                value={deviceInfo.firmware_version}
                fullWidth
                disabled
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Hardware"
                value={deviceInfo.hardware}
                fullWidth
                disabled
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="WiFi SSID"
                value={deviceInfo.wifi_ssid}
                fullWidth
                disabled
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="WiFi Signal"
                value={`${deviceInfo.wifi_rssi} dBm`}
                fullWidth
                disabled
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Uptime"
                value={deviceInfo.uptime}
                fullWidth
                disabled
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Free Memory"
                value={`${Math.round(deviceInfo.heap_free / 1024)} KB`}
                fullWidth
                disabled
                variant="outlined"
                size="small"
              />
            </Grid>
          </Grid>
        ) : (
          <CircularProgress />
        )}
      </CardContent>
    </Card>
  )

  const renderWifiConfig = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          <WifiIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          WiFi Configuration
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              label="WiFi SSID"
              value={wifiConfig.ssid}
              onChange={(e) => setWifiConfig(prev => ({ ...prev, ssid: e.target.value }))}
              fullWidth
              variant="outlined"
              required
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="WiFi Password"
              type="password"
              value={wifiConfig.password}
              onChange={(e) => setWifiConfig(prev => ({ ...prev, password: e.target.value }))}
              fullWidth
              variant="outlined"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="AP SSID (Fallback)"
              value={wifiConfig.ap_ssid}
              onChange={(e) => setWifiConfig(prev => ({ ...prev, ap_ssid: e.target.value }))}
              fullWidth
              variant="outlined"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="AP Password (Fallback)"
              type="password"
              value={wifiConfig.ap_password}
              onChange={(e) => setWifiConfig(prev => ({ ...prev, ap_password: e.target.value }))}
              fullWidth
              variant="outlined"
            />
          </Grid>
        </Grid>
        
        <Box sx={{ mt: 2 }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleWifiSave}
            disabled={saveLoading || !wifiConfig.ssid}
          >
            Save WiFi Settings
          </Button>
        </Box>
      </CardContent>
    </Card>
  )

  const renderMqttConfig = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          <RouterIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          MQTT Configuration
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              label="MQTT Host"
              value={mqttConfig.mqtt_host}
              onChange={(e) => setMqttConfig(prev => ({ ...prev, mqtt_host: e.target.value }))}
              fullWidth
              variant="outlined"
              required
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="MQTT Port"
              type="number"
              value={mqttConfig.mqtt_port}
              onChange={(e) => setMqttConfig(prev => ({ ...prev, mqtt_port: parseInt(e.target.value) }))}
              fullWidth
              variant="outlined"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="MQTT Username"
              value={mqttConfig.mqtt_user}
              onChange={(e) => setMqttConfig(prev => ({ ...prev, mqtt_user: e.target.value }))}
              fullWidth
              variant="outlined"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="MQTT Password"
              type="password"
              value={mqttConfig.mqtt_pass}
              onChange={(e) => setMqttConfig(prev => ({ ...prev, mqtt_pass: e.target.value }))}
              fullWidth
              variant="outlined"
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Device Topic"
              value={mqttConfig.topic}
              onChange={(e) => setMqttConfig(prev => ({ ...prev, topic: e.target.value }))}
              fullWidth
              variant="outlined"
              helperText="Leave empty to use device name"
            />
          </Grid>
        </Grid>
        
        <Box sx={{ mt: 2 }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleMqttSave}
            disabled={saveLoading || !mqttConfig.mqtt_host}
          >
            Save MQTT Settings
          </Button>
        </Box>
      </CardContent>
    </Card>
  )

  const renderDeviceNames = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          <SettingsIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Device Names
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Device Name"
              value={deviceNameConfig.device_name}
              onChange={(e) => setDeviceNameConfig(prev => ({ ...prev, device_name: e.target.value }))}
              fullWidth
              variant="outlined"
              required
              helperText="Used for MQTT topic and hostname"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              label="Friendly Name"
              value={deviceNameConfig.friendly_name}
              onChange={(e) => setDeviceNameConfig(prev => ({ ...prev, friendly_name: e.target.value }))}
              fullWidth
              variant="outlined"
              helperText="Display name for the device"
            />
          </Grid>
        </Grid>
        
        <Box sx={{ mt: 2 }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleNameSave}
            disabled={saveLoading || !deviceNameConfig.device_name}
          >
            Save Device Names
          </Button>
        </Box>
      </CardContent>
    </Card>
  )

  const renderTemplates = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          <MemoryIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Device Templates (GPIO Configuration)
        </Typography>
        
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Device Template</InputLabel>
          <Select
            value={selectedTemplate}
            onChange={(e) => setSelectedTemplate(e.target.value)}
            label="Device Template"
          >
            {Object.entries(templates).map(([key, template]) => (
              <MenuItem key={key} value={key}>
                {template.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        {selectedTemplate && templates[selectedTemplate] && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Template:</strong> {templates[selectedTemplate].name}
            </Typography>
            <Typography variant="body2">
              <strong>Base:</strong> {templates[selectedTemplate].base}
            </Typography>
            <Typography variant="body2">
              <strong>Note:</strong> Applying this template will restart the device and configure GPIO pins.
            </Typography>
          </Alert>
        )}
        
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleTemplateApply}
          disabled={saveLoading || !selectedTemplate}
        >
          Apply Template
        </Button>
      </CardContent>
    </Card>
  )

  const renderConsole = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          <TerminalIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Console Commands
        </Typography>
        
        <TextField
          label="Tasmota Command"
          value={rawCommand}
          onChange={(e) => setRawCommand(e.target.value)}
          fullWidth
          variant="outlined"
          placeholder="e.g., Status, Power, Restart"
          sx={{ mb: 2 }}
        />
        
        <Button
          variant="contained"
          startIcon={<TerminalIcon />}
          onClick={handleRawCommand}
          disabled={saveLoading || !rawCommand}
          sx={{ mb: 2 }}
        >
          Send Command
        </Button>
        
        <Divider sx={{ my: 2 }} />
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<BackupIcon />}
            onClick={handleBackup}
            disabled={saveLoading}
          >
            Backup Config
          </Button>
        </Box>
      </CardContent>
    </Card>
  )

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
        Device Configuration
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Configure your Tasmota device like Tasmotizer
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          {renderDeviceInfoCard()}
        </Grid>
        
        <Grid item xs={12} md={6}>
          {renderWifiConfig()}
        </Grid>
        
        <Grid item xs={12} md={6}>
          {renderMqttConfig()}
        </Grid>
        
        <Grid item xs={12} md={6}>
          {renderDeviceNames()}
        </Grid>
        
        <Grid item xs={12} md={6}>
          {renderTemplates()}
        </Grid>
        
        <Grid item xs={12}>
          {renderConsole()}
        </Grid>
      </Grid>

      {/* Result Dialog */}
      <Dialog
        open={Boolean(commandResult)}
        onClose={() => setCommandResult(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {commandResult?.success ? (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <SuccessIcon color="success" sx={{ mr: 1 }} />
              Command Successful
            </Box>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <ErrorIcon color="error" sx={{ mr: 1 }} />
              Command Failed
            </Box>
          )}
        </DialogTitle>
        <DialogContent>
          {commandResult?.messages && (
            <List>
              {commandResult.messages.map((message: string, index: number) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <SuccessIcon color="success" />
                  </ListItemIcon>
                  <ListItemText primary={message} />
                </ListItem>
              ))}
            </List>
          )}
          
          {commandResult?.error && (
            <Alert severity="error">
              {commandResult.error}
            </Alert>
          )}
          
          {commandResult?.response && (
            <Paper sx={{ p: 2, mt: 2, backgroundColor: 'grey.50' }}>
              <Typography variant="body2" fontFamily="monospace">
                {JSON.stringify(commandResult.response, null, 2)}
              </Typography>
            </Paper>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommandResult(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DeviceConfig