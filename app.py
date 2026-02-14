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


def run_desktop_mode():
    """桌面窗口模式：使用 pywebview 创建原生窗口"""
    try:
        import webview
    except ImportError:
        print("⚠️  pywebview 未安装，自动切换到浏览器模式")
        print("   安装: pip install pywebview")
        run_dev_mode()
        return

    # 启动后端
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()

    # 等待服务器就绪
    time.sleep(1.5)

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

    print(f"\n🔍 PhotoDedup — 重复照片识别")
    print(f"   正在启动服务器...")
    print(f"   访问地址: http://127.0.0.1:{PORT}\n")

    threading.Thread(
        target=lambda: (time.sleep(1.5), webbrowser.open(f"http://127.0.0.1:{PORT}")),
        daemon=True,
    ).start()

    start_backend()


if __name__ == "__main__":
    if "--dev" in sys.argv:
        run_dev_mode()
    else:
        run_desktop_mode()
