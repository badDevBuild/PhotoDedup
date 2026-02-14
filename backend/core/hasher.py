"""
感知哈希计算器 — 使用 pHash 为每张照片生成 64-bit 指纹。
支持多线程并行计算。
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import imagehash
from PIL import Image

from backend.config import MAX_WORKERS


def compute_phash(image_path: str, hash_size: int = 8) -> str | None:
    """
    计算单张图片的 pHash。

    Args:
        image_path: 图片路径（缩略图 JPEG）
        hash_size: 哈希矩阵尺寸，默认 8 → 64-bit 哈希

    Returns:
        十六进制哈希字符串，失败返回 None
    """
    try:
        img = Image.open(image_path)
        h = imagehash.phash(img, hash_size=hash_size)
        return str(h)
    except Exception:
        return None


def compute_phash_batch(
    image_paths: dict[str, str],
    hash_size: int = 8,
    max_workers: int = MAX_WORKERS,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, str | None]:
    """
    多线程批量计算 pHash。

    Args:
        image_paths: {原始文件路径: 缩略图路径} 字典
        hash_size: 哈希矩阵尺寸
        max_workers: 最大线程数
        progress_callback: 进度回调 (已完成数, 总数)

    Returns:
        {原始文件路径: 哈希值} 字典
    """
    total = len(image_paths)
    results = {}
    completed = 0

    def _compute(original_path: str, thumb_path: str):
        return original_path, compute_phash(thumb_path, hash_size)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_compute, orig, thumb): orig
            for orig, thumb in image_paths.items()
            if thumb is not None
        }

        for future in as_completed(futures):
            orig_path, hash_val = future.result()
            results[orig_path] = hash_val
            completed += 1
            if progress_callback and (completed % 50 == 0 or completed == total):
                progress_callback(completed, total)

    # 标记没有缩略图的文件
    for orig, thumb in image_paths.items():
        if thumb is None:
            results[orig] = None

    return results


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    计算两个 pHash 之间的汉明距离。

    Args:
        hash1: 十六进制哈希字符串
        hash2: 十六进制哈希字符串

    Returns:
        汉明距离（0 = 完全相同，64 = 完全不同）
    """
    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    return h1 - h2
