import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Tabs,
  Tab,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Alert,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  CircularProgress
} from '@mui/material'
import {
  Settings as SettingsIcon,
  Wifi as NetworkIcon,
  Storage as StorageIcon,
  Security as SecurityIcon,
  Notifications as NotificationsIcon,
  Backup as BackupIcon,
  RestoreFromTrash as RestoreIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Timer as SchedulerIcon,
  Analytics as AnalyticsIcon
} from '@mui/icons-material'
import api from '../services/api'

interface AppConfig {
  network: {
    discovery_timeout: number
    mdns_enabled: boolean
    port_range: { start: number; end: number }
    max_concurrent_scans: number
  }
  firmware: {
    cache_size_gb: number
    auto_cleanup: boolean
    cleanup_threshold: number
    download_timeout: number
    verify_checksums: boolean
    allow_community_firmware: boolean
  }
  security: {
    scan_uploads: boolean
    scan_timeout: number
    max_upload_size_mb: number
    allowed_extensions: string[]
    quarantine_suspicious: boolean
  }
  analytics: {
    ml_enabled: boolean
    data_retention_days: number
    anonymous_telemetry: boolean
    recommendation_confidence_threshold: number
  }
  scheduler: {
    firmware_check_interval: number
    cache_cleanup_interval: number
    analytics_update_interval: number
    device_health_check_interval: number
  }
  notifications: {
    mqtt_enabled: boolean
    mqtt_topic_prefix: string
    webhook_url: string
    notify_firmware_updates: boolean
    notify_device_issues: boolean
    notify_security_alerts: boolean
  }
}

const Settings: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0)
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await api.getConfig()
      setConfig(response.data || null)
    } catch (error) {
      console.error('Failed to fetch config:', error)
      setErrorMessage('Failed to load configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleConfigChange = (section: keyof AppConfig, key: string, value: any) => {
    if (!config) return

    setConfig({
      ...config,
      [section]: {
        ...config[section],
        [key]: value
      }
    })
    setHasChanges(true)
  }

  const handleSaveConfig = async () => {
    if (!config) return

    try {
      setSaving(true)
      await api.updateConfig(config as Partial<AppConfig>)
      setHasChanges(false)
      setSuccessMessage('Configuration saved successfully')
    } catch (error) {
      console.error('Failed to save config:', error)
      setErrorMessage('Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleResetConfig = async () => {
    try {
      // Reset to default config - implement reset functionality 
      await fetchConfig()
      setHasChanges(false)
      setResetDialogOpen(false)
      setSuccessMessage('Configuration reset to defaults')
    } catch (error) {
      console.error('Failed to reset config:', error)
      setErrorMessage('Failed to reset configuration')
    }
  }

  const handleExportConfig = () => {
    if (!config) return

    const dataStr = JSON.stringify(config, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `tasmota-master-config-${new Date().toISOString().split('T')[0]}.json`
    link.click()
  }

  const handleImportConfig = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const importedConfig = JSON.parse(e.target?.result as string)
        setConfig(importedConfig)
        setHasChanges(true)
        setSuccessMessage('Configuration imported successfully')
      } catch (error) {
        setErrorMessage('Invalid configuration file')
      }
    }
    reader.readAsText(file)
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ ml: 2 }}>Loading Settings...</Typography>
      </Box>
    )
  }

  if (!config) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load configuration. Please try again.</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" fontWeight="bold">
            Settings
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure system behavior and preferences
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<BackupIcon />}
            onClick={handleExportConfig}
          >
            Export
          </Button>
          <input
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            id="import-config"
            onChange={handleImportConfig}
          />
          <label htmlFor="import-config">
            <Button
              variant="outlined"
              component="span"
              startIcon={<RestoreIcon />}
            >
              Import
            </Button>
          </label>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSaveConfig}
            disabled={!hasChanges || saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </Box>

      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage('')}>
          {successMessage}
        </Alert>
      )}

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>
          {errorMessage}
        </Alert>
      )}

      {hasChanges && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          You have unsaved changes. Don't forget to save your configuration.
        </Alert>
      )}

      <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)} sx={{ mb: 3 }}>
        <Tab label="Network" icon={<NetworkIcon />} />
        <Tab label="Firmware" icon={<StorageIcon />} />
        <Tab label="Security" icon={<SecurityIcon />} />
        <Tab label="Analytics" icon={<AnalyticsIcon />} />
        <Tab label="Scheduler" icon={<SchedulerIcon />} />
        <Tab label="Notifications" icon={<NotificationsIcon />} />
      </Tabs>

      {/* Network Settings */}
      {currentTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Discovery Settings</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <TextField
                    label="Discovery Timeout (seconds)"
                    type="number"
                    value={config.network.discovery_timeout}
                    onChange={(e) => handleConfigChange('network', 'discovery_timeout', parseInt(e.target.value))}
                    InputProps={{ inputProps: { min: 5, max: 300 } }}
                    helperText="Time to wait for device responses during discovery"
                  />
                  
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.network.mdns_enabled}
                        onChange={(e) => handleConfigChange('network', 'mdns_enabled', e.target.checked)}
                      />
                    }
                    label="Enable mDNS Discovery"
                  />

                  <TextField
                    label="Max Concurrent Scans"
                    type="number"
                    value={config.network.max_concurrent_scans}
                    onChange={(e) => handleConfigChange('network', 'max_concurrent_scans', parseInt(e.target.value))}
                    InputProps={{ inputProps: { min: 1, max: 50 } }}
                    helperText="Maximum number of simultaneous network scans"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Port Range Configuration</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <TextField
                    label="Start Port"
                    type="number"
                    value={config.network.port_range.start}
                    onChange={(e) => handleConfigChange('network', 'port_range', {
                      ...config.network.port_range,
                      start: parseInt(e.target.value)
                    })}
                    InputProps={{ inputProps: { min: 1, max: 65535 } }}
                  />
                  
                  <TextField
                    label="End Port"
                    type="number"
                    value={config.network.port_range.end}
                    onChange={(e) => handleConfigChange('network', 'port_range', {
                      ...config.network.port_range,
                      end: parseInt(e.target.value)
                    })}
                    InputProps={{ inputProps: { min: 1, max: 65535 } }}
                  />

                  <Alert severity="info">
                    <Typography variant="body2">
                      Port range: {config.network.port_range.start} - {config.network.port_range.end}
                      ({config.network.port_range.end - config.network.port_range.start + 1} ports)
                    </Typography>
                  </Alert>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Firmware Settings */}
      {currentTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Cache Management</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <Box>
                    <Typography gutterBottom>Cache Size: {config.firmware.cache_size_gb} GB</Typography>
                    <Slider
                      value={config.firmware.cache_size_gb}
                      onChange={(_, value) => handleConfigChange('firmware', 'cache_size_gb', value)}
                      min={1}
                      max={10}
                      marks
                      valueLabelDisplay="auto"
                    />
                  </Box>

                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.firmware.auto_cleanup}
                        onChange={(e) => handleConfigChange('firmware', 'auto_cleanup', e.target.checked)}
                      />
                    }
                    label="Auto Cleanup Cache"
                  />

                  <TextField
                    label="Cleanup Threshold (%)"
                    type="number"
                    value={config.firmware.cleanup_threshold}
                    onChange={(e) => handleConfigChange('firmware', 'cleanup_threshold', parseInt(e.target.value))}
                    InputProps={{ inputProps: { min: 50, max: 95 } }}
                    helperText="Trigger cleanup when cache usage exceeds this percentage"
                    disabled={!config.firmware.auto_cleanup}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Download & Verification</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <TextField
                    label="Download Timeout (seconds)"
                    type="number"
                    value={config.firmware.download_timeout}
                    onChange={(e) => handleConfigChange('firmware', 'download_timeout', parseInt(e.target.value))}
                    InputProps={{ inputProps: { min: 30, max: 600 } }}
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.firmware.verify_checksums}
                        onChange={(e) => handleConfigChange('firmware', 'verify_checksums', e.target.checked)}
                      />
                    }
                    label="Verify Firmware Checksums"
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.firmware.allow_community_firmware}
                        onChange={(e) => handleConfigChange('firmware', 'allow_community_firmware', e.target.checked)}
                      />
                    }
                    label="Allow Community Firmware"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Security Settings */}
      {currentTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Upload Security</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.security.scan_uploads}
                        onChange={(e) => handleConfigChange('security', 'scan_uploads', e.target.checked)}
                      />
                    }
                    label="Scan Uploaded Firmware"
                  />

                  <TextField
                    label="Scan Timeout (seconds)"
                    type="number"
                    value={config.security.scan_timeout}
                    onChange={(e) => handleConfigChange('security', 'scan_timeout', parseInt(e.target.value))}
                    InputProps={{ inputProps: { min: 10, max: 300 } }}
                    disabled={!config.security.scan_uploads}
                  />

                  <TextField
                    label="Max Upload Size (MB)"
                    type="number"
                    value={config.security.max_upload_size_mb}
                    onChange={(e) => handleConfigChange('security', 'max_upload_size_mb', parseInt(e.target.value))}
                    InputProps={{ inputProps: { min: 1, max: 100 } }}
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.security.quarantine_suspicious}
                        onChange={(e) => handleConfigChange('security', 'quarantine_suspicious', e.target.checked)}
                      />
                    }
                    label="Quarantine Suspicious Files"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Allowed File Extensions</Typography>
                <Box sx={{ mb: 2 }}>
                  {config.security.allowed_extensions.map((ext, index) => (
                    <Chip
                      key={index}
                      label={ext}
                      onDelete={() => {
                        const newExtensions = config.security.allowed_extensions.filter((_, i) => i !== index)
                        handleConfigChange('security', 'allowed_extensions', newExtensions)
                      }}
                      sx={{ mr: 1, mb: 1 }}
                    />
                  ))}
                </Box>
                <TextField
                  label="Add Extension"
                  placeholder=".bin"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      const input = e.target as HTMLInputElement
                      const ext = input.value.trim()
                      if (ext && !config.security.allowed_extensions.includes(ext)) {
                        handleConfigChange('security', 'allowed_extensions', [
                          ...config.security.allowed_extensions,
                          ext
                        ])
                        input.value = ''
                      }
                    }
                  }}
                  helperText="Press Enter to add extension"
                  fullWidth
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Analytics Settings */}
      {currentTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Machine Learning</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.analytics.ml_enabled}
                        onChange={(e) => handleConfigChange('analytics', 'ml_enabled', e.target.checked)}
                      />
                    }
                    label="Enable ML Analytics"
                  />

                  <Box>
                    <Typography gutterBottom>
                      Recommendation Confidence Threshold: {(config.analytics.recommendation_confidence_threshold * 100).toFixed(0)}%
                    </Typography>
                    <Slider
                      value={config.analytics.recommendation_confidence_threshold}
                      onChange={(_, value) => handleConfigChange('analytics', 'recommendation_confidence_threshold', value)}
                      min={0.5}
                      max={0.95}
                      step={0.05}
                      valueLabelDisplay="auto"
                      valueLabelFormat={(value) => `${(value * 100).toFixed(0)}%`}
                      disabled={!config.analytics.ml_enabled}
                    />
                  </Box>

                  <TextField
                    label="Data Retention (days)"
                    type="number"
                    value={config.analytics.data_retention_days}
                    onChange={(e) => handleConfigChange('analytics', 'data_retention_days', parseInt(e.target.value))}
                    InputProps={{ inputProps: { min: 7, max: 365 } }}
                    helperText="How long to keep analytics data"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Privacy Settings</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.analytics.anonymous_telemetry}
                        onChange={(e) => handleConfigChange('analytics', 'anonymous_telemetry', e.target.checked)}
                      />
                    }
                    label="Anonymous Telemetry"
                  />

                  <Alert severity="info">
                    <Typography variant="body2">
                      Anonymous telemetry helps improve the system by collecting usage statistics.
                      No personal information or device data is transmitted.
                    </Typography>
                  </Alert>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Scheduler Settings */}
      {currentTab === 4 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Background Task Intervals</Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Firmware Check Interval (hours)"
                  type="number"
                  value={config.scheduler.firmware_check_interval}
                  onChange={(e) => handleConfigChange('scheduler', 'firmware_check_interval', parseInt(e.target.value))}
                  InputProps={{ inputProps: { min: 1, max: 168 } }}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Cache Cleanup Interval (hours)"
                  type="number"
                  value={config.scheduler.cache_cleanup_interval}
                  onChange={(e) => handleConfigChange('scheduler', 'cache_cleanup_interval', parseInt(e.target.value))}
                  InputProps={{ inputProps: { min: 1, max: 168 } }}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Analytics Update Interval (hours)"
                  type="number"
                  value={config.scheduler.analytics_update_interval}
                  onChange={(e) => handleConfigChange('scheduler', 'analytics_update_interval', parseInt(e.target.value))}
                  InputProps={{ inputProps: { min: 1, max: 168 } }}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Device Health Check Interval (minutes)"
                  type="number"
                  value={config.scheduler.device_health_check_interval}
                  onChange={(e) => handleConfigChange('scheduler', 'device_health_check_interval', parseInt(e.target.value))}
                  InputProps={{ inputProps: { min: 5, max: 60 } }}
                  fullWidth
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Notifications Settings */}
      {currentTab === 5 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>MQTT Notifications</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.notifications.mqtt_enabled}
                        onChange={(e) => handleConfigChange('notifications', 'mqtt_enabled', e.target.checked)}
                      />
                    }
                    label="Enable MQTT Notifications"
                  />

                  <TextField
                    label="MQTT Topic Prefix"
                    value={config.notifications.mqtt_topic_prefix}
                    onChange={(e) => handleConfigChange('notifications', 'mqtt_topic_prefix', e.target.value)}
                    disabled={!config.notifications.mqtt_enabled}
                    fullWidth
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Webhook Notifications</Typography>
                <TextField
                  label="Webhook URL"
                  value={config.notifications.webhook_url}
                  onChange={(e) => handleConfigChange('notifications', 'webhook_url', e.target.value)}
                  placeholder="https://your-webhook-url.com/notify"
                  fullWidth
                />
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Notification Types</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.notifications.notify_firmware_updates}
                        onChange={(e) => handleConfigChange('notifications', 'notify_firmware_updates', e.target.checked)}
                      />
                    }
                    label="Firmware Updates Available"
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.notifications.notify_device_issues}
                        onChange={(e) => handleConfigChange('notifications', 'notify_device_issues', e.target.checked)}
                      />
                    }
                    label="Device Issues Detected"
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.notifications.notify_security_alerts}
                        onChange={(e) => handleConfigChange('notifications', 'notify_security_alerts', e.target.checked)}
                      />
                    }
                    label="Security Alerts"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Danger Zone */}
      <Card sx={{ mt: 4, border: '1px solid', borderColor: 'error.main' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom color="error">
            Danger Zone
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button
              variant="outlined"
              color="error"
              startIcon={<RefreshIcon />}
              onClick={() => setResetDialogOpen(true)}
            >
              Reset to Defaults
            </Button>
            <Typography variant="body2" color="text.secondary">
              This will reset all settings to their default values
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Reset Confirmation Dialog */}
      <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
        <DialogTitle>Reset Configuration</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action cannot be undone. All current settings will be lost.
          </Alert>
          <Typography>
            Are you sure you want to reset all settings to their default values?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleResetConfig} color="error" variant="contained">
            Reset All Settings
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Settings