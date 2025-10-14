########## Build Stage ##########
FROM node:20-bullseye AS build

WORKDIR /app

# Disable npm optional deps (rollup's platform binaries cause issues)
ENV npm_config_optional=false

# Copy manifests first for caching
COPY package.json package-lock.json ./
COPY frontend/package.json ./frontend/

# Force-clean and reinstall dependencies fresh (no alpine-locked modules)
RUN rm -rf node_modules package-lock.json && \
    npm install --legacy-peer-deps

# Copy source AFTER installing deps
COPY frontend/ ./frontend/

# Build production assets
RUN npm run build --workspace=frontend

########## Runtime Stage ##########
FROM nginx:1.27-bullseye AS runtime

WORKDIR /usr/share/nginx/html

# Copy built frontend assets
COPY --from=build /app/frontend/dist ./

# Copy nginx configuration
COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["nginx", "-g", "daemon off;"]
