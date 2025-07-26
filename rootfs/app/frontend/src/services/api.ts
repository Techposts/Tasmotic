import axios from 'axios'
import { Device, DeviceTemplate, ApiResponse, AppConfig, FlashDevice, Firmware } from '../types'

const axiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const apiService = {
  // Health check
  health: () => axiosInstance.get('/health'),

  // Configuration
  getConfig: (): Promise<ApiResponse<AppConfig>> => axiosInstance.get('/config'),
  updateConfig: (config: Partial<AppConfig>): Promise<ApiResponse> => 
    axiosInstance.post('/config', config),

  // Devices
  getDevices: (): Promise<ApiResponse<{ devices: Record<string, Device>; count: number }>> => 
    axiosInstance.get('/devices'),
  getDevice: (deviceId: string): Promise<ApiResponse<Device>> => 
    axiosInstance.get(`/devices/${deviceId}`),
  sendDeviceCommand: (deviceId: string, command: string, params?: Record<string, any>): Promise<ApiResponse> =>
    axiosInstance.post(`/devices/${deviceId}/command`, { command, params }),

  // Discovery
  startDiscovery: (): Promise<ApiResponse> => axiosInstance.post('/discovery/start'),
  stopDiscovery: (): Promise<ApiResponse> => axiosInstance.post('/discovery/stop'),

  // Templates
  getTemplates: (): Promise<ApiResponse<{ templates: DeviceTemplate[]; count: number }>> =>
    axiosInstance.get('/templates'),
  createTemplate: (template: Partial<DeviceTemplate>): Promise<ApiResponse<{ template_id: string }>> =>
    axiosInstance.post('/templates', template),
  applyTemplate: (templateId: string, deviceId: string): Promise<ApiResponse> =>
    axiosInstance.post(`/templates/${templateId}/apply`, { device_id: deviceId }),

  // Firmware Management
  getOfficialFirmware: (params?: { chip_type?: string; channel?: string; verified_only?: boolean }): Promise<ApiResponse<{ firmware: Firmware[]; count: number }>> =>
    axiosInstance.get('/firmware', { params }),
  getCommunityFirmware: (params?: { chip_type?: string; status?: string; author?: string; limit?: number }): Promise<ApiResponse<{ firmware: Firmware[]; count: number }>> =>
    axiosInstance.get('/firmware/community', { params }),
  getFirmwareRecommendations: (deviceId: string): Promise<ApiResponse<{ recommendations: any[] }>> =>
    axiosInstance.get(`/firmware/recommendations/${deviceId}`),
  getFirmwareDetails: (firmwareId: string): Promise<ApiResponse<any>> =>
    axiosInstance.get(`/firmware/${firmwareId}`),
  downloadFirmware: (firmwareId: string): Promise<Blob> =>
    axiosInstance.get(`/firmware/${firmwareId}/download`, { responseType: 'blob' }),
  uploadCustomFirmware: (formData: FormData, onProgress?: (progress: number) => void): Promise<ApiResponse> =>
    axiosInstance.post('/firmware/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress ? (e) => {
        if (e.total) onProgress((e.loaded / e.total) * 100)
      } : undefined
    }),
  checkFirmwareUpdates: (): Promise<ApiResponse> =>
    axiosInstance.post('/firmware/updates'),
  getFirmwareAnalytics: (): Promise<ApiResponse<any>> =>
    axiosInstance.get('/firmware/analytics'),
  getComprehensiveAnalytics: (): Promise<ApiResponse<any>> =>
    axiosInstance.get('/analytics/comprehensive'),

  // Flashing
  getFlashDevices: (): Promise<ApiResponse<{ devices: FlashDevice[] }>> =>
    axiosInstance.get('/flash/devices'),

  // Device Configuration (Tasmotizer-like)
  getDeviceConfigInfo: (deviceId: string): Promise<ApiResponse<any>> =>
    axiosInstance.get(`/devices/${deviceId}/config/info`),
  configureDeviceWifi: (deviceId: string, config: any): Promise<ApiResponse> =>
    axiosInstance.post(`/devices/${deviceId}/config/wifi`, config),
  configureDeviceMqtt: (deviceId: string, config: any): Promise<ApiResponse> =>
    axiosInstance.post(`/devices/${deviceId}/config/mqtt`, config),
  configureDeviceName: (deviceId: string, config: any): Promise<ApiResponse> =>
    axiosInstance.post(`/devices/${deviceId}/config/name`, config),
  applyDeviceTemplate: (deviceId: string, templateName: string): Promise<ApiResponse> =>
    axiosInstance.post(`/devices/${deviceId}/config/template`, { template_name: templateName }),
  sendRawDeviceCommand: (deviceId: string, command: string): Promise<ApiResponse> =>
    axiosInstance.post(`/devices/${deviceId}/config/command`, { command }),
  backupDeviceConfig: (deviceId: string): Promise<ApiResponse> =>
    axiosInstance.get(`/devices/${deviceId}/config/backup`),
  getDeviceTemplates: (): Promise<ApiResponse<{ templates: any }>> =>
    axiosInstance.get('/config/templates'),
  networkDeviceScan: (networkRange?: string): Promise<ApiResponse<{ devices: any[], count: number }>> =>
    axiosInstance.post('/discovery/network-scan', { network_range: networkRange }),
}

// Export both individual methods and the service object for compatibility
const api = {
  // Direct API methods for compatibility
  get: (url: string) => axiosInstance.get(url),
  post: (url: string, data?: any) => axiosInstance.post(url, data),
  put: (url: string, data?: any) => axiosInstance.put(url, data),
  delete: (url: string) => axiosInstance.delete(url),
  
  // Service methods
  ...apiService
}

export default api