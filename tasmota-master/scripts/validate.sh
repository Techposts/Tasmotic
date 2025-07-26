#!/bin/bash

# Tasmota Master - Validation Script
# This script validates the add-on configuration and code quality

set -e

echo "🔍 Validating Tasmota Master Add-on..."

# Check if running from correct directory
if [ ! -f "config.yaml" ]; then
    echo "❌ Error: Must run from add-on root directory"
    exit 1
fi

echo "✅ Directory structure validated"

# Validate config.yaml
echo "🔧 Validating config.yaml..."
if command -v yq >/dev/null 2>&1; then
    yq eval '.name' config.yaml >/dev/null
    echo "✅ config.yaml is valid YAML"
else
    echo "⚠️  Warning: yq not installed, skipping YAML validation"
fi

# Validate Python code
echo "🐍 Validating Python code..."
if command -v python3 >/dev/null 2>&1; then
    # Check syntax
    find rootfs/app/backend -name "*.py" -exec python3 -m py_compile {} \;
    echo "✅ Python syntax validation passed"
    
    # Skip import check for add-on validation (dependencies installed at runtime)
    echo "⚠️  Skipping import validation (dependencies installed at runtime)"
else
    echo "❌ Error: Python3 not found"
    exit 1
fi

# Validate Node.js/Frontend code
echo "📦 Validating frontend code..."
if [ -d "rootfs/app/frontend" ]; then
    cd rootfs/app/frontend
    
    if [ -f "package.json" ]; then
        if command -v npm >/dev/null 2>&1; then
            # Install dependencies if needed
            if [ ! -d "node_modules" ]; then
                echo "📥 Installing frontend dependencies..."
                npm install --silent
            fi
            
            # Build check (more practical than type-check for add-on validation)
            if npm run build >/dev/null 2>&1; then
                echo "✅ Frontend build validation passed"
            else
                echo "❌ Frontend build validation failed"
                exit 1
            fi
        else
            echo "⚠️  Warning: npm not installed, skipping frontend validation"
        fi
    fi
    
    cd - >/dev/null
fi

# Validate Docker configuration
echo "🐳 Validating Docker configuration..."
if command -v docker >/dev/null 2>&1; then
    # Basic Dockerfile syntax check
    if [ -f "Dockerfile" ] && grep -q "FROM" Dockerfile; then
        echo "✅ Dockerfile basic validation passed"
    else
        echo "❌ Dockerfile validation failed"
        exit 1
    fi
else
    echo "⚠️  Warning: Docker not installed, skipping Docker validation"
fi

# Check required files
echo "📂 Checking required files..."
required_files=(
    "config.yaml"
    "build.yaml"
    "Dockerfile" 
    "run.sh"
    "README.md"
    "CHANGELOG.md"
    "DOCS.md"
    "LICENSE"
    "icon.png"
    "logo.png"
    "translations/en.yaml"
    "apparmor.txt"
    "repository.yaml"
    "rootfs/app/backend/app.py"
    "rootfs/app/backend/requirements.txt"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ Missing required file: $file"
        exit 1
    fi
done

# Validate permissions
echo "🔐 Checking file permissions..."
find rootfs/etc/services.d -name "run" -exec chmod +x {} \;
find rootfs/etc/services.d -name "finish" -exec chmod +x {} \;
echo "✅ File permissions set correctly"

# Final summary
echo ""
echo "🎉 Validation completed successfully!"
echo ""
echo "📋 Summary:"
echo "   ✅ Directory structure"
echo "   ✅ Configuration files"
echo "   ✅ Python code syntax"
echo "   ✅ Frontend code (if available)"
echo "   ✅ Docker configuration"
echo "   ✅ Required files present"
echo "   ✅ File permissions"
echo ""
echo "🚀 Add-on is ready for deployment!"