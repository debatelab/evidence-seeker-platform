########## Base Builder (with cache) ##########
FROM --platform=linux/amd64 node:24-bullseye AS base
WORKDIR /app

# Copy root and frontend manifests (for dependency layer cache)
COPY package*.json ./
COPY frontend/package*.json ./frontend/

# Install dependencies *only once per package.json change*
RUN npm ci --legacy-peer-deps

########## Build Stage ##########
FROM base AS build
WORKDIR /app/frontend

# Copy frontend source only (does not break cache unless code changes)
COPY frontend/ ./

# Build production assets
RUN npm run build

########## Runtime Stage ##########
FROM nginx:1.27-bookworm AS runtime

# Copy built frontend assets
COPY --from=build /app/frontend/dist /usr/share/nginx/html

# Copy nginx config
COPY frontend/nginx.conf /etc/nginx/nginx.conf

# Expose and start
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["nginx", "-g", "daemon off;"]
