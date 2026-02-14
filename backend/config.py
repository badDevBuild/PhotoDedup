"""配置管理"""

import os
from pathlib import Path

# 支持的 RAW 文件扩展名
RAW_EXTENSIONS = {
    '.nef',   # Nikon
    '.cr2',   # Canon (old)
    '.cr3',   # Canon (new)
    '.arw',   # Sony
    '.orf',   # Olympus
    '.rw2',   # Panasonic
    '.raf',   # Fujifilm
    '.dng',   # Adobe DNG
    '.pef',   # Pentax
}

# 支持的普通图片扩展名（可选扫描）
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.heic'}

# 相似度阈值（pHash 汉明距离，越小越严格）
DEFAULT_SIMILARITY_THRESHOLD = 10

# 缩略图尺寸
THUMBNAIL_SIZE = (320, 320)

# 缩略图缓存目录
CACHE_DIR = Path(os.path.expanduser("~/.photodedup/cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 数据库缓存路径
DB_PATH = Path(os.path.expanduser("~/.photodedup/scan_cache.db"))

# 并行线程数
MAX_WORKERS = os.cpu_count() or 4
