/**
 * issues.js — 问题详情页逻辑
 * P3: 分页显示审校问题 → 按类型/文件筛选
 */

const API_BASE = window.location.origin;

// ---- Scan Items Map ----
const SCAN_ITEMS_MAP = {
    'scanItem1001': '英文资料存在中文字符或乱码',
    'scanItem1002': '中文资料存在外语章节',
    'scanItem5001': '英文单词拼写错误',
    'scanItem5002': '中文错别字',
    'scanItem5003': '英文单词大小写错误',
    'scanItem5004': '英文文档低级语法错误',
    'scanItem5005': '不规范用语或错误用语',
    'scanItem6001': '上下文一致性错误',
    'scanItem6002': '标点符号成对匹配检查',
    'scanItem6003': '标点符号前后的空格错误',
    'scanItem6004': '中文文档中使用了半角标点符号',
    'scanItem12009': '文档中是否存在乱码',
    'scanItem13002': '产品名称版本合规性检查',
    'scanItem14003': '英文中是否有隐藏中文字符',
    'scanItem99999': '敏感词扫描',
};

// ---- State ----
const params = new URLSearchParams(window.location.search);
const taskId = params.get('task_id');
let allIssues = []; // all loaded from server
let currentPage = 1;
const pageSize = 20;
let filterType = '';
let filterFile = '';

// ---- DOM ----
const issueListEl = document.getElementById('issueList');
const paginationEl = document.getElementById('pagination');
const emptyState = document.getElementById('emptyState');
const totalCountEl = document.getElementById('totalCount');
const filterTypeEl = document.getElementById('filterType');
const filterFileEl = document.getElementById('filterFile');
const backLink = document.getElementById('backLink');

// ---- Init ----
if (taskId) {
    backLink.href = `task.html?task_id=${taskId}`;
    loadAllIssues();
} else {
    issueListEl.innerHTML = '<div class="empty-state"><div class="empty-icon">❓</div><div class="empty-text">未指定任务 ID</div></div>';
}

// ---- Load Issues (fetch all for client-side filtering) ----
async function loadAllIssues() {
    try {
        // Fetch a large chunk
        const resp = await fetch(`${API_BASE}/v1/issues?task_id=${taskId}&page=1&limit=1000`);
        const data = await resp.json();
        allIssues = data.items || [];

        // Populate filters
        populateFilters();
        renderPage();
    } catch (err) {
        showToast('加载问题列表失败: ' + err.message, 'error');
    }
}

function populateFilters() {
    // Types
    const types = [...new Set(allIssues.map(i => i.type))];
    filterTypeEl.innerHTML = '<option value="">全部检查项</option>' +
        types.map(t => `<option value="${t}">${SCAN_ITEMS_MAP[t] || t}</option>`).join('');

    // Files
    const files = [...new Set(allIssues.map(i => i.location))];
    filterFileEl.innerHTML = '<option value="">全部文件</option>' +
        files.map(f => `<option value="${f}">${f}</option>`).join('');
}

filterTypeEl.addEventListener('change', (e) => {
    filterType = e.target.value;
    currentPage = 1;
    renderPage();
});

filterFileEl.addEventListener('change', (e) => {
    filterFile = e.target.value;
    currentPage = 1;
    renderPage();
});

// ---- Render ----
function getFilteredIssues() {
    return allIssues.filter(i => {
        if (filterType && i.type !== filterType) return false;
        if (filterFile && i.location !== filterFile) return false;
        return true;
    });
}

function renderPage() {
    const filtered = getFilteredIssues();
    const total = filtered.length;
    totalCountEl.textContent = `共 ${total} 条问题`;

    if (total === 0) {
        issueListEl.innerHTML = '';
        paginationEl.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    emptyState.style.display = 'none';

    const totalPages = Math.ceil(total / pageSize);
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * pageSize;
    const pageItems = filtered.slice(start, start + pageSize);

    issueListEl.innerHTML = pageItems.map((item, idx) => {
        const typeName = SCAN_ITEMS_MAP[item.type] || item.type;
        const tagClass = getTagClass(item.type);
        return `
      <div class="issue-card" style="animation: fadeIn 0.3s ease ${idx * 0.03}s both;">
        <div class="issue-header">
          <div class="issue-meta">
            <span class="tag ${tagClass}">${typeName}</span>
          </div>
          <div class="issue-file">📄 ${item.location || '未知文件'}</div>
        </div>
        <div class="issue-sentence">${escapeHtml(item.question || '')}</div>
        <div class="issue-suggestion">${escapeHtml(item.suggestion || '')}</div>
      </div>
    `;
    }).join('');

    // Pagination
    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    if (totalPages <= 1) {
        paginationEl.innerHTML = '';
        return;
    }

    let html = '';
    html += `<button class="page-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="goPage(${currentPage - 1})">‹</button>`;

    const range = getPageRange(currentPage, totalPages);
    range.forEach(p => {
        if (p === '...') {
            html += `<span class="page-btn" style="border:none; cursor:default;">…</span>`;
        } else {
            html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goPage(${p})">${p}</button>`;
        }
    });

    html += `<button class="page-btn" ${currentPage >= totalPages ? 'disabled' : ''} onclick="goPage(${currentPage + 1})">›</button>`;
    paginationEl.innerHTML = html;
}

function getPageRange(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages = [];
    pages.push(1);
    if (current > 3) pages.push('...');
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        pages.push(i);
    }
    if (current < total - 2) pages.push('...');
    pages.push(total);
    return pages;
}

function goPage(page) {
    currentPage = page;
    renderPage();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---- Helpers ----
function getTagClass(scanItem) {
    if (scanItem.startsWith('scanItem50')) return 'tag-error';
    if (scanItem.startsWith('scanItem60')) return 'tag-warning';
    if (scanItem.startsWith('scanItem12')) return 'tag-info';
    if (scanItem === 'scanItem99999') return 'tag-primary';
    return 'tag-info';
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showToast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
