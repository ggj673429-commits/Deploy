# 🔔 Chatwoot Integration - Telegram Alert Forwarding

## Overview

Your Gaming Platform backend now includes endpoints to receive alerts from Chatwoot and automatically forward them to Telegram. This enables real-time notifications for human handoff situations.

## Architecture

```
┌──────────────┐         ┌───────────────────┐         ┌──────────────┐
│   Chatwoot   │────────▶│  Gaming Platform  │────────▶│   Telegram   │
│   (Webhook)  │  HTTP   │   Backend API     │  Bot    │ Notification │
└──────────────┘         └───────────────────┘         └──────────────┘
```

## Endpoints

### 1. **POST /api/v1/chatwoot/alerts** (Recommended)

Receives structured human handoff alerts from your Chatwoot bot.

**Use this endpoint for:** Customer support escalations, complaints, payment issues, etc.

**Request Body:**
```json
{
  "severity": "high",
  "reason": "NEGATIVE_SENTIMENT",
  "conversation_id": 12345,
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "message": "THIS IS RIDICULOUS!!! WHERE IS MY PAYMENT???",
  "timestamp": "2025-01-19T18:30:00Z",
  "chatwoot_url": "https://app.chatwoot.com/app/accounts/1/conversations/12345",
  "additional_info": {
    "user_id": "user_123",
    "order_id": "order_456"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Alert forwarded to Telegram",
  "telegram_message_id": 789,
  "conversation_id": 12345
}
```

**Telegram Message Format:**
```
🟠 CHATWOOT ALERT - HIGH

Reason: NEGATIVE_SENTIMENT
Conversation ID: #12345
Customer: John Doe
Email: john@example.com

Message:
THIS IS RIDICULOUS!!! WHERE IS MY PAYMENT???

Time: 2025-01-19T18:30:00Z

🔗 View in Chatwoot

Additional Info:
  • user_id: user_123
  • order_id: order_456
```

---

### 2. **POST /api/v1/chatwoot/webhook** (Generic)

Receives any Chatwoot webhook event.

**Use this endpoint for:** All Chatwoot events (message_created, conversation_status_changed, etc.)

**Request Body:**
```json
{
  "event": "message_created",
  "conversation": {
    "id": 12345,
    "status": "open"
  },
  "sender": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "message": {
    "content": "I need help with my payment",
    "created_at": "2025-01-19T18:30:00Z"
  },
  "account": {
    "id": 1,
    "name": "Gaming Platform Support"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Webhook forwarded to Telegram",
  "event": "message_created"
}
```

---

### 3. **POST /api/v1/chatwoot/test**

Test endpoint to verify Telegram integration is working.

**Request:** No body required

**Response:**
```json
{
  "success": true,
  "message": "Test alert sent to Telegram",
  "telegram_message_id": 123
}
```

---

### 4. **GET /api/v1/chatwoot/health**

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "chatwoot-integration",
  "timestamp": "2025-01-19T18:30:00.123Z"
}
```

---

## Configuration

### Environment Variables

Your backend already has Telegram configured. Ensure these are set:

```env
# Telegram Bot Configuration (Already in your .env)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=1234567890
```

**How to get these:**
1. **TELEGRAM_BOT_TOKEN**: Talk to @BotFather on Telegram
2. **TELEGRAM_CHAT_ID**: Talk to @userinfobot on Telegram

---

## Chatwoot Setup

### Configure Webhook in Chatwoot

1. **Go to Chatwoot Settings** → Integrations → Webhooks
2. **Add New Webhook:**
   - **URL**: `https://your-gaming-platform.com/api/v1/chatwoot/alerts`
   - **Events**: Select events you want to forward
   - **Method**: POST

### Example: Send Alert from Your Chatwoot Bot

In your Chatwoot bot code (TypeScript/JavaScript):

```typescript
// services/humanHandoffService.ts (in your Chatwoot bot)

async function sendAlertToGamingPlatform(handoffData: any) {
  const alertPayload = {
    severity: handoffData.severity,        // "low" | "medium" | "high" | "critical"
    reason: handoffData.reason,            // "NEGATIVE_SENTIMENT" | "PAYMENT_ISSUE" | etc.
    conversation_id: handoffData.conversationId,
    customer_name: handoffData.customerName,
    customer_email: handoffData.customerEmail,
    message: handoffData.message,
    timestamp: new Date().toISOString(),
    chatwoot_url: `https://app.chatwoot.com/app/accounts/${accountId}/conversations/${conversationId}`,
    additional_info: {
      trigger: handoffData.trigger,
      // any other metadata
    }
  };

  // Send to your Gaming Platform backend
  const response = await fetch('https://your-gaming-platform.com/api/v1/chatwoot/alerts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(alertPayload)
  });

  return response.json();
}
```

---

## Alert Severity Levels

| Severity | Emoji | Use Case |
|----------|-------|----------|
| **low** | 🟢 | Informational alerts |
| **medium** | 🟡 | General support requests, repeated questions |
| **high** | 🟠 | Complaints, payment issues, negative sentiment |
| **critical** | 🔴 | Account hacked, security issues, urgent escalations |

---

## Testing

### Test 1: Using curl

```bash
# Test the alert endpoint
curl -X POST https://your-backend.com/api/v1/chatwoot/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "high",
    "reason": "TEST_ALERT",
    "conversation_id": 99999,
    "customer_name": "Test User",
    "customer_email": "test@test.com",
    "message": "This is a test alert",
    "timestamp": "2025-01-19T18:30:00Z"
  }'
```

### Test 2: Using the test endpoint

```bash
# Send a pre-formatted test alert
curl -X POST https://your-backend.com/api/v1/chatwoot/test
```

### Test 3: Check health

```bash
curl https://your-backend.com/api/v1/chatwoot/health
```

---

## Example Telegram Messages

### High Severity Alert
```
🟠 CHATWOOT ALERT - HIGH

Reason: PAYMENT_ISSUE
Conversation ID: #54321
Customer: Jane Smith
Email: jane@example.com

Message:
I made a deposit 2 hours ago and still haven't received my credits!!!

Time: 2025-01-19T18:30:00Z

🔗 View in Chatwoot

Additional Info:
  • user_id: user_789
  • deposit_amount: $100
```

### Critical Alert
```
🔴 CHATWOOT ALERT - CRITICAL

Reason: ACCOUNT_HACKED
Conversation ID: #11111
Customer: Emergency User
Email: help@example.com

Message:
My account was hacked! Someone is withdrawing all my money!

Time: 2025-01-19T18:35:00Z

🔗 View in Chatwoot
```

---

## Security Considerations

### Optional: Add Webhook Signature Verification

Uncomment the signature verification in `chatwoot_routes.py`:

```python
@router.post("/webhook")
async def receive_webhook(
    webhook: ChatwootWebhook,
    request: Request,
    x_chatwoot_signature: Optional[str] = Header(None)
):
    # Verify signature
    if x_chatwoot_signature:
        verify_chatwoot_signature(await request.body(), x_chatwoot_signature)
    
    # ... rest of the code
```

### Add Rate Limiting

Consider adding rate limiting to prevent abuse:

```python
from slowapi import Limiter

@router.post("/alerts")
@limiter.limit("100/minute")
async def receive_alert(...):
    # ...
```

---

## Troubleshooting

### Alert not appearing in Telegram

**Check:**
1. ✅ `TELEGRAM_BOT_TOKEN` is set correctly
2. ✅ `TELEGRAM_CHAT_ID` is set correctly
3. ✅ Backend logs: `tail -f /var/log/supervisor/backend.*.log`
4. ✅ Test endpoint works: `curl -X POST https://your-backend.com/api/v1/chatwoot/test`

### Chatwoot webhook failing

**Check:**
1. ✅ Backend URL is accessible from internet
2. ✅ Webhook URL in Chatwoot is correct
3. ✅ Backend is running: `sudo supervisorctl status backend`
4. ✅ Check Chatwoot webhook logs

### Message formatting issues

- Messages use HTML formatting
- Long messages are truncated (500 chars for alerts, 300 for webhooks)
- Special characters are automatically escaped

---

## API Documentation

After deployment, view interactive API docs at:
- **Swagger UI**: `https://your-backend.com/docs`
- **ReDoc**: `https://your-backend.com/redoc`

Look for the **"Chatwoot Integration"** section.

---

## Features

✅ **Real-time Forwarding** - Alerts sent to Telegram immediately  
✅ **Severity-based Formatting** - Different emojis for different severities  
✅ **Rich Formatting** - HTML formatting with links and structure  
✅ **Customer Context** - Includes customer name, email, conversation ID  
✅ **Direct Links** - One-click access to Chatwoot conversation  
✅ **Test Endpoint** - Easy testing without Chatwoot  
✅ **Health Checks** - Monitor service status  
✅ **Flexible** - Supports both structured alerts and generic webhooks  

---

## Next Steps

1. **Deploy your backend** using the deployment guides
2. **Test the endpoint** using curl or the test endpoint
3. **Configure Chatwoot webhook** to point to your backend
4. **Update your Chatwoot bot** to send alerts to this endpoint
5. **Monitor Telegram** for incoming alerts

---

## Support

For issues or questions:
- Check backend logs: `/var/log/supervisor/backend.*.log`
- Test endpoint: `POST /api/v1/chatwoot/test`
- Health check: `GET /api/v1/chatwoot/health`

---

**Your Gaming Platform backend is now ready to receive and forward Chatwoot alerts!** 🚀
