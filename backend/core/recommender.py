"""
智能推荐器 — 结合 Lightroom 编辑状态和相似度分析，推荐保留和删除项。
"""

import os
from backend.core.grouper import PhotoGroup


class Recommendation:
    """单组照片的推荐结果"""

    def __init__(self, group: PhotoGroup, keep: list[str], delete: list[str]):
        self.group = group
        self.keep = keep      # 建议保留的文件路径
        self.delete = delete  # 建议删除的文件路径

    @property
    def save_bytes(self) -> int:
        """可释放的空间（字节）"""
        return sum(
            p['size'] for p in self.group.photos if p['path'] in self.delete
        )

    def to_dict(self) -> dict:
        return {
            'group_id': self.group.group_id,
            'total_in_group': self.group.count,
            'keep': self.keep,
            'delete': self.delete,
            'keep_count': len(self.keep),
            'delete_count': len(self.delete),
            'save_bytes': self.save_bytes,
        }


def recommend_for_group(
    group: PhotoGroup,
    edited_photos: set[str] | None = None,
    flagged_photos: dict[str, dict] | None = None,
) -> Recommendation:
    """
    为一组相似照片生成保留/删除推荐。

    策略：
    1. LR 中已编辑的 → 保留
    2. LR 中有星标/旗帜的 → 保留
    3. 若组内没有任何 LR 标记的照片 → 保留第一张（通常是时间最早的）
    4. 其余 → 建议删除

    Args:
        group: 相似照片群组
        edited_photos: LR 已编辑照片路径集合
        flagged_photos: LR 已标记照片 {path: {rating, pick, label}}

    Returns:
        Recommendation 对象
    """
    edited_photos = edited_photos or set()
    flagged_photos = flagged_photos or {}

    keep = []
    delete = []

    for photo in group.photos:
        path = photo['path']
        is_edited = path in edited_photos
        is_flagged = path in flagged_photos
        is_rejected = flagged_photos.get(path, {}).get('pick', 0) == -1

        if is_rejected:
            delete.append(path)
        elif is_edited or is_flagged:
            keep.append(path)
        else:
            delete.append(path)

    # 安全检查：如果整组都被标记为删除，保留第一张
    if not keep and delete:
        keep.append(delete.pop(0))

    return Recommendation(group=group, keep=keep, delete=delete)


def recommend_all(
    groups: list[PhotoGroup],
    edited_photos: set[str] | None = None,
    flagged_photos: dict[str, dict] | None = None,
) -> dict:
    """
    为所有群组生成推荐，并汇总统计。

    Returns:
        {
            'recommendations': [Recommendation.to_dict(), ...],
            'summary': {
                'total_groups': int,
                'total_photos': int,
                'keep_count': int,
                'delete_count': int,
                'save_bytes': int,
                'save_gb': float,
            }
        }
    """
    recommendations = []
    total_keep = 0
    total_delete = 0
    total_save = 0

    for group in groups:
        rec = recommend_for_group(group, edited_photos, flagged_photos)
        recommendations.append(rec)
        total_keep += len(rec.keep)
        total_delete += len(rec.delete)
        total_save += rec.save_bytes

    return {
        'recommendations': [r.to_dict() for r in recommendations],
        'summary': {
            'total_groups': len(groups),
            'total_photos': total_keep + total_delete,
            'keep_count': total_keep,
            'delete_count': total_delete,
            'save_bytes': total_save,
            'save_gb': round(total_save / (1024 ** 3), 2),
        },
    }
