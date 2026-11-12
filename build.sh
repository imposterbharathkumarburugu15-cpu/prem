#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "=================================================="
echo "== PRAMAN Backend: Render Build Process Starting =="
echo "=================================================="

# 1. Upgrade pip
python -m pip install --upgrade pip

# 2. Install application dependencies from requirements.txt
echo "[1/3] Installing application dependencies from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

# 3. Create required runtime directories
echo "[2/3] Creating runtime data directories..."
mkdir -p data/evidence

# 4. Completion
echo "[3/3] Build preparation complete."
echo "=================================================="
echo "== PRAMAN Backend: Build Completed Successfully  =="
echo "=================================================="
