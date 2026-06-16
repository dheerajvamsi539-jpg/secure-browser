import os
import sys
import threading
import requests
import random
import socket
import subprocess
from time import sleep

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
from kivy.utils import platform

# Conditional imports for Android
if platform == 'android':
    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread
    
    # Android Classes
    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
    LinearLayout = autoclass('android.widget.LinearLayout')
    Activity = autoclass('org.kivy.android.PythonActivity').mActivity
    Context = autoclass('android.content.Context')
    ProxyController = autoclass('androidx.webkit.ProxyController')
    ProxyConfig = autoclass('androidx.webkit.ProxyConfig')
    Executor = autoclass('java.util.concurrent.Executor')
else:
    # Placeholders for non-android platforms (for testing UI layout)
    def run_on_ui_thread(f):
        return f

# --- Proxy / VPN Logic ---
class ProxyFetcher:
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



# --- Main App ---
class SecureBrowserAndroid(App):
    def build(self):
        self.title = "Secure Browser Ultimate"
        self.root = BoxLayout(orientation='vertical')
        
        # Toolbar
        self.toolbar = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp', padding='5dp')
        
        self.back_btn = Button(text='<', size_hint_x=None, width='40dp')
        self.back_btn.bind(on_release=self.go_back)
        
        self.url_input = TextInput(text='https://duckduckgo.com', multiline=False, font_size='14sp')
        self.url_input.bind(on_text_validate=self.load_url)
        
        self.js_toggle = CheckBox(size_hint_x=None, width='30dp', active=True)
        self.js_toggle.bind(active=self.toggle_js)
        self.js_label = Label(text='JS', size_hint_x=None, width='30dp', font_size='12sp')
        
        self.vpn_toggle = CheckBox(size_hint_x=None, width='30dp')
        self.vpn_toggle.bind(active=self.toggle_vpn)
        self.vpn_label = Label(text='VPN', size_hint_x=None, width='40dp', font_size='12sp')
        
        self.toolbar.add_widget(self.back_btn)
        self.toolbar.add_widget(self.url_input)
        self.toolbar.add_widget(self.js_label)
        self.toolbar.add_widget(self.js_toggle)
        self.toolbar.add_widget(self.vpn_label)
        self.toolbar.add_widget(self.vpn_toggle)
        
        self.root.add_widget(self.toolbar)
        
        # WebView Container
        self.webview_container = BoxLayout()
        self.root.add_widget(self.webview_container)
        
        # Initialize Android WebView
        if platform == 'android':
            self.init_webview()
            
        self.fetcher = ProxyFetcher(self.apply_proxy, self.handle_error)
        
        return self.root

    @run_on_ui_thread
    def init_webview(self):
        self.webview = WebView(Activity)
        self.webview.getSettings().setJavaScriptEnabled(True)
        self.webview.getSettings().setDomStorageEnabled(True)
        self.webview.setWebViewClient(WebViewClient())
        
        # Overlay the webview on the decor view, leaving space for the Kivy toolbar (50dp)
        decor_view = Activity.getWindow().getDecorView()
        FrameLayout = autoclass('android.widget.FrameLayout')
        FrameLayout_LayoutParams = autoclass('android.widget.FrameLayout$LayoutParams')
        decor_layout = cast(FrameLayout, decor_view)
        
        metrics = Activity.getResources().getDisplayMetrics()
        density = metrics.density
        toolbar_height_px = int(50 * density)
        
        params = FrameLayout_LayoutParams(
            FrameLayout_LayoutParams.MATCH_PARENT,
            FrameLayout_LayoutParams.MATCH_PARENT
        )
        params.topMargin = toolbar_height_px
        
        decor_layout.addView(self.webview, params)
        self.webview.loadUrl("https://duckduckgo.com")

    def load_url(self, instance):
        url = self.url_input.text
        if not url.startswith('http'):
            url = 'https://' + url
        
        if platform == 'android':
            self.run_load_url(url)
        else:
            print(f"Loading URL: {url}")

    @run_on_ui_thread
    def run_load_url(self, url):
        self.webview.loadUrl(url)

    def go_back(self, instance):
        if platform == 'android':
            self.run_go_back()

    @run_on_ui_thread
    def run_go_back(self):
        if self.webview.canGoBack():
            self.webview.goBack()

    def toggle_js(self, checkbox, value):
        if platform == 'android':
            self.run_toggle_js(value)
        else:
            print(f"JS Toggled: {value}")

    @run_on_ui_thread
    def run_toggle_js(self, value):
        self.webview.getSettings().setJavaScriptEnabled(value)
        self.webview.reload()

    def toggle_vpn(self, checkbox, value):
        if value:
            self.fetcher.fetch()
        else:
            self.clear_proxy()

    def apply_proxy(self, host, port):
        if platform == 'android':
            self.set_android_proxy(host, port)
        print(f"Proxy Applied: {host}:{port}")

    @run_on_ui_thread
    def set_android_proxy(self, host, port):
        # Using AndroidX ProxyController (API 29+)
        proxy_config = ProxyConfig.Builder() \
            .addProxyRule(f"{host}:{port}") \
            .addDirect().build()
        
        executor = Activity.getMainExecutor()
        if not hasattr(self, '_proxy_listener') or self._proxy_listener is None:
            self._proxy_listener = PyRunnable(lambda: print("Proxy override applied"))
        ProxyController.getInstance().setProxyOverride(proxy_config, executor, self._proxy_listener)

    @run_on_ui_thread
    def clear_proxy(self):
        if platform == 'android':
            executor = Activity.getMainExecutor()
            if not hasattr(self, '_proxy_listener') or self._proxy_listener is None:
                self._proxy_listener = PyRunnable(lambda: print("Proxy override cleared"))
            ProxyController.getInstance().clearProxyOverride(executor, self._proxy_listener)

    def handle_error(self, error):
        print(f"Error: {error}")
        # In a real app, show a Kivy Popup here
        self.vpn_toggle.active = False

# Runnable implementation for JNI/Android
if platform == 'android':
    from jnius import PythonJavaClass, java_method

    class PyRunnable(PythonJavaClass):
        __javainterfaces__ = ['java/lang/Runnable']

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method('()V')
        def run(self):
            if self.callback:
                self.callback()

if __name__ == '__main__':
    SecureBrowserAndroid().run()
