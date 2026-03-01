/**
 * app.js — 任务创建页逻辑
 * P1: 文件上传 → 检查项选择 → 策略选择 → 提交
 */

const API_BASE = window.location.origin;

// ---- 扫描项配置（全部15项）----
const SCAN_ITEMS = [
    { code: 'scanItem5001', name: '英文单词拼写错误', default: true },
    { code: 'scanItem5002', name: '中文错别字', default: true },
    { code: 'scanItem5005', name: '不规范用语或错误用语', default: false },
    { code: 'scanItem6001', name: '上下文一致性错误', default: true },
    { code: 'scanItem6002', name: '标点符号成对匹配检查', default: true },
    { code: 'scanItem12009', name: '文档中是否存在乱码', default: true },
    { code: 'scanItem1001', name: '英文资料存在中文字符或乱码', default: false },
    { code: 'scanItem1002', name: '中文资料存在外语章节', default: false },
    { code: 'scanItem5003', name: '英文单词大小写错误', default: false },
    { code: 'scanItem5004', name: '英文文档低级语法错误', default: false },
    { code: 'scanItem6003', name: '标点符号前后的空格错误', default: false },
    { code: 'scanItem6004', name: '中文文档中使用了半角标点符号', default: false },
    { code: 'scanItem13002', name: '产品名称版本合规性检查', default: false },
    { code: 'scanItem14003', name: '英文中是否有隐藏中文字符', default: false },
    { code: 'scanItem99999', name: '敏感词扫描', default: true },
];

// ---- State ----
let selectedFiles = [];
let currentStep = 1;
let selectedStrategy = 'ours-adaptive';

// ---- DOM ----
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const btnToStep2 = document.getElementById('btnToStep2');
const btnToStep3 = document.getElementById('btnToStep3');
const btnBackToStep1 = document.getElementById('btnBackToStep1');
const btnBackToStep2 = document.getElementById('btnBackToStep2');
const btnSubmit = document.getElementById('btnSubmit');
const scanGrid = document.getElementById('scanGrid');

// ---- Init ----
renderScanItems();
setupDragDrop();

// ---- File Upload ----
uploadZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => addFiles(e.target.files));

function setupDragDrop() {
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        addFiles(e.dataTransfer.files);
    });
}

function addFiles(fileListObj) {
    const allowed = ['.pdf', '.docx', '.xlsx', '.pptx', '.chm'];
    for (const f of fileListObj) {
        const ext = '.' + f.name.split('.').pop().toLowerCase();
        if (!allowed.includes(ext)) {
            showToast(`不支持的文件类型: ${ext}`, 'error');
            continue;
        }
        // Avoid duplicates
        if (!selectedFiles.find(sf => sf.name === f.name && sf.size === f.size)) {
            selectedFiles.push(f);
        }
    }
    renderFileList();
    fileInput.value = '';
}

function removeFile(idx) {
    selectedFiles.splice(idx, 1);
    renderFileList();
}

function renderFileList() {
    btnToStep2.disabled = selectedFiles.length === 0;
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        return;
    }
    fileList.innerHTML = selectedFiles.map((f, i) => `
    <div class="file-item">
      <div class="file-info">
        <span class="file-icon">${getFileIcon(f.name)}</span>
        <span class="file-name">${f.name}</span>
        <span class="file-size">${formatSize(f.size)}</span>
      </div>
      <button class="file-remove" onclick="removeFile(${i})" title="移除">✕</button>
    </div>
  `).join('');
}

function getFileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    const icons = { pdf: '📕', docx: '📘', xlsx: '📗', pptx: '📙', chm: '📓' };
    return icons[ext] || '📄';
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ---- Scan Items ----
function renderScanItems() {
    scanGrid.innerHTML = SCAN_ITEMS.map(item => `
    <label class="scan-checkbox">
      <input type="checkbox" value="${item.code}" ${item.default ? 'checked' : ''}>
      <span class="scan-label">${item.name}</span>
    </label>
  `).join('');
}

document.getElementById('btnSelectAll').addEventListener('click', () => {
    scanGrid.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
});

document.getElementById('btnSelectDefault').addEventListener('click', () => {
    scanGrid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        const item = SCAN_ITEMS.find(s => s.code === cb.value);
        cb.checked = item ? item.default : false;
    });
});

function getSelectedScanItems() {
    const checked = scanGrid.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checked).map(cb => cb.value);
}

// ---- Strategy ----
function selectStrategy(strategy) {
    selectedStrategy = strategy;
    document.querySelectorAll('.strategy-card').forEach(c => c.classList.remove('selected'));
    if (strategy === 'ours-fixed') {
        document.getElementById('card-ssla').classList.add('selected');
    } else {
        document.getElementById('card-hdca').classList.add('selected');
    }
}

// ---- Step Navigation ----
function goToStep(step) {
    currentStep = step;
    document.getElementById('panel-upload').style.display = step === 1 ? 'block' : 'none';
    document.getElementById('panel-scan').style.display = step === 2 ? 'block' : 'none';
    document.getElementById('panel-strategy').style.display = step === 3 ? 'block' : 'none';

    document.querySelectorAll('.step').forEach((el, i) => {
        el.classList.remove('active', 'completed');
        if (i + 1 < step) el.classList.add('completed');
        if (i + 1 === step) el.classList.add('active');
    });
}

btnToStep2.addEventListener('click', () => {
    if (selectedFiles.length === 0) return;
    goToStep(2);
});

btnToStep3.addEventListener('click', () => {
    const items = getSelectedScanItems();
    if (items.length === 0) {
        showToast('请至少选择一个检查项', 'error');
        return;
    }
    goToStep(3);
});

btnBackToStep1.addEventListener('click', () => goToStep(1));
btnBackToStep2.addEventListener('click', () => goToStep(2));

// ---- Submit Task ----
btnSubmit.addEventListener('click', submitTask);

async function submitTask() {
    const scanItems = getSelectedScanItems();
    if (selectedFiles.length === 0) { showToast('请上传文件', 'error'); return; }
    if (scanItems.length === 0) { showToast('请选择检查项', 'error'); return; }

    const fd = new FormData();
    selectedFiles.forEach(f => fd.append('file', f));
    fd.append('scan_items', scanItems.join(','));
    fd.append('strategy', selectedStrategy);
    fd.append('agent_mode', 'dual-agent');

    btnSubmit.disabled = true;
    document.getElementById('submitting-overlay').style.display = 'block';

    try {
        const resp = await fetch(`${API_BASE}/v1/tasks`, { method: 'POST', body: fd });
        const data = await resp.json();
        if (resp.ok && data.task_id) {
            showToast('任务创建成功', 'success');
            // Save to local history
            saveTaskToHistory(data.task_id);
            setTimeout(() => {
                window.location.href = `task.html?task_id=${data.task_id}`;
            }, 500);
        } else {
            showToast(data.message || '任务创建失败', 'error');
            btnSubmit.disabled = false;
            document.getElementById('submitting-overlay').style.display = 'none';
        }
    } catch (err) {
        showToast('网络请求失败: ' + err.message, 'error');
        btnSubmit.disabled = false;
        document.getElementById('submitting-overlay').style.display = 'none';
    }
}

// ---- Local History ----
function saveTaskToHistory(taskId) {
    const history = JSON.parse(localStorage.getItem('taskHistory') || '[]');
    history.unshift({
        task_id: taskId,
        create_time: new Date().toLocaleString('zh-CN'),
        strategy: selectedStrategy,
        files: selectedFiles.map(f => f.name),
    });
    // Keep last 100 tasks
    localStorage.setItem('taskHistory', JSON.stringify(history.slice(0, 100)));
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
