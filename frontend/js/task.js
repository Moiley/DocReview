/**
 * task.js — 任务结果页逻辑
 * P2: 实时轮询任务状态 → 展示进度/统计 → 结果汇总表
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

// ---- Get task_id from URL ----
const params = new URLSearchParams(window.location.search);
const taskId = params.get('task_id');

if (!taskId) {
    document.body.innerHTML = '<div class="app-container"><div class="empty-state"><div class="empty-icon">❓</div><div class="empty-text">未指定任务 ID</div><div class="empty-hint"><a href="index.html">返回创建任务</a></div></div></div>';
}

// ---- DOM ----
const taskIdTag = document.getElementById('taskIdTag');
const statusText = document.getElementById('statusText');
const statusBadge = document.getElementById('statusBadge');
const progressFill = document.getElementById('progressFill');
const progressLabel = document.getElementById('progressLabel');
const statProblems = document.getElementById('statProblems');
const statFiles = document.getElementById('statFiles');
const resultSection = document.getElementById('resultSection');
const resultTableBody = document.getElementById('resultTableBody');
const actionsRow = document.getElementById('actionsRow');
const btnDownload = document.getElementById('btnDownload');
const btnViewIssues = document.getElementById('btnViewIssues');
const fileSection = document.getElementById('fileSection');
const fileResults = document.getElementById('fileResults');

// ---- Init ----
taskIdTag.textContent = taskId ? taskId.substring(0, 8) + '...' : '';
taskIdTag.title = taskId;

let pollTimer = null;

if (taskId) {
    fetchResult();
    pollTimer = setInterval(fetchResult, 3000);
}

// ---- Fetch Result ----
async function fetchResult() {
    try {
        const resp = await fetch(`${API_BASE}/v1/result?task_id=${taskId}`);
        const data = await resp.json();
        renderResult(data);

        if (data.status === 'complete' || data.status === 'error') {
            clearInterval(pollTimer);
        }
    } catch (err) {
        console.error('Fetch error:', err);
    }
}

function renderResult(data) {
    const { status, progress, all_problem_count, message, data: items, document_summary } = data;

    // Status badge
    if (status === 'complete') {
        statusBadge.innerHTML = '<span class="tag tag-success"><span class="status-dot complete"></span>已完成</span>';
        const problemCount = all_problem_count ?? 0;
        statusText.textContent = `审校完成，共发现 ${problemCount} 个问题`;
        document.getElementById('progressBarWrap').style.display = 'none';
        progressLabel.textContent = '✅ 处理完成';
        actionsRow.style.display = 'flex';
        btnDownload.href = `${API_BASE}/v1/download/?task_id=${taskId}`;
        btnViewIssues.href = `issues.html?task_id=${taskId}`;
    } else if (status === 'error') {
        statusBadge.innerHTML = '<span class="tag tag-error"><span class="status-dot error"></span>失败</span>';
        statusText.textContent = message || '任务执行失败';
        document.getElementById('progressBarWrap').style.display = 'none';
        progressLabel.textContent = '❌ 处理失败';
    } else {
        statusBadge.innerHTML = '<span class="tag tag-warning"><span class="status-dot processing"></span>处理中</span>';
        statusText.textContent = message || '正在处理...';
        const pct = Math.min(progress || 0, 100);
        progressFill.style.width = pct + '%';
        progressLabel.textContent = `进度: ${pct}%`;
    }

    // Stats
    statProblems.textContent = all_problem_count ?? '-';

    // Per-scan item table
    if (items && items.length > 0) {
        resultSection.style.display = 'block';
        let totalFiles = 0;

        resultTableBody.innerHTML = items.map(item => {
            const name = SCAN_ITEMS_MAP[item.scan_items] || item.problem_type || item.scan_items;
            totalFiles = Math.max(totalFiles, item.file_count || 0);
            return `
        <tr>
          <td>${name}</td>
          <td>${item.file_count || 0}</td>
          <td><strong style="color:${item.total_problem_count > 0 ? 'var(--warning)' : 'var(--accent-500)'}">${item.total_problem_count || 0}</strong></td>
          <td>${item.completed_files === item.file_count ? '<span class="tag tag-success">完成</span>' : '<span class="tag tag-warning">处理中</span>'}</td>
        </tr>
      `;
        }).join('');

        statFiles.textContent = totalFiles;

        // Render per-file breakdown
        renderFileBreakdown(items);
    }
}

function renderFileBreakdown(items) {
    // Aggregate by file
    const fileMap = {};
    items.forEach(item => {
        if (item.file_reports) {
            item.file_reports.forEach(fr => {
                if (!fileMap[fr.file_name]) {
                    fileMap[fr.file_name] = { type: fr.file_type, problems: 0, details: [] };
                }
                fileMap[fr.file_name].problems += fr.problem_count || 0;
                fileMap[fr.file_name].details.push({
                    scanItem: item.scan_items,
                    name: SCAN_ITEMS_MAP[item.scan_items] || item.problem_type,
                    count: fr.problem_count || 0,
                });
            });
        }
    });

    const fileNames = Object.keys(fileMap);
    if (fileNames.length === 0) return;

    fileSection.style.display = 'block';
    fileResults.innerHTML = fileNames.map(fn => {
        const f = fileMap[fn];
        return `
      <div class="issue-card">
        <div class="issue-header">
          <div class="issue-meta">
            <span class="tag tag-info">${f.type || '文档'}</span>
            <strong style="color:var(--gray-800)">${fn}</strong>
          </div>
          <span class="tag ${f.problems > 0 ? 'tag-warning' : 'tag-success'}">${f.problems} 个问题</span>
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:8px;">
          ${f.details.map(d => `
            <span class="text-xs" style="padding:4px 8px; background:var(--bg-glass); border:1px solid var(--border-color); border-radius:4px;">
              ${d.name}: <strong>${d.count}</strong>
            </span>
          `).join('')}
        </div>
      </div>
    `;
    }).join('');
}

// ---- Toast ----
function showToast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
