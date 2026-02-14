"""
应用入口 — FastAPI 应用 + 静态文件服务。
"""

import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api.routes import router


def _get_base_dir():
    """获取项目根目录，兼容开发模式和 PyInstaller 打包模式"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，数据文件在 sys._MEIPASS 或可执行文件同级
        # --add-data "frontend:frontend" 会放到 _MEIPASS/frontend
        return sys._MEIPASS
    else:
        # 开发模式：backend/main.py → backend → 项目根目录
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _get_base_dir()
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = FastAPI(
    title="PhotoDedup — 重复照片识别",
    description="智能识别相似照片，释放硬盘空间",
    version="1.0.0",
)

# 挂载 API 路由
app.include_router(router)

# 挂载前端静态文件（仅挂载存在的目录）
for subdir in ["css", "js", "assets"]:
    dirpath = os.path.join(FRONTEND_DIR, subdir)
    if os.path.isdir(dirpath):
        app.mount(f"/{subdir}", StaticFiles(directory=dirpath), name=subdir)


@app.get("/")
async def serve_index():
    """提供前端首页"""
    return FileResponse(
        os.path.join(FRONTEND_DIR, "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


def start_server(host: str = "127.0.0.1", port: int = 8686):
    """启动服务器"""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
