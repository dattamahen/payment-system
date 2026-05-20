#!/bin/bash
# EventPay Production Deployment Script
# Run on a fresh Ubuntu 22.04 VPS
# Usage: chmod +x deploy.sh && ./deploy.sh

set -e

DOMAIN=${1:-"yourdomain.com"}
EMAIL=${2:-"admin@yourdomain.com"}

echo "============================================"
echo "  EventPay Production Deployment"
echo "  Domain: $DOMAIN"
echo "============================================"

# Update system
echo "[1/8] Updating system..."
apt-get update && apt-get upgrade -y

# Install Docker
echo "[2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Install Docker Compose
echo "[3/8] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt-get install -y docker-compose-plugin
fi

# Clone repo
echo "[4/8] Setting up application..."
cd /opt
if [ ! -d "eventpay" ]; then
    git clone https://github.com/dattamahen/payment-system.git eventpay
fi
cd eventpay

# Generate secrets
echo "[5/8] Generating secrets..."
JWT_SECRET=$(openssl rand -hex 32)
N8N_API_KEY=$(openssl rand -hex 16)
MONGO_PASS=$(openssl rand -hex 16)
REDIS_PASS=$(openssl rand -hex 16)
N8N_PASS=$(openssl rand -hex 12)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || pip3 install cryptography && python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create production .env
cat > backend/.env.prod << EOF
APP_NAME=EventPay SaaS
DEBUG=false
API_V1_PREFIX=/api/v1

MONGODB_URL=mongodb://eventpay:${MONGO_PASS}@mongodb:27017/eventpay?authSource=admin
MONGODB_DB_NAME=eventpay

REDIS_URL=redis://:${REDIS_PASS}@redis:6379
REDIS_ENABLED=true

JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

ALLOWED_ORIGINS=["https://${DOMAIN}"]

WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_VERIFY_TOKEN=$(openssl rand -hex 8)

N8N_BASE_URL=http://n8n:5678
N8N_API_KEY=${N8N_API_KEY}

ENCRYPTION_KEY=${ENCRYPTION_KEY}

ADMIN_EMAIL=sancham-admin@eventpay.com
ADMIN_PASSWORD=sancham@1729
EOF

# Create .env for docker-compose
cat > .env << EOF
DOMAIN=${DOMAIN}
MONGO_USER=eventpay
MONGO_PASS=${MONGO_PASS}
REDIS_PASS=${REDIS_PASS}
N8N_USER=admin
N8N_PASS=${N8N_PASS}
EOF

# Setup SSL directory (temporary self-signed for first boot)
echo "[6/8] Setting up SSL..."
mkdir -p nginx/ssl
if [ ! -f nginx/ssl/fullchain.pem ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem \
        -out nginx/ssl/fullchain.pem \
        -subj "/CN=${DOMAIN}"
fi

# Install Certbot for real SSL
echo "[7/8] Setting up Let's Encrypt..."
apt-get install -y certbot
certbot certonly --standalone --non-interactive --agree-tos \
    --email ${EMAIL} -d ${DOMAIN} || echo "Certbot failed - using self-signed cert. Run certbot manually later."

# Copy real certs if available
if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem nginx/ssl/fullchain.pem
    cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem nginx/ssl/privkey.pem
fi

# Deploy
echo "[8/8] Starting services..."
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "  App:     https://${DOMAIN}"
echo "  n8n:     https://${DOMAIN}/n8n/"
echo "  API:     https://${DOMAIN}/api/v1"
echo ""
echo "  Admin credentials saved in: backend/.env.prod"
echo "  (look for ADMIN_EMAIL and ADMIN_PASSWORD)"
echo ""
echo "  n8n login: admin / ${N8N_PASS}"
echo ""
echo "  IMPORTANT: Update Meta webhook URL to:"
echo "  https://${DOMAIN}/webhook/whatsapp-webhook"
echo ""
echo "  Setup SSL auto-renewal:"
echo "  crontab -e"
echo "  0 0 1 * * certbot renew && cp /etc/letsencrypt/live/${DOMAIN}/*.pem /opt/eventpay/nginx/ssl/ && docker compose -f /opt/eventpay/docker-compose.prod.yml restart nginx"
echo "============================================"
