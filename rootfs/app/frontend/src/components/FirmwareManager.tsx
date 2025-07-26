import React, { useState, useEffect } from 'react'
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Alert,
  CircularProgress,
  Rating,
  Badge
} from '@mui/material'
import {
  CloudDownload,
  Verified,
  Warning,
  TrendingUp,
  Group as Community,
  Upload,
  Refresh,
  Info,
  Download,
  Speed,
  Security
} from '@mui/icons-material'
import { useSnackbar } from 'notistack'
import { apiService } from '../services/api'
import { Firmware, Device } from '../types'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div role="tabpanel" hidden={value !== index}>
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
)

interface FirmwareManagerProps {
  selectedDevice?: Device
  onFirmwareSelect: (firmware: Firmware) => void
  onFlashStart: (firmware: Firmware) => void
}

const FirmwareManager: React.FC<FirmwareManagerProps> = ({
  selectedDevice,
  onFirmwareSelect,
  onFlashStart
}) => {
  const [tabValue, setTabValue] = useState(0)
  const [firmwareList, setFirmwareList] = useState<Firmware[]>([])
  const [communityFirmware, setCommunityFirmware] = useState<Firmware[]>([])
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [chipFilter, setChipFilter] = useState('')
  const [channelFilter, setChannelFilter] = useState('stable')
  const [uploadDialog, setUploadDialog] = useState(false)
  const [selectedFirmware, setSelectedFirmware] = useState<Firmware | null>(null)
  const [, setFirmwareDetails] = useState<any>(null)
  const { enqueueSnackbar } = useSnackbar()

  useEffect(() => {
    loadFirmware()
  }, [chipFilter, channelFilter])

  useEffect(() => {
    if (selectedDevice) {
      loadRecommendations()
    }
  }, [selectedDevice])

  const loadFirmware = async () => {
    setLoading(true)
    try {
      const [officialResponse, communityResponse] = await Promise.all([
        apiService.getOfficialFirmware({
          chip_type: chipFilter || undefined,
          channel: channelFilter || undefined
        }),
        apiService.getCommunityFirmware({
          chip_type: chipFilter || undefined,
          status: 'approved'
        })
      ])

      if (officialResponse.data) {
        setFirmwareList(officialResponse.data.firmware || [])
      }
      
      if (communityResponse.data) {
        setCommunityFirmware(communityResponse.data.firmware || [])
      }
    } catch (error) {
      enqueueSnackbar('Failed to load firmware list', { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const loadRecommendations = async () => {
    if (!selectedDevice) return

    try {
      const response = await apiService.getFirmwareRecommendations(selectedDevice.id)
      if (response.data) {
        setRecommendations(response.data.recommendations || [])
      }
    } catch (error) {
      console.error('Failed to load recommendations:', error)
    }
  }

  const handleFirmwareClick = async (firmware: Firmware) => {
    setSelectedFirmware(firmware)
    
    try {
      const response = await apiService.getFirmwareDetails(firmware.id)
      if (response.data) {
        setFirmwareDetails(response.data)
      }
    } catch (error) {
      console.error('Failed to load firmware details:', error)
    }
  }

  const handleFlashFirmware = (firmware: Firmware) => {
    setSelectedFirmware(null)
    onFirmwareSelect(firmware)
    onFlashStart(firmware)
  }

  const getFirmwareIcon = (firmware: Firmware) => {
    if (firmware.verified) return <Verified color="success" />
    if (firmware.channel === 'development') return <Warning color="warning" />
    if (firmware.source?.includes('community')) return <Community color="info" />
    return <CloudDownload />
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success'
    if (confidence >= 0.6) return 'warning'
    return 'error'
  }

  const FirmwareCard: React.FC<{ firmware: Firmware; showRecommendation?: any }> = ({ 
    firmware, 
    showRecommendation 
  }) => (
    <Card 
      sx={{ 
        height: '100%', 
        cursor: 'pointer',
        '&:hover': { boxShadow: 4 }
      }}
      onClick={() => handleFirmwareClick(firmware)}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          {getFirmwareIcon(firmware)}
          <Typography variant="h6" sx={{ ml: 1, flex: 1 }}>
            {firmware.display_name || firmware.name}
          </Typography>
          {showRecommendation && (
            <Chip
              label={`${Math.round(showRecommendation.confidence * 100)}%`}
              color={getConfidenceColor(showRecommendation.confidence)}
              size="small"
            />
          )}
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {firmware.description || 'No description available'}
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
          <Chip label={firmware.chip_type} size="small" />
          <Chip label={firmware.variant} size="small" variant="outlined" />
          <Chip label={firmware.channel} size="small" color="primary" />
        </Box>
        
        {firmware.features && firmware.features.length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {firmware.features.slice(0, 3).map((feature, index) => (
              <Chip key={index} label={feature} size="small" variant="outlined" />
            ))}
            {firmware.features.length > 3 && (
              <Chip label={`+${firmware.features.length - 3} more`} size="small" />
            )}
          </Box>
        )}
        
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
          {firmware.rating && (
            <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
              <Rating value={firmware.rating} readOnly size="small" />
              <Typography variant="caption" sx={{ ml: 0.5 }}>
                ({firmware.rating_count || 0})
              </Typography>
            </Box>
          )}
          
          {firmware.download_count && (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Download fontSize="small" />
              <Typography variant="caption" sx={{ ml: 0.5 }}>
                {firmware.download_count.toLocaleString()}
              </Typography>
            </Box>
          )}
        </Box>
        
        {showRecommendation && showRecommendation.reasons && (
          <List dense sx={{ mt: 1 }}>
            {showRecommendation.reasons.slice(0, 2).map((reason: string, index: number) => (
              <ListItem key={index} sx={{ py: 0 }}>
                <ListItemIcon sx={{ minWidth: 20 }}>
                  <Info fontSize="small" />
                </ListItemIcon>
                <ListItemText 
                  primary={reason}
                  primaryTypographyProps={{ variant: 'caption' }}
                />
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
      
      <CardActions>
        <Button
          size="small"
          onClick={(e) => {
            e.stopPropagation()
            handleFlashFirmware(firmware)
          }}
          disabled={!selectedDevice}
        >
          Flash
        </Button>
        <Button size="small" onClick={(e) => e.stopPropagation()}>
          Details
        </Button>
      </CardActions>
    </Card>
  )

  const FirmwareUploader: React.FC = () => {
    const [dragOver, setDragOver] = useState(false)
    const [uploadProgress, setUploadProgress] = useState(0)
    const [uploading, setUploading] = useState(false)

    const handleFileDrop = async (files: FileList) => {
      const file = files[0]
      if (!file.name.endsWith('.bin')) {
        enqueueSnackbar('Please upload a .bin firmware file', { variant: 'error' })
        return
      }

      setUploading(true)
      setUploadProgress(0)

      try {
        const formData = new FormData()
        formData.append('firmware', file)
        formData.append('metadata', JSON.stringify({
          display_name: file.name,
          chip_type: chipFilter || 'ESP32',
          version: 'custom'
        }))

        const response = await apiService.uploadCustomFirmware(formData, (progress) => {
          setUploadProgress(progress)
        })

        if (response.data?.success) {
          enqueueSnackbar('Firmware uploaded successfully!', { variant: 'success' })
          loadFirmware()
          setUploadDialog(false)
        }
      } catch (error) {
        enqueueSnackbar('Failed to upload firmware', { variant: 'error' })
      } finally {
        setUploading(false)
        setUploadProgress(0)
      }
    }

    return (
      <Box
        sx={{
          border: '2px dashed',
          borderColor: dragOver ? 'primary.main' : 'grey.300',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          backgroundColor: dragOver ? 'action.hover' : 'background.paper',
          cursor: 'pointer'
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          handleFileDrop(e.dataTransfer.files)
        }}
      >
        <Upload sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          Upload Custom Firmware
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Drag & drop your .bin file here, or click to browse
        </Typography>
        
        {uploading && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress variant="determinate" value={uploadProgress} />
            <Typography variant="caption">
              Uploading... {Math.round(uploadProgress)}%
            </Typography>
          </Box>
        )}
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Firmware Manager</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            startIcon={<Refresh />}
            onClick={loadFirmware}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            startIcon={<Upload />}
            variant="outlined"
            onClick={() => setUploadDialog(true)}
          >
            Upload Custom
          </Button>
        </Box>
      </Box>

      {selectedDevice && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">
            <strong>Selected Device:</strong> {selectedDevice.name} ({selectedDevice.chip_type})
          </Typography>
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          label="Search firmware"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          size="small"
          sx={{ minWidth: 200 }}
        />
        
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Chip Type</InputLabel>
          <Select
            value={chipFilter}
            label="Chip Type"
            onChange={(e) => setChipFilter(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="ESP32">ESP32</MenuItem>
            <MenuItem value="ESP8266">ESP8266</MenuItem>
          </Select>
        </FormControl>
        
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Channel</InputLabel>
          <Select
            value={channelFilter}
            label="Channel"
            onChange={(e) => setChannelFilter(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="stable">Stable</MenuItem>
            <MenuItem value="beta">Beta</MenuItem>
            <MenuItem value="development">Development</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
        <Tab 
          label={
            <Badge badgeContent={recommendations.length} color="primary">
              Recommended
            </Badge>
          } 
        />
        <Tab label={`Official (${firmwareList.length})`} />
        <Tab label={`Community (${communityFirmware.length})`} />
        <Tab label="Analytics" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        {selectedDevice ? (
          <>
            <Typography variant="h6" gutterBottom>
              Recommended for {selectedDevice.name}
            </Typography>
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : recommendations.length > 0 ? (
              <Grid container spacing={2}>
                {recommendations.map((rec, index) => (
                  <Grid item xs={12} md={6} lg={4} key={index}>
                    <FirmwareCard 
                      firmware={rec.firmware} 
                      showRecommendation={rec}
                    />
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Alert severity="info">
                No specific recommendations available for this device. 
                Check the Official or Community tabs for compatible firmware.
              </Alert>
            )}
          </>
        ) : (
          <Alert severity="warning">
            Select a device to see personalized firmware recommendations
          </Alert>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Typography variant="h6" gutterBottom>
          Official Tasmota Firmware
        </Typography>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Grid container spacing={2}>
            {firmwareList
              .filter(firmware => 
                !searchTerm || 
                firmware.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                firmware.variant?.toLowerCase().includes(searchTerm.toLowerCase())
              )
              .map((firmware) => (
                <Grid item xs={12} md={6} lg={4} key={firmware.id}>
                  <FirmwareCard firmware={firmware} />
                </Grid>
              ))}
          </Grid>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Typography variant="h6" gutterBottom>
          Community Firmware
        </Typography>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Grid container spacing={2}>
            {communityFirmware
              .filter(firmware => 
                !searchTerm || 
                firmware.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                firmware.description?.toLowerCase().includes(searchTerm.toLowerCase())
              )
              .map((firmware) => (
                <Grid item xs={12} md={6} lg={4} key={firmware.id}>
                  <FirmwareCard firmware={firmware} />
                </Grid>
              ))}
          </Grid>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <Typography variant="h6" gutterBottom>
          Firmware Analytics
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <TrendingUp color="primary" />
                  <Typography variant="h6" sx={{ ml: 1 }}>
                    Popular Firmware
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Most downloaded firmware this month
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Speed color="success" />
                  <Typography variant="h6" sx={{ ml: 1 }}>
                    Success Rate
                  </Typography>
                </Box>
                <Typography variant="h4" color="success.main">
                  94.2%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Average flashing success rate
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Security color="info" />
                  <Typography variant="h6" sx={{ ml: 1 }}>
                    Verified Firmware
                  </Typography>
                </Box>
                <Typography variant="h4" color="info.main">
                  {firmwareList.filter(f => f.verified).length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Verified secure firmware
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Firmware Details Dialog */}
      <Dialog
        open={Boolean(selectedFirmware)}
        onClose={() => setSelectedFirmware(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {selectedFirmware && getFirmwareIcon(selectedFirmware)}
            <Typography variant="h6" sx={{ ml: 1 }}>
              {selectedFirmware?.display_name || selectedFirmware?.name}
            </Typography>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          {selectedFirmware && (
            <Box>
              <Typography variant="body1" paragraph>
                {selectedFirmware.description || 'No description available'}
              </Typography>
              
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">Version:</Typography>
                  <Typography variant="body2">{selectedFirmware.version}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">Chip Type:</Typography>
                  <Typography variant="body2">{selectedFirmware.chip_type}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">Variant:</Typography>
                  <Typography variant="body2">{selectedFirmware.variant}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">Channel:</Typography>
                  <Typography variant="body2">{selectedFirmware.channel}</Typography>
                </Grid>
              </Grid>
              
              {selectedFirmware.features && selectedFirmware.features.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Features:</Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {selectedFirmware.features.map((feature, index) => (
                      <Chip key={index} label={feature} size="small" />
                    ))}
                  </Box>
                </Box>
              )}
              
              {selectedFirmware.changelog && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Changelog:</Typography>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {selectedFirmware.changelog}
                  </Typography>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setSelectedFirmware(null)}>
            Close
          </Button>
          <Button
            variant="contained"
            onClick={() => selectedFirmware && handleFlashFirmware(selectedFirmware)}
            disabled={!selectedDevice}
          >
            Flash This Firmware
          </Button>
        </DialogActions>
      </Dialog>

      {/* Upload Dialog */}
      <Dialog
        open={uploadDialog}
        onClose={() => setUploadDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Upload Custom Firmware</DialogTitle>
        <DialogContent>
          <FirmwareUploader />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialog(false)}>
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default FirmwareManager