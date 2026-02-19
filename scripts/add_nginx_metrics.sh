#!/bin/bash
# Add missing Nginx routes for metrics and health

ssh -i ~/.ssh/academe-key ubuntu@54.200.230.109 << 'ENDSSH'

# Backup current config
sudo cp /etc/nginx/sites-available/academe /etc/nginx/sites-available/academe.backup

# Create updated config with metrics and health
sudo tee /etc/nginx/sites-available/academe > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
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

    # API documentation
    location /docs {
        proxy_pass http://localhost:8000/docs;
    }

    location /openapi.json {
        proxy_pass http://localhost:8000/openapi.json;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }

    # Prometheus metrics
    location /metrics {
        proxy_pass http://localhost:8000/metrics;
    }
}
EOF

# Test and reload
sudo nginx -t && sudo systemctl reload nginx

echo "Nginx updated successfully!"
echo "Test: curl http://localhost/metrics"

ENDSSH
