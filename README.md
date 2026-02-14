# 📸 PhotoDedup — 智能重复照片识别与清理

自动识别连拍/相似照片，结合 Lightroom 编辑记录（XMP），智能推荐清理方案。

支持 NEF、CR2、ARW 等 RAW 格式及 JPG/PNG 常见图片格式。

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20|%20Windows%20|%20Linux-lightgrey)

## ✨ 功能特性

- 🔍 **感知哈希** — 基于 pHash 算法识别视觉相似照片，而非简单文件比较
- 📁 **批量扫描** — 递归扫描文件夹，支持数千张照片
- 🎨 **Lightroom 编辑检测** — 自动通过 XMP sidecar 文件识别已编辑/已评分的照片
- 🤖 **智能推荐** — 优先保留已编辑、高评分的照片，推荐删除冗余副本
- 👁️ **逐组审核** — 可视化对比每一组相似照片，手动决定保留/删除
- ⚡ **一键清理** — 接受智能推荐，批量清理
- 🗑️ **安全删除** — 所有删除操作移入回收站，不会永久删除
- 🖥️ **桌面应用** — 支持 pywebview 原生窗口，也可在浏览器中使用

## 🚀 快速开始

### 环境要求

- Python 3.11+
- macOS / Windows / Linux

### 安装

```bash
git clone https://github.com/yourname/PhotoDedup.git
cd PhotoDedup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 运行

```bash
# 浏览器模式（推荐）
python run.py

# 桌面窗口模式（需要 pywebview）
python app.py
```

启动后浏览器会自动打开 `http://127.0.0.1:8686`。

## 📖 使用方法

1. **输入路径** — 在输入框中填入照片文件夹的完整路径（或点击「浏览」按钮选择）
2. **调整阈值** — 相似度阈值越小越严格，默认值 10 适合大多数场景
3. **开始扫描** — 点击「开始扫描」，等待扫描完成
4. **审核结果** — 扫描完成后自动进入逐组审核模式：
   - 绿色边框 = 推荐保留
   - 红色边框 = 推荐删除
   - 点击照片切换保留/删除状态
   - 使用「仅保留LR已编辑」快速筛选
5. **执行删除** — 确认后文件将移入回收站

## 🏗️ 项目结构

```
PhotoDedup/
├── app.py              # 桌面应用入口
├── run.py              # 开发模式入口（浏览器）
├── build.sh            # 打包脚本（PyInstaller）
├── requirements.txt    # Python 依赖
├── backend/
│   ├── main.py         # FastAPI 应用
│   ├── config.py       # 配置
│   ├── api/
│   │   └── routes.py   # API 路由
│   └── core/
│       ├── scanner.py      # 文件扫描
│       ├── thumbnail.py    # 缩略图提取
│       ├── hasher.py       # 感知哈希计算
│       ├── grouper.py      # 相似照片聚类
│       ├── lightroom.py    # LR 编辑检测（XMP）
│       └── recommender.py  # 智能推荐引擎
└── frontend/
    ├── index.html      # 主页
    ├── css/            # 样式
    └── js/app.js       # 前端逻辑
```

## 📦 打包为桌面应用

```bash
# macOS / Linux
./build.sh

# 打包结果
dist/PhotoDedup.app    # macOS
dist/PhotoDedup/       # Linux
```

打包后的应用不需要安装 Python，双击即可运行。

## 🔧 技术栈

| 组件     | 技术                     |
| -------- | ------------------------ |
| 后端     | Python, FastAPI, uvicorn |
| 前端     | Vanilla HTML/CSS/JS      |
| 图像哈希 | imagehash (pHash)        |
| RAW 解析 | rawpy (libraw)           |
| LR 检测  | XMP sidecar 解析         |
| 桌面窗口 | pywebview                |
| 打包     | PyInstaller              |
| 安全删除 | send2trash               |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[MIT License](LICENSE)
