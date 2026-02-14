#!/usr/bin/env python3
"""
开发模式启动脚本 — 在浏览器中打开应用
"""

import webbrowser
import threading
import time
from backend.main import start_server

PORT = 8686

def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{PORT}")

if __name__ == "__main__":
    print(f"\n🔍 PhotoDedup — 重复照片识别")
    print(f"   正在启动服务器...")
    print(f"   访问地址: http://127.0.0.1:{PORT}\n")

    threading.Thread(target=open_browser, daemon=True).start()
    start_server(port=PORT)
