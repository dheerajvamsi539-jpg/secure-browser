#!/bin/bash

# Exit on error
set -e

APP_NAME="secure-browser"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "--- 0. Checking Dependencies ---"
python3 -c "import PyQt6, PyQt6.QtWebEngineCore, requests" 2>/dev/null || {
    echo "Error: Missing dependencies. Please run: pip install -r requirements.txt"
    exit 1
}

echo "--- 1. Preparing Installation Directory ---"
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"

echo "--- 2. Copying Application Files ---"
cp *.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"
# Note: We assume dependencies are already installed on the system as verified.

echo "--- 3. Creating Launcher ---"
cat <<EOF > "$BIN_DIR/$APP_NAME"
#!/bin/bash
python3 "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/$APP_NAME"

echo "--- 4. Creating Desktop Entry ---"
cat <<EOF > "$DESKTOP_DIR/$APP_NAME.desktop"
[Desktop Entry]
Name=Secure Browser
Comment=Privacy-focused web browser with VPN and Tor
Exec=$BIN_DIR/$APP_NAME
Icon=security-high
Terminal=false
Type=Application
Categories=Network;WebBrowser;
Keywords=privacy;browser;tor;vpn;
EOF

echo "--- Installation Complete ---"
echo "You can now launch 'Secure Browser' from your application menu."
echo "Or run it from the terminal using: $APP_NAME"
echo ""
echo "Note: If '$BIN_DIR' is not in your PATH, you may need to add it:"
echo "export PATH=\$PATH:$BIN_DIR"
