ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies including bashio for Home Assistant add-ons
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nodejs \
    npm \
    nginx \
    git \
    curl \
    avahi-tools \
    mosquitto-clients \
    && rm -rf /var/cache/apk/*

# Install bashio for Home Assistant add-on integration
RUN pip3 install --no-cache-dir bashio

# Install Python dependencies
COPY rootfs/app/backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Create app user and directories
RUN addgroup -g 1000 app && \
    adduser -D -s /bin/bash -u 1000 -G app app && \
    mkdir -p /opt/app/data /opt/app/logs /opt/app/config && \
    chown -R app:app /opt/app

# Copy application files
COPY rootfs/ /

# Build frontend
WORKDIR /opt/app/frontend
RUN npm install --legacy-peer-deps && npm run build

# Set working directory
WORKDIR /opt/app

# Make scripts executable
RUN chmod +x /etc/services.d/*/run /etc/services.d/*/finish

# Copy nginx configuration
COPY rootfs/etc/nginx/nginx.conf /etc/nginx/nginx.conf

# Expose port for ingress
EXPOSE 8099

# Copy run script and make executable
COPY run.sh /
RUN chmod +x /run.sh

# Use run.sh as entry point for Home Assistant add-on compatibility
CMD ["/run.sh"]

# Labels
LABEL \
    io.hass.name="Tasmota Master" \
    io.hass.description="Complete Tasmota device management suite" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"