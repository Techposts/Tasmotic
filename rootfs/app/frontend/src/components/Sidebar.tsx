import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Box,
  Chip
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  Devices as DevicesIcon,
  Article as TemplateIcon,
  Search as DiscoveryIcon,
  FlashOn as FlashingIcon,
  Settings as SettingsIcon,
  Analytics as AnalyticsIcon,
  Router as RouterIcon
} from '@mui/icons-material'

const drawerWidth = 240

interface NavigationItem {
  text: string
  icon: React.ReactNode
  path: string
  badge?: string
}

const navigationItems: NavigationItem[] = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { text: 'Devices', icon: <DevicesIcon />, path: '/devices' },
  { text: 'Discovery', icon: <DiscoveryIcon />, path: '/discovery' },
  { text: 'Templates', icon: <TemplateIcon />, path: '/templates' },
  { text: 'Firmware', icon: <RouterIcon />, path: '/firmware' },
  { text: 'Flashing', icon: <FlashingIcon />, path: '/flashing', badge: 'WebSerial' },
  { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics', badge: 'AI' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings' }
]

const Sidebar: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          backgroundColor: 'background.paper',
          borderRight: '1px solid',
          borderRightColor: 'divider'
        },
      }}
    >
      <Box sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Tasmota Master
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Device Management Suite
        </Typography>
      </Box>

      <Divider />

      <List sx={{ flexGrow: 1, pt: 1 }}>
        {navigationItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => navigate(item.path)}
              sx={{
                mx: 1,
                mb: 0.5,
                borderRadius: 1,
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'primary.contrastText',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                  '& .MuiListItemIcon-root': {
                    color: 'primary.contrastText',
                  }
                }
              }}
            >
              <ListItemIcon>
                {item.icon}
              </ListItemIcon>
              <ListItemText 
                primary={item.text}
                primaryTypographyProps={{
                  fontSize: '0.9rem',
                  fontWeight: location.pathname === item.path ? 600 : 400
                }}
              />
              {item.badge && (
                <Chip 
                  label={item.badge} 
                  size="small" 
                  color="secondary"
                  sx={{ fontSize: '0.7rem', height: 20 }}
                />
              )}
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      <Divider />
      
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Version 1.0.0
        </Typography>
      </Box>
    </Drawer>
  )
}

export default Sidebar