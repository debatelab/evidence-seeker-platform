########## Build Stage ##########
FROM node:20-alpine AS build

WORKDIR /app

# Copy frontend-specific package manifests first for better caching
COPY package.json package-lock.json ./
COPY . ./

# Install dependencies (with caching)
RUN npm ci --legacy-peer-deps

# Build production assets
RUN npm run build --workspace=frontend

########## Runtime Stage ##########
FROM nginx:alpine AS runtime

# Copy built frontend assets
COPY --from=build /app/frontend/dist /usr/share/nginx/html

# Copy nginx configuration (correct relative path for CI context)
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 3000
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
