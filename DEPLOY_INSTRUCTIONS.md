# 🚀 Quick Deployment Guide for Gaming Platform

## Option 1: Railway (Recommended - Easiest)

### Step 1: Install Railway CLI on your local machine
```bash
# Install Railway CLI
npm i -g @railway/cli
# OR
curl -fsSL https://railway.app/install.sh | sh
```

### Step 2: Navigate to your project folder
```bash
cd /path/to/Final3-main
```

### Step 3: Login to Railway
```bash
railway login
```

### Step 4: Initialize and Deploy
```bash
# Create new project
railway init

# Add PostgreSQL database
railway add --database postgres

# Deploy backend
cd backend
railway up

# Deploy frontend (in another terminal)
cd ../frontend
railway up

# Link services and set environment variables
railway variables set JWT_SECRET_KEY=your-secret-key-min-32-chars
railway variables set TELEGRAM_BOT_TOKEN=your-telegram-token
railway variables set TELEGRAM_CHAT_ID=your-telegram-chat-id
```

### Step 5: Run Migrations
```bash
railway run alembic upgrade head
```

---

## Option 2: Render (Free Tier Available)

### Method A: Using Web Dashboard (Easiest)

1. **Go to https://render.com/** and sign up/login

2. **Create PostgreSQL Database:**
   - Click "New +" → "PostgreSQL"
   - Name: `gaming-platform-db`
   - Plan: Free
   - Create Database
   - Copy the "Internal Database URL"

3. **Deploy Backend:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository or use "Deploy from Git"
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - Add Environment Variables:
     - `DATABASE_URL` = [paste internal database URL]
     - `JWT_SECRET_KEY` = [generate 32+ char secret]
     - `TELEGRAM_BOT_TOKEN` = [your telegram token]
     - `TELEGRAM_CHAT_ID` = [your telegram chat id]

4. **Deploy Frontend:**
   - Click "New +" → "Static Site"
   - Build Command: `cd frontend && yarn install && yarn build`
   - Publish Directory: `frontend/build`
   - Add Environment Variable:
     - `REACT_APP_BACKEND_URL` = [your backend URL from step 3]

### Method B: Using render.yaml (Automated)

1. Push your code to GitHub
2. Go to https://render.com/
3. Click "New +" → "Blueprint"
4. Connect repository
5. Render will auto-detect `render.yaml` and deploy everything!

---

## Option 3: Vercel (Frontend) + Railway (Backend + DB)

### Deploy Backend + Database to Railway:
```bash
railway login
railway init
railway add --database postgres
railway up
```

### Deploy Frontend to Vercel:
```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to frontend folder
cd frontend

# Deploy
vercel

# Set environment variable
vercel env add REACT_APP_BACKEND_URL
# Enter your Railway backend URL
```

---

## Option 4: DigitalOcean App Platform

1. Go to https://cloud.digitalocean.com/apps
2. Click "Create App"
3. Connect GitHub repository
4. DigitalOcean will auto-detect Docker files
5. Add PostgreSQL database from marketplace
6. Configure environment variables
7. Deploy!

---

## Option 5: Heroku

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login

# Create app
heroku create your-gaming-platform

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Deploy
git push heroku main

# Run migrations
heroku run alembic upgrade head
```

---

## Environment Variables Required

```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/portal_db

# Security
JWT_SECRET_KEY=your-super-secret-key-at-least-32-characters-long

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=1234567890

# Games API (Optional)
GAMES_API_TOKEN=your-games-api-token

# Frontend
REACT_APP_BACKEND_URL=https://your-backend-url.com
```

---

## Post-Deployment Checklist

✅ Database is running and accessible  
✅ Backend health check passes: `curl https://your-backend.com/api/health`  
✅ Frontend loads and can connect to backend  
✅ Run database migrations: `alembic upgrade head`  
✅ Create admin user: `python scripts/create_admin.py`  
✅ Test login functionality  
✅ Test wallet operations  
✅ Configure custom domain (optional)  

---

## Troubleshooting

### Backend won't start
- Check DATABASE_URL is set correctly
- Verify JWT_SECRET_KEY is at least 32 characters
- Check logs for specific errors

### Frontend can't connect to backend
- Verify REACT_APP_BACKEND_URL is set
- Check CORS settings in backend
- Ensure backend is accessible

### Database connection errors
- Check DATABASE_URL format
- Verify database is running
- Check firewall rules

---

## Need Help?

- Railway Docs: https://docs.railway.app/
- Render Docs: https://render.com/docs
- Vercel Docs: https://vercel.com/docs

---

**Recommended:** Railway is the easiest! Just 5 commands and you're live! 🎉
