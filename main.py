import sys
import os
import threading
import requests
import random
import socket
import re
import time
import select

# Helper for local host checks
def is_local_host(host):
    host = host.strip().lower()
    if host in ("localhost", "::1"):
        return True
    if host.startswith("127."):
        return True
    if host.startswith("192.168."):
        return True
    if host.startswith("10."):
        return True
    if host.startswith("172."):
        match = re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", host)
        if match:
            return True
    if host.startswith("fe80:") or host == "::":
        return True
    return False

# --- Local SOCKS5 Proxy Server for Dynamic Upstream Routing ---
class LocalSocks5Proxy:
    def __init__(self):
        self.server = None
        self.port = 0
        self.mode = "direct"  # "direct", "tor", "vpn"
        self.upstream_host = None
        self.upstream_port = None
        self.running = False

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('127.0.0.1', 0))
        self.port = self.server.getsockname()[1]
        self.server.listen(128)
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()
        print(f"Local SOCKS5 proxy listening on 127.0.0.1:{self.port}")

    def set_mode(self, mode, host=None, port=None):
        self.mode = mode
        self.upstream_host = host
        self.upstream_port = port
        print(f"Local SOCKS5 proxy mode changed to: {mode} (upstream: {host}:{port})")

    def _listen(self):
        while self.running:
            try:
                client_sock, addr = self.server.accept()
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except Exception:
                break

    def _handle_client(self, client_sock):
        try:
            # 1. Greeting
            greeting = client_sock.recv(262)
            if not greeting or greeting[0] != 5:
                client_sock.close()
                return
            
            client_sock.sendall(b"\x05\x00")
            
            # 2. Request
            request = client_sock.recv(4)
            if not request or request[0] != 5 or request[1] != 1:
                client_sock.close()
                return
                
            atyp = request[3]
            if atyp == 1:
                addr_bytes = client_sock.recv(4)
                dest_addr = socket.inet_ntoa(addr_bytes)
            elif atyp == 3:
                len_byte = client_sock.recv(1)
                if not len_byte:
                    client_sock.close()
                    return
                addr_len = len_byte[0]
                dest_addr = client_sock.recv(addr_len).decode('utf-8')
            elif atyp == 4:
                addr_bytes = client_sock.recv(16)
                dest_addr = socket.inet_ntop(socket.AF_INET6, addr_bytes)
            else:
                client_sock.close()
                return
                
            port_bytes = client_sock.recv(2)
            dest_port = int.from_bytes(port_bytes, 'big')

            if atyp == 1:
                full_request = request + addr_bytes + port_bytes
            elif atyp == 3:
                full_request = request + len_byte + dest_addr.encode('utf-8') + port_bytes
            elif atyp == 4:
                full_request = request + addr_bytes + port_bytes

            upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            if self.mode == "vpn":
                proxy_host = self.upstream_host
                proxy_port = self.upstream_port
                
                upstream_sock.connect((proxy_host, proxy_port))
                upstream_sock.sendall(greeting)
                reply = upstream_sock.recv(2)
                if not reply or reply[0] != 5 or reply[1] != 0:
                    client_sock.close()
                    upstream_sock.close()
                    return
                
                upstream_sock.sendall(full_request)
                resp = upstream_sock.recv(1024)
                client_sock.sendall(resp)
                if not resp or resp[1] != 0:
                    client_sock.close()
                    upstream_sock.close()
                    return
            else:
                upstream_sock.connect((dest_addr, dest_port))
                client_sock.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")

            self._forward(client_sock, upstream_sock)
        except Exception:
            try: client_sock.close()
            except: pass
            try: upstream_sock.close()
            except: pass

    def _forward(self, sock1, sock2):
        inputs = [sock1, sock2]
        while True:
            readable, _, exceptional = select.select(inputs, [], inputs, 60)
            if exceptional:
                break
            for s in readable:
                other = sock2 if s is sock1 else sock1
                try:
                    data = s.recv(4096)
                    if not data:
                        return
                    other.sendall(data)
                except Exception:
                    return

# Check if running on Android
IS_ANDROID = os.environ.get('ANDROID_ARGUMENT') is not None
if not IS_ANDROID:
    try:
        from kivy.utils import platform
        if platform == 'android':
            IS_ANDROID = True
    except ImportError:
        pass

if IS_ANDROID:
    # ==========================================
    #             ANDROID (KIVY) IMPLEMENTATION
    # ==========================================
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from kivy.uix.label import Label
    from kivy.uix.checkbox import CheckBox
    from kivy.uix.widget import Widget
    from kivy.clock import Clock
    from kivy.utils import platform
    from kivy.graphics import Color, Rectangle

    from jnius import autoclass, cast, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread

    # Android native classes via PyJNIus
    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
    LinearLayout = autoclass('android.widget.LinearLayout')
    Activity = autoclass('org.kivy.android.PythonActivity').mActivity
    Context = autoclass('android.content.Context')
    ProxyController = autoclass('androidx.webkit.ProxyController')
    ProxyConfig = autoclass('androidx.webkit.ProxyConfig')
    Executor = autoclass('java.util.concurrent.Executor')
    WebResourceResponse = autoclass('android.webkit.WebResourceResponse')

    class PyRunnable(PythonJavaClass):
        __javainterfaces__ = ['java/lang/Runnable']

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method('()V')
        def run(self):
            if self.callback:
                self.callback()

    class MyWebViewClient(PythonJavaClass):
        __javaclass__ = 'android/webkit/WebViewClient'

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method('(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;)Landroid/webkit/WebResourceResponse;')
        def shouldInterceptRequest(self, view, request):
            url = request.getUrl().toString()
            
            # HTTPS Upgrade for subresources
            if self.app.https_enabled and url.startswith("http://"):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.netloc.split(':')[0]
                if not is_local_host(host):
                    return WebResourceResponse("text/plain", "UTF-8", None)
                    
            # Ad blocker / tracker blocker
            if self.app.adblock_enabled:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.netloc.split(':')[0].lower()
                if not is_local_host(host):
                    host_parts = host.split('.')
                    for i in range(len(host_parts) - 1):
                        parent = '.'.join(host_parts[i:])
                        if parent in self.app.blocked_domains:
                            return WebResourceResponse("text/plain", "UTF-8", None)
                            
            return None

        @java_method('(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;)Z')
        def shouldOverrideUrlLoading(self, view, request):
            url = request.getUrl().toString()
            return self.app.handle_navigation(view, url)

        @java_method('(Landroid/webkit/WebView;Ljava/lang/String;Landroid/graphics/Bitmap;)V')
        def onPageStarted(self, view, url, favicon):
            self.app.url_input.text = url
            if self.app.js_enabled:
                view.evaluateJavascript(self.app.injected_script_code, None)

        @java_method('(Landroid/webkit/WebView;Ljava/lang/String;)V')
        def onPageFinished(self, view, url):
            self.app.url_input.text = url
            if self.app.js_enabled:
                view.evaluateJavascript(self.app.injected_script_code, None)

    class KivyProxyFetcher:
        def __init__(self, on_ready, on_error):
            self.on_ready = on_ready
            self.on_error = on_error

        def fetch(self):
            def _task():
                try:
                    api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=1000&country=all&ssl=all&anonymity=all"
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\r\n')
                        if proxies:
                            random.shuffle(proxies)
                            for addr in proxies[:10]:
                                try:
                                    host, port = addr.split(':')
                                    with socket.create_connection((host, int(port)), timeout=3):
                                        Clock.schedule_once(lambda dt: self.on_ready(host, int(port)))
                                        return
                                except:
                                    continue
                            Clock.schedule_once(lambda dt: self.on_error("No responsive proxies found."))
                        else:
                            Clock.schedule_once(lambda dt: self.on_error("No proxies found."))
                    else:
                        Clock.schedule_once(lambda dt: self.on_error(f"API Error: {response.status_code}"))
                except Exception as e:
                    Clock.schedule_once(lambda dt: self.on_error(str(e)))
            
            threading.Thread(target=_task, daemon=True).start()

    class ColorBoxLayout(BoxLayout):
        def __init__(self, bg_color, **kwargs):
            super().__init__(**kwargs)
            self.bg_color = bg_color
            with self.canvas.before:
                Color(*bg_color)
                self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)

        def _update_rect(self, instance, value):
            self.rect.pos = instance.pos
            self.rect.size = instance.size

    class SecureBrowserAndroid(App):
        def build(self):
            self.title = "Secure Browser Ultimate"
            
            # Start local proxy
            self.local_proxy = LocalSocks5Proxy()
            self.local_proxy.start()
            
            # App variables for feature parity
            self.js_enabled = True
            self.adblock_enabled = True
            self.https_enabled = True
            
            # Set up injected JS script code (anti-fingerprinting)
            self.injected_script_code = """
            // Screen Geometry
            Object.defineProperty(window.screen, 'width', { get: function(){ return 1920; } });
            Object.defineProperty(window.screen, 'height', { get: function(){ return 1080; } });
            Object.defineProperty(window.screen, 'availWidth', { get: function(){ return 1920; } });
            Object.defineProperty(window.screen, 'availHeight', { get: function(){ return 1080; } });
            Object.defineProperty(window.screen, 'colorDepth', { get: function(){ return 24; } });
            Object.defineProperty(window.screen, 'pixelDepth', { get: function(){ return 24; } });
            Object.defineProperty(window, 'devicePixelRatio', { get: function(){ return 1; } });

            // Hardware Obfuscation
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: function(){ return 4; } });
            Object.defineProperty(navigator, 'deviceMemory', { get: function(){ return 8; } });
            Object.defineProperty(navigator, 'platform', { get: function(){ return 'Win32'; } });
            Object.defineProperty(navigator, 'plugins', { get: function(){ return []; } });
            Object.defineProperty(navigator, 'mimeTypes', { get: function(){ return []; } });

            // Canvas Poisoning
            (function() {
                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                    const imageData = originalGetImageData.apply(this, arguments);
                    const index = Math.floor(Math.random() * (imageData.data.length / 4)) * 4 + 3;
                    imageData.data[index] = imageData.data[index] ^ 1; 
                    return imageData;
                };
            })();

            // Audio Wave Spoofing
            (function() {
                if (window.AudioBuffer) {
                    const originalGetChannelData = AudioBuffer.prototype.getChannelData;
                    AudioBuffer.prototype.getChannelData = function(channel) {
                        const data = originalGetChannelData.apply(this, arguments);
                        for (let i = 0; i < data.length; i += 100) {
                            data[i] += (Math.random() - 0.5) * 1e-5;
                        }
                        return data;
                    };
                }
            })();

            // Battery Mocking
            if (navigator.getBattery) {
                navigator.getBattery = function() {
                    return Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 1.0,
                        onchargingchange: null,
                        onchargingtimechange: null,
                        ondischargingtimechange: null,
                        onlevelchange: null
                    });
                };
            }
            """
            
            # Load hosts list for adblocking
            self.load_hosts()
            
            # Main Layout
            self.root = BoxLayout(orientation='vertical')
            
            # Color palette
            toolbar_bg = (0.086, 0.106, 0.133, 1) # #161b22
            btn_bg = (0.13, 0.15, 0.18, 1) # #21262d
            btn_text = (0.79, 0.82, 0.85, 1) # #c9d1d9
            lbl_text = (0.55, 0.58, 0.62, 1) # #8b949e
            
            # Row 1: Nav buttons + URL input
            self.row1 = ColorBoxLayout(bg_color=toolbar_bg, size_hint_y=None, height='45dp', spacing='5dp', padding='5dp')
            
            self.back_btn = Button(text='<', size_hint_x=None, width='40dp', background_normal='', background_color=btn_bg, color=btn_text)
            self.back_btn.bind(on_release=self.go_back)
            
            self.forward_btn = Button(text='>', size_hint_x=None, width='40dp', background_normal='', background_color=btn_bg, color=btn_text)
            self.forward_btn.bind(on_release=self.go_forward)
            
            self.reload_btn = Button(text='↻', size_hint_x=None, width='40dp', background_normal='', background_color=btn_bg, color=btn_text)
            self.reload_btn.bind(on_release=self.reload_page)
            
            self.url_input = TextInput(
                text='https://duckduckgo.com', 
                multiline=False, 
                font_size='14sp',
                background_normal='',
                background_color=(0.004, 0.016, 0.035, 1), # #010409
                foreground_color=(0.35, 0.65, 1.0, 1), # #58a6ff
                cursor_color=(0.35, 0.65, 1.0, 1)
            )
            self.url_input.bind(on_text_validate=self.load_url)
            
            self.row1.add_widget(self.back_btn)
            self.row1.add_widget(self.forward_btn)
            self.row1.add_widget(self.reload_btn)
            self.row1.add_widget(self.url_input)
            
            # Row 2: Features Toggles + VPN + Rot + Status
            self.row2 = ColorBoxLayout(bg_color=toolbar_bg, size_hint_y=None, height='40dp', spacing='5dp', padding='5dp')
            
            # JS Toggle
            self.js_label = Label(text='JS', size_hint_x=None, width='25dp', font_size='12sp', color=lbl_text)
            self.js_toggle = CheckBox(size_hint_x=None, width='30dp', active=True)
            self.js_toggle.bind(active=self.toggle_js)
            
            js_layout = BoxLayout(orientation='horizontal', size_hint_x=None, width='55dp')
            js_layout.add_widget(self.js_label)
            js_layout.add_widget(self.js_toggle)
            
            # Ads Toggle
            self.ads_label = Label(text='Ads', size_hint_x=None, width='30dp', font_size='12sp', color=lbl_text)
            self.ads_toggle = CheckBox(size_hint_x=None, width='30dp', active=True)
            self.ads_toggle.bind(active=self.toggle_adblock)
            
            ads_layout = BoxLayout(orientation='horizontal', size_hint_x=None, width='60dp')
            ads_layout.add_widget(self.ads_label)
            ads_layout.add_widget(self.ads_toggle)
            
            # HTTPS Toggle
            self.https_label = Label(text='HTTPS', size_hint_x=None, width='45dp', font_size='12sp', color=lbl_text)
            self.https_toggle = CheckBox(size_hint_x=None, width='30dp', active=True)
            self.https_toggle.bind(active=self.toggle_https)
            
            https_layout = BoxLayout(orientation='horizontal', size_hint_x=None, width='75dp')
            https_layout.add_widget(self.https_label)
            https_layout.add_widget(self.https_toggle)
            
            # Spring Spacer
            spacer = Widget()
            
            # VPN Section
            self.vpn_label = Label(text='VPN', size_hint_x=None, width='30dp', font_size='12sp', color=lbl_text)
            self.vpn_toggle = CheckBox(size_hint_x=None, width='30dp')
            self.vpn_toggle.bind(active=self.toggle_vpn)
            
            vpn_layout = BoxLayout(orientation='horizontal', size_hint_x=None, width='60dp')
            vpn_layout.add_widget(self.vpn_label)
            vpn_layout.add_widget(self.vpn_toggle)
            
            # Rotate button
            self.rotate_btn = Button(text='Rot', size_hint_x=None, width='45dp', background_normal='', background_color=btn_bg, color=btn_text, disabled=True)
            self.rotate_btn.bind(on_release=self.rotate_proxy)
            
            # Status Label
            self.vpn_status = Label(text='Off', size_hint_x=None, width='35dp', font_size='12sp', color=lbl_text)
            
            self.row2.add_widget(js_layout)
            self.row2.add_widget(ads_layout)
            self.row2.add_widget(https_layout)
            self.row2.add_widget(spacer)
            self.row2.add_widget(vpn_layout)
            self.row2.add_widget(self.rotate_btn)
            self.row2.add_widget(self.vpn_status)
            
            # Add toolbars to layout
            self.root.add_widget(self.row1)
            self.root.add_widget(self.row2)
            
            # WebView Container (bottom layout placeholder)
            self.webview_container = BoxLayout()
            self.root.add_widget(self.webview_container)
            
            # Initialize Android WebView
            if platform == 'android':
                self.init_webview()
                
            self.fetcher = KivyProxyFetcher(self.apply_proxy, self.handle_error)
            
            return self.root

        # Hosts loader
        def load_hosts(self):
            self.blocked_domains = {
                "doubleclick.net", "google-analytics.com", "googletagservices.com",
                "googlesyndication.com", "adnxs.com", "quantserve.com",
                "scorecardresearch.com", "facebook.net", "facebook.com/tr/",
                "amazon-adsystem.com", "taboola.com", "outbrain.com",
                "adroll.com", "chartbeat.com", "pixel.wp.com"
            }
            
            cache_dir = self.user_data_dir
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, "blocked_hosts.txt")
            
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r") as f:
                        for line in f:
                            domain = line.strip()
                            if domain:
                                self.blocked_domains.add(domain)
                except Exception as e:
                    print(f"Error reading cache: {e}")
                    
            def _download():
                try:
                    url = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        new_domains = set()
                        for line in r.text.splitlines():
                            line = line.strip()
                            if line.startswith("0.0.0.0 "):
                                parts = line.split()
                                if len(parts) >= 2:
                                    d = parts[1].strip()
                                    if d and d not in ("localhost", "0.0.0.0"):
                                        new_domains.add(d)
                        if new_domains:
                            self.blocked_domains = new_domains
                            with open(cache_path, "w") as f:
                                for d in sorted(new_domains):
                                    f.write(d + "\n")
                except Exception as e:
                    print(f"Failed to download hosts list: {e}")
                    
            threading.Thread(target=_download, daemon=True).start()

        @run_on_ui_thread
        def init_webview(self):
            self.webview = WebView(Activity)
            self.webview.getSettings().setJavaScriptEnabled(True)
            self.webview.getSettings().setDomStorageEnabled(True)
            self.webview.getSettings().setDatabaseEnabled(True)
            
            self.webview_client = MyWebViewClient(self)
            self.webview.setWebViewClient(self.webview_client)
            
            self.set_android_proxy("127.0.0.1", self.local_proxy.port)
            
            decor_view = Activity.getWindow().getDecorView()
            FrameLayout = autoclass('android.widget.FrameLayout')
            FrameLayout_LayoutParams = autoclass('android.widget.FrameLayout$LayoutParams')
            decor_layout = cast(FrameLayout, decor_view)
            
            metrics = Activity.getResources().getDisplayMetrics()
            density = metrics.density
            toolbar_height_px = int(85 * density)  # 45dp (row1) + 40dp (row2) = 85dp
            
            params = FrameLayout_LayoutParams(
                FrameLayout_LayoutParams.MATCH_PARENT,
                FrameLayout_LayoutParams.MATCH_PARENT
            )
            params.topMargin = toolbar_height_px
            
            decor_layout.addView(self.webview, params)
            self.webview.loadUrl("https://duckduckgo.com")

        def load_url(self, instance=None):
            url = self.url_input.text.strip()
            if url:
                if not url.startswith('http') and not url.startswith('about:'):
                    url = 'https://' + url
                if platform == 'android':
                    self.run_load_url(url)
                else:
                    print(f"Loading URL: {url}")

        @run_on_ui_thread
        def run_load_url(self, url):
            self.webview.loadUrl(url)

        def go_back(self, instance=None):
            if platform == 'android':
                self.run_go_back()

        @run_on_ui_thread
        def run_go_back(self):
            if self.webview.canGoBack():
                self.webview.goBack()

        def go_forward(self, instance=None):
            if platform == 'android':
                self.run_go_forward()

        @run_on_ui_thread
        def run_go_forward(self):
            if self.webview.canGoForward():
                self.webview.goForward()

        def reload_page(self, instance=None):
            if platform == 'android':
                self.run_reload_page()

        @run_on_ui_thread
        def run_reload_page(self):
            self.webview.reload()

        def toggle_js(self, checkbox, value):
            self.js_enabled = value
            if platform == 'android':
                self.run_toggle_js(value)

        @run_on_ui_thread
        def run_toggle_js(self, value):
            self.webview.getSettings().setJavaScriptEnabled(value)
            self.webview.reload()

        def toggle_adblock(self, checkbox, value):
            self.adblock_enabled = value
            if platform == 'android':
                self.run_reload_page()

        def toggle_https(self, checkbox, value):
            self.https_enabled = value
            if platform == 'android':
                self.run_reload_page()

        def toggle_vpn(self, checkbox, value):
            if value:
                self.vpn_status.text = '...'
                self.vpn_status.color = (0.86, 0.67, 0.04, 1) # Orange
                self.rotate_btn.disabled = False
                self.fetcher.fetch()
            else:
                self.local_proxy.set_mode("direct")
                self.vpn_status.text = 'Off'
                self.vpn_status.color = (0.55, 0.58, 0.62, 1) # Gray
                self.rotate_btn.disabled = True
                if platform == 'android':
                    self.run_reload_page()

        def rotate_proxy(self, instance=None):
            self.vpn_status.text = '...'
            self.vpn_status.color = (0.86, 0.67, 0.04, 1) # Orange
            self.fetcher.fetch()

        def apply_proxy(self, host, port):
            self.local_proxy.set_mode("vpn", host, port)
            self.vpn_status.text = 'ON'
            self.vpn_status.color = (0.18, 0.63, 0.26, 1) # Green
            if platform == 'android':
                self.run_reload_page()

        def handle_error(self, error):
            self.vpn_status.text = 'ERR'
            self.vpn_status.color = (0.97, 0.32, 0.29, 1) # Red
            self.vpn_toggle.active = False
            self.rotate_btn.disabled = True

        def handle_navigation(self, view, url):
            if url.startswith("http://"):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.netloc.split(':')[0]
                if is_local_host(host):
                    return False
                
                new_url = "https://" + url[7:]
                from android.runnable import run_on_ui_thread
                @run_on_ui_thread
                def load():
                    view.loadUrl(new_url)
                load()
                return True
            return False

        @run_on_ui_thread
        def set_android_proxy(self, host, port):
            proxy_config = ProxyConfig.Builder() \
                .addProxyRule(f"socks://{host}:{port}") \
                .addDirect().build()
            
            executor = Activity.getMainExecutor()
            if not hasattr(self, '_proxy_listener') or self._proxy_listener is None:
                self._proxy_listener = PyRunnable(lambda: print("Proxy override applied"))
            ProxyController.getInstance().setProxyOverride(proxy_config, executor, self._proxy_listener)

        def on_start(self):
            from kivy.core.window import Window
            Window.bind(on_keyboard=self.on_key_down)
            self.last_escape_time = 0

        def on_key_down(self, window, key, scancode, codepoint, modifiers):
            if key == 27: # Escape/Back
                current_time = time.time()
                if (current_time - self.last_escape_time) < 0.5:
                    import gc
                    gc.collect()
                    if platform == 'android':
                        Activity.finishAndRemoveTask()
                    else:
                        sys.exit(0)
                    return True
                else:
                    self.last_escape_time = current_time
                    if platform == 'android' and self.webview.canGoBack():
                        self.run_go_back()
                        return True
                    return False
            return False

else:
    # ==========================================
    #             DESKTOP (PYQT6) IMPLEMENTATION
    # ==========================================
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QLabel, QCheckBox, QProgressBar, QTabWidget
    )
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import (
        QWebEngineProfile, QWebEngineSettings, QWebEnginePage, QWebEngineScript, QWebEngineUrlRequestInterceptor
    )
    from PyQt6.QtCore import QUrl, pyqtSignal, QObject, Qt
    from PyQt6.QtNetwork import QNetworkProxy

    # --- Ad-Blocker / Tracker / Security Interceptor ---
    class TrackerInterceptor(QWebEngineUrlRequestInterceptor):
        def __init__(self):
            super().__init__()
            self.enabled = True
            self.force_https = True
            self.strip_referer = True 
            
            self.blocked_domains = {
                "doubleclick.net", "google-analytics.com", "googletagservices.com",
                "googlesyndication.com", "adnxs.com", "quantserve.com",
                "scorecardresearch.com", "facebook.net", "facebook.com/tr/",
                "amazon-adsystem.com", "taboola.com", "outbrain.com",
                "adroll.com", "chartbeat.com", "pixel.wp.com"
            }
            self.load_hosts()

        def load_hosts(self):
            cache_dir = os.path.expanduser("~/.local/share/secure-browser")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, "blocked_hosts.txt")
            
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r") as f:
                        for line in f:
                            domain = line.strip()
                            if domain:
                                self.blocked_domains.add(domain)
                    print(f"Loaded {len(self.blocked_domains)} blocked domains from cache.")
                except Exception as e:
                    print(f"Error reading cache: {e}")
                    
            def _download():
                try:
                    url = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        new_domains = set()
                        for line in r.text.splitlines():
                            line = line.strip()
                            if line.startswith("0.0.0.0 "):
                                parts = line.split()
                                if len(parts) >= 2:
                                    d = parts[1].strip()
                                    if d and d not in ("localhost", "0.0.0.0"):
                                        new_domains.add(d)
                        if new_domains:
                            self.blocked_domains = new_domains
                            with open(cache_path, "w") as f:
                                for d in sorted(new_domains):
                                    f.write(d + "\n")
                            print(f"Downloaded and updated {len(new_domains)} blocked domains.")
                except Exception as e:
                    print(f"Failed to download hosts list: {e}")
                    
            threading.Thread(target=_download, daemon=True).start()

        def interceptRequest(self, info):
            url_obj = info.requestUrl()
            host = url_obj.host().lower()
            if is_local_host(host):
                return

            if self.strip_referer:
                info.setHttpHeader(b"Referer", b"")

            if self.force_https and url_obj.scheme() == "http":
                info.block(True)
                return

            if self.enabled:
                host_parts = host.split('.')
                for i in range(len(host_parts) - 1):
                    parent = '.'.join(host_parts[i:])
                    if parent in self.blocked_domains:
                        info.block(True)
                        return

    # --- Proxy / VPN Logic ---
    class ProxyFetcher(QObject):
        proxy_ready = pyqtSignal(str, int)
        error = pyqtSignal(str)

        def fetch(self):
            def _task():
                try:
                    api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=1000&country=all&ssl=all&anonymity=all"
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\r\n')
                        if proxies:
                            random.shuffle(proxies)
                            for addr in proxies[:10]:
                                try:
                                    host, port = addr.split(':')
                                    with socket.create_connection((host, int(port)), timeout=3):
                                        self.proxy_ready.emit(host, int(port))
                                        return
                                except (socket.timeout, ConnectionRefusedError, OSError):
                                    continue
                            self.error.emit("Could not find a responsive proxy. Try rotating.")
                        else:
                            self.error.emit("No proxies found.")
                    else:
                        self.error.emit(f"API Error: {response.status_code}")
                except Exception as e:
                    self.error.emit(str(e))
            
            threading.Thread(target=_task, daemon=True).start()

    # --- Hardened Web Page ---
    class SecureWebPage(QWebEnginePage):
        def __init__(self, profile, parent=None):
            super().__init__(profile, parent)

        def acceptNavigationRequest(self, url, nav_type, is_main_frame):
            if url.scheme() == "http":
                if is_local_host(url.host()):
                    return True
                new_url = QUrl(url)
                new_url.setScheme("https")
                self.setUrl(new_url)
                return False

            if nav_type == QWebEnginePage.NavigationType.NavigationTypeRedirect:
                reply = QMessageBox.question(
                    None, "Redirect Blocked",
                    f"The website is trying to redirect you to:\n{url.toString()}\n\nDo you want to allow this?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                return reply == QMessageBox.StandardButton.Yes
            return True

        def createWindow(self, _type):
            parent = self.view().window()
            if parent and hasattr(parent, 'add_new_tab'):
                new_browser = parent.add_new_tab(QUrl("about:blank"))
                return new_browser.page()
            return None

    # --- Main Application ---
    class SecureBrowser(QMainWindow):
        def __init__(self, local_proxy):
            super().__init__()
            self.setWindowTitle("Secure Privacy Browser Ultimate")
            self.resize(1300, 850)
            self.last_escape_time = 0
            self.local_proxy = local_proxy

            self.profile = QWebEngineProfile("SecureProfile", self)
            self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
            self.profile.cookieStore().setCookieFilter(lambda request: not request.thirdParty)
            
            self.interceptor = TrackerInterceptor()
            self.profile.setUrlRequestInterceptor(self.interceptor)

            settings = self.profile.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            
            if hasattr(QWebEngineSettings.WebAttribute, "ReadingFromCanvasEnabled"):
                settings.setAttribute(QWebEngineSettings.WebAttribute.ReadingFromCanvasEnabled, False)

            ua_pool = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
            ]
            selected_ua = random.choice(ua_pool)
            self.current_user_agent = selected_ua
            self.profile.setHttpUserAgent(selected_ua)

            script_code = """
            // Screen Geometry
            Object.defineProperty(window.screen, 'width', { get: function(){ return 1920; } });
            Object.defineProperty(window.screen, 'height', { get: function(){ return 1080; } });
            Object.defineProperty(window.screen, 'availWidth', { get: function(){ return 1920; } });
            Object.defineProperty(window.screen, 'availHeight', { get: function(){ return 1080; } });
            Object.defineProperty(window.screen, 'colorDepth', { get: function(){ return 24; } });
            Object.defineProperty(window.screen, 'pixelDepth', { get: function(){ return 24; } });
            Object.defineProperty(window, 'devicePixelRatio', { get: function(){ return 1; } });

            // Hardware Obfuscation
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: function(){ return 4; } });
            Object.defineProperty(navigator, 'deviceMemory', { get: function(){ return 8; } });
            Object.defineProperty(navigator, 'platform', { get: function(){ return 'Win32'; } });
            Object.defineProperty(navigator, 'plugins', { get: function(){ return []; } });
            Object.defineProperty(navigator, 'mimeTypes', { get: function(){ return []; } });

            // Canvas Poisoning
            (function() {
                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                    const imageData = originalGetImageData.apply(this, arguments);
                    const index = Math.floor(Math.random() * (imageData.data.length / 4)) * 4 + 3;
                    imageData.data[index] = imageData.data[index] ^ 1; 
                    return imageData;
                };
            })();

            // Audio Wave Spoofing
            (function() {
                if (window.AudioBuffer) {
                    const originalGetChannelData = AudioBuffer.prototype.getChannelData;
                    AudioBuffer.prototype.getChannelData = function(channel) {
                        const data = originalGetChannelData.apply(this, arguments);
                        for (let i = 0; i < data.length; i += 100) {
                            data[i] += (Math.random() - 0.5) * 1e-5;
                        }
                        return data;
                    };
                }
            })();

            // Battery Mocking
            if (navigator.getBattery) {
                navigator.getBattery = function() {
                    return Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 1.0,
                        onchargingchange: null,
                        onchargingtimechange: null,
                        ondischargingtimechange: null,
                        onlevelchange: null
                    });
                };
            }
            """
            self.injected_script_code = script_code
            script = QWebEngineScript()
            script.setSourceCode(script_code)
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(True)
            self.profile.scripts().insert(script)

            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)
            self.main_layout = QVBoxLayout(self.central_widget)
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(0)

            self.setStyleSheet("""
                QMainWindow { background-color: #0d1117; }
                QWidget { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
                QPushButton { 
                    background-color: #21262d; border: 1px solid #30363d; border-radius: 4px; padding: 4px; color: #c9d1d9; 
                }
                QPushButton:hover { background-color: #30363d; border-color: #8b949e; }
                QPushButton:pressed { background-color: #161b22; }
                QPushButton:disabled { color: #484f58; background-color: #0d1117; }
                
                QLineEdit { 
                    background-color: #010409; border: 1px solid #30363d; border-radius: 6px; padding: 4px 10px; color: #58a6ff; 
                }
                QLineEdit:focus { border: 1px solid #58a6ff; }
                
                QCheckBox { spacing: 5px; }
                QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #30363d; border-radius: 3px; background: #21262d; }
                QCheckBox::indicator:checked { background-color: #238636; border-color: #2ea043; }
                
                QProgressBar { background-color: #161b22; border: none; height: 2px; }
                QProgressBar::chunk { background-color: #58a6ff; }
                
                QLabel { color: #8b949e; }

                QTabWidget::pane { border: 1px solid #30363d; top: -1px; background-color: #0d1117; }
                QTabBar::tab {
                    background: #161b22;
                    border: 1px solid #30363d;
                    border-bottom: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    padding: 6px 15px;
                    color: #8b949e;
                    min-width: 100px;
                    max-width: 200px;
                }
                QTabBar::tab:selected {
                    background: #0d1117;
                    color: #c9d1d9;
                    border-bottom: 1px solid #0d1117;
                    font-weight: bold;
                }
                QTabBar::tab:hover {
                    background: #21262d;
                    color: #c9d1d9;
                }
            """)

            self.toolbar_widget = QWidget()
            self.toolbar_widget.setFixedHeight(40)
            self.toolbar_widget.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #30363d;")
            self.toolbar = QHBoxLayout(self.toolbar_widget)
            self.toolbar.setContentsMargins(8, 0, 8, 0)
            self.toolbar.setSpacing(8)

            def create_separator():
                line = QLabel("|")
                line.setStyleSheet("color: #30363d; font-weight: bold; margin: 0 2px;")
                return line

            self.back_btn = QPushButton("<")
            self.back_btn.setFixedSize(28, 28)
            self.forward_btn = QPushButton(">")
            self.forward_btn.setFixedSize(28, 28)
            self.reload_btn = QPushButton("↻")
            self.reload_btn.setFixedSize(28, 28)
            
            self.add_tab_btn = QPushButton("+")
            self.add_tab_btn.setFixedSize(28, 28)
            self.add_tab_btn.clicked.connect(lambda: self.add_new_tab())
            
            self.address_bar = QLineEdit()
            self.address_bar.setPlaceholderText("Search or enter address...")
            self.address_bar.returnPressed.connect(self.load_url)
            
            self.js_toggle = QCheckBox("JS")
            self.js_toggle.setChecked(True)
            self.js_toggle.stateChanged.connect(self.toggle_js)

            self.adblock_toggle = QCheckBox("Ads")
            self.adblock_toggle.setChecked(True)
            self.adblock_toggle.stateChanged.connect(self.toggle_adblock)

            self.https_toggle = QCheckBox("HTTPS")
            self.https_toggle.setChecked(True)
            self.https_toggle.stateChanged.connect(self.toggle_https)

            self.vpn_toggle = QCheckBox("VPN")
            self.vpn_toggle.stateChanged.connect(self.toggle_vpn)
            self.rotate_btn = QPushButton("Rot")
            self.rotate_btn.setFixedSize(35, 26)
            self.rotate_btn.clicked.connect(self.rotate_proxy)
            self.rotate_btn.setEnabled(False)
            self.vpn_status = QLabel("Off")
            self.vpn_status.setFixedWidth(30)

            self.toolbar.addWidget(self.back_btn)
            self.toolbar.addWidget(self.forward_btn)
            self.toolbar.addWidget(self.reload_btn)
            self.toolbar.addWidget(self.add_tab_btn)
            self.toolbar.addWidget(create_separator())
            self.toolbar.addWidget(self.address_bar)
            self.toolbar.addWidget(create_separator())
            self.toolbar.addWidget(self.js_toggle)
            self.toolbar.addWidget(self.adblock_toggle)
            self.toolbar.addWidget(self.https_toggle)
            self.toolbar.addWidget(create_separator())
            self.toolbar.addWidget(self.vpn_toggle)
            self.toolbar.addWidget(self.rotate_btn)
            self.toolbar.addWidget(self.vpn_status)
            
            self.main_layout.addWidget(self.toolbar_widget)

            self.progress_bar = QProgressBar()
            self.progress_bar.setMaximumHeight(2)
            self.progress_bar.setTextVisible(False)
            self.main_layout.addWidget(self.progress_bar)

            self.tabs = QTabWidget()
            self.tabs.setTabsClosable(True)
            self.tabs.tabCloseRequested.connect(self.close_tab)
            self.tabs.currentChanged.connect(self.on_tab_changed)
            self.main_layout.addWidget(self.tabs)

            self.back_btn.clicked.connect(self.go_back)
            self.forward_btn.clicked.connect(self.go_forward)
            self.reload_btn.clicked.connect(self.reload_tab)

            self.fetcher = ProxyFetcher()
            self.fetcher.proxy_ready.connect(self.apply_proxy)
            self.fetcher.error.connect(self.handle_proxy_error)

            self.add_new_tab(QUrl("https://duckduckgo.com"))

        def keyPressEvent(self, event):
            if event.key() == Qt.Key.Key_Escape:
                current_time = time.time()
                if (current_time - self.last_escape_time) < 0.5:
                    print("Panic Button Double Pressed. Wiping RAM and exiting...")
                    import gc
                    gc.collect()
                    QApplication.quit()
                else:
                    self.last_escape_time = current_time
                    super().keyPressEvent(event)
            elif event.key() == Qt.Key.Key_Q and (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                print("Panic Button Ctrl+Shift+Q Pressed. Wiping RAM and exiting...")
                import gc
                gc.collect()
                QApplication.quit()
            else:
                super().keyPressEvent(event)

        def current_browser(self):
            return self.tabs.currentWidget()

        def go_back(self):
            cb = self.current_browser()
            if cb:
                cb.back()

        def go_forward(self):
            cb = self.current_browser()
            if cb:
                cb.forward()

        def reload_tab(self):
            cb = self.current_browser()
            if cb:
                cb.reload()

        def add_new_tab(self, qurl=None, label="New Tab"):
            if qurl is None:
                qurl = QUrl("https://duckduckgo.com")

            browser = QWebEngineView()
            page = SecureWebPage(self.profile, browser)
            browser.setPage(page)

            browser.urlChanged.connect(lambda q, b=browser: self.on_url_changed(q, b))
            browser.titleChanged.connect(lambda t, b=browser: self.on_title_changed(t, b))
            browser.loadProgress.connect(lambda p, b=browser: self.on_load_progress(p, b))

            back_action = page.action(QWebEnginePage.WebAction.Back)
            forward_action = page.action(QWebEnginePage.WebAction.Forward)
            back_action.changed.connect(lambda b=browser: self.on_navigation_state_changed(b))
            forward_action.changed.connect(lambda b=browser: self.on_navigation_state_changed(b))

            index = self.tabs.addTab(browser, label)
            self.tabs.setCurrentIndex(index)
            browser.setUrl(qurl)
            self.update_navigation_buttons()
            return browser

        def close_tab(self, index):
            if self.tabs.count() > 1:
                widget = self.tabs.widget(index)
                self.tabs.removeTab(index)
                widget.deleteLater()

        def on_tab_changed(self, index):
            cb = self.tabs.widget(index)
            if cb:
                self.address_bar.setText(cb.url().toString())
                self.update_navigation_buttons()

        def on_navigation_state_changed(self, browser):
            if browser == self.current_browser():
                self.update_navigation_buttons()

        def update_navigation_buttons(self):
            cb = self.current_browser()
            if cb:
                back_action = cb.page().action(QWebEnginePage.WebAction.Back)
                forward_action = cb.page().action(QWebEnginePage.WebAction.Forward)
                self.back_btn.setEnabled(back_action.isEnabled())
                self.forward_btn.setEnabled(forward_action.isEnabled())
            else:
                self.back_btn.setEnabled(False)
                self.forward_btn.setEnabled(False)

        def on_url_changed(self, qurl, browser):
            if browser == self.current_browser():
                self.address_bar.setText(qurl.toString())

        def on_title_changed(self, title, browser):
            index = self.tabs.indexOf(browser)
            if index != -1:
                short_title = title if len(title) <= 15 else title[:12] + "..."
                self.tabs.setTabText(index, short_title)

        def on_load_progress(self, progress, browser):
            if browser == self.current_browser():
                self.progress_bar.setValue(progress)

        def toggle_js(self, state):
            self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, (state == 2))
            self.reload_tab()

        def toggle_https(self, state):
            self.interceptor.force_https = (state == 2)
            self.reload_tab()

        def toggle_adblock(self, state):
            self.interceptor.enabled = (state == 2)
            self.reload_tab()

        def toggle_vpn(self, state):
            if state == 2:
                self.vpn_status.setText("...")
                self.vpn_status.setStyleSheet("color: #dbab09;")
                self.fetcher.fetch()
                self.rotate_btn.setEnabled(True)
            else:
                self.local_proxy.set_mode("direct")
                self.vpn_status.setText("Off")
                self.vpn_status.setStyleSheet("color: #8b949e;")
                self.rotate_btn.setEnabled(False)
                self.reload_tab()

        def rotate_proxy(self):
            self.vpn_status.setText("...")
            self.vpn_status.setStyleSheet("color: #dbab09;")
            self.fetcher.fetch()

        def apply_proxy(self, host, port):
            self.local_proxy.set_mode("vpn", host, port)
            self.vpn_status.setText("ON")
            self.vpn_status.setStyleSheet("color: #2ea043;")
            self.reload_tab()

        def handle_proxy_error(self, err):
            self.vpn_status.setText("ERR")
            self.vpn_status.setStyleSheet("color: #f85149;")
            self.vpn_toggle.setChecked(False)
            QMessageBox.warning(self, "VPN Error", f"Failed to connect to a VPN proxy:\n{err}")

        def load_url(self):
            url = self.address_bar.text()
            if url:
                if not url.startswith("http") and not url.startswith("about:"):
                    url = "https://" + url
                cb = self.current_browser()
                if cb:
                    cb.setUrl(QUrl(url))

if __name__ == "__main__":
    if IS_ANDROID:
        SecureBrowserAndroid().run()
    else:
        app = QApplication(sys.argv)
        
        # Start local SOCKS5 proxy
        local_proxy = LocalSocks5Proxy()
        local_proxy.start()

        # Set system proxy for QtWebEngine
        proxy = QNetworkProxy()
        proxy.setType(QNetworkProxy.ProxyType.Socks5Proxy)
        proxy.setHostName("127.0.0.1")
        proxy.setPort(local_proxy.port)
        proxy.setCapabilities(QNetworkProxy.Capability.HostNameLookupCapability)
        QNetworkProxy.setApplicationProxy(proxy)

        window = SecureBrowser(local_proxy)
        window.show()
        sys.exit(app.exec())
