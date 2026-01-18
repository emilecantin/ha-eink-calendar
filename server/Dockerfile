FROM node:20-slim

# Install canvas dependencies (cairo, pango, etc.) and symbol fonts
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    fonts-dejavu-core \
    fonts-symbola \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f -v

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including devDependencies for TypeScript types)
RUN npm ci

# Copy source files and fonts
COPY *.ts ./
COPY fonts/ ./fonts/

# Expose port
EXPOSE 4000

# Run with ts-node
CMD ["npx", "ts-node", "index.ts"]
