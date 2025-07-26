import React, { useState, useEffect } from 'react'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  IconButton,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  CircularProgress,
  Badge
} from '@mui/material'
import {
  Devices as DevicesIcon,
  Router as FirmwareIcon,
  Cloud as CloudIcon,
  Speed as SpeedIcon,
  Warning as WarningIcon,
  CheckCircle as HealthyIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon
} from '@mui/icons-material'
import { useSocket } from '../contexts/SocketContext'
import { useDevices } from '../contexts/DeviceContext'
import api from '../services/api'

interface SystemMetrics {
  cpu: { value: number; status: string; unit: string }
  memory: { value: number; status: string; unit: string }
  disk: { value: number; status: string; unit: string }
}

interface HealthStatus {
  overall_status: string
  services: Record<string, any>
  dependencies: any
  uptime_seconds: number
  system_metrics: SystemMetrics
}

const Dashboard: React.FC = () => {
  const { socket, connected } = useSocket()
  const { devices, devicesLoading } = useDevices()
  const deviceArray = Object.values(devices)
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  useEffect(() => {
    fetchHealthStatus()
    const interval = setInterval(fetchHealthStatus, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchHealthStatus = async () => {
    try {
      const response = await api.get('/health/comprehensive')
      setHealthStatus(response.data)
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to fetch health status:', error)
    } finally {
      setHealthLoading(false)
    }
  }

  const getStatusColor = (status: string): 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' | 'inherit' => {
    switch (status) {
      case 'healthy':
        return 'success'
      case 'degraded':
        return 'warning'
      case 'critical':
      case 'unhealthy':
        return 'error'
      default:
        return 'primary'
    }
  }

  const getChipColor = (status: string): 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' | 'default' => {
    switch (status) {
      case 'healthy':
        return 'success'
      case 'degraded':
        return 'warning'
      case 'critical':
      case 'unhealthy':
        return 'error'
      default:
        return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <HealthyIcon color="success" />
      case 'degraded':
        return <WarningIcon color="warning" />
      case 'critical':
      case 'unhealthy':
        return <ErrorIcon color="error" />
      default:
        return <CircularProgress size={20} />
    }
  }

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          Dashboard
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </Typography>
          <IconButton onClick={fetchHealthStatus} disabled={healthLoading}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Connection Status Alert */}
      {!connected && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          WebSocket connection lost. Real-time updates are disabled.
        </Alert>
      )}

      {/* Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* System Health */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {healthLoading ? (
                  <CircularProgress size={40} />
                ) : (
                  getStatusIcon(healthStatus?.overall_status || 'unknown')
                )}
                <Box>
                  <Typography variant="h6">System Health</Typography>
                  <Chip
                    label={healthStatus?.overall_status || 'Loading...'}
                    color={getChipColor(healthStatus?.overall_status || 'default')}
                    size="small"
                  />
                </Box>
              </Box>
              {healthStatus && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Uptime: {formatUptime(healthStatus.uptime_seconds)}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Device Count */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Badge badgeContent={deviceArray.length} color="primary">
                  <DevicesIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                </Badge>
                <Box>
                  <Typography variant="h6">Devices</Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {devicesLoading ? '...' : deviceArray.length}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Firmware Status */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <FirmwareIcon sx={{ fontSize: 40, color: 'info.main' }} />
                <Box>
                  <Typography variant="h6">Firmware</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Auto-tracking active
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* WebSocket Status */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <CloudIcon sx={{ fontSize: 40, color: connected ? 'success.main' : 'error.main' }} />
                <Box>
                  <Typography variant="h6">Connection</Typography>
                  <Chip
                    label={connected ? 'Connected' : 'Disconnected'}
                    color={connected ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* System Metrics */}
      {healthStatus?.system_metrics && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <SpeedIcon color="primary" />
                  <Typography variant="h6">CPU Usage</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={healthStatus.system_metrics.cpu.value}
                    color={getStatusColor(healthStatus.system_metrics.cpu.status)}
                    sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="body2" fontWeight="bold">
                    {healthStatus.system_metrics.cpu.value.toFixed(1)}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <MemoryIcon color="primary" />
                  <Typography variant="h6">Memory Usage</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={healthStatus.system_metrics.memory.value}
                    color={getStatusColor(healthStatus.system_metrics.memory.status)}
                    sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="body2" fontWeight="bold">
                    {healthStatus.system_metrics.memory.value.toFixed(1)}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <StorageIcon color="primary" />
                  <Typography variant="h6">Disk Usage</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={healthStatus.system_metrics.disk.value}
                    color={getStatusColor(healthStatus.system_metrics.disk.status)}
                    sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="body2" fontWeight="bold">
                    {healthStatus.system_metrics.disk.value.toFixed(1)}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Services Status */}
      {healthStatus?.services && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2 }}>Service Status</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Service</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Uptime</TableCell>
                        <TableCell>Errors</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(healthStatus.services).map(([serviceName, serviceData]) => (
                        <TableRow key={serviceName}>
                          <TableCell>
                            <Typography variant="body2" fontWeight="bold">
                              {serviceName.replace('_', ' ').toUpperCase()}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {getStatusIcon(serviceData.health?.status || 'unknown')}
                              <Chip
                                label={serviceData.health?.status || 'Unknown'}
                                color={getChipColor(serviceData.health?.status || 'default')}
                                size="small"
                              />
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {serviceData.health?.uptime_seconds 
                                ? formatUptime(serviceData.health.uptime_seconds)
                                : 'N/A'
                              }
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {serviceData.health?.error_count || 0}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Recent Devices */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Recent Devices</Typography>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<TrendingUpIcon />}
                  href="/devices"
                >
                  View All
                </Button>
              </Box>
              
              {devicesLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                  <CircularProgress />
                </Box>
              ) : deviceArray.length === 0 ? (
                <Alert severity="info">
                  No devices found. Start discovery to find Tasmota devices on your network.
                </Alert>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>IP Address</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Firmware</TableCell>
                        <TableCell>Last Seen</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {deviceArray.slice(0, 5).map((device) => (
                        <TableRow key={device.id}>
                          <TableCell>
                            <Typography variant="body2" fontWeight="bold">
                              {device.name || device.hostname || 'Unknown'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontFamily="monospace">
                              {device.ip}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={device.online ? 'Online' : 'Offline'}
                              color={device.online ? 'success' : 'default'}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {device.firmware_version || 'Unknown'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {device.last_seen 
                                ? new Date(device.last_seen).toLocaleString()
                                : 'Never'
                              }
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Dashboard