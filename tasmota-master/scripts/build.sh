#!/bin/bash

# Tasmota Master - Build Script
# This script builds the add-on for testing and deployment

set -e

ADDON_NAME="tasmota-master"
VERSION=$(grep "version:" config.yaml | cut -d'"' -f2)
PLATFORMS="linux/amd64,linux/arm64,linux/arm/v7"

echo "🏗️  Building Tasmota Master Add-on v${VERSION}..."

# Validate before building
echo "🔍 Running validation..."
./scripts/validate.sh

# Build frontend if it exists
if [ -d "rootfs/app/frontend" ]; then
    echo "📦 Building frontend..."
    cd rootfs/app/frontend
    
    # Install dependencies
    if [ ! -d "node_modules" ]; then
        echo "📥 Installing dependencies..."
        npm install
    fi
    
    # Build production version
    echo "🏗️  Building production frontend..."
    npm run build
    
    cd - >/dev/null
    echo "✅ Frontend build completed"
fi

# Create build directory
BUILD_DIR="build"
mkdir -p "$BUILD_DIR"

# Function to build for specific architecture
build_arch() {
    local arch=$1
    echo "🏗️  Building for architecture: $arch"
    
    docker buildx build \
        --platform "linux/$arch" \
        --build-arg "BUILD_FROM=ghcr.io/home-assistant/${arch}-base:3.19" \
        --tag "${ADDON_NAME}:${arch}-${VERSION}" \
        --load \
        .
    
    echo "✅ Build completed for $arch"
}

# Check if Docker Buildx is available
if ! docker buildx version >/dev/null 2>&1; then
    echo "❌ Docker Buildx not available. Installing..."
    docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
    docker buildx create --name multiarch --driver docker-container --use
    docker buildx inspect --bootstrap
fi

# Build for all architectures
if [ "$1" = "--multi-arch" ]; then
    echo "🏗️  Building multi-architecture images..."
    
    docker buildx build \
        --platform "$PLATFORMS" \
        --build-arg "BUILD_FROM=ghcr.io/home-assistant/\$TARGETARCH-base:3.19" \
        --tag "${ADDON_NAME}:${VERSION}" \
        --push \
        .
    
    echo "✅ Multi-architecture build completed"
else
    # Build for local architecture only
    LOCAL_ARCH=$(uname -m)
    case "$LOCAL_ARCH" in
        x86_64) ARCH="amd64" ;;
        aarch64) ARCH="arm64" ;;
        armv7l) ARCH="armv7" ;;
        *) ARCH="amd64" ;;
    esac
    
    build_arch "$ARCH"
fi

# Test the built image
echo "🧪 Testing built image..."
if docker run --rm "${ADDON_NAME}:${ARCH:-$VERSION}-${VERSION}" python3 -c "print('Build test successful!')" >/dev/null 2>&1; then
    echo "✅ Image test passed"
else
    echo "❌ Image test failed"
    exit 1
fi

# Create build information
cat > "$BUILD_DIR/build-info.json" <<EOF
{
  "name": "Tasmota Master",
  "version": "$VERSION",
  "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "architecture": "${ARCH:-multi}",
  "git_commit": "$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')",
  "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')"
}
EOF

echo "✅ Build information saved to $BUILD_DIR/build-info.json"

# Generate deployment files
echo "📄 Generating deployment files..."

# Create deployment README
cat > "$BUILD_DIR/README.md" <<EOF
# Tasmota Master Deployment

## Build Information
- Version: $VERSION
- Build Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Architecture: ${ARCH:-multi-arch}

## Deployment

### Home Assistant Add-on Store
1. Add custom repository: \`https://github.com/yourusername/tasmota-master\`
2. Install "Tasmota Master" add-on
3. Configure and start

### Manual Docker Deployment
\`\`\`bash
docker run -d \\
  --name tasmota-master \\
  --network host \\
  -v /path/to/data:/app/data \\
  ${ADDON_NAME}:${ARCH:-$VERSION}-${VERSION}
\`\`\`

## Configuration
See DOCS.md for detailed configuration options.
EOF

echo "📋 Build Summary:"
echo "   Name: Tasmota Master"
echo "   Version: $VERSION"
echo "   Architecture: ${ARCH:-multi-arch}"
echo "   Image: ${ADDON_NAME}:${ARCH:-$VERSION}-${VERSION}"
echo "   Build files: $BUILD_DIR/"
echo ""
echo "🚀 Build completed successfully!"
echo ""
echo "Next steps:"
echo "1. Test the built image locally"
echo "2. Push to GitHub repository"
echo "3. Create release tag: v$VERSION"
echo "4. Add to HACS"