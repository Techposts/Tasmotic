import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Box } from '@mui/material'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Devices from './pages/Devices'
import Templates from './pages/Templates'
import Discovery from './pages/Discovery'
import Flashing from './pages/Flashing'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import DeviceConfig from './pages/DeviceConfig'
import { SocketProvider } from './contexts/SocketContext'
import { DeviceProvider } from './contexts/DeviceContext'

const App: React.FC = () => {
  return (
    <SocketProvider>
      <DeviceProvider>
        <Router>
          <Box sx={{ display: 'flex', height: '100vh' }}>
            <Sidebar />
            <Box component="main" sx={{ flexGrow: 1, overflow: 'auto' }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/devices" element={<Devices />} />
                <Route path="/devices/:deviceId/config" element={<DeviceConfig />} />
                <Route path="/templates" element={<Templates />} />
                <Route path="/discovery" element={<Discovery />} />
                <Route path="/flashing" element={<Flashing />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Box>
          </Box>
        </Router>
      </DeviceProvider>
    </SocketProvider>
  )
}

export default App