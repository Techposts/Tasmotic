import React, { createContext, useContext, useEffect, useState } from 'react'
import { io, Socket } from 'socket.io-client'
import { Device, SystemStatus } from '../types'

interface SocketContextType {
  socket: Socket | null
  connected: boolean
  systemStatus: SystemStatus | null
}

const SocketContext = createContext<SocketContextType>({
  socket: null,
  connected: false,
  systemStatus: null,
})

export const useSocket = () => {
  const context = useContext(SocketContext)
  if (!context) {
    throw new Error('useSocket must be used within a SocketProvider')
  }
  return context
}

interface SocketProviderProps {
  children: React.ReactNode
}

export const SocketProvider: React.FC<SocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [connected, setConnected] = useState(false)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)

  useEffect(() => {
    const newSocket = io('/', {
      transports: ['websocket', 'polling'],
    })

    newSocket.on('connect', () => {
      console.log('Socket connected')
      setConnected(true)
    })

    newSocket.on('disconnect', () => {
      console.log('Socket disconnected')
      setConnected(false)
    })

    newSocket.on('status', (data: SystemStatus) => {
      setSystemStatus(data)
    })

    newSocket.on('device_update', (data: { device_id: string; device: Device }) => {
      console.log('Device updated:', data)
      // This will be handled by DeviceContext
    })

    newSocket.on('device_discovered', (data: { device: Device }) => {
      console.log('Device discovered:', data)
      // This will be handled by DeviceContext
    })

    newSocket.on('discovery_status', (data: { active: boolean }) => {
      console.log('Discovery status:', data)
      // This will be handled by components that need it
    })

    setSocket(newSocket)

    return () => {
      newSocket.close()
    }
  }, [])

  return (
    <SocketContext.Provider value={{ socket, connected, systemStatus }}>
      {children}
    </SocketContext.Provider>
  )
}