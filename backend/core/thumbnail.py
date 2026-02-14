"""
缩略图提取器 — 从 RAW 文件中提取嵌入式 JPEG 预览图。
NEF 文件内嵌有 JPEG 预览，直接提取比完整解码 RAW 快 100 倍以上。
"""

import hashlib
import os
from pathlib import Path
from typing import Callable

import rawpy
from PIL import Image
from io import BytesIO

from backend.config import THUMBNAIL_SIZE, CACHE_DIR


def _cache_key(filepath: str) -> str:
    """基于文件路径和修改时间生成缓存键"""
    mtime = os.path.getmtime(filepath)
    key_str = f"{filepath}:{mtime}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _cache_path(filepath: str) -> Path:
    """获取缓存文件路径"""
    return CACHE_DIR / f"{_cache_key(filepath)}.jpg"


def extract_thumbnail(
    filepath: str,
    size: tuple[int, int] = THUMBNAIL_SIZE,
    use_cache: bool = True,
) -> Path | None:
    """
    从 RAW 文件提取缩略图。

    优先提取嵌入式 JPEG 预览（极快），失败则回退到完整解码（慢）。
    结果缓存到磁盘，重复调用不会重复提取。

    Args:
        filepath: RAW 文件路径
        size: 缩略图尺寸
        use_cache: 是否使用缓存

    Returns:
        缩略图文件路径，失败返回 None
    """
    cached = _cache_path(filepath)

    if use_cache and cached.exists():
        return cached

    try:
        # 方法 1: 提取嵌入式 JPEG 预览（极快）
        with rawpy.imread(filepath) as raw:
            thumb = raw.extract_thumb()

        if thumb.format == rawpy.ThumbFormat.JPEG:
            img = Image.open(BytesIO(thumb.data))
        elif thumb.format == rawpy.ThumbFormat.BITMAP:
            img = Image.fromarray(thumb.data)
        else:
            raise ValueError(f"Unknown thumb format: {thumb.format}")

    except Exception:
        try:
            # 方法 2: 完整解码 RAW（较慢，作为兜底）
            with rawpy.imread(filepath) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    half_size=True,  # 半尺寸加速
                    no_auto_bright=True,
                )
            img = Image.fromarray(rgb)
        except Exception:
            return None

    # 缩放并保存
    img.thumbnail(size, Image.LANCZOS)

    if img.mode != 'RGB':
        img = img.convert('RGB')

    img.save(str(cached), 'JPEG', quality=85)
    return cached


def extract_thumbnails_batch(
    filepaths: list[str],
    size: tuple[int, int] = THUMBNAIL_SIZE,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, Path | None]:
    """
    批量提取缩略图。

    Args:
        filepaths: 文件路径列表
        size: 缩略图尺寸
        progress_callback: 进度回调

    Returns:
        {文件路径: 缩略图路径} 字典
    """
    total = len(filepaths)
    results = {}

    for i, fp in enumerate(filepaths):
        results[fp] = extract_thumbnail(fp, size)
        if progress_callback and (i % 20 == 0 or i == total - 1):
            progress_callback(i + 1, total, os.path.basename(fp))

    return results
