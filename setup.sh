#!/bin/bash

echo "🚀 راه‌اندازی سیستم دمو شاپرک"

# Generate secrets
export JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)
export JUPYTERHUB_API_TOKEN=$(openssl rand -hex 32)

# Save to .env
cat > .env << EOF
JUPYTERHUB_CRYPT_KEY=$JUPYTERHUB_CRYPT_KEY
JUPYTERHUB_API_TOKEN=$JUPYTERHUB_API_TOKEN
EOF

echo "✅ کلیدهای امنیتی تولید شد"

# Build Jupyter user image first
echo "🐳 ساخت Docker image کاربران..."
cd jupyter-user-image
docker build -t shaparak-jupyter-user:latest .
cd ..

# Start services
echo "🚀 راه‌اندازی سرویس‌ها..."
docker-compose up -d

echo ""
echo "✅ سیستم راه‌اندازی شد!"
echo ""
echo "📊 دسترسی‌ها:"
echo "  - پورتال: http://localhost:3000"
echo "  - JupyterHub: http://localhost:8000"
echo "  - API: http://localhost:8001"
echo ""
echo "👤 کاربران دمو:"
echo "  - admin / shaparak123"
echo "  - ali.rezaei / shaparak123"
echo "  - sara.ahmadi / shaparak123"
echo "  - reza.mohammadi / shaparak123"
echo ""
echo "⏰ لطفاً 30 ثانیه صبر کنید تا تمام سرویس‌ها آماده شوند..."