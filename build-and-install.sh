#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "=== copilot-key-handler build & install ==="
echo ""

# Step 1: Install build dependencies
echo "[1/4] Installing build dependencies..."
sudo apt install -y devscripts debhelper build-essential

# Step 2: Build the .deb
echo ""
echo "[2/4] Building .deb package..."
dpkg-buildpackage -us -uc -b

# Step 3: Install the .deb
echo ""
echo "[3/4] Installing copilot-key-handler..."
DEB=$(ls -t ../copilot-key-handler_*_all.deb | head -1)
echo "Installing $DEB..."
sudo apt install -y "$DEB"

# Step 4: Enable and start the service
echo ""
echo "[4/4] Enabling and starting the service..."
sudo systemctl enable --now copilot-key-handler
sudo systemctl status copilot-key-handler --no-pager

echo ""
echo "=== Done! Press the Copilot key to launch Claude Code. ==="
echo "Config: /etc/copilot-key-handler/config.yaml"
echo "Logs:   journalctl -u copilot-key-handler -f"
