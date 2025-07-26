# 🚀 Tasmota Master - Deployment Guide

## Pre-Deployment Checklist

### ✅ **Required Steps Before GitHub Upload**

1. **Update Repository URLs:**
   - Replace `yourusername` with your GitHub username in:
     - `config.yaml` (image and url fields)
     - `build.yaml` (source field)  
     - `repository.yaml` (url and maintainer)
     - `.github/workflows/*.yml` (repository references)

2. **Add Required Assets:**
   - **icon.png**: 512x512 pixel icon for the add-on
   - **logo.png**: 256x256 pixel logo for the add-on store
   - Both should be professional quality PNG files

3. **Update Personal Information:**
   - `repository.yaml`: Update maintainer name and email
   - `LICENSE`: Update copyright holder name
   - `DOCS.md`: Update any placeholder information

## GitHub Repository Setup

### 1. **Create Repository**
```bash
# Create new repository on GitHub
# Name: tasmota-master
# Description: Complete Tasmota device management suite for Home Assistant
# Public repository (required for HACS)
```

### 2. **Upload Files**
```bash
git init
git add .
git commit -m "Initial release of Tasmota Master v1.0.0"
git branch -M main
git remote add origin https://github.com/yourusername/tasmota-master.git
git push -u origin main
```

### 3. **Create First Release**
```bash
# Create and push tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Create release on GitHub:
# - Go to Releases → Create new release
# - Tag: v1.0.0
# - Title: "Tasmota Master v1.0.0 - Initial Release"
# - Description: Copy from CHANGELOG.md
```

## Home Assistant Testing

### **Method 1: HACS Custom Repository (Recommended)**

1. **Add Custom Repository:**
   ```
   HACS → Add-ons → ⋮ menu → Custom repositories
   Repository: https://github.com/yourusername/tasmota-master
   Category: Add-on
   ```

2. **Install Add-on:**
   - Find "Tasmota Master" in HACS add-ons
   - Click Install
   - Wait for installation

3. **Configure:**
   ```yaml
   # Basic configuration
   mqtt_host: core-mosquitto
   mqtt_port: 1883
   mqtt_username: ""
   mqtt_password: ""
   log_level: info
   ```

4. **Start and Test:**
   - Start the add-on
   - Check logs for any errors
   - Open Web UI from add-on info page

### **Method 2: Manual Installation**

1. **Copy Files:**
   ```bash
   # Copy to Home Assistant addons folder
   cp -r tasmota-master /path/to/homeassistant/addons/
   ```

2. **Restart Home Assistant:**
   ```bash
   # Restart to detect new add-on
   systemctl restart home-assistant
   ```

3. **Install from Supervisor:**
   - Go to Supervisor → Add-on Store
   - Refresh if needed
   - Install "Tasmota Master"

## Production Testing

### **Essential Tests**

1. **Add-on Startup:**
   - ✅ Add-on starts without errors
   - ✅ Web UI accessible at ingress URL
   - ✅ All backend services initialize

2. **MQTT Integration:**
   - ✅ Connects to MQTT broker
   - ✅ Discovers existing Tasmota devices
   - ✅ Can send commands to devices

3. **Device Discovery:**
   - ✅ mDNS discovery works
   - ✅ Network scanning finds devices
   - ✅ Manual device addition works

4. **Firmware Management:**
   - ✅ Downloads firmware list
   - ✅ Shows recommendations
   - ✅ Cache management works

5. **Web Interface:**
   - ✅ All tabs load correctly
   - ✅ Device list populates
   - ✅ Real-time updates work
   - ✅ Mobile responsive

### **Advanced Tests**

1. **Firmware Flashing:**
   - ✅ Detects connected ESP devices
   - ✅ Downloads and caches firmware
   - ✅ Flashing process works (if hardware available)

2. **Community Features:**
   - ✅ Firmware upload works
   - ✅ Rating system functions
   - ✅ Community firmware display

3. **Analytics:**
   - ✅ Analytics dashboard loads
   - ✅ Background tasks run
   - ✅ Insights generation works

## HACS Official Submission

### **Prerequisites for Official HACS**

1. **Repository Requirements:**
   - ✅ Public GitHub repository
   - ✅ Proper README.md
   - ✅ Valid license file
   - ✅ Release tags with semantic versioning

2. **Code Quality:**
   - ✅ Passes all validation checks
   - ✅ No critical security issues
   - ✅ Follows Home Assistant best practices
   - ✅ Good documentation

3. **Testing:**
   - ✅ Tested on multiple architectures
   - ✅ Works with different HA versions
   - ✅ No breaking changes to HA

### **Submission Process**

1. **Ensure Requirements:**
   - Minimum 2 weeks of testing
   - At least 10 GitHub stars
   - Active maintenance (responses to issues)

2. **Submit to HACS:**
   ```
   Go to: https://github.com/hacs/default
   Create PR to add repository to default.json:
   
   {
     "name": "Tasmota Master",
     "domain": "tasmota_master", 
     "repo": "yourusername/tasmota-master",
     "category": "addon"
   }
   ```

3. **Review Process:**
   - HACS team reviews code
   - May request changes
   - Once approved, available in default HACS

## Monitoring and Maintenance

### **Release Process**

1. **Update Version:**
   ```yaml
   # config.yaml
   version: "1.1.0"
   ```

2. **Update Changelog:**
   ```markdown
   ## [1.1.0] - 2025-XX-XX
   ### Added
   - New feature descriptions
   ### Fixed  
   - Bug fix descriptions
   ```

3. **Create Release:**
   ```bash
   git tag -a v1.1.0 -m "Release version 1.1.0"
   git push origin v1.1.0
   # GitHub Actions will build and publish automatically
   ```

### **Issue Management**

1. **Respond to Issues:**
   - Use GitHub issue templates
   - Provide clear reproduction steps
   - Fix critical issues promptly

2. **Feature Requests:**
   - Evaluate community feedback
   - Prioritize most requested features
   - Maintain roadmap in README

### **Community Engagement**

1. **Documentation:**
   - Keep docs up to date
   - Add FAQ for common issues
   - Create video tutorials if possible

2. **Support Channels:**
   - Monitor GitHub issues
   - Participate in HA community forums
   - Respond to social media mentions

## Success Metrics

### **Launch Success Indicators:**

- ✅ Add-on installs without errors
- ✅ Web UI loads and functions properly  
- ✅ MQTT integration works out of box
- ✅ Device discovery finds devices
- ✅ No critical bugs in first week

### **Long-term Success:**

- 📈 Growing number of installations
- 📈 Positive community feedback
- 📈 Active issue resolution
- 📈 Feature requests and contributions
- 📈 Integration with other HA add-ons

## Troubleshooting Deployment

### **Common Issues:**

1. **Docker Build Fails:**
   - Check all imports are available
   - Verify requirements.txt versions
   - Test on multiple architectures

2. **Add-on Won't Start:**
   - Check config.yaml syntax
   - Verify all required files present
   - Review add-on logs

3. **MQTT Connection Issues:**
   - Verify MQTT broker accessible
   - Check network connectivity
   - Validate credentials

4. **Permission Errors:**
   - Ensure service scripts executable
   - Check file ownership
   - Verify container permissions

### **Getting Help:**

- Check existing GitHub issues
- Review Home Assistant add-on docs
- Ask in HA Discord #add-on-development
- Consult HACS documentation

---

🎉 **You're ready to deploy Tasmota Master!**

This is a comprehensive system that will revolutionize Tasmota device management. Good luck with the launch! 🚀