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
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Badge,
  Tabs,
  Tab
} from '@mui/material'
import {
  Add as AddIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  Code as CodeIcon,
  Visibility as ViewIcon,
  Public as PublicIcon,
  Star as StarIcon,
  Category as CategoryIcon
} from '@mui/icons-material'
import api from '../services/api'
import { Device, DeviceTemplate } from '../types'

interface Template {
  id: string
  name: string
  description: string
  category: string
  manufacturer: string
  model: string
  template_data: any
  gpio_config: Record<string, string>
  rules?: string
  settings?: Record<string, any>
  image_url?: string
  author: string
  version: string
  tags: string[]
  public: boolean
  downloads: number
  rating: number
  created_at: string
  updated_at: string
}

interface Device {
  id: string
  name: string
  ip: string
  online: boolean
}

const Templates: React.FC = () => {
  const [templates, setTemplates] = useState<Template[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [templateDetailOpen, setTemplateDetailOpen] = useState(false)
  const [createTemplateOpen, setCreateTemplateOpen] = useState(false)
  const [applyTemplateOpen, setApplyTemplateOpen] = useState(false)
  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState('')
  const [currentTab, setCurrentTab] = useState(0)
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [newTemplate, setNewTemplate] = useState<Partial<DeviceTemplate>>({
    name: '',
    description: '',
    category: '',
    manufacturer: '',
    model: '',
    template_data: {},
    gpio_config: {},
    settings: {},
    public: false
  })

  const categories = ['all', 'Switch', 'Plug', 'Sensor', 'Light', 'Development', 'Other']

  useEffect(() => {
    fetchTemplates()
    fetchDevices()
  }, [])

  const fetchTemplates = async () => {
    try {
      const response = await api.getTemplates()
      setTemplates(response.data?.templates || [])
    } catch (error) {
      console.error('Failed to fetch templates:', error)
    } finally {
      setTemplatesLoading(false)
    }
  }

  const fetchDevices = async () => {
    try {
      const response = await api.getDevices()
      const devicesData = response.data?.devices || {}
      const deviceArray = Object.values(devicesData)
      setDevices(Array.isArray(deviceArray) ? deviceArray : [])
    } catch (error) {
      console.error('Failed to fetch devices:', error)
    }
  }

  const handleTemplateClick = (template: Template) => {
    setSelectedTemplate(template)
    setTemplateDetailOpen(true)
  }

  const handleApplyTemplate = async () => {
    if (!selectedTemplate || !selectedDevice) return

    try {
      await api.applyTemplate(selectedTemplate.id, selectedDevice)
      setApplyTemplateOpen(false)
      alert('Template applied successfully!')
    } catch (error) {
      console.error('Failed to apply template:', error)
      alert('Failed to apply template')
    }
  }

  const handleCreateTemplate = async () => {
    try {
      await api.createTemplate(newTemplate)
      setCreateTemplateOpen(false)
      fetchTemplates()
      setNewTemplate({
        name: '',
        description: '',
        category: '',
        manufacturer: '',
        model: '',
        template_data: {},
        gpio_config: {},
        settings: {},
        public: false
      })
    } catch (error) {
      console.error('Failed to create template:', error)
    }
  }

  const filteredTemplates = templates.filter(template => 
    categoryFilter === 'all' || template.category === categoryFilter
  )

  const builtInTemplates = filteredTemplates.filter(t => t.author === 'system')
  const communityTemplates = filteredTemplates.filter(t => t.author !== 'system' && t.public)
  const myTemplates = filteredTemplates.filter(t => t.author !== 'system' && !t.public)

  const renderTemplateCard = (template: Template) => (
    <Grid item xs={12} sm={6} md={4} key={template.id}>
      <Card 
        sx={{ 
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          cursor: 'pointer',
          transition: 'all 0.2s',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: 4
          }
        }}
        onClick={() => handleTemplateClick(template)}
      >
        <CardContent sx={{ flexGrow: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h6" noWrap>
                {template.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {template.manufacturer} {template.model}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
              <Chip
                label={template.category}
                size="small"
                color="primary"
                icon={<CategoryIcon />}
              />
              {template.public && (
                <Chip
                  label="Public"
                  size="small"
                  color="success"
                  icon={<PublicIcon />}
                />
              )}
            </Box>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {template.description}
          </Typography>

          <Divider sx={{ my: 2 }} />

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                GPIO Pins:
              </Typography>
              <Typography variant="body2">
                {Object.keys(template.gpio_config || {}).length}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Version:
              </Typography>
              <Typography variant="body2">
                {template.version || '1.0.0'}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Downloads:
              </Typography>
              <Badge badgeContent={template.downloads} color="primary">
                <DownloadIcon fontSize="small" />
              </Badge>
            </Box>

            {template.rating > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  Rating:
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <StarIcon sx={{ color: 'gold', fontSize: 16 }} />
                  <Typography variant="body2">
                    {template.rating.toFixed(1)}
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>
        </CardContent>

        <CardActions>
          <Button
            size="small"
            startIcon={<ViewIcon />}
            onClick={(e) => {
              e.stopPropagation()
              handleTemplateClick(template)
            }}
          >
            View
          </Button>
          <Button
            size="small"
            startIcon={<UploadIcon />}
            onClick={(e) => {
              e.stopPropagation()
              setSelectedTemplate(template)
              setApplyTemplateOpen(true)
            }}
          >
            Apply
          </Button>
        </CardActions>
      </Card>
    </Grid>
  )

  const renderTemplateGrid = (templateList: Template[], emptyMessage: string) => (
    templatesLoading ? (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    ) : templateList.length === 0 ? (
      <Card>
        <CardContent sx={{ textAlign: 'center', py: 6 }}>
          <CodeIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            {emptyMessage}
          </Typography>
        </CardContent>
      </Card>
    ) : (
      <Grid container spacing={3}>
        {templateList.map(renderTemplateCard)}
      </Grid>
    )
  )

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          Device Templates
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Category</InputLabel>
            <Select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              label="Category"
            >
              {categories.map(category => (
                <MenuItem key={category} value={category}>
                  {category === 'all' ? 'All Categories' : category}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateTemplateOpen(true)}
          >
            Create Template
          </Button>
        </Box>
      </Box>

      <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)} sx={{ mb: 3 }}>
        <Tab label={`Built-in (${builtInTemplates.length})`} />
        <Tab label={`Community (${communityTemplates.length})`} />
        <Tab label={`My Templates (${myTemplates.length})`} />
      </Tabs>

      {currentTab === 0 && renderTemplateGrid(builtInTemplates, 'No built-in templates available')}
      {currentTab === 1 && renderTemplateGrid(communityTemplates, 'No community templates available')}
      {currentTab === 2 && renderTemplateGrid(myTemplates, 'No personal templates created')}

      {/* Template Detail Dialog */}
      <Dialog
        open={templateDetailOpen}
        onClose={() => setTemplateDetailOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Template Details: {selectedTemplate?.name}
        </DialogTitle>
        <DialogContent>
          {selectedTemplate && (
            <Box sx={{ pt: 1 }}>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Name"
                    value={selectedTemplate.name}
                    fullWidth
                    disabled
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Category"
                    value={selectedTemplate.category}
                    fullWidth
                    disabled
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Manufacturer"
                    value={selectedTemplate.manufacturer}
                    fullWidth
                    disabled
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Model"
                    value={selectedTemplate.model}
                    fullWidth
                    disabled
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    label="Description"
                    value={selectedTemplate.description}
                    fullWidth
                    multiline
                    rows={2}
                    disabled
                  />
                </Grid>
              </Grid>

              <Typography variant="h6" gutterBottom>
                GPIO Configuration
              </Typography>
              <TableContainer component={Paper} sx={{ mb: 3 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>GPIO Pin</TableCell>
                      <TableCell>Function</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(selectedTemplate.gpio_config || {}).map(([pin, func]) => (
                      <TableRow key={pin}>
                        <TableCell>{pin}</TableCell>
                        <TableCell>{func}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              <Typography variant="h6" gutterBottom>
                Template Data
              </Typography>
              <Paper sx={{ p: 2, backgroundColor: 'grey.50', mb: 3 }}>
                <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(selectedTemplate.template_data, null, 2)}
                </pre>
              </Paper>

              {selectedTemplate.settings && Object.keys(selectedTemplate.settings).length > 0 && (
                <>
                  <Typography variant="h6" gutterBottom>
                    Default Settings
                  </Typography>
                  <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
                    <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(selectedTemplate.settings, null, 2)}
                    </pre>
                  </Paper>
                </>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTemplateDetailOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              setTemplateDetailOpen(false)
              setApplyTemplateOpen(true)
            }}
          >
            Apply to Device
          </Button>
        </DialogActions>
      </Dialog>

      {/* Apply Template Dialog */}
      <Dialog
        open={applyTemplateOpen}
        onClose={() => setApplyTemplateOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Apply Template</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              Select a device to apply the template "{selectedTemplate?.name}" to.
            </Alert>
            <FormControl fullWidth>
              <InputLabel>Select Device</InputLabel>
              <Select
                value={selectedDevice}
                onChange={(e) => setSelectedDevice(e.target.value)}
                label="Select Device"
              >
                {devices.filter(d => d.online).map(device => (
                  <MenuItem key={device.id} value={device.id}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                      <span>{device.name}</span>
                      <span style={{ color: 'text.secondary' }}>{device.ip}</span>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApplyTemplateOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleApplyTemplate}
            disabled={!selectedDevice}
          >
            Apply Template
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create Template Dialog */}
      <Dialog
        open={createTemplateOpen}
        onClose={() => setCreateTemplateOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Create New Template</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Template Name"
                  value={newTemplate.name}
                  onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                  fullWidth
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth required>
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={newTemplate.category}
                    onChange={(e) => setNewTemplate({ ...newTemplate, category: e.target.value })}
                    label="Category"
                  >
                    {categories.slice(1).map(category => (
                      <MenuItem key={category} value={category}>
                        {category}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Manufacturer"
                  value={newTemplate.manufacturer}
                  onChange={(e) => setNewTemplate({ ...newTemplate, manufacturer: e.target.value })}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Model"
                  value={newTemplate.model}
                  onChange={(e) => setNewTemplate({ ...newTemplate, model: e.target.value })}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Description"
                  value={newTemplate.description}
                  onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
                  fullWidth
                  multiline
                  rows={3}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Template Data (JSON)"
                  value={JSON.stringify(newTemplate.template_data, null, 2)}
                  onChange={(e) => {
                    try {
                      setNewTemplate({ ...newTemplate, template_data: JSON.parse(e.target.value) })
                    } catch {}
                  }}
                  fullWidth
                  multiline
                  rows={8}
                  placeholder='{"NAME": "Device Name", "GPIO": [...], "FLAG": 0, "BASE": 1}'
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateTemplateOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateTemplate}
            disabled={!newTemplate.name || !newTemplate.category}
          >
            Create Template
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Templates