import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  IconButton,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Badge,
  Tooltip
} from '@mui/material'
import {
  Analytics as AnalyticsIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Speed as PerformanceIcon,
  Security as SecurityIcon,
  Memory as CompatibilityIcon,
  Insights as InsightsIcon,
  BugReport as IssuesIcon,
  Star as RecommendationIcon,
  Assessment as ReportIcon
} from '@mui/icons-material'
import api from '../services/api'

interface AnalyticsData {
  device_compatibility: {
    summary: {
      total_devices: number
      compatibility_score: number
      risk_devices: number
      recommendations_available: number
    }
    by_chip_type: Record<string, {
      device_count: number
      avg_compatibility: number
      common_issues: string[]
    }>
    recent_analyses: Array<{
      device_id: string
      device_name: string
      compatibility_score: number
      risk_level: string
      timestamp: string
      issues_found: number
    }>
  }
  firmware_insights: {
    summary: {
      total_firmware: number
      success_rate: number
      avg_download_time: number
      cache_hit_rate: number
    }
    popular_firmware: Array<{
      name: string
      version: string
      downloads: number
      success_rate: number
      compatibility_score: number
    }>
    performance_metrics: {
      download_speed: { value: number; trend: string }
      cache_efficiency: { value: number; trend: string }
      error_rate: { value: number; trend: string }
    }
  }
  ml_recommendations: {
    summary: {
      total_recommendations: number
      accuracy_score: number
      user_adoption_rate: number
    }
    recent_recommendations: Array<{
      device_id: string
      device_name: string
      recommended_firmware: string
      confidence_score: number
      reason: string
      timestamp: string
      adopted: boolean
    }>
    model_performance: {
      accuracy: number
      precision: number
      recall: number
      f1_score: number
    }
  }
  security_analysis: {
    summary: {
      scanned_firmware: number
      security_issues: number
      risk_score: number
    }
    recent_scans: Array<{
      firmware_name: string
      scan_date: string
      risk_level: string
      issues_found: string[]
      status: string
    }>
    vulnerability_trends: Array<{
      date: string
      high_risk: number
      medium_risk: number
      low_risk: number
    }>
  }
}

const Analytics: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0)
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [timeRange, setTimeRange] = useState('7d')
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  useEffect(() => {
    fetchAnalytics()
  }, [timeRange])

  const fetchAnalytics = async () => {
    try {
      setRefreshing(true)
      const response = await api.getComprehensiveAnalytics()
      setAnalyticsData(response.data)
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'high': return 'error'
      case 'medium': return 'warning'
      case 'low': return 'success'
      default: return 'default'
    }
  }

  const getRiskIcon = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'high': return <ErrorIcon color="error" />
      case 'medium': return <WarningIcon color="warning" />
      case 'low': return <SuccessIcon color="success" />
      default: return <AnalyticsIcon />
    }
  }

  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ ml: 2 }}>Loading Analytics...</Typography>
      </Box>
    )
  }

  if (!analyticsData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load analytics data. Please try again.</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" fontWeight="bold">
            Analytics Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            AI-powered insights and device intelligence
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              label="Time Range"
            >
              <MenuItem value="24h">Last 24 Hours</MenuItem>
              <MenuItem value="7d">Last 7 Days</MenuItem>
              <MenuItem value="30d">Last 30 Days</MenuItem>
              <MenuItem value="90d">Last 90 Days</MenuItem>
            </Select>
          </FormControl>
          <Typography variant="caption" color="text.secondary">
            Updated: {lastUpdated.toLocaleTimeString()}
          </Typography>
          <IconButton onClick={fetchAnalytics} disabled={refreshing}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <CompatibilityIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                <Box>
                  <Typography variant="h6">Compatibility</Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {formatPercentage(analyticsData.device_compatibility.summary.compatibility_score)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {analyticsData.device_compatibility.summary.total_devices} devices analyzed
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <RecommendationIcon sx={{ fontSize: 40, color: 'info.main' }} />
                <Box>
                  <Typography variant="h6">ML Accuracy</Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {formatPercentage(analyticsData.ml_recommendations.summary.accuracy_score)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {analyticsData.ml_recommendations.summary.total_recommendations} recommendations
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <PerformanceIcon sx={{ fontSize: 40, color: 'success.main' }} />
                <Box>
                  <Typography variant="h6">Success Rate</Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {formatPercentage(analyticsData.firmware_insights.summary.success_rate)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Firmware flash operations
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <SecurityIcon sx={{ fontSize: 40, color: 'warning.main' }} />
                <Box>
                  <Typography variant="h6">Security Score</Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {(10 - analyticsData.security_analysis.summary.risk_score).toFixed(1)}/10
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {analyticsData.security_analysis.summary.scanned_firmware} firmware scanned
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)} sx={{ mb: 3 }}>
        <Tab label="Device Compatibility" icon={<CompatibilityIcon />} />
        <Tab label="Firmware Insights" icon={<InsightsIcon />} />
        <Tab label="ML Recommendations" icon={<RecommendationIcon />} />
        <Tab label="Security Analysis" icon={<SecurityIcon />} />
      </Tabs>

      {/* Device Compatibility Tab */}
      {currentTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Recent Compatibility Analyses</Typography>
                {analyticsData.device_compatibility.recent_analyses.length === 0 ? (
                  <Alert severity="info">No recent analyses available</Alert>
                ) : (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Device</TableCell>
                          <TableCell>Compatibility</TableCell>
                          <TableCell>Risk Level</TableCell>
                          <TableCell>Issues</TableCell>
                          <TableCell>Analyzed</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {analyticsData.device_compatibility.recent_analyses.map((analysis, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="bold">
                                {analysis.device_name}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <LinearProgress
                                  variant="determinate"
                                  value={analysis.compatibility_score * 100}
                                  sx={{ width: 60, height: 6, borderRadius: 3 }}
                                />
                                <Typography variant="body2">
                                  {formatPercentage(analysis.compatibility_score)}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={analysis.risk_level}
                                color={getRiskColor(analysis.risk_level)}
                                size="small"
                                icon={getRiskIcon(analysis.risk_level)}
                              />
                            </TableCell>
                            <TableCell>
                              <Badge badgeContent={analysis.issues_found} color="error">
                                <IssuesIcon fontSize="small" />
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {new Date(analysis.timestamp).toLocaleDateString()}
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

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Compatibility by Chip Type</Typography>
                {Object.entries(analyticsData.device_compatibility.by_chip_type).map(([chipType, data]) => (
                  <Box key={chipType} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2" fontWeight="bold">{chipType}</Typography>
                      <Typography variant="body2">{data.device_count} devices</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={data.avg_compatibility * 100}
                      sx={{ height: 8, borderRadius: 4, mb: 1 }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {formatPercentage(data.avg_compatibility)} avg compatibility
                    </Typography>
                    {data.common_issues.length > 0 && (
                      <List dense sx={{ mt: 1 }}>
                        {data.common_issues.slice(0, 3).map((issue, idx) => (
                          <ListItem key={idx} sx={{ py: 0, px: 0 }}>
                            <ListItemIcon sx={{ minWidth: 20 }}>
                              <WarningIcon fontSize="small" color="warning" />
                            </ListItemIcon>
                            <ListItemText
                              primary={issue}
                              primaryTypographyProps={{ variant: 'caption' }}
                            />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Box>
                ))}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Firmware Insights Tab */}
      {currentTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Popular Firmware</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Firmware</TableCell>
                        <TableCell>Downloads</TableCell>
                        <TableCell>Success Rate</TableCell>
                        <TableCell>Compatibility</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {analyticsData.firmware_insights.popular_firmware.map((firmware, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Box>
                              <Typography variant="body2" fontWeight="bold">
                                {firmware.name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                v{firmware.version}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{firmware.downloads}</Typography>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={firmware.success_rate * 100}
                                sx={{ width: 60, height: 6, borderRadius: 3 }}
                              />
                              <Typography variant="body2">
                                {formatPercentage(firmware.success_rate)}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {formatPercentage(firmware.compatibility_score)}
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

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Performance Metrics</Typography>
                {Object.entries(analyticsData.firmware_insights.performance_metrics).map(([metric, data]) => (
                  <Box key={metric} sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                        {metric.replace('_', ' ')}
                      </Typography>
                      {data.trend === 'up' ? (
                        <TrendingUpIcon color="success" fontSize="small" />
                      ) : data.trend === 'down' ? (
                        <TrendingDownIcon color="error" fontSize="small" />
                      ) : null}
                    </Box>
                    <Typography variant="h5" fontWeight="bold">
                      {metric === 'download_speed' ? `${data.value.toFixed(1)} MB/s` :
                       metric === 'cache_efficiency' ? formatPercentage(data.value) :
                       formatPercentage(data.value)}
                    </Typography>
                  </Box>
                ))}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* ML Recommendations Tab */}
      {currentTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Recent AI Recommendations</Typography>
                {analyticsData.ml_recommendations.recent_recommendations.length === 0 ? (
                  <Alert severity="info">No recent recommendations available</Alert>
                ) : (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Device</TableCell>
                          <TableCell>Recommended Firmware</TableCell>
                          <TableCell>Confidence</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Date</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {analyticsData.ml_recommendations.recent_recommendations.map((rec, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="bold">
                                {rec.device_name}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Box>
                                <Typography variant="body2">{rec.recommended_firmware}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {rec.reason}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <LinearProgress
                                  variant="determinate"
                                  value={rec.confidence_score * 100}
                                  sx={{ width: 60, height: 6, borderRadius: 3 }}
                                />
                                <Typography variant="body2">
                                  {formatPercentage(rec.confidence_score)}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={rec.adopted ? 'Adopted' : 'Pending'}
                                color={rec.adopted ? 'success' : 'default'}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {new Date(rec.timestamp).toLocaleDateString()}
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

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Model Performance</Typography>
                {Object.entries(analyticsData.ml_recommendations.model_performance).map(([metric, value]) => (
                  <Box key={metric} sx={{ mb: 2 }}>
                    <Typography variant="body2" sx={{ textTransform: 'capitalize', mb: 0.5 }}>
                      {metric.replace('_', ' ')}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={value * 100}
                        sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                      />
                      <Typography variant="body2" fontWeight="bold">
                        {formatPercentage(value)}
                      </Typography>
                    </Box>
                  </Box>
                ))}
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  Adoption rate: {formatPercentage(analyticsData.ml_recommendations.summary.user_adoption_rate)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Security Analysis Tab */}
      {currentTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Recent Security Scans</Typography>
                {analyticsData.security_analysis.recent_scans.length === 0 ? (
                  <Alert severity="info">No recent security scans available</Alert>
                ) : (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Firmware</TableCell>
                          <TableCell>Scan Date</TableCell>
                          <TableCell>Risk Level</TableCell>
                          <TableCell>Issues Found</TableCell>
                          <TableCell>Status</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {analyticsData.security_analysis.recent_scans.map((scan, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="bold">
                                {scan.firmware_name}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {new Date(scan.scan_date).toLocaleDateString()}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={scan.risk_level}
                                color={getRiskColor(scan.risk_level)}
                                size="small"
                                icon={getRiskIcon(scan.risk_level)}
                              />
                            </TableCell>
                            <TableCell>
                              <Tooltip title={scan.issues_found.join(', ')}>
                                <Badge badgeContent={scan.issues_found.length} color="error">
                                  <SecurityIcon fontSize="small" />
                                </Badge>
                              </Tooltip>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={scan.status}
                                color={scan.status === 'approved' ? 'success' : 'warning'}
                                size="small"
                              />
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
      )}

      {/* Export Button */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
        <Button
          variant="outlined"
          startIcon={<ReportIcon />}
          onClick={() => {
            // Export analytics data
            const dataStr = JSON.stringify(analyticsData, null, 2)
            const dataBlob = new Blob([dataStr], { type: 'application/json' })
            const url = URL.createObjectURL(dataBlob)
            const link = document.createElement('a')
            link.href = url
            link.download = `analytics-report-${new Date().toISOString().split('T')[0]}.json`
            link.click()
          }}
        >
          Export Report
        </Button>
      </Box>
    </Box>
  )
}

export default Analytics