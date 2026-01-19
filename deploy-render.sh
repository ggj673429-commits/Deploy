#!/bin/bash
# One-Click Deploy to Render

echo "🚀 Gaming Platform - Render Deployment"
echo "======================================"
echo ""

# Check if render CLI is installed
if ! command -v render &> /dev/null; then
    echo "📦 Installing Render CLI..."
    npm i -g render
fi

echo "📝 Please follow these steps:"
echo ""
echo "1. Go to https://render.com and sign up/login"
echo "2. Click 'New +' → 'Blueprint'"
echo "3. Connect this GitHub repository"
echo "4. Render will auto-detect render.yaml and deploy!"
echo ""
echo "OR manually:"
echo ""
echo "1. Create PostgreSQL database on Render"
echo "2. Copy the Internal Database URL"
echo "3. Create Web Service for backend"
echo "   - Build: pip install -r backend/requirements.txt"
echo "   - Start: cd backend && uvicorn server:app --host 0.0.0.0 --port \$PORT"
echo "4. Create Static Site for frontend"
echo "   - Build: cd frontend && yarn && yarn build"
echo "   - Publish: frontend/build"
echo ""
echo "Environment Variables needed:"
echo "  - DATABASE_URL (from step 2)"
echo "  - JWT_SECRET_KEY (generate with: openssl rand -hex 32)"
echo "  - TELEGRAM_BOT_TOKEN (optional)"
echo "  - TELEGRAM_CHAT_ID (optional)"
echo "  - REACT_APP_BACKEND_URL (backend URL from step 3)"
echo ""
