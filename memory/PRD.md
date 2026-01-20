# Financial Gaming Platform - PRD

## Project Overview
Full-stack financial gaming platform with React frontend, FastAPI backend, and MongoDB database.

## Tech Stack
- **Frontend**: React.js with Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (migrated from PostgreSQL)
- **Auth**: JWT-based authentication

## User Personas
1. **Clients**: End users who deposit funds, play games, redeem promos
2. **Admins**: Platform operators who manage balances, users, and payment methods

## Core Requirements
- Single source of truth: Admin Payment/QR config controls client Add Funds UI
- Explicit user feedback: Promo redeem shows persistent on-screen status
- Financial accuracy: Balance changes reflect immediately and visibly
- No fake fallbacks: Client shows only backend-configured payment methods

---

## What's Been Implemented (Jan 20, 2026 - Session 2)

### P0: Admin Dashboard MongoDB Migration + Business Definitions ✅
Complete rewrite of Admin Dashboard to use MongoDB with exact business definitions.

**Backend Changes:**
1. **Timezone Helper** (`/app/backend/api/v1/core/timezone_helper.py`):
   - `get_client_today_range()` - Returns today's UTC boundaries based on client timezone
   - `get_last_n_days_ranges()` - Returns N days of date ranges for trend charts
   - `get_rolling_window()` - Returns rolling N-day window for active client calculations
   - `get_last_24h_range()` - Returns last 24 hours for risk calculations

2. **Dashboard Endpoint** (`GET /admin/dashboard`):
   - Uses client timezone headers (X-Client-Timezone, X-Client-TZ-Offset)
   - Returns exact business definitions:
     - `deposits_in_today`: SUM of game_load.amount (approved_at in client's today)
     - `withdrawals_out_today`: SUM of withdrawal_game.payout_amount
     - `net_profit_today`: deposits - withdrawals - referral_earnings_paid
     - `cash_balance_total`: SUM of all clients' withdrawable cash balance
     - `active_clients_7d`: Distinct users with 3+ deposits ≥$10 in rolling 7 days

3. **Analytics Endpoints** (MongoDB-native):
   - `GET /admin/analytics/risk-snapshot`:
     - `risk_max_24h`: MAX(deposit_amount * multiplier) from last 24h deposits
     - `total_client_balance`: Combined cash/bonus/play_credits
     - `cashout_pressure`: Pending withdrawal indicator
   - `GET /admin/analytics/platform-trends`:
     - 30 daily data points with deposits, withdrawals, bonus_issued, bonus_voided
     - Includes `referral_earnings_paid` in totals
     - Uses client timezone for day boundaries

4. **Admin Routes Migration** (`admin_routes_v2.py`):
   - `GET /admin/orders`: MongoDB pagination with order_type filter
   - `GET /admin/orders/{id}`: Full order detail from MongoDB
   - `GET /admin/approvals/pending`: Pending orders with user flags
   - `GET /admin/referrals/dashboard`: Referral earnings totals (today, 7d, 30d)

**Frontend Changes:**
1. **http.js** - Sends timezone headers on every request:
   - `X-Client-Timezone`: IANA timezone (e.g., "Asia/Manila")
   - `X-Client-TZ-Offset`: Offset in minutes

2. **AdminDashboard.js**:
   - **New Cash Balance card** showing all clients' withdrawable balance
   - Fixed drill-down links: Deposits → `/admin/orders?order_type=game_load`
   - Fixed drill-down links: Withdrawals → `/admin/orders?order_type=withdrawal_game`
   - Safe formatting with `toMoney()` helper (no more toFixed on non-numbers)
   - Added active_clients_7d display
   - Added Referral Earnings Paid Today card

3. **PlatformTrendChart.js**:
   - Added Referral Earnings metric toggle
   - Uses `data.data` from backend response
   - Safe value formatting with `toMoney()` helper
   - Shows 6 totals including referral_earnings_paid

4. **RiskSnapshotCards.js**:
   - **Risk Max 24h card** (replaces "Max Cashout Exposure")
   - Shows MAX(deposit * multiplier) from last 24h deposits
   - Safe value formatting

### P0: Payment QR System Migration ✅
- Admin Payment QR CRUD endpoints migrated to MongoDB
- Admin Payment Methods CRUD endpoints migrated to MongoDB
- Client `/payments/methods` endpoint fetches from MongoDB

---

## What's Been Implemented (Jan 18, 2026)

### P0-1: Payment Methods + QR Code Wiring ✅
- **Removed hardcoded payment method fallback** in AddFunds.js
- **Empty state UI**: Shows "No Payment Methods Available" when backend returns empty
- **QR Code display**: Step 3 now renders deposit QR codes from `paymentMethod.qr_codes[]`
- **QR indicator**: Payment methods show "QR Available" badge if they have QR codes
- **No fake defaults**: Client only shows what admin configures

### P0-2: Admin Balance Control UI ✅
- **Fixed header copy**: "instant execution" instead of "with approval"
- **Fixed balance field**: Now uses `client.balance?.real ?? client.real_balance`
- **Fixed recent actions query**: Uses `order_type=admin_load,admin_withdraw`
- **Fixed status mapping**: APPROVED_EXECUTED shows as "Executed" badge

### P1: Promo Redemption Persistent Status ✅
- **Already implemented in ClientRewards.js**: `redeemResult` state shows persistent message
- Success: "✅ Promo code redeemed" with credit amount
- Error: "❌ Promo code not redeemed" with reason

---

## Files Modified
**Backend (MongoDB Migration):**
- `/app/backend/api/v1/core/timezone_helper.py` - NEW: Timezone utilities
- `/app/backend/api/v1/routes/admin_routes_v2.py` - Dashboard, Orders, Approvals, Referrals
- `/app/backend/api/v1/routes/analytics_routes.py` - Risk snapshot, Platform trends
- `/app/backend/api/v1/routes/admin_system_routes.py` - Payment Methods/QR CRUD
- `/app/backend/api/v1/routes/payment_routes.py` - Client payment methods

**Frontend:**
- `/app/frontend/src/api/http.js` - Timezone headers
- `/app/frontend/src/pages/admin/AdminDashboard.js` - Cash Balance card, fixed links
- `/app/frontend/src/components/analytics/PlatformTrendChart.js` - Referral earnings
- `/app/frontend/src/components/analytics/RiskSnapshotCards.js` - Risk Max 24h

## Test Data Created
- User: `testuser` / `Test123456` (client)
- Admin: `admin` / `Admin123456` (admin role)
- Payment Methods: GCash, PayMaya, BDO Bank Transfer (with QR codes)
- Promo Code: `WELCOME50` (gives $50)

---

## Backlog / Future Improvements

### P0 (Critical)
- None remaining

### P1 (High)
- Add real payment provider integration (actual payment processing)
- Implement withdrawal flow with real bank/wallet APIs

### P2 (Medium)
- Admin dashboard analytics improvements
- Email notifications for promo redemptions
- Rate limiting on promo redemption

---

## Next Tasks
1. End-to-end browser testing with real user flows
2. Payment provider integration (if needed)
3. Production deployment readiness check

---

## Deployment Readiness Verification (Jan 18, 2026)

### 1) Client Add Funds ✅
- Payment methods disappear immediately when disabled in Admin
- Deposit QR codes match Admin configuration
- Empty state message appears when no methods enabled

### 2) Admin Balance Control ✅
- admin_load and admin_withdraw execute instantly
- client.balance.real updates after refetch (verified: $100 load - $25 withdraw = $75)
- Recent actions show correct order_type and APPROVED_EXECUTED status
- Audit log entries created for each action
- Fixed: fetchRecentActions uses parallel API calls (backend expects single order_type)

### 3) Promo Redeem UX ✅
- Invalid promo → persistent "Invalid promo code" error
- Valid promo → persistent "Successful! Redeemed $50.00"
- Already redeemed → "You have already redeemed this promo code"
- Promo history reflects redemption after refresh

### Status: PRODUCTION READY
No blockers found.

---

## What's Been Implemented (Jan 20, 2026)

### P0: Referral System Fix (MongoDB Migration) ✅
**Problem**: Referral system was broken after PostgreSQL to MongoDB migration. The backend was using SQL compatibility functions (`fetch_one`, `fetch_all`) that return `None`/`[]` in MongoDB environment.

**Solution**:
1. **Backend - portal_routes.py**: Rewrote `/portal/referrals/details` endpoint to use native MongoDB aggregation queries
   - Uses `db.users.count_documents()` for total referrals count
   - Uses MongoDB aggregation pipelines for active referrals and earnings calculations
   - Properly returns referral_code, referral_link, commission info, tier system, earnings, and stats

2. **Backend - auth.py**: Rewrote authentication functions to use MongoDB
   - `resolve_user_from_jwt()`: Uses `db.users.find_one()` instead of SQL
   - `resolve_user_from_portal_token()`: Uses MongoDB for session lookup
   - `get_portal_user()` helper: Uses MongoDB for user lookup

3. **Frontend (already working)**: 
   - `Register.js`: Correctly parses `?ref=CODE` from URL and auto-fills referral input
   - `ClientReferrals.js`: Displays stats correctly with proper error handling

**Test Results**: 
- All 13 backend tests passed (100%)
- All frontend tests passed
- Full referral flow verified: Create referrer → Get code → Create referred user → Verify count increments

**Key Endpoints**:
- `POST /api/v1/auth/signup` - Creates user with `referred_by_code` linked to referrer
- `GET /api/v1/portal/referrals/details` - Returns complete referral stats

**Test Credentials**:
- Referrer: testref001 / TestPass123! (code: O5037H70)
- Referred: referreduser01 / TestPass123!

---

## What's Been Implemented (Jan 20, 2026 - Session 2)

### P0: Payment QR System Migration (MongoDB Native) ✅
**Problem**: Payment QR management system was broken because backend routes still used non-functional SQL compatibility layer (`fetch_one`, `fetch_all`, `execute`) instead of native MongoDB queries.

**Solution**:
1. **Backend - admin_system_routes.py**: Rewrote ALL Payment Methods CRUD endpoints to use native MongoDB:
   - `GET /api/v1/admin/system/payment-methods`: Uses `db.payment_methods.find()`
   - `POST /api/v1/admin/system/payment-methods`: Uses `db.payment_methods.insert_one()`
   - `PUT /api/v1/admin/system/payment-methods/{id}`: Uses `db.payment_methods.update_one()`
   - `DELETE /api/v1/admin/system/payment-methods/{id}`: Uses `db.payment_methods.delete_one()`

2. **Backend - admin_system_routes.py**: Rewrote ALL Payment QR CRUD endpoints to use native MongoDB:
   - `GET /api/v1/admin/system/payment-qr`: Uses `db.payment_qr.find()` with sorting
   - `POST /api/v1/admin/system/payment-qr`: Uses `db.payment_qr.insert_one()` with unique active/default logic
   - `PATCH /api/v1/admin/system/payment-qr/{id}`: Uses `db.payment_qr.update_one()` with unique active/default logic
   - `DELETE /api/v1/admin/system/payment-qr/{id}`: Uses `db.payment_qr.delete_one()` with 404 handling

3. **Backend - payment_routes.py**: Rewrote client-facing `/payments/methods` endpoint:
   - Uses `db.payment_methods.find({"enabled": True})` for methods
   - Uses `db.payment_qr.find()` with `$or` query for backward compatibility (matches on both `title` and `method_id`)
   - Uses `serialize_docs()` for JSON serialization

4. **MongoDB Indexes** (already existed in database.py):
   - `payment_methods`: method_id (unique), enabled, priority
   - `payment_qr`: qr_id (unique), payment_method, compound indexes for is_active and is_default

**Key Features Verified**:
- ✅ Unique active QR per payment method (creating new active QR deactivates previous)
- ✅ Unique default QR per payment method
- ✅ Backward compatibility (QR matches on both `title` and `method_id`)
- ✅ Proper 404 handling on DELETE and PATCH
- ✅ Client endpoint shows only enabled methods with their active QRs

**Test Data Created**:
- Payment Method: GCash (method_id: 01ce2a7b-032d-4622-9bb5-21c6de4a556e)
- Payment QR: "Updated QR Label" (qr_id: f5cc9f9e-aebb-47c9-85d5-7609f5c67db7, is_active: true)

---

## Backlog / Future Tasks

### P1: Complete PostgreSQL to MongoDB Migration
- Many other backend routes still use SQL compatibility functions
- Files that need audit: admin_system_routes.py (webhooks, API keys, wallet loads), payment_routes.py (proof upload, order action)
- Convert to native MongoDB queries

### P2: Referral Earnings Tracking
- Implement earnings tracking when referred users make deposits
- Add earnings history to referrals page

