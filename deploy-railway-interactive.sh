#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🚀 Gaming Platform - Railway Deployment Guide         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Your application is READY for Railway deployment!"
echo ""

# Check if Railway CLI is installed
if command -v railway &> /dev/null; then
    echo "✅ Railway CLI is installed"
else
    echo "📦 Installing Railway CLI..."
    npm i -g @railway/cli
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "   STEP-BY-STEP DEPLOYMENT"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "1️⃣  LOGIN TO RAILWAY"
echo "   Run: railway login"
echo "   → Browser will open for authentication"
echo ""
read -p "Press Enter after you've logged in..."
echo ""

echo "2️⃣  INITIALIZE PROJECT"
echo "   Run: railway init"
echo "   → Creates new Railway project"
echo ""
read -p "Press Enter after project is created..."
echo ""

echo "3️⃣  ADD POSTGRESQL DATABASE"
echo "   Run: railway add"
echo "   → Select 'PostgreSQL' from the list"
echo ""
read -p "Press Enter after database is added..."
echo ""

echo "4️⃣  GENERATE JWT SECRET"
echo "   Generating secure JWT secret..."
JWT_SECRET=$(openssl rand -hex 32)
echo "   Generated: $JWT_SECRET"
echo ""

echo "5️⃣  SET ENVIRONMENT VARIABLES"
echo "   Run the following commands:"
echo ""
echo "   railway variables set JWT_SECRET_KEY=$JWT_SECRET"
echo ""
read -p "Do you want to add Telegram integration? (y/n): " add_telegram

if [ "$add_telegram" = "y" ]; then
    echo ""
    echo "   Enter your Telegram Bot Token (from @BotFather):"
    read -p "   TELEGRAM_BOT_TOKEN=" telegram_token
    echo ""
    echo "   Enter your Telegram Chat ID (from @userinfobot):"
    read -p "   TELEGRAM_CHAT_ID=" telegram_chat
    echo ""
    echo "   Run:"
    echo "   railway variables set TELEGRAM_BOT_TOKEN=$telegram_token"
    echo "   railway variables set TELEGRAM_CHAT_ID=$telegram_chat"
fi

echo ""
read -p "Press Enter after setting environment variables..."
echo ""

echo "6️⃣  DEPLOY TO RAILWAY"
echo "   Run: railway up"
echo "   → Uploads and deploys your application"
echo ""
read -p "Press Enter to continue..."
echo ""

echo "7️⃣  RUN DATABASE MIGRATIONS"
echo "   Run: railway run alembic upgrade head"
echo "   → Sets up database schema"
echo ""
read -p "Press Enter after migrations complete..."
echo ""

echo "8️⃣  CREATE ADMIN USER (Optional)"
echo "   Run: railway run python scripts/create_admin.py"
echo "   → Creates default admin account"
echo ""
read -p "Press Enter to continue..."
echo ""

echo "9️⃣  GET YOUR DEPLOYMENT URL"
echo "   Run: railway open"
echo "   → Opens your live application!"
echo ""

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "   ✅ DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Your Gaming Platform is now live on Railway! 🎉"
echo ""
echo "Useful Commands:"
echo "  • railway logs          - View application logs"
echo "  • railway status        - Check deployment status"
echo "  • railway open          - Open your app in browser"
echo "  • railway variables     - View environment variables"
echo "  • railway run <cmd>     - Run commands in production"
echo ""
echo "Next Steps:"
echo "  1. Test your application"
echo "  2. Configure custom domain (optional)"
echo "  3. Monitor logs for any issues"
echo ""
