#!/bin/bash

# Exit on error
set -e

echo "--- 1. Installing Build Dependencies ---"
./venv/bin/pip install pyinstaller

echo "--- 2. Building Standalone Executable ---"
./venv/bin/pyinstaller --onefile --windowed --name secure-browser main.py

echo "--- 3. Build Complete ---"
echo "The executable is located at: dist/secure-browser"
echo ""
echo "To install system-wide (requires sudo):"
echo "  sudo cp dist/secure-browser /usr/local/bin/"
echo "  sudo cp secure-browser.desktop /usr/share/applications/"
echo ""
echo "To install for current user only:"
echo "  mkdir -p ~/.local/bin ~/.local/share/applications"
echo "  cp dist/secure-browser ~/.local/bin/"
echo "  sed -i 's|/usr/local/bin/secure-browser|'\"\$HOME\"'/.local/bin/secure-browser|' secure-browser.desktop"
echo "  cp secure-browser.desktop ~/.local/share/applications/"
