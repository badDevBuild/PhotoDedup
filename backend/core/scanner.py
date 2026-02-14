"""
目录扫描器 — 递归扫描指定目录，收集所有 RAW 图像文件及其元数据。
"""

import os
from pathlib import Path
from typing import Callable

import exifread

from backend.config import RAW_EXTENSIONS, IMAGE_EXTENSIONS


class PhotoInfo:
    """单张照片的信息"""

    __slots__ = ['path', 'filename', 'size', 'date_taken', 'camera_model']

    def __init__(self, path: str):
        self.path = path
        self.filename = os.path.basename(path)
        self.size = os.path.getsize(path)
        self.date_taken: str | None = None
        self.camera_model: str | None = None

    def to_dict(self) -> dict:
        return {
            'path': self.path,
            'filename': self.filename,
            'size': self.size,
            'date_taken': self.date_taken,
            'camera_model': self.camera_model,
        }


def read_exif_quick(filepath: str) -> dict:
    """快速读取关键 EXIF 信息（只读前 64KB 获取基本信息）"""
    try:
        with open(filepath, 'rb') as f:
            tags = exifread.process_file(f, stop_tag='DateTimeOriginal', details=False)
        return {
            'date_taken': str(tags.get('EXIF DateTimeOriginal', '')),
            'camera_model': str(tags.get('Image Model', '')),
        }
    except Exception:
        return {}


def scan_directory(
    directory: str,
    include_raw: bool = True,
    include_images: bool = False,
    read_exif: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[PhotoInfo]:
    """
    递归扫描目录，收集所有照片文件。

    Args:
        directory: 要扫描的目录路径
        include_raw: 是否包含 RAW 文件
        include_images: 是否包含普通图片（JPG 等）
        read_exif: 是否读取 EXIF 信息
        progress_callback: 进度回调 (当前数量, 总数量, 当前文件名)

    Returns:
        PhotoInfo 列表
    """
    # 先收集所有符合条件的文件路径
    extensions = set()
    if include_raw:
        extensions |= RAW_EXTENSIONS
    if include_images:
        extensions |= IMAGE_EXTENSIONS

    all_files = []
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if fname.startswith('.'):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                all_files.append(os.path.join(root, fname))

    total = len(all_files)
    photos = []

    for i, filepath in enumerate(all_files):
        info = PhotoInfo(filepath)

        if read_exif:
            exif = read_exif_quick(filepath)
            info.date_taken = exif.get('date_taken') or None
            info.camera_model = exif.get('camera_model') or None

        photos.append(info)

        if progress_callback and (i % 50 == 0 or i == total - 1):
            progress_callback(i + 1, total, info.filename)

    return photos
