## Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Copy root workspace manifests and lockfile (includes frontend workspace)
COPY package.json package-lock.json ./
# Copy only the frontend workspace package manifest initially for dependency resolution caching
COPY frontend/package.json frontend/package.json

# Install all workspaces (will include frontend). Use ci for reproducibility.
RUN npm ci --omit=dev

# Copy frontend source (only after deps for better caching)
COPY frontend ./frontend

WORKDIR /app/frontend
RUN npm run build

## Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/frontend/dist /usr/share/nginx/html

# Copy nginx configuration (source path relative to root build context)
COPY frontend/nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
