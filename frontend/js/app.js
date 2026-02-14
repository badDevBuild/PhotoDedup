/**
 * PhotoDedup — 主应用逻辑
 * 处理页面路由、API 交互、WebSocket 进度、照片群组展示
 */

// ─── 常量 ─────────────────────────────────────────────
const API = '/api';
const WS_URL = `ws://${location.host}/api/ws/progress`;

// ─── 状态 ─────────────────────────────────────────────
const state = {
    currentPage: 'scan',
    groups: [],
    recommendations: null,
    currentGroupIndex: 0,
    ws: null,
    // 用户在审核模式中的操作记录：{ path: 'keep' | 'delete' }
    decisions: {},
};

// ─── DOM 引用 ──────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── 初始化 ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    showPage('scan');
});

function initEventListeners() {
    // 扫描页
    $('#btn-start-scan').addEventListener('click', startScan);
    $('#btn-browse-folder').addEventListener('click', browseFolder);
    $('#threshold').addEventListener('input', (e) => {
        $('#threshold-val').textContent = e.target.value;
    });

    // HTML5 文件夹选择回调
    $('#folder-picker').addEventListener('change', handleFolderPicked);

    // 结果页
    $('#btn-review-mode').addEventListener('click', () => enterReviewMode());
    $('#btn-auto-mode').addEventListener('click', () => enterAutoMode());
    $('#btn-new-scan').addEventListener('click', resetAndGoHome);
    $('#btn-go-home').addEventListener('click', resetAndGoHome);

    // 审核导航
    $('#btn-prev-group').addEventListener('click', () => navigateGroup(-1));
    $('#btn-next-group').addEventListener('click', () => navigateGroup(1));
    $('#btn-keep-edited').addEventListener('click', () => bulkAction('edited'));
    $('#btn-keep-first').addEventListener('click', () => bulkAction('first'));
    $('#btn-keep-all').addEventListener('click', () => bulkAction('all'));

    // 自动清理
    $('#btn-cancel-auto').addEventListener('click', () => {
        $('#auto-panel').classList.add('hidden');
        $('#review-panel').classList.add('hidden');
    });
    $('#btn-confirm-delete').addEventListener('click', executeDelete);

    // 完成页
    $('#btn-back-home').addEventListener('click', resetAndGoHome);

    // Lightbox
    $('.lightbox-overlay').addEventListener('click', closeLightbox);
    $('.lightbox-close').addEventListener('click', closeLightbox);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeLightbox();
        // 审核模式快捷键
        if (state.currentPage === 'results' && !$('#review-panel').classList.contains('hidden')) {
            if (e.key === 'ArrowLeft') navigateGroup(-1);
            if (e.key === 'ArrowRight') navigateGroup(1);
        }
    });
}

// ─── 页面路由 ──────────────────────────────────────────
function showPage(name) {
    $$('.page').forEach(p => p.classList.remove('active'));
    $(`#page-${name}`).classList.add('active');
    state.currentPage = name;
}

// ─── 扫描 ─────────────────────────────────────────────
async function startScan() {
    const directory = $('#scan-dir').value.trim();
    if (!directory) {
        alert('请输入照片文件夹路径');
        return;
    }

    const threshold = parseInt($('#threshold').value);
    const includeImages = $('#include-images').checked;

    // 切换到进度页
    showPage('progress');
    updateStatusBadge('scanning');

    // 连接 WebSocket
    connectWebSocket();

    // 发起扫描请求
    try {
        const res = await fetch(`${API}/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                directory,
                threshold,
                include_images: includeImages,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`扫描启动失败: ${err.detail || '未知错误'}`);
            showPage('scan');
            updateStatusBadge('idle');
            return;
        }
    } catch (e) {
        alert(`无法连接服务器: ${e.message}`);
        showPage('scan');
        updateStatusBadge('idle');
    }
}

// ─── WebSocket 进度 ──────────────────────────────────
function connectWebSocket() {
    if (state.ws) {
        state.ws.close();
    }

    state.ws = new WebSocket(WS_URL);

    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleProgress(data);
    };

    state.ws.onerror = () => {
        console.warn('WebSocket 连接失败，使用轮询模式');
        startPolling();
    };

    state.ws.onclose = () => {
        state.ws = null;
    };
}

function startPolling() {
    const poll = setInterval(async () => {
        try {
            const res = await fetch(`${API}/scan/status`);
            const data = await res.json();
            handleProgress({
                stage: data.status,
                progress: data.progress,
                total: data.total,
                message: data.message,
            });
            if (data.status === 'done' || data.status === 'error') {
                clearInterval(poll);
            }
        } catch (e) {
            clearInterval(poll);
        }
    }, 1000);
}

function handleProgress(data) {
    const { stage, progress, total, message, summary } = data;

    // 更新进度文本
    if (message) {
        $('#progress-message').textContent = message;
    }

    // 更新进度条
    if (total > 0) {
        const pct = Math.round((progress / total) * 100);
        $('#progress-fill').style.width = `${pct}%`;
        $('#progress-percent').textContent = `${pct}%`;
    }

    // 更新阶段指示器
    const stageOrder = ['scanning', 'extracting', 'hashing', 'grouping'];
    const currentIdx = stageOrder.indexOf(stage);

    stageOrder.forEach((s, i) => {
        const el = $(`#stage-${s}`);
        el.classList.remove('active', 'done');
        if (i < currentIdx) el.classList.add('done');
        if (i === currentIdx) el.classList.add('active');
    });

    // 更新标题
    const titles = {
        scanning: '正在扫描文件...',
        extracting: '正在提取缩略图...',
        hashing: '正在计算图像指纹...',
        grouping: '正在识别相似照片...',
        lightroom: '正在读取 Lightroom 目录...',
    };
    if (titles[stage]) {
        $('#progress-title').textContent = titles[stage];
    }

    // 扫描完成
    if (stage === 'done') {
        updateStatusBadge('done');
        if (summary) {
            loadResults(summary);
        } else {
            loadResultsFromAPI();
        }
    }

    // 扫描出错
    if (stage === 'error') {
        updateStatusBadge('error');
        alert(`扫描出错: ${message}`);
        showPage('scan');
    }
}

// ─── 加载结果 ──────────────────────────────────────────
async function loadResultsFromAPI() {
    try {
        const [groupsRes, recRes] = await Promise.all([
            fetch(`${API}/groups`),
            fetch(`${API}/recommendations`),
        ]);
        const groupsData = await groupsRes.json();
        const recData = await recRes.json();

        state.groups = groupsData.groups || [];
        state.recommendations = recData;

        populateResultsSummary(recData.summary);
        showPage('results');

        // 扫描完成后自动进入逐组审核模式
        if (state.groups.length > 0) {
            enterReviewMode();
        }
    } catch (e) {
        alert(`加载结果失败: ${e.message}`);
        showPage('scan');
    }
}

function loadResults(summary) {
    // 先显示摘要，再异步加载详细数据
    populateResultsSummary(summary);
    showPage('results');

    // 异步加载完整数据
    loadResultsFromAPI().catch(() => { });
}

function populateResultsSummary(summary) {
    if (!summary) return;
    $('#stat-total').textContent = summary.total_photos || 0;
    $('#stat-groups').textContent = summary.total_groups || 0;
    $('#stat-deletable').textContent = summary.delete_count || 0;
    $('#stat-save-space').textContent = `${summary.save_gb || 0} GB`;
}

// ─── 审核模式 ──────────────────────────────────────────
function enterReviewMode() {
    if (state.groups.length === 0) {
        alert('没有发现相似照片组');
        return;
    }

    $('#auto-panel').classList.add('hidden');
    $('#review-panel').classList.remove('hidden');
    state.currentGroupIndex = 0;

    // 初始化决策：使用推荐结果
    if (state.recommendations) {
        state.decisions = {};
        for (const rec of state.recommendations.recommendations) {
            for (const p of rec.keep) state.decisions[p] = 'keep';
            for (const p of rec.delete) state.decisions[p] = 'delete';
        }
    }

    renderCurrentGroup();
}

function navigateGroup(delta) {
    const newIdx = state.currentGroupIndex + delta;
    if (newIdx < 0 || newIdx >= state.groups.length) return;
    state.currentGroupIndex = newIdx;
    renderCurrentGroup();
}

function renderCurrentGroup() {
    const group = state.groups[state.currentGroupIndex];
    if (!group) return;

    // 更新导航
    $('#group-indicator').textContent =
        `第 ${state.currentGroupIndex + 1} / ${state.groups.length} 组（${group.count} 张）`;

    // 渲染照片卡片
    const gallery = $('#group-gallery');
    gallery.innerHTML = '';

    for (const photo of group.photos) {
        const decision = state.decisions[photo.path] || 'undecided';
        const card = createPhotoCard(photo, decision);
        gallery.appendChild(card);
    }
}

function createPhotoCard(photo, decision) {
    const card = document.createElement('div');
    card.className = `photo-card ${decision}`;
    card.dataset.path = photo.path;

    const thumbUrl = `${API}/thumbnail?path=${encodeURIComponent(photo.path)}`;
    const filename = photo.path.split('/').pop();
    const sizeStr = formatFileSize(photo.size);

    // 徽章
    let badges = '';
    if (photo.is_edited) badges += '<span class="badge badge-edited">已编辑</span>';
    if (photo.is_flagged) badges += '<span class="badge badge-flagged">⭐</span>';

    // 操作按钮内容
    const actionIcon = decision === 'keep' ? '✓' : decision === 'delete' ? '✕' : '';

    card.innerHTML = `
        <img src="${thumbUrl}" alt="${filename}" loading="lazy"
             onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 320 213%22><rect fill=%22%231a1e2a%22 width=%22320%22 height=%22213%22/><text x=%2250%25%22 y=%2250%25%22 fill=%22%23555%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2214%22>加载失败</text></svg>'" />
        <div class="photo-card-badges">${badges}</div>
        <div class="photo-card-action" title="切换保留/删除">${actionIcon}</div>
        <div class="photo-card-info">
            <span title="${photo.path}">${filename}</span>
            <span>${sizeStr}</span>
        </div>
    `;

    // 点击图片 → 预览
    card.querySelector('img').addEventListener('click', (e) => {
        e.stopPropagation();
        openLightbox(thumbUrl, filename, sizeStr);
    });

    // 点击操作按钮 → 切换状态
    card.querySelector('.photo-card-action').addEventListener('click', (e) => {
        e.stopPropagation();
        togglePhotoDecision(photo.path, card);
    });

    return card;
}

function togglePhotoDecision(path, card) {
    const current = state.decisions[path] || 'undecided';
    let next;
    if (current === 'keep') next = 'delete';
    else if (current === 'delete') next = 'keep';
    else next = 'keep';

    state.decisions[path] = next;

    // 更新 UI
    card.className = `photo-card ${next}`;
    const actionBtn = card.querySelector('.photo-card-action');
    actionBtn.textContent = next === 'keep' ? '✓' : '✕';
}

function bulkAction(type) {
    const group = state.groups[state.currentGroupIndex];
    if (!group) return;

    if (type === 'edited') {
        // 检查是否有已编辑照片
        const hasEdited = group.photos.some(p => p.is_edited);
        if (!hasEdited) {
            alert('⚠️ 当前组中没有 Lightroom 已编辑的照片。\n\n可能的原因：\n• 未指定 Lightroom 目录\n• LR 目录中没有这些照片的编辑记录\n• LR 目录文件在云盘上未下载到本地');
            return;
        }
    }

    for (let i = 0; i < group.photos.length; i++) {
        const photo = group.photos[i];
        if (type === 'all') {
            state.decisions[photo.path] = 'keep';
        } else if (type === 'first') {
            state.decisions[photo.path] = i === 0 ? 'keep' : 'delete';
        } else if (type === 'edited') {
            state.decisions[photo.path] = photo.is_edited ? 'keep' : 'delete';
        }
    }

    renderCurrentGroup();
}

// ─── 自动清理模式 ──────────────────────────────────────
function enterAutoMode() {
    if (!state.recommendations) {
        alert('推荐数据暂未就绪');
        return;
    }

    const rec = state.recommendations;
    const summary = rec.summary;

    // 更新统计
    $('#auto-keep-count').textContent = summary.keep_count;
    $('#auto-delete-count').textContent = summary.delete_count;
    $('#auto-save-space').textContent = `${summary.save_gb} GB`;
    $('#confirm-delete-count').textContent = summary.delete_count;

    // 渲染分组列表
    const list = $('#auto-groups-list');
    list.innerHTML = '';

    for (const r of rec.recommendations) {
        const group = state.groups.find(g => g.group_id === r.group_id);
        if (!group) continue;

        const item = document.createElement('div');
        item.className = 'auto-group-item';

        // 缩略图（最多显示 3 张）
        const thumbsHtml = group.photos.slice(0, 3).map(p => {
            const url = `${API}/thumbnail?path=${encodeURIComponent(p.path)}`;
            return `<img src="${url}" alt="" loading="lazy" />`;
        }).join('');

        item.innerHTML = `
            <div class="auto-group-thumbs">${thumbsHtml}</div>
            <div class="auto-group-info">
                <strong>${group.count} 张相似照片</strong><br>
                <span>保留 ${r.keep_count} 张，删除 ${r.delete_count} 张，
                释放 ${formatFileSize(r.save_bytes)}</span>
            </div>
        `;

        list.appendChild(item);

        // 记录决策
        for (const p of r.keep) state.decisions[p] = 'keep';
        for (const p of r.delete) state.decisions[p] = 'delete';
    }

    // 显示面板
    $('#review-panel').classList.add('hidden');
    $('#auto-panel').classList.remove('hidden');
}

// ─── 执行删除 ──────────────────────────────────────────
async function executeDelete() {
    const toDelete = Object.entries(state.decisions)
        .filter(([_, v]) => v === 'delete')
        .map(([k]) => k);

    if (toDelete.length === 0) {
        alert('没有选择要删除的照片');
        return;
    }

    if (!confirm(`即将删除 ${toDelete.length} 张照片（移入回收站）。\n\n确定要继续吗？`)) {
        return;
    }

    $('#btn-confirm-delete').disabled = true;
    $('#btn-confirm-delete').textContent = '正在删除...';

    try {
        const res = await fetch(`${API}/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths: toDelete }),
        });

        const result = await res.json();

        // 计算释放空间
        let savedSize = 0;
        for (const p of result.deleted) {
            const group = state.groups.find(g => g.photos.some(ph => ph.path === p));
            if (group) {
                const photo = group.photos.find(ph => ph.path === p);
                if (photo) savedSize += photo.size;
            }
        }

        $('#complete-message').textContent =
            `已成功清理 ${result.deleted_count} 张照片，释放 ${formatFileSize(savedSize)} 空间`;

        if (result.error_count > 0) {
            $('#complete-message').textContent += `\n（${result.error_count} 个文件删除失败）`;
        }

        showPage('complete');
    } catch (e) {
        alert(`删除失败: ${e.message}`);
    } finally {
        $('#btn-confirm-delete').disabled = false;
        $('#btn-confirm-delete').innerHTML = `<span class="btn-icon">🗑️</span> 确认删除`;
    }
}

// ─── Lightbox 预览 ──────────────────────────────────────
function openLightbox(src, filename, size) {
    $('#lightbox-img').src = src;
    $('#lightbox-filename').textContent = filename;
    $('#lightbox-size').textContent = size;
    $('#lightbox').classList.remove('hidden');
}

function closeLightbox() {
    $('#lightbox').classList.add('hidden');
    $('#lightbox-img').src = '';
}

// ─── 文件夹选择（跨平台） ──────────────────────────────────
async function browseFolder() {
    $('#btn-browse-folder').textContent = '选择中...';
    $('#btn-browse-folder').disabled = true;
    try {
        const res = await fetch(`${API}/pick-folder`);
        const data = await res.json();
        if (data.path) {
            $('#scan-dir').value = data.path;
        } else if (data.fallback) {
            // 后端没有原生对话框支持，用 HTML5 fallback
            $('#folder-picker').click();
        }
    } catch (e) {
        // 网络错误时也用 HTML5 fallback
        $('#folder-picker').click();
    } finally {
        $('#btn-browse-folder').textContent = '浏览...';
        $('#btn-browse-folder').disabled = false;
    }
}

function handleFolderPicked(e) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const firstPath = files[0].webkitRelativePath;
    const folderName = firstPath.split('/')[0];

    const currentVal = $('#scan-dir').value.trim();
    if (!currentVal) {
        alert(`已选择文件夹: ${folderName}\n\n` +
            `检测到 ${files.length} 个文件。\n` +
            `由于浏览器安全限制，请在输入框中输入完整路径。`);
    }
}

// ─── 工具函数 ──────────────────────────────────────────
function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function updateStatusBadge(status) {
    const badge = $('#status-badge');
    badge.className = `status-badge ${status}`;
    const labels = {
        idle: '就绪',
        scanning: '扫描中',
        done: '完成',
        error: '出错',
    };
    badge.textContent = labels[status] || status;
}

async function resetAndGoHome() {
    try {
        await fetch(`${API}/reset`, { method: 'POST' });
    } catch (e) { }

    state.groups = [];
    state.recommendations = null;
    state.currentGroupIndex = 0;
    state.decisions = {};

    updateStatusBadge('idle');
    showPage('scan');
}
