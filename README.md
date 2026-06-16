# Secure Privacy Browser Ultimate

A privacy-focused daily-driver web browser built on PyQt6 and Chromium WebEngine. It provides programmatic, local-first control over user identity signatures, network routing, and security policies, making it ideal for both developers and privacy advocates.

---

## Key Features

### 🛡️ Advanced Fingerprint Protection Shield
Intercepts and spoofs critical browser fingerprinting vectors at document creation:
* **Canvas Poisoning**: Injects micro-noise to the alpha channels of multiple random pixels during canvas reads (`getImageData`), making canvas rendering hashes completely dynamic.
* **Audio Wave Spoofing**: Overrides `AudioBuffer.prototype.getChannelData` to inject static-level noise into synthesized audio vectors, preventing audio hardware fingerprinters from profiling physical soundcards.
* **Hardware & Specs Obfuscation**: Forces `navigator.hardwareConcurrency` to 4, `navigator.deviceMemory` to 8GB, platform to `Win32`, and completely masks browser plugins and mimeTypes.
* **Display Uniformity**: Hardcodes window screen coordinates to 1920x1080 and color/pixel depths to 24-bit to prevent screen-geometry-based tracing.
* **Battery Mocking**: Returns static charging details to stop battery-drain session tracking.

### 🌐 Network Anonymity Toggles
* **Tor 3-Hop Routing**: Features a **"Tor"** toggle that automatically checks local ports `9050` (system Tor service) and `9150` (Tor Browser bundle). If active, all requests route securely through the Onion routing network.
* **Dynamic SOCKS5 Proxies**: Scrapes and rotates public SOCKS5 proxies at the click of the "Rot" (Rotate) button.
* **Chromium Leak Blocking**: Disables WebRTC (`--disable-webrtc`) to prevent public/private IP leakage through STUN/TURN queries, and disables speculative prefetching (`--dns-prefetch-disable`).

### 💻 Developer Local Subnet Exceptions
* Automatically detects and exempts loopbacks and local subnets (`localhost`, `127.0.0.1`, `::1`, `192.168.x.x`, `10.x.x.x`, `172.16.x.x - 172.31.x.x`) from forced HTTPS redirection and tracker blocklists.
* Enables seamless local development testing alongside strict web security layers.

### 🚨 Dual Exit Panic Switch
Includes a hardware-level exit handler that safely releases RAM and terminates execution immediately:
* Pressing **`Ctrl+Shift+Q`**
* Double-pressing **`Escape`** (within 500ms)

### 🎨 Premium UI & Stylesheet
* Features a dark-mode palette (#0c0f12, #0d1117, #161b22, #58a6ff) reminiscent of advanced IDEs.
* Dynamic history tracking that automatically enables/disables Back (`<`) and Forward (`>`) controls based on standard QWebEnginePage actions.
* Smart URL bar search fallback routing non-URL strings straight to encrypted DuckDuckGo search queries.

---

## Setup & Running

### 1. Install Dependencies
Ensure you have Python 3 and the required libraries:
```bash
pip install -r requirements.txt
```

### 2. Run the Browser
```bash
python3 main.py
```

### 3. Using Tor Routing
To utilize the Tor Mode:
* Make sure you have a local Tor instance running:
  * **Linux (System Tor)**: `sudo systemctl start tor` (exposes port `9050`)
  * **Any OS (Tor Browser Bundle)**: Just launch Tor Browser in the background (exposes port `9150`)
* Click the **Tor** checkbox on the toolbar. If it connects, the status indicator will turn green showing `Tor (port)`. If not, it falls back to a direct connection and shows `Tor Offline`.
