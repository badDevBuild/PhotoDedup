"""
FastAPI 路由 — 提供扫描、分组、推荐、删除等 API 端点。
"""

import asyncio
import os
import json
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from send2trash import send2trash

from backend.core.scanner import scan_directory, PhotoInfo
from backend.core.thumbnail import extract_thumbnail, extract_thumbnails_batch
from backend.core.hasher import compute_phash_batch
from backend.core.grouper import group_similar_photos, PhotoGroup
from backend.core.lightroom import LightroomCatalog
from backend.core.recommender import recommend_all
from backend.config import DEFAULT_SIMILARITY_THRESHOLD

router = APIRouter(prefix="/api")

# ─── 全局扫描状态（线程安全通过 GIL 保证简单读写）─────────
scan_state = {
    "status": "idle",       # idle | scanning | extracting | hashing | grouping | done | error
    "progress": 0,
    "total": 0,
    "current_file": "",
    "message": "",
    "stage": "idle",
    # 扫描结果
    "photos": [],           # PhotoInfo 列表
    "photo_hashes": {},     # {path: hash}
    "groups": [],           # PhotoGroup 列表
    "scan_dir": "",
    "lrcat_path": "",
    "edited_photos": set(),
    "flagged_photos": {},
    "recommendations": None,
}


# ─── 请求模型 ─────────────────────────────────────────────

class ScanRequest(BaseModel):
    directory: str
    lrcat_path: Optional[str] = None
    threshold: int = DEFAULT_SIMILARITY_THRESHOLD
    include_images: bool = False


class DeleteRequest(BaseModel):
    paths: list[str]


class GroupDecision(BaseModel):
    keep: list[str]
    delete: list[str]


# ─── WebSocket 端点（前端通过轮询 /scan/status 获取进度，WebSocket 可选） ───

ws_clients: list[WebSocket] = []


@router.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    try:
        # 持续推送状态给客户端
        last_msg = ""
        while True:
            await asyncio.sleep(0.5)
            current = json.dumps({
                "stage": scan_state["stage"],
                "progress": scan_state["progress"],
                "total": scan_state["total"],
                "message": scan_state["message"],
            }, ensure_ascii=False)
            if current != last_msg:
                await websocket.send_text(current)
                last_msg = current

            # 扫描完成或出错时发送最终状态并退出
            if scan_state["status"] in ("done", "error"):
                summary = None
                if scan_state.get("recommendations"):
                    summary = scan_state["recommendations"].get("summary")
                final = json.dumps({
                    "stage": scan_state["status"],
                    "message": scan_state["message"],
                    "total_photos": len(scan_state.get("photos", [])),
                    "total_groups": len(scan_state.get("groups", [])),
                    "summary": summary,
                }, ensure_ascii=False)
                await websocket.send_text(final)
                break
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in ws_clients:
            ws_clients.remove(websocket)


# ─── 扫描 API ────────────────────────────────────────────

@router.post("/scan")
async def start_scan(req: ScanRequest):
    """启动扫描任务"""
    if not os.path.isdir(req.directory):
        raise HTTPException(400, f"目录不存在: {req.directory}")

    if scan_state["status"] not in ("idle", "done", "error"):
        raise HTTPException(409, "扫描正在进行中")

    # 重置状态
    scan_state.update({
        "status": "scanning",
        "stage": "scanning",
        "progress": 0,
        "total": 0,
        "current_file": "",
        "message": "正在扫描目录...",
        "photos": [],
        "photo_hashes": {},
        "groups": [],
        "scan_dir": req.directory,
        "lrcat_path": req.lrcat_path or "",
        "edited_photos": set(),
        "flagged_photos": {},
        "recommendations": None,
    })

    # 在后台线程执行扫描
    thread = threading.Thread(
        target=_run_scan,
        args=(req.directory, req.lrcat_path, req.threshold, req.include_images),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "message": "扫描已启动"}


def _update_progress(stage: str, message: str, progress: int = 0, total: int = 0, filename: str = ""):
    """线程安全地更新进度状态"""
    scan_state["stage"] = stage
    scan_state["status"] = stage if stage not in ("done", "error") else stage
    scan_state["message"] = message
    scan_state["progress"] = progress
    scan_state["total"] = total
    scan_state["current_file"] = filename


def _run_scan(directory: str, lrcat_path: str | None, threshold: int, include_images: bool):
    """在后台线程执行完整扫描流程"""
    try:
        # 步骤 1: 扫描目录
        _update_progress("scanning", "正在扫描目录，收集照片文件...")

        def scan_progress(current, total, filename):
            _update_progress("scanning", f"扫描中: {filename}", current, total, filename)

        photos = scan_directory(
            directory,
            include_raw=True,
            include_images=include_images,
            progress_callback=scan_progress,
        )
        scan_state["photos"] = photos

        if not photos:
            _update_progress("done", "未找到任何照片文件")
            return

        # 步骤 2: 提取缩略图
        _update_progress("extracting", "正在提取缩略图...")

        def thumb_progress(current, total, filename):
            _update_progress("extracting", f"提取缩略图: {filename}", current, total, filename)

        thumb_results = extract_thumbnails_batch(
            [p.path for p in photos],
            progress_callback=thumb_progress,
        )

        # 步骤 3: 计算哈希
        _update_progress("hashing", "正在计算图像指纹...")

        thumb_map = {orig: str(thumb) for orig, thumb in thumb_results.items() if thumb}

        def hash_progress(current, total):
            _update_progress("hashing", f"计算哈希: {current}/{total}", current, total)

        hashes = compute_phash_batch(thumb_map, progress_callback=hash_progress)
        scan_state["photo_hashes"] = hashes

        # 步骤 4: 聚类分组
        _update_progress("grouping", "正在识别相似照片...")

        photo_sizes = {p.path: p.size for p in photos}
        groups = group_similar_photos(hashes, photo_sizes, threshold)
        scan_state["groups"] = groups

        # 步骤 5: 检测 Lightroom 编辑状态（通过 XMP sidecar 文件）
        _update_progress("grouping", "正在检测 Lightroom 编辑状态...")
        try:
            from backend.core.lightroom import detect_edited_photos
            photo_path_list = [p.path for p in photos]
            edited, flagged = detect_edited_photos(photo_path_list)
            scan_state["edited_photos"] = edited
            scan_state["flagged_photos"] = flagged
            if edited:
                _update_progress("grouping", f"检测到 {len(edited)} 张已编辑照片")
        except Exception as e:
            scan_state["message"] = f"LR 编辑状态检测失败: {e}"

        # 步骤 6: 生成推荐
        _update_progress("grouping", "正在生成推荐...")
        recommendations = recommend_all(
            groups,
            scan_state.get("edited_photos"),
            scan_state.get("flagged_photos"),
        )
        scan_state["recommendations"] = recommendations

        # 完成
        _update_progress(
            "done",
            f"扫描完成！共 {len(photos)} 张照片，发现 {len(groups)} 组相似照片",
        )

    except Exception as e:
        _update_progress("error", f"扫描出错: {str(e)}")


# ─── 查询 API ────────────────────────────────────────────

@router.get("/scan/status")
async def get_scan_status():
    """获取扫描状态"""
    return {
        "status": scan_state["status"],
        "progress": scan_state["progress"],
        "total": scan_state["total"],
        "message": scan_state["message"],
        "current_file": scan_state["current_file"],
    }


@router.get("/groups")
async def get_groups():
    """获取所有相似照片群组"""
    if scan_state["status"] != "done":
        raise HTTPException(400, "扫描尚未完成")

    groups = scan_state.get("groups", [])
    edited = scan_state.get("edited_photos", set())
    flagged = scan_state.get("flagged_photos", {})

    result = []
    for group in groups:
        group_data = group.to_dict()
        for photo in group_data["photos"]:
            path = photo["path"]
            norm_path = os.path.normpath(path)
            filename = os.path.basename(path)
            # 按完整路径、标准化路径、文件名三种方式匹配
            photo["is_edited"] = (
                path in edited or norm_path in edited or filename in edited
            )
            photo["is_flagged"] = (
                path in flagged or norm_path in flagged or filename in flagged
            )
            flag_info = (
                flagged.get(path) or flagged.get(norm_path)
                or flagged.get(filename) or {}
            )
            photo["rating"] = flag_info.get("rating", 0)
            photo["pick"] = flag_info.get("pick", 0)
        result.append(group_data)

    return {"groups": result, "total": len(result)}


@router.get("/recommendations")
async def get_recommendations():
    """获取自动推荐结果"""
    if scan_state["status"] != "done":
        raise HTTPException(400, "扫描尚未完成")

    rec = scan_state.get("recommendations")
    if not rec:
        raise HTTPException(404, "暂无推荐结果")

    return rec


@router.get("/thumbnails/{photo_id}")
async def get_thumbnail(photo_id: str):
    """通过照片路径哈希获取缩略图"""
    import hashlib
    # photo_id 是完整路径的 URL-safe base64 或直接传路径
    # 先尝试从缓存查找
    from backend.config import CACHE_DIR
    for cached_file in CACHE_DIR.iterdir():
        if cached_file.name.startswith(photo_id[:8]):
            return FileResponse(str(cached_file), media_type="image/jpeg")

    raise HTTPException(404, "缩略图未找到")


@router.get("/thumbnail")
async def get_thumbnail_by_path(path: str):
    """通过原始文件路径获取缩略图"""
    thumb_path = extract_thumbnail(path)
    if thumb_path and thumb_path.exists():
        return FileResponse(str(thumb_path), media_type="image/jpeg")
    raise HTTPException(404, "缩略图提取失败")


# ─── 操作 API ────────────────────────────────────────────

@router.post("/delete")
async def delete_photos(req: DeleteRequest):
    """将照片移入回收站"""
    deleted = []
    errors = []

    for path in req.paths:
        try:
            if os.path.exists(path):
                send2trash(path)
                deleted.append(path)
            else:
                errors.append({"path": path, "error": "文件不存在"})
        except Exception as e:
            errors.append({"path": path, "error": str(e)})

    return {
        "deleted_count": len(deleted),
        "error_count": len(errors),
        "deleted": deleted,
        "errors": errors,
    }


@router.post("/reset")
async def reset_scan():
    """重置扫描状态"""
    scan_state.update({
        "status": "idle",
        "progress": 0,
        "total": 0,
        "current_file": "",
        "message": "",
        "photos": [],
        "photo_hashes": {},
        "groups": [],
        "scan_dir": "",
        "lrcat_path": "",
        "edited_photos": set(),
        "flagged_photos": {},
        "recommendations": None,
    })
    return {"status": "reset"}


# ─── Lightroom API (保留，供未来使用) ─────────────────────────

@router.get("/lightroom/info")
async def get_catalog_info(path: str):
    """获取 Lightroom 目录信息"""
    try:
        with LightroomCatalog(path) as catalog:
            return catalog.get_catalog_info()
    except Exception as e:
        raise HTTPException(400, str(e))


# ─── 文件/文件夹选择 API（跨平台） ─────────────────────────

def _pick_directory() -> str | None:
    """跨平台弹出原生文件夹选择对话框"""
    import sys
    import subprocess

    if sys.platform == 'darwin':
        # macOS: AppleScript
        script = ('tell application "System Events" to activate\n'
                  'set chosenFolder to choose folder with prompt "选择照片文件夹"\n'
                  'return POSIX path of chosenFolder')
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().rstrip('/')
        except Exception:
            pass

    elif sys.platform == 'win32':
        # Windows: PowerShell
        ps_script = (
            '[System.Reflection.Assembly]::LoadWithPartialName("System.windows.forms") | Out-Null;'
            '$dialog = New-Object System.Windows.Forms.FolderBrowserDialog;'
            '$dialog.Description = "选择照片文件夹";'
            '$result = $dialog.ShowDialog();'
            'if ($result -eq "OK") { $dialog.SelectedPath }'
        )
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

    else:
        # Linux: zenity
        try:
            result = subprocess.run(
                ['zenity', '--file-selection', '--directory', '--title=选择照片文件夹'],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

    return None


@router.get("/pick-folder")
async def pick_folder():
    """弹出原生文件夹选择对话框（跨平台）"""
    import concurrent.futures
    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            folder = await asyncio.get_event_loop().run_in_executor(pool, _pick_directory)
        if folder:
            return {"path": folder}
        return {"path": None, "fallback": True, "message": "未选择文件夹"}
    except Exception:
        return {"path": None, "fallback": True, "message": "文件选择器不可用"}


