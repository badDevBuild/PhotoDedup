#!/usr/bin/env python3
"""
PhotoDedup 桌面应用入口

两种运行模式：
  python app.py          → 桌面窗口模式（pywebview）
  python app.py --dev    → 开发模式（浏览器）
  python run.py          → 等同于 --dev 模式
"""

import sys
import threading
import time

PORT = 8686


def start_backend():
    """在后台线程启动 FastAPI 服务器"""
    from backend.main import start_server
    start_server(port=PORT, host="127.0.0.1")


def wait_for_server(timeout=30):
    """轮询等待服务器就绪，最多等 timeout 秒"""
    import urllib.request
    import urllib.error

    url = f"http://127.0.0.1:{PORT}/"
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(0.3)
    return False


def run_desktop_mode():
    """桌面窗口模式：使用 pywebview 创建原生窗口"""
    try:
        import webview
    except ImportError:
        print("[WARN] pywebview 未安装，自动切换到浏览器模式")
        print("   安装: pip install pywebview")
        run_dev_mode()
        return

    # 启动后端
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()

    # 等待服务器真正就绪（而不是固定 sleep）
    print("[INFO] 正在启动服务器...")
    if not wait_for_server():
        print("[ERROR] 服务器启动超时，请检查日志")
        return

    print("[OK] 服务器就绪，打开窗口")

    # 创建原生窗口
    window = webview.create_window(
        "PhotoDedup — 重复照片识别",
        f"http://127.0.0.1:{PORT}",
        width=1200,
        height=800,
        min_size=(900, 600),
    )
    webview.start()


def run_dev_mode():
    """开发模式：在浏览器中打开"""
    import webbrowser

    print(f"\nPhotoDedup — 重复照片识别")
    print(f"   正在启动服务器...")
    print(f"   访问地址: http://127.0.0.1:{PORT}\n")

    def open_browser():
        if wait_for_server():
            webbrowser.open(f"http://127.0.0.1:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()
    start_backend()


if __name__ == "__main__":
    if "--dev" in sys.argv:
        run_dev_mode()
    else:
        run_desktop_mode()
