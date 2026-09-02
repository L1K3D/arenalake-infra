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
let biGridInicializado = false;
let biGrid = null;

function switchTab(tabId, element) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.menu-item').forEach(item => item.classList.remove('active'));

    document.getElementById(tabId).classList.add('active');
    element.classList.add('active');
    closePanel();

    if (tabId === 'data') loadCatalog();
    if (tabId === 'compute') initCharts();

    // NOVA LÓGICA DO BI:
    if (tabId === 'bi' && !biGridInicializado) {
        biGrid = GridStack.init({
            cellHeight: 120,
            margin: 10,
            resizable: { handles: 'e, se, s, sw, w' }
        }, '.grid-stack');
        biGridInicializado = true;
    }
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

            atualizarListaDatasetsBI();
        }
    } catch (e) {
        // Show error message in table if catalog fetch fails
        document.querySelector('#catalogTable tbody').innerHTML = '<tr><td colspan="3" style="text-align:center; color:red;">Error connecting to MinIO.</td></tr>';
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
    if (fileInput.files.length === 0) return alert('Select a file first!');

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('bucket', bucket);
    formData.append('usuario', usuario);

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const result = await res.json();
        if (result.status === 'success') {
            fileInput.value = '';
            loadCatalog();
        } else {
            alert('Error: ' + result.message);
        }
    } catch (e) {
        alert('Error uploading the file.');
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
    document.getElementById('spContent').innerHTML = "<div style='color:#8b949e'>Generating preview and extracting metadata...</div>";
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
        document.getElementById('spContent').innerHTML = "<div style='color:red'>Error loading preview.</div>";
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
            if (ramValEl) ramValEl.innerText = `${data.memory_usage_mb} MB`;
            if (ramPctEl) ramPctEl.innerText = `${data.memory_percent}% of ${data.memory_limit_mb}MB`;
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
            workersHtml = '<span style="color: #8b949e;">No worker allocated/active at the moment.</span>';
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
            activeHtml = '<span style="color: #8b949e;">No application is running right now. Start a process in your Jupyter session.</span>';
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
            completedHtml = '<span style="color: #8b949e;">No recent execution history.</span>';
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
            contentDiv.innerHTML = `<span style="color:#f85149">❌ Failed to fetch metrics: ${data.message}</span>`;
            return;
        }

        if (!data.jobs || data.jobs.length === 0) {
            contentDiv.innerHTML = '<span style="color:#8b949e">Waiting for processing to begin... Run an action in Jupyter (such as .show() or .write).</span>';
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
                        <span style="font-size: 12px; color: #8b949e;">${completed}/${total} Completed Tasks</span>
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
            scriptsHtml = '<p style="color: #8b949e; font-style: italic;">No .py scripts found in the host /jobs folder.</p>';
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
            schedHtml = '<p style="color: #8b949e; font-style: italic;">No jobs scheduled at the moment.</p>';
        } else {
            data.scheduled.forEach(job => {
                schedHtml += `
                <div style="display: flex; justify-content: space-between; align-items: center; background: #0d1117; padding: 12px; margin-bottom: 8px; border-radius: 6px; border: 1px solid #30363d;">
                    <div>
                        <div style="color: #c9d1d9; font-weight: bold;">${job.name}</div>
                        <div style="color: #8b949e; font-size: 12px; margin-top: 4px;">Next run: <span style="color: #e6edf3;">${job.next_run}</span></div>
                    </div>
                    <button onclick="cancelSchedule('${job.id}')" class="btn" style="background: #da3633; border: none; padding: 6px 12px; font-size: 12px;">❌ Cancel</button>
                </div>`;
            });
        }
        document.getElementById('scheduled-jobs-list').innerHTML = schedHtml;

    } catch (e) {
        console.error("Erro ao carregar dados do scheduler:", e);
    }
}

async function runJobNow(scriptName) {
    if (!confirm(`Do you want to send the script "${scriptName}" to the Spark cluster now?`)) return;

    try {
        const res = await fetch(`/api/jobs/run/${scriptName}`, { method: 'POST' });
        const data = await res.json();
        alert(data.message);

        if (data.status === 'success') {
            document.querySelectorAll('.menu-item')[4].click();
        }
    } catch (e) {
        alert("Fatal error while trying to execute the script.");
    }
}

async function promptScheduleJob(scriptName) {
    const cron = prompt(`⏰ Schedule: ${scriptName}\n\nEnter the Cron expression.\nExample: "0 2 * * *" (Every day at 02:00)`, "0 2 * * *");
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
        alert("Error while trying to schedule the script.");
    }
}

async function cancelSchedule(jobId) {
    if (!confirm("Do you really want to cancel this schedule? It will no longer run automatically.")) return;

    try {
        const res = await fetch(`/api/jobs/schedule/${jobId}`, { method: 'DELETE' });
        const data = await res.json();
        loadSchedulerData();
    } catch (e) {
        alert("Error while trying to cancel the schedule.");
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

// ==============================================================
// ARENALAKE BI TOOLS - LÓGICA DO DASHBOARD
// ==============================================================

function abrirModalVisual() {
    const tabela = document.getElementById('biDatasetSelector').value;
    if (!tabela) {
        alert("Por favor, selecione uma Tabela/Dataset primeiro!");
        return;
    }
    document.getElementById('biModal').style.display = 'flex';
}

function fecharModalVisual() {
    document.getElementById('biModal').style.display = 'none';
}

async function confirmarNovoVisual() {
    const selector = document.getElementById('biDatasetSelector').value;
    const tipo = document.getElementById('biTipoGrafico').value;
    const eixoX = document.getElementById('biEixoX').value;
    const eixoY = document.getElementById('biEixoY').value;
    const eixoZ = document.getElementById('biEixoZ').value;
    const agregacao = document.getElementById('biAgregacao').value;

    // CAPTURA AS NOVAS VARIÁVEIS DA TABELA
    const tema = document.getElementById('biTemaTabela').value;
    const ordenarPor = document.getElementById('biOrdenarPor').value;
    const ordem = document.getElementById('biOrdem').value;
    const limiteLinhas = parseInt(document.getElementById('biLimiteLinhas').value) || 100;
    const colunasSelecionadas = Array.from(document.getElementById('biColunasTabela').selectedOptions).map(opt => opt.value);

    if (!selector) return alert("Select a table.");

    if (tipo === 'table' && colunasSelecionadas.length === 0) return alert("Select at least 1 column for the table.");
    if (tipo === 'kpi' && !eixoY) return alert("Select the metric (Y Axis).");
    if (tipo !== 'table' && tipo !== 'kpi' && (!eixoX || !eixoY)) return alert("Select the X and Y axes.");

    const [bucket, filename] = selector.split('|');
    fecharModalVisual();

    try {
        const res = await fetch('/api/bi/gerar_dados', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bucket, filename, eixo_x: eixoX, eixo_y: eixoY, eixo_z: eixoZ,
                agregacao, tipo_grafico: tipo, colunas_tabela: colunasSelecionadas,
                tema: tema, ordenar_por: ordenarPor, ordem: ordem, limite_linhas: limiteLinhas,
                filtro_coluna: window.globalFiltroColuna, filtro_valor: window.globalFiltroValor
            })
        });
        const result = await res.json();
        const config = { bucket, filename, eixo_x: eixoX, eixo_y: eixoY, eixo_z: eixoZ, agregacao, tipo, colunas_tabela: colunasSelecionadas, tema, ordenar_por: ordenarPor, ordem, limite_linhas: limiteLinhas };

        if (result.status === 'success') {
            const idUnico = 'chart_' + Math.random().toString(36).substr(2, 9);

            // LÓGICA INTELIGENTE DE TÍTULO
            let titulo = '';
            if (tipo === 'table' || tipo === 'matrix') titulo = 'Tabela de Dados';
            else if (tipo === 'kpi') titulo = `Indicador: ${agregacao.toUpperCase()} de ${eixoY}`;
            else titulo = `${agregacao.toUpperCase()} de ${eixoY} por ${eixoX}`;

            // Salvamos as configurações escolhidas
            const config = { bucket, filename, eixo_x: eixoX, eixo_y: eixoY, eixo_z: eixoZ, agregacao, tipo, colunas_tabela: colunasSelecionadas, tema: tema, ordenar_por: ordenarPor, ordem, limite_linhas: limiteLinhas };
            adicionarGraficoGrid(idUnico, titulo, tipo, result.data, config);
        } else {
            alert("Error processing the data: " + result.message);
        }
    } catch (e) {
        alert("Error connecting to the analytical engine.");
    }
}

// Criamos uma função separada para gerar a Option do Echarts, facilitando o re-uso na edição
function getEchartsOption(tipo, dados) {
    let option = {
        tooltip: { trigger: 'axis' },
        color: ['#10b981', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6'], // Paleta da sua imagem
        xAxis: { type: 'category', data: dados.categorias },
        yAxis: { type: 'value' },
        series: []
    };

    // A Mágica: Stacked Bar = Eixos Invertidos (Horizontal). Stacked Column cai no normal (Vertical).
    if (tipo === 'stacked_bar') {
        option.xAxis = { type: 'value' };
        option.yAxis = { type: 'category', data: dados.categorias };
    }

    if (dados.is_stacked) {
        option.legend = { textStyle: { color: '#c9d1d9' }, bottom: 0 };
        dados.series.forEach(serie => {
            option.series.push({
                name: serie.name,
                data: serie.data,
                type: 'bar',
                stack: 'total',
                emphasis: { focus: 'series' }
            });
        });
    } else {
        if (tipo === 'pie') {
            option.xAxis = null; option.yAxis = null;
            option.series = [{
                type: 'pie', radius: '70%',
                data: dados.categorias.map((cat, i) => ({ name: cat, value: dados.valores[i] }))
            }];
        } else if (tipo === 'funnel') {
            // TRATAMENTO PARA O GRÁFICO DE FUNIL
            option.xAxis = null; option.yAxis = null;
            option.series = [{
                type: 'funnel',
                left: '10%',
                top: '10%',
                bottom: '10%',
                width: '80%',
                min: 0,
                max: Math.max(...dados.valores, 100),
                minSize: '0%',
                maxSize: '100%',
                sort: 'descending',
                gap: 2,
                label: { show: true, position: 'inside', color: '#fff' },
                data: dados.categorias.map((cat, i) => ({ name: cat, value: dados.valores[i] }))
            }];
        } else if (tipo === 'scatter') {
            return {
                tooltip: {
                    trigger: 'item',
                    backgroundColor: 'rgba(13, 17, 23, 0.9)',
                    borderColor: '#30363d',
                    textStyle: { color: '#c9d1d9' },
                    formatter: function (param) {
                        return `<div style="font-weight:bold;margin-bottom:5px;">${param.seriesName}</div>
                            <span style="display:inline-block;margin-right:5px;border-radius:10px;width:9px;height:9px;background-color:${param.color};"></span> X: ${param.data[0]}<br/>
                            <span style="display:inline-block;margin-right:5px;border-radius:10px;width:9px;height:9px;background-color:${param.color};"></span> Y: ${param.data[1]}`;
                    }
                },
                legend: dados.has_z ? { textStyle: { color: '#c9d1d9' }, top: 10 } : null,
                xAxis: {
                    type: 'value',
                    name: 'Eixo X', // Você pode injetar config.eixo_x aqui se passar a config pra função
                    splitLine: { lineStyle: { color: '#30363d', type: 'dashed' } }
                },
                yAxis: {
                    type: 'value',
                    name: 'Eixo Y',
                    splitLine: { lineStyle: { color: '#30363d', type: 'dashed' } }
                },
                grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
                series: dados.series.map(s => ({
                    name: s.name,
                    type: 'scatter',
                    data: s.data,
                    symbolSize: 12, // Tamanho da bolinha
                    itemStyle: { opacity: 0.8 } // Leve transparência para pontos sobrepostos
                }))
            };
        } else if (tipo === 'doughnut') {
            // Prepara os dados no formato {name: 'Categoria', value: 10} que a Rosca exige
            let chartData = dados.categorias.map((cat, idx) => ({
                name: cat,
                value: dados.valores[idx]
            }));

            return {
                tooltip: {
                    trigger: 'item',
                    backgroundColor: 'rgba(13, 17, 23, 0.9)',
                    borderColor: '#30363d',
                    textStyle: { color: '#c9d1d9' }
                },
                legend: {
                    top: 10,
                    textStyle: { color: '#c9d1d9' }
                },
                series: [{
                    name: 'Valores',
                    type: 'pie',
                    // O SEGREDO ESTÁ AQUI: O primeiro valor é o buraco interno, o segundo é o tamanho total
                    radius: ['45%', '70%'],
                    avoidLabelOverlap: false,
                    itemStyle: {
                        borderRadius: 5, // Borda arredondada nas fatias (Visual Premium)
                        borderColor: '#0d1117', // Cria um "vão" entre as fatias da mesma cor do fundo
                        borderWidth: 2
                    },
                    label: {
                        show: false,
                        position: 'center'
                    },
                    // Efeito PowerBI: Quando passa o mouse, o nome da fatia aparece no centro da rosca!
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: 18,
                            fontWeight: 'bold',
                            color: '#c9d1d9'
                        }
                    },
                    labelLine: { show: false },
                    data: chartData
                }]
            };
        } else if (tipo === 'waterfall') {
            // MATEMÁTICA DA CASCATA: Calcula a base invisível, os aumentos e as quedas
            let baseData = [];
            let posData = [];
            let negData = [];
            let currentSum = 0;

            dados.valores.forEach((val) => {
                let num = parseFloat(val) || 0;
                if (num >= 0) {
                    posData.push(num);
                    negData.push('-'); // '-' ignora a renderização da barra negativa
                    baseData.push(currentSum);
                    currentSum += num;
                } else {
                    posData.push('-');
                    negData.push(Math.abs(num)); // Deixa positivo para a barra desenhar pra baixo da base
                    currentSum += num;
                    baseData.push(currentSum); // A base desce para encontrar a barra vermelha
                }
            });

            return {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    backgroundColor: 'rgba(13, 17, 23, 0.9)',
                    borderColor: '#30363d',
                    textStyle: { color: '#c9d1d9' },
                    formatter: function (params) {
                        let tar = params[1].value !== '-' ? params[1] : params[2];
                        let formatterVal = new Intl.NumberFormat('pt-BR').format(tar.value);
                        return `<b>${tar.name}</b><br/>${tar.seriesName} : ${formatterVal}`;
                    }
                },
                legend: { data: ['Aumento', 'Queda'], textStyle: { color: '#c9d1d9' }, top: 10 },
                grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                xAxis: {
                    type: 'category',
                    data: dados.categorias,
                    axisLabel: { color: '#8b949e' },
                    splitLine: { show: false }
                },
                yAxis: {
                    type: 'value',
                    axisLabel: { color: '#8b949e' },
                    splitLine: { lineStyle: { color: '#30363d', type: 'dashed' } }
                },
                series: [
                    {
                        name: 'Base Invisível',
                        type: 'bar',
                        stack: 'Total',
                        itemStyle: { borderColor: 'transparent', color: 'transparent' },
                        emphasis: { itemStyle: { borderColor: 'transparent', color: 'transparent' } },
                        data: baseData
                    },
                    {
                        name: 'Aumento',
                        type: 'bar',
                        stack: 'Total',
                        itemStyle: { color: '#3fb950', borderRadius: [3, 3, 0, 0] }, // Verde do GitHub
                        data: posData
                    },
                    {
                        name: 'Queda',
                        type: 'bar',
                        stack: 'Total',
                        itemStyle: { color: '#f85149', borderRadius: [0, 0, 3, 3] }, // Vermelho do GitHub
                        data: negData
                    }
                ]
            };
        } else {
            let isArea = (tipo === 'area');
            option.series = [{
                data: dados.valores,
                type: isArea ? 'line' : (tipo === 'line' ? 'line' : 'bar'),
                areaStyle: isArea ? {} : undefined,
                itemStyle: { color: '#58a6ff' }
            }];
        }
    }
    return option;
}

window.biCharts = window.biCharts || {};

function adicionarGraficoGrid(id, titulo, tipo, dados, config) {
    let widgetHtml = `
        <div style="display: flex; flex-direction: column; height: 100%; width: 100%;">
            <div class="chart-header-bi">
                <span class="titulo-grafico">${titulo}</span>
                <div class="actions">
                    <span onclick="abrirModalEdicao('${id}')" title="Editar">✏️</span>
                    <span onclick="removerGraficoGrid(this, '${id}')" title="Excluir">🗑️</span>
                </div>
            </div>
            <div id="${id}" style="flex: 1; min-height: 0; width: 100%; overflow: hidden;"></div>
        </div>
    `;

    biGrid.addWidget({ w: 6, h: 3, content: widgetHtml });
    let containerDom = document.getElementById(id);

    // SE FOR TABELA OU MATRIZ, RENDERIZAMOS HTML PURO ESTILIZADO
    if (tipo === 'table' || tipo === 'matrix') {
        let htmlTable = `<div class="bi-table-container"><table class="bi-custom-table"><thead><tr>`;

        // Monta o cabeçalho
        if (tipo === 'table') {
            dados.colunas.forEach(col => { htmlTable += `<th>${col}</th>`; });
        } else {
            htmlTable += `<th>${dados.index_nome || 'Categoria'}</th>`;
            dados.colunas.forEach(col => { htmlTable += `<th>${col}</th>`; });
        }
        htmlTable += `</tr></thead><tbody>`;

        // Monta as linhas
        dados.linhas.forEach(row => {
            htmlTable += `<tr>`;
            row.forEach(cell => {
                let val = (typeof cell === 'number') ? cell.toLocaleString(undefined, { maximumFractionDigits: 2 }) : cell;
                htmlTable += `<td>${val}</td>`;
            });
            htmlTable += `</tr>`;
        });
        htmlTable += `</tbody></table></div>`;

        containerDom.innerHTML = htmlTable;

        // Salvamos os metadados para edição futura
        let dummyChartObj = { arenaConfig: config, getOption: () => ({ series: [] }), setOption: () => { } };
        window.biCharts[id] = dummyChartObj;
        return;
    } else if (tipo === 'kpi') {
        let formatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
        let valorFormatado = formatter.format(dados.valor);

        let corKpi = '#58a6ff'; // Azul padrão
        if (config.tema === 'green') corKpi = '#3fb950';
        if (config.tema === 'orange') corKpi = '#f59e0b';
        if (config.tema === 'padrao') corKpi = '#c9d1d9'; // Cinza claro

        // INJETANDO ESTILOS DIRETO NO HTML PARA GARANTIR O VISUAL PREMIUM
        let htmlKpi = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; width: 100%; text-align: center; box-sizing: border-box; padding: 10px;">
            <div style="font-size: 3.5rem; font-weight: 800; color: ${corKpi}; line-height: 1.1; text-shadow: 0px 4px 15px ${corKpi}40;">${valorFormatado}</div>
            <div style="font-size: 0.85rem; color: #8b949e; margin-top: 8px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: bold;">${config.agregacao} DE ${config.eixo_y}</div>
        </div>`;

        containerDom.innerHTML = htmlKpi;

        let dummyChartObj = { arenaConfig: config, getOption: () => ({ series: [] }), setOption: () => { } };
        window.biCharts[id] = dummyChartObj;
        return;
    }

    // CASO CONTRÁRIO, SEGUE A RENDERIZAÇÃO NORMAL DOS GRÁFICOS ECHARTS...
    let myChart = echarts.init(containerDom, 'dark', { backgroundColor: 'transparent' });
    myChart.arenaConfig = config;
    myChart.setOption(getEchartsOption(tipo, dados));

    window.biCharts[id] = myChart;
    setTimeout(() => { if (window.biCharts[id]) window.biCharts[id].resize(); }, 150);
    biGrid.on('resizestop', function () { Object.values(window.biCharts).forEach(c => c.resize()); });
}

function removerGraficoGrid(element, id) {
    biGrid.removeWidget(element.closest('.grid-stack-item'));
    if (window.biCharts[id]) delete window.biCharts[id];
}

// -------------------------------------------------------------------
// LÓGICA DE EDIÇÃO (CORES GRANULARES E TROCA DE MÉTRICAS)
// -------------------------------------------------------------------
let chartEmEdicao = null;

async function abrirModalEdicao(id) {
    chartEmEdicao = id;
    const chart = window.biCharts[id];
    const config = chart.arenaConfig;
    const option = chart.getOption();

    document.getElementById('biEditTitulo').value = document.getElementById(id).previousElementSibling.querySelector('.titulo-grafico').innerText;
    document.getElementById('biEditColorsContainer').innerHTML = '<div style="color:#8b949e; text-align: center;">Carregando configurações...</div>';
    document.getElementById('biEditModal').style.display = 'flex';

    const res = await fetch('/api/bi/colunas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bucket: config.bucket, filename: config.filename })
    });
    const data = await res.json();

    let colsHtml = '<option value="">(Nenhum)</option>';
    let colsMultiHtml = '';
    if (data.status === 'success') {
        data.colunas.forEach(col => {
            colsHtml += `<option value="${col}">${col}</option>`;
            colsMultiHtml += `<option value="${col}">${col}</option>`;
        });
    }

    // Preenche todos os selects
    ['biEditEixoX', 'biEditEixoY', 'biEditEixoZ', 'biEditOrdenarPor'].forEach(el => document.getElementById(el).innerHTML = colsHtml);
    document.getElementById('biEditColunasTabela').innerHTML = colsMultiHtml;

    // Restaura valores normais
    document.getElementById('biEditEixoX').value = config.eixo_x;
    document.getElementById('biEditEixoY').value = config.eixo_y;
    document.getElementById('biEditEixoZ').value = config.eixo_z || "";
    document.getElementById('biEditAgregacao').value = config.agregacao;
    document.getElementById('biEditTemaTabela').value = config.tema || 'padrao';
    document.getElementById('biEditOrdenarPor').value = config.ordenar_por || '';
    document.getElementById('biEditOrdem').value = config.ordem || 'asc';
    document.getElementById('biEditLimiteLinhas').value = config.limite_linhas || 100;

    // Restaura as colunas múltiplas selecionadas
    if (config.colunas_tabela) {
        Array.from(document.getElementById('biEditColunasTabela').options).forEach(opt => {
            if (config.colunas_tabela.includes(opt.value)) opt.selected = true;
        });
    }

    // Alterna a visualização dos painéis para esconder Eixos se for tabela
    toggleCamposGrafico('edit');

    // Monta o painel de Cores dinâmico apenas se NÃO for tabela/matriz
    const colorsContainer = document.getElementById('biEditColorsContainer');
    colorsContainer.innerHTML = '';

    if (config.tipo !== 'table' && config.tipo !== 'matrix') {
        if (config.tipo === 'pie' || config.tipo === 'funnel' || config.tipo === 'doughnut') {
            option.series[0].data.forEach((item, index) => {
                let defaultColor = option.color[index % option.color.length];
                let currentColor = (item.itemStyle && item.itemStyle.color) ? item.itemStyle.color : defaultColor;
                colorsContainer.innerHTML += `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 13px; color: #c9d1d9;">🔻 ${item.name}</span>
                        <input type="color" class="bi-input color-picker-edit" data-index="${index}" value="${currentColor}" style="height: 30px; width: 50px; padding: 0;">
                    </div>`;
            });
        } else if (config.tipo.includes('stacked')) {
            option.series.forEach((serie, index) => {
                let defaultColor = option.color[index % option.color.length];
                let currentColor = (serie.itemStyle && serie.itemStyle.color) ? serie.itemStyle.color : defaultColor;
                colorsContainer.innerHTML += `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 13px; color: #c9d1d9;">🏷️ ${serie.name}</span>
                        <input type="color" class="bi-input color-picker-edit" data-index="${index}" value="${currentColor}" style="height: 30px; width: 50px; padding: 0;">
                    </div>`;
            });
        } else {
            let currentColor = (option.series[0].itemStyle && option.series[0].itemStyle.color) ? option.series[0].itemStyle.color : '#58a6ff';
            colorsContainer.innerHTML += `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 13px; color: #c9d1d9;">🎨 Cor Principal do Gráfico</span>
                    <input type="color" class="bi-input color-picker-edit" data-index="0" value="${currentColor}" style="height: 30px; width: 50px; padding: 0;">
                </div>`;
        }
    }
}

async function salvarEdicaoGrafico() {
    if (!chartEmEdicao) return;
    const id = chartEmEdicao;
    const chart = window.biCharts[id];
    let config = chart.arenaConfig;

    const novoTitulo = document.getElementById('biEditTitulo').value;
    const novoX = document.getElementById('biEditEixoX').value;
    const novoY = document.getElementById('biEditEixoY').value;
    const novoZ = document.getElementById('biEditEixoZ').value;
    const novaAgregacao = document.getElementById('biEditAgregacao').value;

    // Captura campos de Tabela
    const novoTema = document.getElementById('biEditTemaTabela').value;
    const novoOrdenarPor = document.getElementById('biEditOrdenarPor').value;
    const novaOrdem = document.getElementById('biEditOrdem').value;
    const novoLimite = parseInt(document.getElementById('biEditLimiteLinhas').value) || 100;
    const novasColunas = Array.from(document.getElementById('biEditColunasTabela').selectedOptions).map(opt => opt.value);

    document.getElementById(id).previousElementSibling.querySelector('.titulo-grafico').innerText = novoTitulo;

    // Checa se algum dado estrutural mudou
    let dataChanged = (
        novoX !== config.eixo_x || novoY !== config.eixo_y || novoZ !== config.eixo_z ||
        novaAgregacao !== config.agregacao || novoTema !== config.tema ||
        novoOrdenarPor !== config.ordenar_por || novaOrdem !== config.ordem || novoLimite !== config.limite_linhas ||
        JSON.stringify(novasColunas) !== JSON.stringify(config.colunas_tabela)
    );

    if (dataChanged) {
        try {
            const res = await fetch('/api/bi/gerar_dados', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    bucket: config.bucket, filename: config.filename,
                    eixo_x: novoX, eixo_y: novoY, eixo_z: novoZ, agregacao: novaAgregacao,
                    tipo_grafico: config.tipo, colunas_tabela: novasColunas, tema: novoTema,
                    ordenar_por: novoOrdenarPor, ordem: novaOrdem, limite_linhas: novoLimite
                })
            });
            const result = await res.json();

            if (result.status === 'success') {
                config.eixo_x = novoX; config.eixo_y = novoY; config.eixo_z = novoZ;
                config.agregacao = novaAgregacao; config.colunas_tabela = novasColunas; config.tema = novoTema;

                // Se for tabela, re-renderizamos a DOM manualmente
                if (config.tipo === 'table' || config.tipo === 'matrix') {
                    const dados = result.data;
                    let classeTema = config.tema ? `theme-${config.tema}` : 'theme-padrao';
                    let htmlTable = `<div class="bi-table-container"><table class="bi-custom-table ${classeTema}"><thead><tr>`;

                    if (config.tipo === 'table') {
                        dados.colunas.forEach(col => { htmlTable += `<th>${col}</th>`; });
                    } else {
                        htmlTable += `<th>${dados.index_nome || 'Categoria'}</th>`;
                        dados.colunas.forEach(col => { htmlTable += `<th>${col}</th>`; });
                    }
                    htmlTable += `</tr></thead><tbody>`;

                    dados.linhas.forEach(row => {
                        htmlTable += `<tr>`;
                        row.forEach(cell => {
                            let val = (typeof cell === 'number') ? cell.toLocaleString(undefined, { maximumFractionDigits: 2 }) : cell;
                            htmlTable += `<td>${val}</td>`;
                        });
                        htmlTable += `</tr>`;
                    });
                    htmlTable += `</tbody></table></div>`;
                    document.getElementById(id).innerHTML = htmlTable;
                } else {
                    chart.setOption(getEchartsOption(config.tipo, result.data), true);
                }
            } else {
                alert("Erro ao recalcular os dados: " + result.message);
            }
        } catch (e) {
            alert("Falha de conexão.");
        }
    } else if (config.tipo !== 'table' && config.tipo !== 'matrix') {
        // Se os dados continuam os mesmos e for gráfico, aplicamos apenas as cores
        const option = chart.getOption();
        const pickers = document.querySelectorAll('.color-picker-edit');

        pickers.forEach(picker => {
            let idx = parseInt(picker.getAttribute('data-index'));
            let color = picker.value;

            if (config.tipo === 'pie' || config.tipo === 'funnel' || config.tipo === 'doughnut') {
                if (!option.series[0].data[idx].itemStyle) option.series[0].data[idx].itemStyle = {};
                option.series[0].data[idx].itemStyle.color = color;
            } else if (config.tipo.includes('stacked')) {
                if (!option.series[idx].itemStyle) option.series[idx].itemStyle = {};
                option.series[idx].itemStyle.color = color;
            } else {
                if (!option.series[0].itemStyle) option.series[0].itemStyle = {};
                option.series[0].itemStyle.color = color;
            }
        });
        chart.setOption(option, true);
    } else if (config.tipo === 'kpi') {
        let formatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
        let valorFormatado = formatter.format(result.data.valor);

        let corKpi = '#58a6ff';
        if (config.tema === 'green') corKpi = '#3fb950';
        if (config.tema === 'orange') corKpi = '#f59e0b';
        if (config.tema === 'padrao') corKpi = '#c9d1d9';

        let htmlKpi = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; width: 100%; text-align: center; box-sizing: border-box; padding: 10px;">
                        <div style="font-size: 3.5rem; font-weight: 800; color: ${corKpi}; line-height: 1.1; text-shadow: 0px 4px 15px ${corKpi}40;">${valorFormatado}</div>
                        <div style="font-size: 0.85rem; color: #8b949e; margin-top: 8px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: bold;">${config.agregacao} DE ${config.eixo_y}</div>
                    </div>`;
        document.getElementById(id).innerHTML = htmlKpi;
    } else {
        chart.setOption(getEchartsOption(config.tipo, result.data), true);
    }

    document.getElementById('biEditModal').style.display = 'none';
    chartEmEdicao = null;
}

function atualizarListaDatasetsBI() {
    const biSelector = document.getElementById('biDatasetSelector');
    if (!biSelector) return;

    let optionsHtml = '<option value="">Selecione a Tabela...</option>';

    for (const bucket in globalCatalogData) {
        const files = globalCatalogData[bucket];
        files.forEach(f => {
            if (f.endsWith('.csv') || f.endsWith('.parquet') || f.includes('part-')) {
                // Passamos bucket e filename no value
                const value = `${bucket}|${f}`;
                optionsHtml += `<option value="${value}">📁 ${f} (${bucket})</option>`;
            }
        });
    }
    biSelector.innerHTML = optionsHtml;
}

// Busca as colunas via Pandas quando o usuário escolhe a tabela
async function carregarColunasDataset() {
    const selector = document.getElementById('biDatasetSelector');
    const eixoX = document.getElementById('biEixoX');
    const eixoY = document.getElementById('biEixoY');

    if (!selector.value) {
        eixoX.innerHTML = '<option value="">Selecione a tabela primeiro...</option>';
        eixoY.innerHTML = '<option value="">Selecione a tabela primeiro...</option>';
        return;
    }

    const [bucket, filename] = selector.value.split('|');

    eixoX.innerHTML = '<option value="">Extraindo metadados...</option>';
    eixoY.innerHTML = '<option value="">Extraindo metadados...</option>';

    try {
        const res = await fetch('/api/bi/colunas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: bucket, filename: filename })
        });
        const data = await res.json();

        if (data.status === 'success') {
            let colsHtml = '<option value="">(Nenhum)</option>';
            let colsMultiHtml = '';
            data.colunas.forEach(col => {
                colsHtml += `<option value="${col}">${col}</option>`;
                colsMultiHtml += `<option value="${col}">${col}</option>`;
            });
            // NOVO: Adicionado biOrdenarPor na lista
            ['biEixoX', 'biEixoY', 'biEixoZ', 'biOrdenarPor'].forEach(el => document.getElementById(el).innerHTML = colsHtml);
            document.getElementById('biColunasTabela').innerHTML = colsMultiHtml;
        } else {
            alert("Error extracting columns: " + data.message);
        }
    } catch (e) {
        alert("Connection failure with the backend.");
    }
}

// ==============================================================
// FUNÇÕES DE EXPORTAÇÃO DE RELATÓRIO (PNG e PDF)
// ==============================================================
async function exportarDashboard(formato) {
    const gridArea = document.querySelector('.grid-container');

    // Verifica se tem algum card no Dashboard
    if (biGrid.engine.nodes.length === 0) {
        alert("The dashboard is empty. Add charts before exporting.");
        return;
    }

    // Pequeno ajuste cosmético temporário: tira as bordas tracejadas para a "foto" ficar mais limpa
    const bordaOriginal = gridArea.style.border;
    gridArea.style.border = 'none';

    try {
        // html2canvas tira a foto exata dos elementos HTML
        const canvas = await html2canvas(gridArea, {
            backgroundColor: '#0d1117',
            scale: 2, // Dobra a resolução para o PDF/PNG ficar em alta qualidade
            useCORS: true
        });

        const imgData = canvas.toDataURL('image/png');

        if (formato === 'png') {
            // Cria um link invisível, anexa a imagem e clica nele para forçar o download
            let link = document.createElement('a');
            link.download = `ArenaLake_Relatorio_${new Date().toISOString().slice(0, 10)}.png`;
            link.href = imgData;
            link.click();
        }
        else if (formato === 'pdf') {
            // Inicializa a biblioteca PDF e configura a página como Paisagem (Landscape) formato A4
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF('l', 'mm', 'a4');

            const pdfWidth = pdf.internal.pageSize.getWidth();
            // Calcula a altura proporcional da imagem no PDF
            const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

            // Adiciona a imagem, centraliza no topo e salva o documento
            pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
            pdf.save(`ArenaLake_Relatorio_${new Date().toISOString().slice(0, 10)}.pdf`);
        }
    } catch (error) {
        alert("An error occurred while generating the report.");
        console.error(error);
    } finally {
        // Restaura a borda da interface
        gridArea.style.border = bordaOriginal;
    }
}

function toggleCamposGrafico(modo) {
    let prefix = modo === 'create' ? 'bi' : 'biEdit';
    let tipo = document.getElementById(prefix + 'TipoGrafico')?.value;

    if (modo === 'edit' && window.biCharts[chartEmEdicao]) tipo = window.biCharts[chartEmEdicao].arenaConfig.tipo;

    const isTable = (tipo === 'table');
    const isMatrix = (tipo === 'matrix');
    const isKpi = (tipo === 'kpi');
    const isScatter = (tipo === 'scatter'); // NOVO
    const isWaterfall = (tipo === 'waterfall');

    document.getElementById(prefix + 'EixosComuns').style.display = isTable ? 'none' : 'block';

    // Esconde Eixos específicos para KPI
    if (document.getElementById(prefix + 'DivEixoX')) document.getElementById(prefix + 'DivEixoX').style.display = isKpi ? 'none' : 'block';
    if (document.getElementById(prefix + 'DivEixoZ')) document.getElementById(prefix + 'DivEixoZ').style.display = isKpi ? 'none' : 'block';

    // NOVO: Esconde Agregação para Tabelas e Scatter Plot
    if (document.getElementById(prefix + 'DivAgregacao')) {
        document.getElementById(prefix + 'DivAgregacao').style.display = (isTable || isScatter) ? 'none' : 'block';
    }

    document.getElementById(prefix + 'DivColunasTabela').style.display = isTable ? 'block' : 'none';

    // O Tema só não se aplica ao Scatter e aos gráficos comuns
    document.getElementById(prefix + 'DivTemaTabela').style.display = (isTable || isMatrix || isKpi) ? 'block' : 'none';

    // NOVO: O Limite de Linhas é muito útil no Scatter também!
    document.getElementById(prefix + 'DivConfigTabela').style.display = (isTable || isMatrix || isScatter) ? 'block' : 'none';

    if (modo === 'edit') {
        // NOVO: Esconde a edição de cores para a Cascata (já usamos verde/vermelho por padrão)
        document.getElementById('biEditColorSection').style.display = (isTable || isMatrix || isKpi || isWaterfall) ? 'none' : 'block';
    }
}

// VARIÁVEIS DE FILTRO GLOBAL
window.globalFiltroColuna = "";
window.globalFiltroValor = "";

async function abrirModalFiltroGlobal() {
    const selector = document.getElementById('biDatasetSelector').value;
    if (!selector) return alert("Select a data source from the top bar first.");

    const [bucket, filename] = selector.split('|');
    const res = await fetch('/api/bi/colunas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bucket, filename }) });
    const data = await res.json();

    if (data.status === 'success') {
        let html = '<option value="">(Nenhum)</option>';
        data.colunas.forEach(col => html += `<option value="${col}">${col}</option>`);
        document.getElementById('biFiltroColuna').innerHTML = html;
        document.getElementById('biFiltroColuna').value = window.globalFiltroColuna;

        if (window.globalFiltroColuna) await carregarValoresFiltro();
    }
    document.getElementById('biFiltroModal').style.display = 'flex';
}

async function carregarValoresFiltro() {
    const selector = document.getElementById('biDatasetSelector').value;
    const coluna = document.getElementById('biFiltroColuna').value;
    if (!coluna) return;

    const [bucket, filename] = selector.split('|');
    document.getElementById('biFiltroValor').innerHTML = '<option>Carregando...</option>';

    const res = await fetch('/api/bi/valores_coluna', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bucket, filename, coluna }) });
    const data = await res.json();

    if (data.status === 'success') {
        let html = '<option value="">(Todos)</option>';
        data.valores.forEach(v => html += `<option value="${v}">${v}</option>`);
        document.getElementById('biFiltroValor').innerHTML = html;
        document.getElementById('biFiltroValor').value = window.globalFiltroValor;
    }
}

async function aplicarFiltroGlobal() {
    window.globalFiltroColuna = document.getElementById('biFiltroColuna').value;
    window.globalFiltroValor = document.getElementById('biFiltroValor').value;
    document.getElementById('biFiltroModal').style.display = 'none';
    await recarregarTodosGraficos();
}

async function limparFiltroGlobal() {
    window.globalFiltroColuna = "";
    window.globalFiltroValor = "";
    document.getElementById('biFiltroModal').style.display = 'none';
    await recarregarTodosGraficos();
}

async function recarregarTodosGraficos() {
    // Passa por todos os gráficos na grid e pede para o backend gerar os dados novamente com o filtro!
    for (let id in window.biCharts) {
        let chartObj = window.biCharts[id];
        let config = chartObj.arenaConfig;
        config.filtro_coluna = window.globalFiltroColuna;
        config.filtro_valor = window.globalFiltroValor;

        const res = await fetch('/api/bi/gerar_dados', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) });
        const result = await res.json();

        if (result.status === 'success') {
            if (config.tipo === 'table' || config.tipo === 'matrix') {
                // Aqui podemos apenas apagar e forçar o HTML a se recriar da mesma forma que na Edição
                let classeTema = config.tema ? `theme-${config.tema}` : 'theme-padrao';
                let htmlTable = `<div class="bi-table-container"><table class="bi-custom-table ${classeTema}"><thead><tr>`;
                if (config.tipo === 'table') result.data.colunas.forEach(col => { htmlTable += `<th>${col}</th>`; });
                else { htmlTable += `<th>${result.data.index_nome || 'Categoria'}</th>`; result.data.colunas.forEach(col => { htmlTable += `<th>${col}</th>`; }); }
                htmlTable += `</tr></thead><tbody>`;
                result.data.linhas.forEach(row => { htmlTable += `<tr>`; row.forEach(cell => { let val = (typeof cell === 'number') ? cell.toLocaleString(undefined, { maximumFractionDigits: 2 }) : cell; htmlTable += `<td>${val}</td>`; }); htmlTable += `</tr>`; });
                htmlTable += `</tbody></table></div>`;
                document.getElementById(id).innerHTML = htmlTable;
            } else if (config.tipo === 'kpi') {
                let valFormat = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(result.data.valor);
                let cor = config.tema === 'green' ? '#3fb950' : (config.tema === 'orange' ? '#f59e0b' : (config.tema === 'padrao' ? '#c9d1d9' : '#58a6ff'));
                document.getElementById(id).innerHTML = `<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; width: 100%; text-align: center; box-sizing: border-box; padding: 10px;"><div style="font-size: 3.5rem; font-weight: 800; color: ${cor}; line-height: 1.1; text-shadow: 0px 4px 15px ${cor}40;">${valFormat}</div><div style="font-size: 0.85rem; color: #8b949e; margin-top: 8px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: bold;">${config.agregacao} DE ${config.eixo_y}</div></div>`;
            } else {
                chartObj.setOption(getEchartsOption(config.tipo, result.data), true);
            }
        }
    }
}