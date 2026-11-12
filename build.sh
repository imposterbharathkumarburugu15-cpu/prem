#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "=================================================="
echo "== PRAMAN Backend: Render Build Process Starting =="
echo "=================================================="

# 1. Upgrade pip
python -m pip install --upgrade pip

# 2. Install PyTorch CPU-only wheels first (fast, ~170MB vs 2.5GB CUDA)
echo "[1/4] Installing CPU-only PyTorch and torchvision..."
pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 3. Install remaining application dependencies
echo "[2/4] Installing application dependencies from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

# 4. Compile frontend web console if node/npm are present
if command -v npm &> /dev/null && [ -d "frontend" ]; then
  echo "[3/4] Compiling frontend web console distribution..."
  cd frontend
  npm install --no-audit --no-fund
  npm run build
  cd ..
else
  echo "[3/4] Skipping frontend build (using pre-built web_console static assets)..."
fi

# 5. Database migrations check / build completion
echo "[4/4] Build preparation complete."
echo "=================================================="
echo "== PRAMAN Backend: Build Completed Successfully  =="
echo "=================================================="
