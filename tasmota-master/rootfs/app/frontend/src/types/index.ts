export interface Device {
  id: string
  name: string
  hostname: string
  ip: string
  mac: string
  firmware_version: string
  hardware: string
  template?: DeviceTemplate
  config?: Record<string, any>
  last_seen: string
  status: 'online' | 'offline' | 'unknown'
  online: boolean
  uptime?: number
  free_memory?: number
  wifi_signal?: number
  rssi?: number
  power_state?: any
  discovery_method?: string
  chip_type?: string
  created_at?: string
  updated_at?: string
}

export interface DeviceTemplate {
  id: string
  name: string
  description: string
  category: string
  manufacturer: string
  model: string
  template_data: Record<string, any>
  gpio_config: Record<string, string>
  rules?: string
  settings?: Record<string, any>
  image_url?: string
  author?: string
  version?: string
  tags?: string[]
  public?: boolean
  downloads?: number
  rating?: number
  created_at: string
  updated_at: string
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface DeviceCommand {
  command: string
  params?: Record<string, any>
}

export interface FlashDevice {
  port: string
  description: string
  hwid: string
}

export interface Firmware {
  id: string
  name: string
  display_name?: string
  version: string
  filename?: string
  size: number
  features?: string[]
  url?: string
  download_url?: string
  chip_type: string
  variant?: string
  channel?: string
  verified?: boolean
  description?: string
  rating?: number
  rating_count?: number
  download_count?: number
  changelog?: string
  source?: string
}

export interface FlashProgress {
  step: string
  progress: number
  message?: string
}

export interface DiscoveryStatus {
  active: boolean
  found_devices: number
  scan_progress?: number
}

export interface AppConfig {
  mqtt_host: string
  mqtt_port: number
  mqtt_username: string
  mqtt_password: string
  discovery_prefix: string
  device_scan_interval: number
  auto_backup: boolean
  log_level: string
}

export interface SystemStatus {
  services: {
    mqtt: boolean
    discovery: boolean
  }
  devices_count: number
  templates_count: number
  memory_usage?: number
  cpu_usage?: number
}