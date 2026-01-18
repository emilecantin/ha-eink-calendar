# EPCAL Add-on Dockerfile
# Using Node.js base for canvas support

ARG BUILD_FROM=node:20-slim
FROM ${BUILD_FROM}

# Install canvas dependencies and bashio for HA Supervisor API
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    fonts-dejavu-core \
    fonts-symbola \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f -v

# Install bashio for Home Assistant Supervisor API integration
ARG BASHIO_VERSION=0.16.2
RUN curl -L -s "https://github.com/hassio-addons/bashio/archive/v${BASHIO_VERSION}.tar.gz" \
    | tar -xzf - -C /tmp \
    && mv /tmp/bashio-${BASHIO_VERSION}/lib /usr/lib/bashio \
    && ln -s /usr/lib/bashio/bashio /usr/bin/bashio \
    && rm -rf /tmp/bashio-${BASHIO_VERSION}

WORKDIR /app

# Copy package files and install dependencies
COPY server/package*.json ./
RUN npm ci

# Copy server source files and fonts
COPY server/*.ts ./
COPY server/fonts/ ./fonts/

# Pre-compile TypeScript to JavaScript
RUN npx tsc --outDir ./dist --esModuleInterop --module commonjs --target ES2020 --resolveJsonModule *.ts

# Copy startup script
COPY addon/run.sh /run.sh
RUN chmod +x /run.sh

# Expose port for API and Ingress
EXPOSE 4000

# Labels for Home Assistant
LABEL \
    io.hass.name="EPCAL" \
    io.hass.description="E-Paper Calendar Display" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

CMD ["/run.sh"]
