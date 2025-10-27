# Evidence Seeker Platform - Production Deployment Guide

This guide provides a comprehensive step-by-step process for deploying the Evidence Seeker Platform to a production Ubuntu server. The platform consists of a FastAPI backend, React frontend, PostgreSQL database with pgvector extension, and supporting services.

## Prerequisites

### Server Requirements
- Ubuntu 20.04 LTS or later (64-bit)
- Minimum 4GB RAM, 2 CPU cores
- 20GB free disk space
- SSH access with sudo privileges
- Static IP address or domain name

### Required Software
- Docker Engine 24.0+
- Docker Compose v2.0+
- Git
- curl
- ufw (firewall)
- certbot (for SSL certificates)

## Step 1: Server Preparation

### 1.1 Update System and Install Dependencies
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose docker-buildx-plugin docker-compose-plugin

# Start and enable Docker (usually already done by installation)
sudo systemctl enable --now docker

# Add current user to docker group
sudo usermod -aG docker $USER

# Verify installation
echo "Docker installation complete. Version:"
docker --version
```

You'll need to log out and back in (or run newgrp docker) for the group membership to take effect and use Docker without sudo.

### 1.2 Configure Firewall
```bash
# Enable UFW
sudo ufw enable

# Allow SSH (change 22 to your SSH port if different)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

### 1.3 Create Application Directory
```bash
# Create application directory
sudo mkdir -p /opt/evidence-seeker-platform
sudo chown $USER:$USER /opt/evidence-seeker-platform
cd /opt/evidence-seeker-platform
```

## Step 2: Clone and Configure Application


### 2.1 add deploy key


```bash
# Generate a dedicated deploy key
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""

# Add the public key to GitHub → Repo Settings → Deploy keys
cat ~/.ssh/deploy_key.pub

# Configure SSH config (cleaner for permanent setup)
cat >> ~/.ssh/config << 'EOF'
Host github.com
    IdentityFile ~/.ssh/deploy_key
    IdentitiesOnly yes
EOF

chmod 600 ~/.ssh/config

# Then clone normally
git clone git@github.com:username/repo.git
```

### 2.2 Clone github repo

```bash
# Clone the application
git clone git@github.com:debatelab/evidence-seeker-platform.git .
git checkout main  # or your production branch
```

### 2.3 Configure Environment Variables

Create production environment files with secure secrets:

```bash
# Backend production environment
cat > backend/.env.prod << EOF
# Database
DATABASE_URL=postgresql://evidence_user:CHANGE_THIS_STRONG_PASSWORD@db:5432/evidence_seeker

# Security - Generate strong random keys
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Application
DEBUG=false
CORS_ORIGINS=["https://b7233fdd-ac70-4e21-ae82-54a2e6c682e4.ka.bw-cloud-instance.org","https://www.b7233fdd-ac70-4e21-ae82-54a2e6c682e4.ka.bw-cloud-instance.org"]
LOG_LEVEL=WARNING

# Email Configuration (configure in Step 4)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Evidence Seeker Platform

# File Upload
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=[".pdf",".txt"]
EOF

# Frontend production environment
cat > frontend/.env.prod << EOF
VITE_API_URL=https://yourdomain.com/api/v1
EOF
```

**Security Note:** Never commit these files to version control. Add `.env.prod` to your `.gitignore`.

### 2.3 Generate Encryption Key for API Keys
```bash
# Generate encryption key for storing user API keys
cd backend
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > encryption_key
chmod 600 encryption_key
```

## Step 3: Database and Docker Configuration

### 3.1 Create Docker Compose Override for Production
```bash
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_DB: evidence_seeker
      POSTGRES_USER: evidence_user
      POSTGRES_PASSWORD: CHANGE_THIS_STRONG_PASSWORD
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backup:/backup
    ports:
      - "127.0.0.1:5432:5432"  # Only accessible locally
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U evidence_user -d evidence_seeker"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - evidence-seeker-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file:
      - ./backend/.env.prod
    environment:
      - DATABASE_URL=postgresql://evidence_user:CHANGE_THIS_STRONG_PASSWORD@db:5432/evidence_seeker
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/encryption_key:/app/encryption_key:ro
    depends_on:
      db:
        condition: service_healthy
    networks:
      - evidence-seeker-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - VITE_API_URL=https://yourdomain.com/api/v1
    networks:
      - evidence-seeker-network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/certs:ro
      - ./backend/uploads:/var/www/uploads:ro
    depends_on:
      - backend
      - frontend
    networks:
      - evidence-seeker-network

volumes:
  postgres_data:
  backup:

networks:
  evidence-seeker-network:
    driver: bridge
EOF
```

### 3.2 Create Production Nginx Configuration
```bash
mkdir -p nginx
cat > nginx/prod.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Performance
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json;

    # Upstream backend
    upstream backend {
        server backend:8000;
    }

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Server block
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/ssl/certs/fullchain.pem;
        ssl_certificate_key /etc/ssl/certs/privkey.pem;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

        # Frontend
        location / {
            proxy_pass http://frontend:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # API specific settings
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Static files (uploads)
        location /uploads/ {
            alias /var/www/uploads/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF
```

## Step 4: Email Service Configuration

### 4.1 Gmail SMTP Setup
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. Update the SMTP settings in `backend/.env.prod`

### 4.2 Alternative Email Providers
For other providers, update the SMTP settings accordingly:

**SendGrid:**
```bash
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

**Mailgun:**
```bash
SMTP_SERVER=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=postmaster@yourdomain.mailgun.org
SMTP_PASSWORD=your-mailgun-password
```

## Step 5: SSL Certificate Setup

### 5.1 Install Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 5.2 Obtain SSL Certificate
```bash
# Stop nginx temporarily if running
sudo systemctl stop nginx

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Create symbolic links for nginx
sudo mkdir -p /opt/evidence-seeker-platform/ssl
sudo ln -s /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/evidence-seeker-platform/ssl/
sudo ln -s /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/evidence-seeker-platform/ssl/
```

### 5.3 Set Up Auto-Renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Add renewal hook to update symlinks
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy
sudo tee /etc/letsencrypt/renewal-hooks/deploy/update_ssl_links.sh > /dev/null << 'EOF'
#!/bin/bash
ln -sf /etc/letsencrypt/live/b7233fdd-ac70-4e21-ae82-54a2e6c682e4.ka.bw-cloud-instance.org/fullchain.pem /opt/evidence-seeker-platform/ssl/
ln -sf /etc/letsencrypt/live/b7233fdd-ac70-4e21-ae82-54a2e6c682e4.ka.bw-cloud-instance.org/privkey.pem /opt/evidence-seeker-platform/ssl/
systemctl reload nginx
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/update_ssl_links.sh
```

## Step 6: Initial User Creation

### 6.1 Modify Backend for Initial User Creation

Add an endpoint to create the first platform admin user:

```python
# Add to backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.auth import get_user_manager
from fastapi_users import BaseUserManager

router = APIRouter()

@router.post("/create-initial-admin")
async def create_initial_admin(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_async_db),
    user_manager: BaseUserManager[User, int] = Depends(get_user_manager)
):
    """Create the initial platform admin user (only works if no users exist)"""
    # Check if any users already exist
    result = await session.execute("SELECT COUNT(*) FROM users")
    user_count = result.scalar()
    
    if user_count > 0:
        raise HTTPException(status_code=400, detail="Initial admin already created")
    
    # Create the user
    user = await user_manager.create(user_data)
    
    # Mark as verified
    user.is_verified = True
    await session.commit()
    
    return {"message": "Initial admin created successfully", "user_id": user.id}
```

### 6.2 Create Initial Admin User
```bash
# Start the application temporarily to create initial user
cd /opt/evidence-seeker-platform
docker-compose -f docker-compose.prod.yml up -d db
sleep 30

# Create initial admin user via API
curl -X POST http://localhost:8000/api/v1/auth/create-initial-admin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "password": "CHANGE_THIS_STRONG_PASSWORD",
    "username": "admin",
    "is_active": true,
    "is_superuser": true,
    "is_verified": true
  }'

# Stop temporary database
docker-compose -f docker-compose.prod.yml down
```

## Step 7: Application Deployment

### 7.1 Build and Start Services
```bash
# Build and start all services
cd /opt/evidence-seeker-platform
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for services to be healthy
sleep 60

# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs
```

### 7.2 Run Database Migrations
```bash
# Run Alembic migrations
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# Create test user (optional)
docker-compose -f docker-compose.prod.yml exec backend python init_db.py
```

### 7.3 Verify Deployment
```bash
# Test health endpoints
curl -f https://yourdomain.com/health
curl -f https://yourdomain.com/api/v1/auth/test

# Check application logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
```

## Step 8: CI/CD Integration

### 8.1 Configure GitHub Actions Secrets

In your GitHub repository, add these secrets:
- `PRODUCTION_HOST`: Your server IP or domain
- `PRODUCTION_USER`: SSH username
- `PRODUCTION_SSH_KEY`: Private SSH key
- `REGISTRY_URL`: Docker registry URL
- `REGISTRY_USERNAME`: Registry username
- `REGISTRY_PASSWORD`: Registry password

### 8.2 Update Deployment Workflow

The existing `.github/workflows/deploy.yml` should work with the secrets above. Ensure the production host has the correct SSH key configured.

### 8.3 Automated Deployment
```bash
# The CI/CD pipeline will automatically deploy on pushes to main branch
# Manual deployment can be triggered from GitHub Actions tab
```

## Step 9: Database Backup Strategy

### 9.1 Create Backup Script
```bash
cat > /opt/evidence-seeker-platform/backup.sh << 'EOF'
#!/bin/bash

# Database backup script
BACKUP_DIR="/opt/evidence-seeker-platform/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/evidence_seeker_$TIMESTAMP.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U evidence_user evidence_seeker | gzip > $BACKUP_FILE

# Keep only last 30 backups
cd $BACKUP_DIR
ls -t *.sql.gz | tail -n +31 | xargs -r rm

# Log backup
echo "$(date): Database backup created: $BACKUP_FILE" >> $BACKUP_DIR/backup.log

# Optional: Upload to cloud storage (uncomment and configure)
# aws s3 cp $BACKUP_FILE s3://your-backup-bucket/
# or
# rclone copy $BACKUP_FILE remote:backup/

echo "Backup completed: $BACKUP_FILE"
EOF

chmod +x /opt/evidence-seeker-platform/backup.sh
```

### 9.2 Set Up Automated Backups
```bash
# Add to crontab for daily backups at 2 AM
(crontab -l ; echo "0 2 * * * /opt/evidence-seeker-platform/backup.sh") | crontab -

# Test backup script
/opt/evidence-seeker-platform/backup.sh
```

### 9.3 Backup Verification
```bash
# List recent backups
ls -la /opt/evidence-seeker-platform/backup/

# Verify backup integrity
gunzip -c /opt/evidence-seeker-platform/backup/evidence_seeker_*.sql.gz | head -20
```

## Step 10: Monitoring and Maintenance

### 10.1 Set Up Log Rotation
```bash
# Create logrotate configuration
cat > /etc/logrotate.d/evidence-seeker << EOF
/opt/evidence-seeker-platform/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/evidence-seeker-platform/docker-compose.prod.yml restart nginx
    endscript
}
EOF
```

### 10.2 Health Monitoring
```bash
# Create health check script
cat > /opt/evidence-seeker-platform/health_check.sh << 'EOF'
#!/bin/bash

# Health check script
HEALTH_URL="https://yourdomain.com/health"
API_URL="https://yourdomain.com/api/v1/auth/test"

# Check main health endpoint
if curl -f -s $HEALTH_URL > /dev/null; then
    echo "✓ Health check passed"
else
    echo "✗ Health check failed"
    exit 1
fi

# Check API endpoint
if curl -f -s $API_URL > /dev/null; then
    echo "✓ API check passed"
else
    echo "✗ API check failed"
    exit 1
fi

echo "All health checks passed"
EOF

chmod +x /opt/evidence-seeker-platform/health_check.sh

# Add to crontab for hourly health checks
(crontab -l ; echo "0 * * * * /opt/evidence-seeker-platform/health_check.sh >> /opt/evidence-seeker-platform/logs/health_check.log 2>&1") | crontab -
```

### 10.3 Update Management
```bash
# Create update script
cat > /opt/evidence-seeker-platform/update.sh << 'EOF'
#!/bin/bash

cd /opt/evidence-seeker-platform

# Pull latest changes
git pull origin main

# Build and deploy
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# Health check
sleep 30
./health_check.sh

echo "Update completed successfully"
EOF

chmod +x /opt/evidence-seeker-platform/update.sh
```

## Security Considerations

### 11.1 File Permissions
```bash
# Secure sensitive files
chmod 600 /opt/evidence-seeker-platform/backend/.env.prod
chmod 600 /opt/evidence-seeker-platform/ssl/privkey.pem
chmod 600 /opt/evidence-seeker-platform/backend/encryption_key

# Secure backup directory
chmod 700 /opt/evidence-seeker-platform/backup
```

### 11.2 Fail2Ban Setup
```bash
# Install and configure Fail2Ban
sudo apt install -y fail2ban

# Create jail for nginx
cat > /etc/fail2ban/jail.d/nginx.conf << EOF
[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600

[nginx-noscript]
enabled = true
port = http,https
filter = nginx-noscript
logpath = /var/log/nginx/access.log
maxretry = 6
bantime = 3600

[nginx-badbots]
enabled = true
port = http,https
filter = nginx-badbots
logpath = /var/log/nginx/access.log
maxretry = 2
bantime = 3600
EOF

sudo systemctl restart fail2ban
```

## Troubleshooting

### Common Issues

**Database Connection Issues:**
```bash
# Check database logs
docker-compose -f docker-compose.prod.yml logs db

# Test database connection
docker-compose -f docker-compose.prod.yml exec db psql -U evidence_user -d evidence_seeker -c "SELECT version();"
```

**Application Startup Issues:**
```bash
# Check application logs
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

**SSL Certificate Issues:**
```bash
# Renew certificates manually
sudo certbot renew

# Check certificate validity
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/cert.pem -text -noout | grep "Not After"
```

**Email Delivery Issues:**
```bash
# Test email configuration
docker-compose -f docker-compose.prod.yml exec backend python test_email.py
```

## Maintenance Commands

```bash
# View service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Update application
./update.sh

# Manual backup
./backup.sh

# Health check
./health_check.sh

# Scale services (if needed)
docker-compose -f docker-compose.prod.yml up -d --scale backend=2
```

## Performance Optimization

### Database Optimization
```sql
-- Run these queries in the database for optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_evidence_seeker_id ON documents(evidence_seeker_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_document_id ON embeddings(document_id);
ANALYZE;
```

### Nginx Optimization
```nginx
# Add to nginx/prod.conf under server block
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

This deployment guide provides a production-ready setup for the Evidence Seeker Platform. Follow each step carefully and test thoroughly before going live. Regular backups and monitoring are essential for maintaining a reliable service.
