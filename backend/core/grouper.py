"""
相似照片聚类器 — 使用 Union-Find 将相似照片归入同一组。
"""

from backend.config import DEFAULT_SIMILARITY_THRESHOLD
from backend.core.hasher import hamming_distance


class UnionFind:
    """Union-Find 数据结构（带路径压缩和按秩合并）"""

    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # 路径压缩
        return self.parent[x]

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        # 按秩合并
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1

    def connected(self, x, y) -> bool:
        return self.find(x) == self.find(y)


class PhotoGroup:
    """一组相似照片"""

    def __init__(self, group_id: int, photos: list[dict]):
        self.group_id = group_id
        self.photos = photos  # [{'path': ..., 'hash': ..., 'size': ...}, ...]

    @property
    def count(self) -> int:
        return len(self.photos)

    @property
    def total_size(self) -> int:
        return sum(p.get('size', 0) for p in self.photos)

    def to_dict(self) -> dict:
        return {
            'group_id': self.group_id,
            'count': self.count,
            'total_size': self.total_size,
            'photos': self.photos,
        }


def group_similar_photos(
    photo_hashes: dict[str, str | None],
    photo_sizes: dict[str, int] | None = None,
    threshold: int = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[PhotoGroup]:
    """
    将相似照片聚类为群组。

    算法：
    1. 对所有照片对计算汉明距离
    2. 距离 < 阈值 → Union-Find 合并
    3. 提取连通分量作为群组
    4. 只返回包含 2 张及以上照片的群组

    Args:
        photo_hashes: {文件路径: pHash} 字典
        photo_sizes: {文件路径: 文件大小} 字典（可选）
        threshold: 相似度阈值（汉明距离）

    Returns:
        PhotoGroup 列表，按照片数量从大到小排序
    """
    # 过滤掉没有哈希值的照片
    valid = {p: h for p, h in photo_hashes.items() if h is not None}
    paths = list(valid.keys())
    n = len(paths)

    if n == 0:
        return []

    uf = UnionFind()

    # O(N²) 两两比较 — 对于几千张照片是可接受的
    # 优化思路：如果 N > 10000，可用 VP-Tree 或 LSH 加速
    for i in range(n):
        for j in range(i + 1, n):
            dist = hamming_distance(valid[paths[i]], valid[paths[j]])
            if dist <= threshold:
                uf.union(paths[i], paths[j])

    # 提取群组
    groups_dict: dict[str, list[str]] = {}
    for path in paths:
        root = uf.find(path)
        groups_dict.setdefault(root, []).append(path)

    # 构建 PhotoGroup，过滤独立照片
    photo_sizes = photo_sizes or {}
    groups = []
    for gid, (_, members) in enumerate(
        sorted(groups_dict.items(), key=lambda x: -len(x[1]))
    ):
        if len(members) < 2:
            continue
        photos = [
            {
                'path': p,
                'hash': valid[p],
                'size': photo_sizes.get(p, 0),
            }
            for p in sorted(members)  # 按路径排序，通常也是时间顺序
        ]
        groups.append(PhotoGroup(group_id=gid, photos=photos))

    return groups
