"""
Lightroom 编辑检测器 — 通过 XMP sidecar 文件检测照片编辑状态。

Lightroom (CC 和 Classic) 在编辑 RAW 文件时，会生成同名的 .xmp sidecar 文件，
其中包含编辑参数、星标评分等信息。本模块通过检测 .xmp 文件来判断照片的编辑状态。
"""

import os
import re
from pathlib import Path


def find_lrcat_files(search_dirs: list[str] | None = None) -> list[str]:
    """
    在系统中搜索 Lightroom 目录文件（.lrcat 和 .lrlibrary）。
    macOS 上使用 Spotlight (mdfind) 搜索。

    Returns:
        找到的 Lightroom 目录文件路径列表
    """
    candidates = set()

    # macOS Spotlight 搜索
    try:
        import subprocess

        # 搜索 .lrcat (Classic)
        r1 = subprocess.run(
            ['mdfind', '-name', '.lrcat'],
            capture_output=True, text=True, timeout=10,
        )
        if r1.returncode == 0:
            for line in r1.stdout.strip().split('\n'):
                line = line.strip()
                if line.endswith('.lrcat') and not line.endswith(('-wal', '-shm')):
                    if os.path.exists(line):
                        candidates.add(line)

        # 搜索 .lrlibrary (CC)
        r2 = subprocess.run(
            ['mdfind', '-name', '.lrlibrary'],
            capture_output=True, text=True, timeout=10,
        )
        if r2.returncode == 0:
            for line in r2.stdout.strip().split('\n'):
                line = line.strip()
                if line.endswith('.lrlibrary'):
                    if os.path.exists(line):
                        candidates.add(line)
    except Exception:
        pass

    # 手动搜索常见目录（兜底）
    home = os.path.expanduser("~")
    default_dirs = [
        os.path.join(home, "Pictures"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Library", "CloudStorage"),
    ]

    if search_dirs:
        default_dirs.extend(search_dirs)

    for d in default_dirs:
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                if f.endswith('.lrcat') and not f.endswith(('-wal', '-shm')):
                    candidates.add(os.path.join(root, f))
                elif f.endswith('.lrlibrary'):
                    candidates.add(os.path.join(root, f))
            depth = root.replace(d, '').count(os.sep)
            if depth >= 3:
                _dirs.clear()

    return sorted(candidates)


def detect_edited_photos(photo_paths: list[str]) -> tuple[set[str], dict[str, dict]]:
    """
    通过 XMP sidecar 文件检测照片的编辑和标记状态。

    对于每张照片（如 DSC_1234.NEF），检查同目录下是否存在
    同名 .xmp 文件（如 DSC_1234.xmp）。如果存在，则认为该照片
    已被 Lightroom 编辑过。同时解析 XMP 文件中的评分和标记信息。

    Args:
        photo_paths: 照片文件路径列表

    Returns:
        (edited_set, flagged_dict)
        - edited_set: 被编辑过的照片路径集合
        - flagged_dict: {path: {'rating': int, 'pick': int, 'label': str}}
    """
    edited = set()
    flagged = {}

    for photo_path in photo_paths:
        base, _ = os.path.splitext(photo_path)

        # 检查 .xmp sidecar（大小写都试）
        xmp_path = None
        for ext in ('.xmp', '.XMP'):
            candidate = base + ext
            if os.path.exists(candidate):
                xmp_path = candidate
                break

        if xmp_path is None:
            continue

        # 有 XMP = 被编辑过
        edited.add(photo_path)

        # 解析 XMP 中的评分和标记信息
        try:
            info = _parse_xmp_metadata(xmp_path)
            if info.get('rating', 0) > 0 or info.get('pick', 0) != 0 or info.get('label', ''):
                flagged[photo_path] = info
        except Exception:
            pass  # XMP 解析失败，至少编辑状态已标记

    return edited, flagged


def _parse_xmp_metadata(xmp_path: str) -> dict:
    """
    解析 XMP sidecar 文件中的关键元数据。

    Returns:
        {'rating': int, 'pick': int, 'label': str}
    """
    try:
        with open(xmp_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return {'rating': 0, 'pick': 0, 'label': ''}

    # 解析 Rating (xmp:Rating="5")
    rating = 0
    m = re.search(r'xmp:Rating="(-?\d+)"', content)
    if m:
        rating = int(m.group(1))

    # 解析 Pick/Flag (xmp:Label / crs:RawFileName - LR 没有标准 pick 字段)
    # Lightroom 的 pick 标记通常只在 .lrcat 中，XMP 中没有
    # 但 Rating = -1 通常表示 reject
    pick = 0
    if rating == -1:
        pick = -1
        rating = 0

    # 解析 Label (颜色标签 xmp:Label="Red")
    label = ''
    m = re.search(r'xmp:Label="([^"]*)"', content)
    if m:
        label = m.group(1)

    return {
        'rating': rating,
        'pick': pick,
        'label': label,
    }


class LightroomCatalog:
    """
    Lightroom 编辑检测器（基于 XMP sidecar 文件）。

    保留类接口以兼容现有代码，但内部实现改为 XMP 检测。
    """

    def __init__(self, lrcat_path: str | None = None):
        """
        Args:
            lrcat_path: 可选的 LR 目录路径（仅用于显示信息）
        """
        self.lrcat_path = lrcat_path
        self._photo_paths: list[str] = []

    def set_photo_paths(self, paths: list[str]):
        """设置要检测的照片路径列表"""
        self._photo_paths = paths

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def get_edited_photos(self) -> set[str]:
        """获取所有被编辑过的照片路径（基于 XMP sidecar 检测）"""
        edited, _ = detect_edited_photos(self._photo_paths)
        return edited

    def get_flagged_photos(self) -> dict[str, dict]:
        """获取有评分或标签的照片"""
        _, flagged = detect_edited_photos(self._photo_paths)
        return flagged

    def get_catalog_info(self) -> dict:
        """获取编辑检测信息"""
        edited, flagged = detect_edited_photos(self._photo_paths)
        return {
            'path': self.lrcat_path or 'XMP Sidecar 检测',
            'total_photos': len(self._photo_paths),
            'edited_count': len(edited),
            'flagged_count': len(flagged),
            'method': 'xmp_sidecar',
        }
