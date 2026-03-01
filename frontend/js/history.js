/**
 * history.js — 历史任务列表页逻辑
 * 从后端 GET /v1/tasks/list 加载任务列表
 */

const API_BASE = window.location.origin;

const historyBody = document.getElementById('historyBody');
const emptyState = document.getElementById('emptyState');
const loadingState = document.getElementById('loadingState');

// ---- Init ----
loadTaskHistory();

async function loadTaskHistory() {
    try {
        const resp = await fetch(`${API_BASE}/v1/tasks/list`);
        const data = await resp.json();

        loadingState.style.display = 'none';

        if (!data.tasks || data.tasks.length === 0) {
            emptyState.style.display = 'block';
            return;
        }

        renderTable(data.tasks);
    } catch (err) {
        // Fallback: load from localStorage
        loadingState.style.display = 'none';
        loadFromLocalStorage();
    }
}

function loadFromLocalStorage() {
    const history = JSON.parse(localStorage.getItem('taskHistory') || '[]');
    if (history.length === 0) {
        emptyState.style.display = 'block';
        return;
    }
    // Convert local history to table format
    const rows = history.map(h => ({
        task_id: h.task_id,
        status: 'unknown',
        problem_count: null,
        create_time: h.create_time || '-',
        complete_time: '-',
    }));
    renderTable(rows);
}

function renderTable(tasks) {
    historyBody.innerHTML = tasks.map(t => {
        const shortId = t.task_id.substring(0, 8) + '...';
        const statusTag = getStatusTag(t.status);
        return `
      <tr class="task-row" onclick="window.location.href='task.html?task_id=${t.task_id}'">
        <td>
          <code style="font-size:0.85rem; color:var(--primary-400); cursor:pointer;" title="${t.task_id}">${shortId}</code>
        </td>
        <td>${statusTag}</td>
        <td>${t.problem_count ?? '-'}</td>
        <td class="text-sm">${t.create_time || '-'}</td>
        <td class="text-sm">${t.complete_time || '-'}</td>
        <td>
          <a href="task.html?task_id=${t.task_id}" class="btn btn-sm btn-secondary" onclick="event.stopPropagation();">查看</a>
        </td>
      </tr>
    `;
    }).join('');
}

function getStatusTag(status) {
    if (status === 'complete') return '<span class="tag tag-success"><span class="status-dot complete"></span>完成</span>';
    if (status === 'error') return '<span class="tag tag-error"><span class="status-dot error"></span>失败</span>';
    if (status === 'processing') return '<span class="tag tag-warning"><span class="status-dot processing"></span>处理中</span>';
    return '<span class="tag tag-info">未知</span>';
}

function showToast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
