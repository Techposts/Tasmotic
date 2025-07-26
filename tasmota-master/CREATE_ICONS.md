# Icon Creation Guide

## Required Icons

### icon.png (512x512 pixels)
- **Purpose**: Main add-on icon in Home Assistant
- **Size**: 512x512 pixels
- **Format**: PNG with transparency
- **Theme**: Tasmota device management

### logo.png (256x256 pixels) 
- **Purpose**: Add-on store and documentation
- **Size**: 256x256 pixels
- **Format**: PNG with transparency
- **Theme**: Tasmota device management

## Design Suggestions

### Icon Concept
- Central microchip or ESP32/ESP8266 symbol
- Surrounding elements: WiFi waves, smart home icons
- Color scheme: Blue/green tech colors
- Modern, clean design

### Logo Concept
- Text "Tasmota Master" with icon
- Or simplified version of the icon
- Professional, readable at small sizes

## Quick Creation Options

### Option 1: AI Image Generators
- Use DALL-E, Midjourney, or Stable Diffusion
- Prompt: "Modern technology icon for IoT device management, 512x512 pixels, microchip with WiFi waves, blue and green colors, transparent background"

### Option 2: Icon Libraries
- Check Flaticon, Icons8, or Material Design Icons
- Search for: microchip, IoT, smart home, WiFi
- Customize colors and combine elements

### Option 3: Simple Design Tools
- Canva, Figma, or Adobe Express
- Use templates and modify
- Export as high-resolution PNG

## Once Created
Place both files in the project root directory:
- `/icon.png`
- `/logo.png`

The build system will automatically include them in the add-on package.