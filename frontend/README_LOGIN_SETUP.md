# Login Setup Guide

## Backend API URL Configuration

### Development (with CRA Proxy)

1. **Check `package.json`**: Ensure proxy is configured
   ```json
   "proxy": "http://localhost:8001"
   ```

2. **Backend must run on the proxy port**: Start backend on port 8001
   ```bash
   cd backend
   uvicorn server:app --host 0.0.0.0 --port 8001
   ```

3. **Frontend**: Start normally (uses proxy for API calls)
   ```bash
   cd frontend
   yarn start
   ```

4. **Optional**: Set explicit backend URL in `.env` (overrides proxy)
   ```
   REACT_APP_BACKEND_URL=http://localhost:8001
   ```

### Production / External Backend

1. **Set backend URL**: Create `frontend/.env`
   ```
   REACT_APP_BACKEND_URL=https://your-backend-url.com
   ```

2. **Build frontend**:
   ```bash
   yarn build
   ```

## Port Matching Rules

- **Proxy method**: `package.json` proxy port MUST match backend port
- **Direct method**: `REACT_APP_BACKEND_URL` points directly to backend
- **Priority**: Explicit `REACT_APP_BACKEND_URL` > CRA proxy

## Verifying API Calls

1. Open DevTools → Network tab
2. Login
3. Check request URL:
   - **With proxy**: `http://localhost:3000/api/v1/auth/login` (200 OK)
   - **Direct**: `http://localhost:8001/api/v1/auth/login` (200 OK)

## Common Issues

### "ERR_CONNECTION_REFUSED"
- Backend is not running
- Port mismatch (proxy vs backend)
- Solution: Check backend is on correct port

### "Session expired" on valid credentials
- Backend can't find user in database
- Database empty or wrong credentials
- Solution: Check backend logs, ensure MongoDB is populated

### "Server unreachable"
- Backend is down
- Network issue
- Firewall blocking request
- Solution: Check backend status, verify URL

## Testing Login End-to-End

```bash
# 1. Start backend
cd backend
python -m uvicorn server:app --host 0.0.0.0 --port 8001

# 2. Start frontend (new terminal)
cd frontend
yarn start

# 3. Open browser to http://localhost:3000
# 4. Try login:
#    - Wrong credentials → "Invalid username/password"
#    - Correct credentials → Login success
#    - Backend down → "Server unreachable"
```
