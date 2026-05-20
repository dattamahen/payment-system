# EventPay SaaS - Multi-Tenant WhatsApp Event Registration & Payment Platform

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Ionic Angular  │────▶│  FastAPI Backend  │────▶│   MongoDB   │
│   (Frontend)    │     │   (REST API)      │     │  (Database) │
└─────────────────┘     └──────────────────┘     └─────────────┘
                              │       │
                    ┌─────────┘       └──────────┐
                    ▼                             ▼
             ┌───────────┐                ┌─────────────┐
             │   Redis   │                │     n8n     │
             │ (Sessions │                │ (Workflows) │
             │  & Cache) │                └─────────────┘
             └───────────┘                       │
                    │                            ▼
                    ▼                   ┌─────────────────┐
          ┌──────────────────┐         │  Google Sheets  │
          │  WhatsApp Cloud  │         │   Razorpay      │
          │      API         │         └─────────────────┘
          └──────────────────┘
```

## Multi-Tenant Isolation Strategy

| Layer | Strategy |
|-------|----------|
| Database | `tenant_id` field on every collection, compound indexes |
| API | JWT contains `tenant_id`, injected via dependency |
| Redis | Key prefix `{tenant_id}:session:{phone}` |
| Secrets | Per-tenant encrypted credentials (Fernet) |
| n8n | Workflow payloads include `tenant_id` for routing |

## MongoDB Indexes (create on startup)

```javascript
db.tenants.createIndex({ slug: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ tenant_id: 1 });
db.events.createIndex({ tenant_id: 1, slug: 1 }, { unique: true });
db.events.createIndex({ tenant_id: 1, status: 1 });
db.forms.createIndex({ tenant_id: 1 });
db.registrations.createIndex({ tenant_id: 1, event_id: 1 });
db.registrations.createIndex({ phone: 1, tenant_id: 1, status: 1 });
db.registrations.createIndex({ "payment.razorpay_order_id": 1 });
db.webhook_logs.createIndex({ created_at: 1 }, { expireAfterSeconds: 604800 }); // TTL 7 days
```

## Scalability Recommendations

1. **Horizontal Scaling**
   - Stateless FastAPI behind load balancer (Nginx/ALB)
   - Redis for session state (not in-memory) enables multi-instance
   - MongoDB replica set for read scaling

2. **Caching**
   - Cache tenant config in Redis (TTL 5min) — avoids DB hit per webhook
   - Cache active event lookups per tenant
   - Cache form definitions (rarely change)

3. **Async Processing**
   - WhatsApp webhook → immediate 200 response → process via background task/Celery
   - Google Sheets sync via n8n workflow (batch, not per-registration)
   - Payment webhook processing in background

4. **Database**
   - MongoDB sharding on `tenant_id` for horizontal scale
   - Archive completed registrations older than 6 months to cold storage
   - Use MongoDB Change Streams to trigger n8n workflows

5. **Rate Limiting**
   - Redis-based rate limiting per tenant (prevent abuse)
   - WhatsApp API rate limits respected via queue

6. **Infrastructure**
   - Deploy on AWS ECS/EKS or equivalent
   - MongoDB Atlas for managed DB with auto-scaling
   - ElastiCache for managed Redis
   - CloudFront CDN for frontend

## Security Recommendations

1. **Authentication & Authorization**
   - JWT with short-lived access tokens (30min) + refresh tokens
   - Role-based access: `super_admin`, `tenant_admin`, `tenant_member`
   - All tenant queries filtered by `tenant_id` from JWT (never from request body)

2. **Data Encryption**
   - Tenant secrets (API keys) encrypted at rest with Fernet
   - TLS everywhere (HTTPS, MongoDB TLS, Redis TLS)
   - Environment variables for server secrets, never in code

3. **Webhook Security**
   - WhatsApp: Verify `hub.verify_token` on subscription
   - Razorpay: HMAC signature verification on every webhook
   - IP whitelisting for webhook endpoints where possible

4. **Input Validation**
   - Pydantic schemas validate all inputs
   - Sanitize WhatsApp message content before processing
   - File upload size limits and type validation

5. **Multi-Tenant Isolation**
   - Never expose one tenant's data to another
   - Compound indexes enforce tenant boundary at DB level
   - Separate encryption keys per tenant (future enhancement)

6. **Operational Security**
   - Webhook logs with TTL (auto-delete after 7 days)
   - Audit log for admin actions
   - Rate limiting per tenant and per IP
   - CORS restricted to known frontend domains in production

## Running Locally

```bash
# Start infrastructure
docker-compose up -d mongodb redis n8n

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (requires Ionic CLI)
cd frontend
npm install
ionic serve
```
