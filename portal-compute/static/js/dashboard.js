/* ============================================================================
   ArenaLake Dashboard JavaScript - Main Interface Logic
   ============================================================================
   This module implements all client-side dashboard functionality.
   Responsibilities:
   - Tab switching and UI state management
   - Real-time metrics collection (CPU, RAM) via polling
   - Data catalog browsing and file preview
   - File upload to MinIO data lake
   - Spark cluster monitoring and job progress tracking
   - Chart visualization with Chart.js
   ============================================================================ */

// Configuration passed from Jinja2 template (username and domain)
const dashboardConfig = window.dashboardConfig || { usuario: 'usuario', domain: 'localhost' };
const usuario = dashboardConfig.usuario;

// Interval handle for metrics polling (CPU/RAM updates)
let metricsInterval;

// Chart.js instances for CPU and RAM history graphs
let ramChart, cpuChart;

// Chart configuration
const maxDataPoints = 20;  // Keep last 20 data points in history
const chartOptions = {
    responsive: true,
    animation: false,  // Disable animation for real-time updates
    scales: {
        x: { display: false },  // Hide X-axis labels (timestamps)
        y: { beginAtZero: true, grid: { color: '#30363d' }, ticks: { color: '#8b949e' } }
    },
    plugins: { legend: { labels: { color: 'white' } } }
};

/* ============================================================================
   UI Navigation - Tab and Sidebar Management
   ============================================================================ */

/**
 * Toggle sidebar collapse/expand state
 * Animates width change and hides text labels when collapsed
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
}

/**
 * Initialize Chart.js instances for CPU and RAM history
 * Only initializes if charts don't already exist (prevents duplicates)
 */
function initCharts() {
    if (ramChart) return;  // Already initialized

    // RAM usage history chart (blue line)
    const ctxRam = document.getElementById('ramChart').getContext('2d');
    ramChart = new Chart(ctxRam, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Histórico de RAM (MB)',
                data: [],
                borderColor: '#58a6ff',  // Blue
                backgroundColor: 'rgba(88, 166, 255, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: chartOptions
    });

    // CPU usage history chart (green line)
    const ctxCpu = document.getElementById('cpuChart').getContext('2d');
    cpuChart = new Chart(ctxCpu, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Histórico de CPU (%)',
                data: [],
                borderColor: '#2ea043',  // Green
                backgroundColor: 'rgba(46, 160, 67, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: chartOptions
    });
}

/**
 * Switch active tab and show corresponding content
 * @param {string} tabId - ID of tab to activate (workspace, data, compute, spark)
 * @param {Element} element - The menu item that was clicked
 */
function switchTab(tabId, element) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    // Remove active class from all menu items
    document.querySelectorAll('.menu-item').forEach(item => item.classList.remove('active'));

    // Show selected tab and mark menu item as active
    document.getElementById(tabId).classList.add('active');
    element.classList.add('active');
    closePanel();  // Close file preview panel if open

    // Load data when switching to specific tabs
    if (tabId === 'data') loadCatalog();
    if (tabId === 'compute') initCharts();
}

/* ============================================================================
   DATA CATALOG - MinIO bucket browsing and file management
   ============================================================================ */

// Global cache of catalog data to avoid repeated API calls
let globalCatalogData = {};

/**
 * Fetch complete data catalog from MinIO/S3
 * Populates bucket dropdown and renders file table
 */
async function loadCatalog() {
    try {
        const res = await fetch('/api/catalog');
        const data = await res.json();
        if (data.status === 'success') {
            globalCatalogData = data.data;  // Cache data
            updateFolderDropdown();
            renderCatalogTable();
        }
    } catch (e) {
        // Show error message in table if catalog fetch fails
        document.querySelector('#catalogTable tbody').innerHTML = '<tr><td colspan="3" style="text-align:center; color:red;">Erro ao conectar no MinIO.</td></tr>';
    }
}

/**
 * Handle bucket selection change
 * Triggers folder dropdown update and table re-render
 */
function onBucketChange() {
    updateFolderDropdown();
    renderCatalogTable();
}

/**
 * Update folder dropdown based on selected bucket
 * Extracts folder names from file paths and builds dropdown options
 */
function updateFolderDropdown() {
    const bucket = document.getElementById('bucketSelect').value;
    const folderSelect = document.getElementById('folderSelect');
    const files = globalCatalogData[bucket] || [];

    // Extract unique folder names from file paths
    let folders = new Set();
    files.forEach(f => {
        if (f.includes('/')) {
            const pastaPai = f.split('/')[0];
            folders.add(pastaPai);
        }
    });

    // Build dropdown options: root + all folders
    let optionsHtml = '<option value="/">📁 (Raiz - Arquivos Soltos)</option>';
    folders.forEach(folder => {
        optionsHtml += `<option value="${folder}">📁 ${folder}</option>`;
    });

    folderSelect.innerHTML = optionsHtml;
}

/**
 * Render file catalog table based on selected bucket and folder
 * Groups Spark datasets (parquet files) separately from loose files
 */
function renderCatalogTable() {
    const bucket = document.getElementById('bucketSelect').value;
    const selectedFolder = document.getElementById('folderSelect').value;
    const files = globalCatalogData[bucket] || [];
    let tbody = '';

    // Track datasets to avoid duplicates (Spark creates multiple part-* files per dataset)
    let displayedDatasets = new Set();
    let filteredFiles = [];

    // Filter files based on selected folder
    files.forEach(f => {
        if (selectedFolder === '/') {
            // Root folder: show only loose files (no slash in path)
            if (!f.includes('/')) {
                filteredFiles.push({ name: f, display: f });
            }
        } else {
            // Subfolder: show files in this folder only
            if (f.startsWith(selectedFolder + '/')) {
                let subPath = f.substring(selectedFolder.length + 1);

                // Check if this is a Spark dataset (contains part-* or .parquet)
                if (subPath.includes('part-') || subPath.endsWith('.parquet')) {
                    let datasetName = subPath.split('/')[0];
                    let datasetKey = `${selectedFolder}/${datasetName}`;
                    // Show dataset only once, even if it has multiple part files
                    if (!displayedDatasets.has(datasetKey)) {
                        displayedDatasets.add(datasetKey);
                        filteredFiles.push({ name: f, display: `📁 ${datasetName} (Dataset Spark)` });
                    }
                } else {
                    // Regular file
                    filteredFiles.push({ name: f, display: subPath });
                }
            }
        }
    });

    // Build table rows
    if (filteredFiles.length > 0) {
        filteredFiles.forEach(item => {
            tbody += `<tr>
                <td>${bucket}</td>
                <td><span class="file-link" onclick="openPreview('${bucket}', '${item.name}')">${item.display}</span></td>
                <td><span style="font-size:0.8em; padding:3px 8px; background:#21262d; border-radius:3px;">Pronto</span></td>
            </tr>`;
        });
    } else {
        tbody = '<tr><td colspan="3" style="text-align:center; color:#8b949e;">Nenhum arquivo ou tabela encontrado nesta pasta.</td></tr>';
    }

    document.querySelector('#catalogTable tbody').innerHTML = tbody;
}

/**
 * Upload file to MinIO data lake
 * Sends file to backend with bucket and username metadata
 */
async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const bucket = document.getElementById('bucketSelect').value;
    if (fileInput.files.length === 0) return alert('Selecione um arquivo primeiro!');

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('bucket', bucket);
    formData.append('usuario', usuario);

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const result = await res.json();
        if (result.status === 'success') {
            fileInput.value = '';  // Clear input
            loadCatalog();  // Refresh catalog display
        } else {
            alert('Erro: ' + result.message);
        }
    } catch (e) {
        alert('Erro ao enviar arquivo.');
    }
}

/* ============================================================================
   FILE PREVIEW - Side panel for file details and content preview
   ============================================================================ */

/**
 * Open file preview panel showing file details and content
 * @param {string} bucket - MinIO bucket name
 * @param {string} filename - File path in bucket
 */
async function openPreview(bucket, filename) {
    // Show side panel and set filename
    document.getElementById('sidePanel').classList.add('open');
    document.getElementById('spFilename').innerText = filename;
    document.getElementById('spContent').innerHTML = "<div style='color:#8b949e'>Gerando visualização e extraindo metadados...</div>";

    try {
        // Fetch preview data from backend
        const res = await fetch(`/api/preview/${bucket}/${filename}`);
        const result = await res.json();

        if (result.status === 'success') {
            // Display file metadata
            document.getElementById('spDate').innerText = result.data.last_modified;
            document.getElementById('spSize').innerText = result.data.size;
            document.getElementById('spUploader').innerText = result.data.uploader;

            // Display preview content based on file type
            let contentHtml = '';
            if (result.data.type === 'image') {
                contentHtml = `<img src="${result.data.preview_content}" class="preview-img">`;
            } else if (result.data.type === 'table') {
                // HTML table for CSV/Parquet
                contentHtml = result.data.preview_content;
            } else if (result.data.type === 'text') {
                // Monospace text for text files
                contentHtml = `<div class="preview-txt">${result.data.preview_content}</div>`;
            } else {
                contentHtml = `<div style="color:#8b949e">${result.data.preview_content}</div>`;
            }

            document.getElementById('spContent').innerHTML = contentHtml;
        }
    } catch (e) {
        document.getElementById('spContent').innerHTML = "<div style='color:red'>Erro ao carregar preview.</div>";
    }
}

/**
 * Close file preview side panel
 */
function closePanel() {
    document.getElementById('sidePanel').classList.remove('open');
}

/* ============================================================================
   METRICS MONITORING - Real-time CPU and RAM usage tracking
   ============================================================================ */

/**
 * Fetch and update workspace metrics (CPU, RAM usage)
 * Called every 3 seconds to refresh dashboard metrics and charts
 * Updates both header bar and compute tab charts
 */
async function loadMetrics() {
    try {
        const res = await fetch(`/api/metrics/${usuario}`);
        const data = await res.json();

        // Get DOM elements for metric display
        const ramValEl = document.getElementById('ramValue');
        const ramPctEl = document.getElementById('ramPercent');
        const cpuValEl = document.getElementById('cpuValue');
        const wsCpuText = document.getElementById('wsCpuText');
        const wsCpuBar = document.getElementById('wsCpuBar');
        const wsRamText = document.getElementById('wsRamText');
        const wsRamBar = document.getElementById('wsRamBar');

        if (data.status === 'online') {
            // Workspace is running - update all metric displays
            if (ramValEl) ramValEl.innerText = `${data.memory_usage_mb} MB`;
            if (ramPctEl) ramPctEl.innerText = `${data.memory_percent}% de ${data.memory_limit_mb}MB`;
            if (cpuValEl) cpuValEl.innerText = `${data.cpu_percent} %`;

            // Update workspace top bar metrics
            if (wsCpuText) wsCpuText.innerText = `${data.cpu_percent}%`;
            if (wsCpuBar) wsCpuBar.style.width = `${Math.min(data.cpu_percent, 100)}%`;
            if (wsRamText) wsRamText.innerText = `${data.memory_percent}%`;
            if (wsRamBar) wsRamBar.style.width = `${Math.min(data.memory_percent, 100)}%`;

            // Get current time for chart labels
            const now = new Date().toLocaleTimeString();

            // Update RAM chart if initialized
            if (typeof ramChart !== 'undefined' && ramChart) {
                ramChart.data.labels.push(now);
                ramChart.data.datasets[0].data.push(data.memory_usage_mb);
                // Keep only last N data points to prevent memory bloat
                if (ramChart.data.labels.length > maxDataPoints) {
                    ramChart.data.labels.shift();
                    ramChart.data.datasets[0].data.shift();
                }
                ramChart.update();
            }

            // Update CPU chart if initialized
            if (typeof cpuChart !== 'undefined' && cpuChart) {
                cpuChart.data.labels.push(now);
                cpuChart.data.datasets[0].data.push(data.cpu_percent);
                // Keep only last N data points
                if (cpuChart.data.labels.length > maxDataPoints) {
                    cpuChart.data.labels.shift();
                    cpuChart.data.datasets[0].data.shift();
                }
                cpuChart.update();
            }
        } else {
            // Workspace is offline - show offline state
            if (ramValEl) ramValEl.innerText = 'Offline';
            if (cpuValEl) cpuValEl.innerText = 'Offline';
            if (wsCpuText) wsCpuText.innerText = '--%';
            if (wsCpuBar) wsCpuBar.style.width = '0%';
            if (wsRamText) wsRamText.innerText = '--%';
            if (wsRamBar) wsRamBar.style.width = '0%';
        }
    } catch (e) {
        console.error('Erro ao buscar métricas');
    }
}

/**
 * Format duration in milliseconds to human-readable string
 * @param {number} ms - Duration in milliseconds
 * @returns {string} Formatted duration (e.g., "5.2 s", "1.5 min")
 */
function formatDuration(ms) {
    if (!ms) return '0 s';
    const seconds = ms / 1000;
    if (seconds < 60) return seconds.toFixed(1) + ' s';
    return (seconds / 60).toFixed(1) + ' min';
}

const tableStyle = 'width: 100%; text-align: left; border-collapse: collapse;';
const thStyle = 'border-bottom: 1px solid #30363d; padding-bottom: 8px; color: #8b949e; font-weight: normal;';
const tdStyle = 'padding: 10px 0; border-bottom: 1px solid #21262d;';

let expandedAppId = null;

async function updateSparkDashboard() {
    try {
        const res = await fetch('/api/spark/status');
        const data = await res.json();

        if (data.status !== 'success') return;

        let workersHtml = '';
        if (data.workers && data.workers.length === 0) {
            workersHtml = '<span style="color: #8b949e;">Nenhum worker alocado/ativo no momento.</span>';
        } else {
            data.workers.forEach(w => {
                workersHtml += `
                    <div style="margin-bottom: 5px;">
                        <span style="color: #c9d1d9;"><strong>ID:</strong> ${w.id}</span><br>
                        <span style="color: #8b949e;"><strong>Host:</strong> ${w.host}:${w.port}</span> | 
                        <span style="color: #8b949e;"><strong>Cores:</strong> ${w.coresused} / ${w.cores}</span> | 
                        <span style="color: #8b949e;"><strong>Memória:</strong> ${w.memoryused} / ${w.memory} MB</span>
                    </div>`;
            });
        }
        document.getElementById('spark-workers-content').innerHTML = workersHtml;

        let activeHtml = '';
        if (data.active_apps && data.active_apps.length === 0) {
            activeHtml = '<span style="color: #8b949e;">Nenhuma aplicação rodando no momento. Inicie um processo no seu Jupyter.</span>';
            expandedAppId = null;
        } else {
            activeHtml = `<table style="${tableStyle}">
                    <tr><th style="${thStyle}">Nome do Job</th><th style="${thStyle}">Usuário</th><th style="${thStyle}">Cores Usados</th><th style="${thStyle}">Memória/Nó</th><th style="${thStyle}">Duração</th></tr>`;

            data.active_apps.forEach(app => {
                let isExpanded = (expandedAppId === app.id);
                let displayState = isExpanded ? 'table-row' : 'none';
                let bgHover = isExpanded ? '#21262d' : 'transparent';
                let seta = isExpanded ? '▼' : '▶';

                activeHtml += `<tr style="cursor: pointer; background: ${bgHover}; transition: 0.2s;" 
                           onclick="toggleAppDetails('${app.id}')" 
                           onmouseover="this.style.background='#21262d'" 
                           onmouseout="this.style.background='${isExpanded ? '#21262d' : 'transparent'}'">
                    <td style="${tdStyle} color: #58a6ff; font-weight: bold;">${seta} ${app.name}</td>
                    <td style="${tdStyle} color: #c9d1d9;">${app.user}</td>
                    <td style="${tdStyle} color: #c9d1d9;">${app.cores}</td>
                    <td style="${tdStyle} color: #c9d1d9;">${app.memoryperslave} MB</td>
                    <td style="${tdStyle} color: #c9d1d9;">⏳ ${formatDuration(app.duration)}</td>
                </tr>`;

                activeHtml += `<tr id="details-${app.id}" style="display: ${displayState}; background: #0d1117;">
                     <td colspan="5" style="padding: 15px; border-bottom: 1px solid #30363d;" id="content-${app.id}">
                        <span style="color: #8b949e;">Buscando métricas de paralelismo em tempo real...</span>
                     </td>
                   </tr>`;
            });
            activeHtml += `</table>`;
        }
        document.getElementById('spark-active-apps').innerHTML = activeHtml;

        if (expandedAppId) {
            refreshJobProgress(expandedAppId);
        }

        let completedHtml = '';
        if (data.completed_apps && data.completed_apps.length === 0) {
            completedHtml = '<span style="color: #8b949e;">Nenhum histórico recente de execuções.</span>';
        } else {
            completedHtml = `<table style="${tableStyle}">
                    <tr><th style="${thStyle}">Nome do Job</th><th style="${thStyle}">Usuário</th><th style="${thStyle}">Estado</th><th style="${thStyle}">Duração</th></tr>`;
            data.completed_apps.forEach(app => {
                let stateColor = app.state === 'FINISHED' ? '#3fb950' : (app.state === 'FAILED' || app.state === 'KILLED' ? '#f85149' : '#d29922');
                completedHtml += `<tr>
                            <td style="${tdStyle} color: #c9d1d9;">${app.name}</td>
                            <td style="${tdStyle} color: #c9d1d9;">${app.user}</td>
                            <td style="${tdStyle} font-weight: bold; color: ${stateColor};">${app.state}</td>
                            <td style="${tdStyle} color: #c9d1d9;">⏱️ ${formatDuration(app.duration)}</td>
                        </tr>`;
            });
            completedHtml += `</table>`;
        }
        document.getElementById('spark-completed-apps').innerHTML = completedHtml;

    } catch (error) {
        console.error('Erro na engine do dashboard:', error);
    }
}

function toggleAppDetails(appId) {
    if (expandedAppId === appId) {
        expandedAppId = null;
        updateSparkDashboard();
    } else {
        expandedAppId = appId;
        updateSparkDashboard();
    }
}

async function refreshJobProgress(appId) {
    const contentDiv = document.getElementById(`content-${appId}`);
    if (!contentDiv) return;

    try {
        const res = await fetch(`/api/spark/app/${appId}/jobs`);
        const data = await res.json();

        if (data.status !== 'success') {
            contentDiv.innerHTML = `<span style="color:#f85149">❌ Falha ao buscar métricas: ${data.message}</span>`;
            return;
        }

        if (!data.jobs || data.jobs.length === 0) {
            contentDiv.innerHTML = '<span style="color:#8b949e">Aguardando início de processamento... Execute uma ação (como .show() ou .write) no Jupyter!</span>';
            return;
        }

        let jobsHtml = '<div style="display: flex; flex-direction: column; gap: 12px; margin-top: 5px;">';

        const sortedJobs = data.jobs.sort((a, b) => b.jobId - a.jobId);

        sortedJobs.forEach(job => {
            const total = job.numTasks || 1;
            const completed = job.numCompletedTasks || 0;
            const active = job.numActiveTasks || 0;

            const percComp = (completed / total) * 100;
            const percAct = (active / total) * 100;

            const statusColor = job.status === 'SUCCEEDED' ? '#3fb950' : (job.status === 'RUNNING' ? '#58a6ff' : '#8b949e');

            jobsHtml += `
                <div style="background: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong style="color: #c9d1d9; font-size: 13px;">Job ID ${job.jobId} 
                            <span style="color: ${statusColor}; font-size: 11px; margin-left: 8px; border: 1px solid ${statusColor}40; padding: 2px 6px; border-radius: 10px;">${job.status}</span>
                        </strong>
                        <span style="font-size: 12px; color: #8b949e;">${completed}/${total} Tasks Completas</span>
                    </div>
                    
                    <div style="font-size: 12px; color: #8b949e; margin-bottom: 10px; font-family: monospace;">${job.name}</div>
                    
                    <div style="background: #0d1117; border-radius: 4px; width: 100%; height: 14px; overflow: hidden; display: flex; border: 1px solid #30363d;">
                        <div style="background: #3fb950; width: ${percComp}%; height: 100%; transition: width 0.5s ease-in-out;" title="Completas"></div>
                        <div style="background: #58a6ff; width: ${percAct}%; height: 100%; transition: width 0.5s ease-in-out;" title="Processando"></div>
                    </div>
                </div>
            `;
        });

        jobsHtml += '</div>';
        contentDiv.innerHTML = jobsHtml;

    } catch (error) {
        contentDiv.innerHTML = '<span style="color:#f85149">Erro ao processar as métricas na tela.</span>';
    }
}

/* ============================================================================
   Application Initialization - Start polling and dashboard updates
   ============================================================================ */

document.addEventListener('DOMContentLoaded', () => {
    // Load and poll workspace metrics every 3 seconds
    loadMetrics();
    metricsInterval = setInterval(loadMetrics, 3000);

    // Update Spark dashboard every 2.5 seconds
    updateSparkDashboard();
    setInterval(updateSparkDashboard, 2500);
});

// ==============================================================
// ARENALAKE SCHEDULER - LÓGICA DE EXECUÇÃO DE JOBS
// ==============================================================

async function loadSchedulerData() {
    try {
        const res = await fetch('/api/jobs');
        const data = await res.json();

        if (data.status !== 'success') return;

        // 1. Renderiza Scripts Disponíveis
        let scriptsHtml = '';
        if (data.scripts.length === 0) {
            scriptsHtml = '<p style="color: #8b949e; font-style: italic;">Nenhum script .py encontrado na pasta /jobs do host.</p>';
        } else {
            data.scripts.forEach(script => {
                scriptsHtml += `
                <div style="display: flex; justify-content: space-between; align-items: center; background: #0d1117; padding: 12px; margin-bottom: 8px; border-radius: 6px; border: 1px solid #30363d;">
                    <span style="color: #c9d1d9; font-family: monospace; font-size: 14px;">${script}</span>
                    <div>
                        <button onclick="runJobNow('${script}')" class="btn" style="background: #238636; border: none; padding: 6px 12px; font-size: 12px; margin-right: 5px;">▶️ Rodar Agora</button>
                        <button onclick="promptScheduleJob('${script}')" class="btn" style="background: #1f6feb; border: none; padding: 6px 12px; font-size: 12px;">⏰ Agendar (Cron)</button>
                    </div>
                </div>`;
            });
        }
        document.getElementById('available-scripts-list').innerHTML = scriptsHtml;

        // 2. Renderiza Agendamentos Ativos
        let schedHtml = '';
        if (data.scheduled.length === 0) {
            schedHtml = '<p style="color: #8b949e; font-style: italic;">Nenhum job agendado no momento.</p>';
        } else {
            data.scheduled.forEach(job => {
                schedHtml += `
                <div style="display: flex; justify-content: space-between; align-items: center; background: #0d1117; padding: 12px; margin-bottom: 8px; border-radius: 6px; border: 1px solid #30363d;">
                    <div>
                        <div style="color: #c9d1d9; font-weight: bold;">${job.name}</div>
                        <div style="color: #8b949e; font-size: 12px; margin-top: 4px;">Próxima execução: <span style="color: #e6edf3;">${job.next_run}</span></div>
                    </div>
                    <button onclick="cancelSchedule('${job.id}')" class="btn" style="background: #da3633; border: none; padding: 6px 12px; font-size: 12px;">❌ Cancelar</button>
                </div>`;
            });
        }
        document.getElementById('scheduled-jobs-list').innerHTML = schedHtml;

    } catch (e) {
        console.error("Erro ao carregar dados do scheduler:", e);
    }
}

async function runJobNow(scriptName) {
    if (!confirm(`Deseja enviar o script "${scriptName}" agora para processamento no cluster Spark?`)) return;

    try {
        const res = await fetch(`/api/jobs/run/${scriptName}`, { method: 'POST' });
        const data = await res.json();
        alert(data.message);

        // Se disparar com sucesso, manda o usuário pra aba "Spark Process" pra ver as barras carregando!
        if (data.status === 'success') {
            document.querySelectorAll('.menu-item')[4].click();
        }
    } catch (e) {
        alert("Erro fatal ao tentar executar o script.");
    }
}

async function promptScheduleJob(scriptName) {
    const cron = prompt(`⏰ Agendar: ${scriptName}\n\nDigite a expressão Cron.\nExemplo: "0 2 * * *" (Todo dia às 02:00 da manhã)`, "0 2 * * *");
    if (!cron) return;

    const formData = new FormData();
    formData.append('job_name', scriptName);
    formData.append('cron_expr', cron);

    try {
        const res = await fetch(`/api/jobs/schedule`, { method: 'POST', body: formData });
        const data = await res.json();
        alert(data.message);
        loadSchedulerData();
    } catch (e) {
        alert("Erro ao tentar agendar o script.");
    }
}

async function cancelSchedule(jobId) {
    if (!confirm("Deseja realmente cancelar este agendamento? Ele não rodará mais automaticamente.")) return;

    try {
        const res = await fetch(`/api/jobs/schedule/${jobId}`, { method: 'DELETE' });
        const data = await res.json();
        loadSchedulerData();
    } catch (e) {
        alert("Erro ao tentar cancelar o agendamento.");
    }
}

// Carrega os dados na inicialização
loadSchedulerData();

// Adiciona um listener para dar auto-refresh suave quando o usuário estiver na aba do Scheduler
setInterval(() => {
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab && activeTab.id === 'scheduler') {
        loadSchedulerData();
    }
}, 10000); // Atualiza a cada 10 segundos