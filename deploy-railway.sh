#!/bin/bash
# Quick Deploy Script for Railway

echo "🚀 Gaming Platform - Railway Deployment"
echo "========================================"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm i -g @railway/cli
fi

# Login to Railway
echo "🔐 Logging into Railway..."
railway login

# Initialize project
echo "🎯 Initializing Railway project..."
railway init

# Add PostgreSQL database
echo "🗄️  Adding PostgreSQL database..."
railway add --database postgres

# Link project
railway link

# Set environment variables
echo "⚙️  Setting environment variables..."
echo "Enter your JWT Secret Key (min 32 characters):"
read JWT_SECRET

echo "Enter your Telegram Bot Token (or press Enter to skip):"
read TELEGRAM_TOKEN

echo "Enter your Telegram Chat ID (or press Enter to skip):"
read TELEGRAM_CHAT

railway variables set JWT_SECRET_KEY="$JWT_SECRET"

if [ ! -z "$TELEGRAM_TOKEN" ]; then
    railway variables set TELEGRAM_BOT_TOKEN="$TELEGRAM_TOKEN"
fi

if [ ! -z "$TELEGRAM_CHAT" ]; then
    railway variables set TELEGRAM_CHAT_ID="$TELEGRAM_CHAT"
fi

# Deploy
echo "🚀 Deploying to Railway..."
railway up

# Run migrations
echo "📊 Running database migrations..."
railway run alembic upgrade head

echo ""
echo "✅ Deployment complete!"
echo "🌐 Your app is now live!"
echo ""
echo "Run 'railway open' to view your deployment"
