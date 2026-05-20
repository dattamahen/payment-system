# EventPay - Deployment Guide

## Local Development

```bash
# Start all services
start-all.bat

# Or manually:
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm start
# MongoDB, Redis, n8n must be running
```

## Production Deployment (VPS)

### Prerequisites
- Ubuntu 22.04 VPS (min 4GB RAM)
- Domain pointing to VPS IP
- SSH access

### One-command deploy

```bash
ssh root@your-vps-ip
curl -fsSL https://raw.githubusercontent.com/dattamahen/payment-system/main/deploy.sh -o deploy.sh
chmod +x deploy.sh
./deploy.sh yourdomain.com your-email@example.com
```

### Manual deploy

```bash
# 1. Clone
git clone https://github.com/dattamahen/payment-system.git /opt/eventpay
cd /opt/eventpay

# 2. Configure
cp backend/.env.prod.example backend/.env.prod
# Edit backend/.env.prod with your values

# 3. SSL
mkdir -p nginx/ssl
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/

# 4. Deploy
docker compose -f docker-compose.prod.yml up -d --build
```

### Post-deployment

1. **Update Meta webhook URL** to `https://yourdomain.com/webhook/whatsapp-webhook`
2. **Import n8n workflows** at `https://yourdomain.com/n8n/`
   - Update "Handle Message (Backend)" URL to `http://backend:8000/api/v1/n8n/session/message`
3. **Login** at `https://yourdomain.com` with credentials from `.env.prod`

### SSL Auto-renewal

```bash
crontab -e
# Add:
0 0 1 * * certbot renew && cp /etc/letsencrypt/live/yourdomain.com/*.pem /opt/eventpay/nginx/ssl/ && cd /opt/eventpay && docker compose -f docker-compose.prod.yml restart nginx
```

### Monitoring

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Check health
curl https://yourdomain.com/health

# Restart
docker compose -f docker-compose.prod.yml restart
```

## Architecture

```
Internet → Nginx (SSL + Rate Limiting)
              ├── /api/*        → Backend (FastAPI, 4 workers)
              ├── /webhook/*    → Backend → n8n
              ├── /n8n/*        → n8n Dashboard
              └── /*            → Frontend (Angular)

Backend → MongoDB (data)
       → Redis (sessions)
       → n8n (workflow orchestration)
       → WhatsApp API (messaging)
       → Razorpay (payments)
       → Google Sheets (sync)
```
