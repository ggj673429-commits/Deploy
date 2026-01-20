# 🎮 Games API Integration & Connection Guide

## Overview

Your Gaming Platform integrates with an external Games API provider to handle game operations:
- **Create Account** - Create game accounts for users
- **Load/Recharge** - Add credits to game accounts
- **Redeem** - Withdraw credits from game accounts
- **Check Balance** - Query current game balance

---

## Architecture

```
┌──────────────┐         ┌────────────────────┐         ┌─────────────────┐
│   Chatwoot   │────────▶│  Central System    │────────▶│   Games API     │
│   (Orders)   │  HTTP   │  (Your Backend)    │  HTTP   │  (External)     │
└──────────────┘         └────────────────────┘         └─────────────────┘
```

**Flow:**
1. **Chatwoot** sends game order request to Central System
2. **Central System** validates order, checks user balance
3. **Central System** calls **Games API** with order details
4. **Games API** processes request (create, load, redeem)
5. **Central System** updates database with result
6. **Central System** responds to Chatwoot with status

---

## Configuration (Dynamic - Not Hardcoded!)

All Games API settings are configured via environment variables:

### Required Environment Variables

```env
# Games API Base URL
AUTOMATION_BASE_URL=https://automation.joycegames.vip

# API Authentication Token (REQUIRED)
# Get this from your games provider
AUTOMATION_TOKEN=your-actual-token-here
```

### Optional Environment Variables

```env
# Custom endpoints (if different from defaults)
AUTOMATION_CREATE_ENDPOINT=/api/game/create-account/
AUTOMATION_LOAD_ENDPOINT=/api/game/recharge/
AUTOMATION_REDEEM_ENDPOINT=/api/game/redeem/
AUTOMATION_GET_USER_BALANCE_ENDPOINT=/api/game/get-balance/{game_id}/{user_id}/

# Timeout configuration (milliseconds)
AUTOMATION_TIMEOUT_MS=15000

# Retry configuration
AUTOMATION_MAX_RETRIES=3
AUTOMATION_RETRY_DELAY=1.0
```

---

## Current Status

### ✅ What's Working

**Infrastructure:**
- ✅ Games API client exists (`games_api_service.py`)
- ✅ Environment variable configuration (dynamic, not hardcoded)
- ✅ Retry logic with exponential backoff
- ✅ Timeout configuration
- ✅ Structured logging
- ✅ Error handling

**Endpoints:**
- ✅ `/api/game-accounts/create` - Create game account
- ✅ `/api/game-accounts/load` - Load credits to game
- ✅ `/api/game-accounts/redeem` - Redeem credits from game
- ✅ `/api/game-accounts/balance` - Check game balance

### ⚠️ Known Issues

**1. Missing AUTOMATION_TOKEN**
```
Status: Not configured
Impact: Games API calls will fail
Fix: Set AUTOMATION_TOKEN in environment variables
```

**2. PostgreSQL Queries in game_account_routes.py**
```
Status: Uses SQL queries (MongoDB not converted yet)
Impact: Routes return empty results
Fix: Convert to MongoDB queries or use compatibility layer
```

**3. Login Connection Issues**
```
Error: "Connection issues" during game account login
Cause: PostgreSQL queries returning None (empty MongoDB)
Fix: Convert game account routes to MongoDB
```

---

## How to Fix Connection Issues

### Issue: "Connection issues during login"

**Root Cause:**
- Game account routes use PostgreSQL queries
- MongoDB compatibility layer returns None/empty
- User appears to have no game account

**Solution:**

**Option 1: Add AUTOMATION_TOKEN (Immediate)**
```bash
# In your deployment environment, set:
AUTOMATION_TOKEN=your-actual-games-api-token

# This allows Games API calls to work
```

**Option 2: Convert Routes to MongoDB (Long-term)**
```python
# Current (PostgreSQL):
game_account = await conn.fetchrow("""
    SELECT * FROM game_accounts WHERE user_id = $1
""", user_id)

# Convert to (MongoDB):
db = await get_db()
game_account = await db.game_accounts.find_one({"user_id": user_id})
```

---

## Testing Games API Integration

### Test 1: Check Configuration

```bash
# Check if AUTOMATION_TOKEN is set
curl https://your-backend.com/api/game-accounts/config

# Expected: 
# {
#   "configured": true,
#   "base_url": "https://automation.joycegames.vip"
# }
```

### Test 2: Create Game Account

```bash
curl -X POST https://your-backend.com/api/game-accounts/create \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "juwa",
    "username_hint": "testuser",
    "nickname": "Test Player"
  }'

# Expected: 
# {
#   "success": true,
#   "game_username": "testuser",
#   "game_password": "generated_password"
# }
```

### Test 3: Load Credits

```bash
curl -X POST https://your-backend.com/api/game-accounts/load \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "juwa",
    "amount": 100.0
  }'

# Expected:
# {
#   "success": true,
#   "new_balance": 100.0
# }
```

---

## Chatwoot → Central System Integration

### Expected Webhook from Chatwoot

```json
{
  "event": "game_order",
  "order_type": "create_account | load | redeem",
  "user_id": "user_123",
  "game_id": "juwa",
  "amount": 100.0,
  "metadata": {
    "conversation_id": 12345,
    "customer_email": "user@example.com"
  }
}
```

### Central System Response

```json
{
  "success": true,
  "order_id": "order_456",
  "status": "completed",
  "game_response": {
    "game_username": "player123",
    "game_balance": 100.0
  }
}
```

---

## Environment Setup Checklist

For Games API to work, ensure:

- [ ] `AUTOMATION_BASE_URL` is set
- [ ] `AUTOMATION_TOKEN` is set (CRITICAL!)
- [ ] Token is valid and not expired
- [ ] Games API is accessible from your server
- [ ] Firewall allows outbound HTTPS to games API
- [ ] MongoDB has `game_accounts` collection (auto-created)
- [ ] Users exist in MongoDB `users` collection

---

## Troubleshooting

### Issue: "AUTOMATION_TOKEN is required"

**Cause**: Environment variable not set

**Fix**:
```bash
# Set in your deployment environment
export AUTOMATION_TOKEN=your-token-here

# Or in .env file
echo 'AUTOMATION_TOKEN=your-token-here' >> .env
```

### Issue: "Game not found"

**Cause**: No games in MongoDB `games` collection

**Fix**:
```javascript
// Add games to MongoDB
db.games.insertOne({
  game_id: "juwa",
  game_name: "Juwa",
  display_name: "Juwa Casino",
  is_active: true,
  category: "casino",
  created_at: new Date()
})
```

### Issue: "User not found"

**Cause**: No users in MongoDB `users` collection

**Fix**:
```bash
# Create user via signup endpoint
curl -X POST https://your-backend.com/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123",
    "display_name": "Test User"
  }'
```

### Issue: Connection timeout

**Cause**: Games API not responding

**Check**:
1. Is `AUTOMATION_BASE_URL` correct?
2. Is Games API online?
3. Is `AUTOMATION_TOKEN` valid?
4. Check firewall rules

**Adjust timeout**:
```env
# Increase timeout to 30 seconds
AUTOMATION_TIMEOUT_MS=30000
```

---

## Security Considerations

### ⚠️ Important

1. **Never commit AUTOMATION_TOKEN to git**
2. **Use environment variables only**
3. **Rotate tokens periodically**
4. **Monitor failed API calls**
5. **Implement rate limiting**
6. **Log all games API requests**

### Token Management

**Production:**
```bash
# Set via deployment dashboard
# Or environment variable management system
```

**Development:**
```bash
# Use separate development token
AUTOMATION_TOKEN=dev-token-here
```

---

## Next Steps

**Immediate (Fix connection issues):**
1. ✅ Set `AUTOMATION_TOKEN` environment variable
2. ✅ Verify Games API is accessible
3. ✅ Test create account endpoint
4. ✅ Test load credits endpoint

**Short-term (Improve functionality):**
1. Convert game_account_routes.py to MongoDB
2. Add game accounts to MongoDB
3. Test full flow: create → load → redeem
4. Integrate with Chatwoot webhook

**Long-term (Optimize):**
1. Add caching for game balances
2. Implement webhook for game events
3. Add monitoring and alerts
4. Optimize retry logic

---

## Support

**Games API Provider:**
- URL: https://automation.joycegames.vip
- Contact your games provider for:
  - API token
  - Documentation
  - Support

**Central System (Your Backend):**
- Check logs: `/var/log/supervisor/backend.*.log`
- Monitor Games API calls in structured logs
- Health check: `GET /health`

---

## Summary

✅ **Games API integration is properly configured with dynamic environment variables**
✅ **Not hardcoded - all URLs and tokens come from env vars**
⚠️ **Need to set AUTOMATION_TOKEN for it to work**
⚠️ **Game account routes need MongoDB conversion**
⚠️ **"Connection issues" are due to empty MongoDB (no game accounts yet)**

**To fix login issues: Set AUTOMATION_TOKEN and create game accounts!**
