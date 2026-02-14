#!/bin/bash
# PhotoDedup 打包脚本
# 使用 PyInstaller 将应用打包为独立的桌面程序

set -e

echo "🔨 PhotoDedup 打包工具"
echo "========================"

# 检查 PyInstaller
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "安装 PyInstaller..."
    pip install pyinstaller
fi

# 检查 pywebview
if ! python -c "import webview" 2>/dev/null; then
    echo "安装 pywebview..."
    pip install pywebview
fi

# 清理旧的构建文件
rm -rf build dist

# 获取操作系统类型
OS=$(uname -s)
echo "操作系统: $OS"

if [ "$OS" = "Darwin" ]; then
    # macOS: 打包为 .app
    echo "打包为 macOS .app..."
    pyinstaller \
        --name "PhotoDedup" \
        --windowed \
        --onedir \
        --add-data "frontend:frontend" \
        --hidden-import "rawpy" \
        --hidden-import "imagehash" \
        --hidden-import "PIL" \
        --hidden-import "uvicorn" \
        --hidden-import "fastapi" \
        --hidden-import "webview" \
        --hidden-import "send2trash" \
        --hidden-import "uvicorn.logging" \
        --hidden-import "uvicorn.loops" \
        --hidden-import "uvicorn.loops.auto" \
        --hidden-import "uvicorn.protocols" \
        --hidden-import "uvicorn.protocols.http" \
        --hidden-import "uvicorn.protocols.http.auto" \
        --hidden-import "uvicorn.protocols.websockets" \
        --hidden-import "uvicorn.protocols.websockets.auto" \
        --hidden-import "uvicorn.lifespan" \
        --hidden-import "uvicorn.lifespan.on" \
        --noconfirm \
        app.py

    echo ""
    echo "✅ 打包完成！"
    echo "   应用位置: dist/PhotoDedup.app"
    echo "   双击即可运行"

elif [ "$OS" = "Linux" ]; then
    echo "打包为 Linux 可执行文件..."
    pyinstaller \
        --name "PhotoDedup" \
        --onedir \
        --add-data "frontend:frontend" \
        --hidden-import "rawpy" \
        --hidden-import "imagehash" \
        --hidden-import "PIL" \
        --hidden-import "uvicorn" \
        --hidden-import "fastapi" \
        --hidden-import "webview" \
        --hidden-import "send2trash" \
        --noconfirm \
        app.py

    echo ""
    echo "✅ 打包完成！"
    echo "   可执行文件: dist/PhotoDedup/PhotoDedup"
else
    echo "⚠️  Windows 请使用 build.bat 或直接运行:"
    echo "   pyinstaller --name PhotoDedup --windowed --onedir --add-data \"frontend;frontend\" app.py"
fi
