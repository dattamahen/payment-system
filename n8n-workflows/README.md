# n8n Workflows Setup Guide

## Architecture

**Single workflow handles ALL tenants and ALL events automatically.**

The backend manages conversation state — n8n is just a thin relay between WhatsApp and the backend API.

```
User (WhatsApp) → n8n (relay) → Backend API (conversation logic) → n8n → WhatsApp reply
```

## Prerequisites
- n8n running: `npx n8n start` (port 5678)
- Backend running (port 8000)
- WhatsApp Business API access (Meta Developer account)
- `N8N_API_KEY` set in backend `.env`

## Environment Variables (n8n Settings → Variables)

| Variable | Value | Notes |
|----------|-------|-------|
| `BACKEND_URL` | `https://your-api.com` | Backend URL |
| `N8N_API_KEY` | `your-secret-key` | Must match backend `.env` |
| `WA_ACCESS_TOKEN` | `EAAxxxxxxx` | WhatsApp Business API token |
| `WA_PHONE_NUMBER_ID` | `1234567890` | For payment confirmation replies |

**No TENANT_ID or EVENT_ID needed!** Everything is resolved dynamically.

## How It Works

### Registration Flow:
1. User sends any message to tenant's WhatsApp number
2. n8n receives webhook → sends to `POST /api/v1/n8n/session/message`
3. Backend resolves tenant from WhatsApp number
4. Backend finds active events for that tenant
5. If multiple events → asks user to choose
6. Asks registration questions one by one
7. After all answered:
   - Free event → marks complete, syncs to sheet
   - Paid event → creates UPI payment link, sends to user
8. Returns reply text → n8n sends via WhatsApp

### Payment Confirmation:
1. User pays via UPI link
2. Razorpay sends webhook to n8n
3. n8n parses payment → sends confirmation via WhatsApp
4. Syncs to Google Sheet

## Import Workflows

1. Open n8n UI (`http://localhost:5678`)
2. Workflows → Import from File
3. Import `registration-flow.json`
4. Import `payment-confirmation.json`
5. Set environment variables
6. Activate both workflows

## Webhook URLs to Configure

### WhatsApp (Meta Developer Dashboard):
```
https://your-n8n-domain.com/webhook/whatsapp-webhook
```
Verify token: set in Meta dashboard, n8n handles verification.

### Razorpay (Dashboard → Settings → Webhooks):
```
https://your-n8n-domain.com/webhook/payment-confirmed
```
Events: `payment_link.paid`, `payment.captured`

## Multi-Tenant / Multi-Event Support

| Scenario | Behavior |
|----------|----------|
| 1 tenant, 1 event | Starts registration directly |
| 1 tenant, multiple events | Asks "Which event?" with numbered list |
| Multiple tenants | Each tenant has their own WhatsApp number, resolved automatically |
| Event deadline passed | Returns "Registration closed" |
| Event full | Returns "Event is full" |
| Event paused/stopped | Returns "Not accepting registrations" |

## Session Management
- Sessions stored in Redis (or in-memory fallback)
- 1 hour timeout per session
- Each phone number has one active session at a time
- Session cleared after registration completes

## API Endpoints Used by n8n

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/n8n/session/message` | Main conversation handler (used by registration flow) |
| `POST /api/v1/n8n/{tenant}/events/{event}/sync-sheet` | Sync to Google Sheet (used by payment confirmation) |

## Testing Locally

1. Use ngrok to expose n8n: `ngrok http 5678`
2. Set ngrok URL as WhatsApp webhook
3. Send a message to the tenant's WhatsApp number
4. Check n8n execution logs for debugging
