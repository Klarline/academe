#!/bin/bash
# EC2 User Data Script - Automated Setup for Academe
# This script runs on first boot to configure the server

set -e

echo "========================================="
echo "Academe Server Setup - Starting"
echo "========================================="

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
echo "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Git
apt-get install -y git

# Install Nginx
echo "Installing Nginx..."
apt-get install -y nginx

# Clone repository
echo "Cloning Academe repository..."
cd /home/ubuntu
git clone https://github.com/Klarline/academe.git
cd academe

# Log in to Docker Hub
echo "Logging in to Docker Hub..."
echo "${docker_password}" | docker login -u "${docker_username}" --password-stdin

# Create production environment file
echo "Creating production .env file..."
cat > backend/.env << EOF
# Production Environment Variables
GOOGLE_API_KEY=${google_api_key}
MONGODB_URI=${mongodb_uri}
JWT_SECRET_KEY=${jwt_secret_key}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
PINECONE_API_KEY=${pinecone_api_key}
PINECONE_INDEX_NAME=${pinecone_index_name}
CELERY_BROKER_URL=redis://redis:6379/0
LOG_LEVEL=INFO
EOF

# Pull latest images
echo "Pulling Docker images..."
docker-compose pull

# Start services
echo "Starting services..."
docker-compose up -d

# Configure Nginx reverse proxy
echo "Configuring Nginx..."
cat > /etc/nginx/sites-available/academe << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    # Frontend proxy (will be on Vercel, but keeping for reference)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }

    # Prometheus metrics (restrict in production!)
    location /metrics {
        proxy_pass http://localhost:8000/metrics;
        # TODO: Add IP whitelist for security
    }
}
NGINX_EOF

# Enable site
ln -sf /etc/nginx/sites-available/academe /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
nginx -t
systemctl reload nginx

# Set up log rotation for Docker
cat > /etc/logrotate.d/docker << 'LOGROTATE_EOF'
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
LOGROTATE_EOF

# Change ownership
chown -R ubuntu:ubuntu /home/ubuntu/academe

echo "========================================="
echo "Academe Server Setup - Complete!"
echo "========================================="
echo "Services running:"
docker-compose ps
echo ""
echo "Backend API: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
echo "Health check: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/api/health"
