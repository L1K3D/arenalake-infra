/* portal-compute/static/js/admin.js */

function showSection(targetSection) {
    document.querySelectorAll('.admin-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.menu-item').forEach(li => li.classList.remove('active'));

    document.getElementById('sec-' + targetSection).classList.add('active');
    document.getElementById('nav-' + targetSection).classList.add('active');
}

const token = sessionStorage.getItem('access_token');
if (!token) {
    window.location.href = '/';
}

let loggedAdminUsername = '';
let allUsers = [];
let activeUsernames = new Set();
let currentSortCol = 'id';
let currentSortAsc = true;

function logoutAdmin() {
    sessionStorage.removeItem('access_token');
    window.location.href = '/';
}

// Gera e baixa o arquivo CSV
function downloadCSV() {
    if (!allUsers || allUsers.length === 0) {
        alert('No users to download.');
        return;
    }

    const headers = ['ID', 'Username', 'Email', 'Name', 'Role', '2FA Status'];

    const rows = allUsers.map(u => [
        u.id,
        u.username,
        u.email || 'N/A',
        u.full_name,
        u.role,
        u.is_2fa_verified ? 'Verified' : 'Pending'
    ]);

    const csvContent = headers.join(',') + '\n' + rows.map(r => r.map(cell => `"${cell}"`).join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('href', url);
    a.setAttribute('download', 'arenalake_users.csv');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

async function carregarWorkspaces() {
    try {
        const res = await fetch('/api/admin/workspaces', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (data.status === 'success') {
            activeUsernames = new Set(data.workspaces.map(w => w.username));
            renderUserTable();

            const tbody = document.getElementById('workspaceTableBody');
            tbody.innerHTML = '';

            if (data.workspaces.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="padding: 15px; text-align: center; color: #8b949e;">No active workspace at the moment.</td></tr>';
                return;
            }

            data.workspaces.forEach(w => {
                tbody.innerHTML += `
                    <tr style="border-bottom: 1px solid #21262d;">
                        <td style="padding: 10px; color: #58a6ff; font-weight: bold;">${w.username}</td>
                        <td style="padding: 10px; font-family: monospace; font-size: 0.9em;">${w.service_name}</td>
                        <td style="padding: 10px;">${w.cpu} | ${w.ram}</td>
                        <td style="padding: 10px; text-align: right;">
                            <button onclick="killWorkspace('${w.username}')" style="background: #da3633; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-weight: bold; cursor: pointer;">🛑 Derrubar Sessão</button>
                        </td>
                    </tr>
                `;
            });
        }
    } catch (e) {
        console.error('Error on load workspaces', e);
    }
}

async function carregarUsuarios() {
    try {
        const res = await fetch('/api/admin/users', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (data.status === 'success') {
            allUsers = data.users;

            const currentAdmin = allUsers.find(u => u.role === 'admin');
            if (currentAdmin) {
                loggedAdminUsername = currentAdmin.username;
                document.getElementById('expectedPhraseLabel').innerText = `DELETE ACCOUNT ${loggedAdminUsername}`;
            }

            renderUserTable();
        }
    } catch (e) {
        console.error('Erro ao carregar usuários', e);
    }
}

function sortUsers(col) {
    if (currentSortCol === col) {
        currentSortAsc = !currentSortAsc;
    } else {
        currentSortCol = col;
        currentSortAsc = true;
    }
    renderUserTable();
}

function renderUserTable() {
    if (!allUsers || allUsers.length === 0) return;

    let sortedUsers = [...allUsers].sort((a, b) => {
        let valA = a[currentSortCol] || '';
        let valB = b[currentSortCol] || '';

        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();

        if (valA < valB) return currentSortAsc ? -1 : 1;
        if (valA > valB) return currentSortAsc ? 1 : -1;
        return 0;
    });

    const total = sortedUsers.length;
    const admins = sortedUsers.filter(u => u.role === 'admin').length;
    const common = sortedUsers.filter(u => u.role === 'common').length;
    const onlineCount = sortedUsers.filter(u => activeUsernames.has(u.username)).length;

    document.getElementById('kpi-total').innerText = total;
    document.getElementById('kpi-admins').innerText = `${admins} (${Math.round((admins / total) * 100)}%)`;
    document.getElementById('kpi-common').innerText = `${common} (${Math.round((common / total) * 100)}%)`;
    document.getElementById('kpi-online').innerText = onlineCount;

    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = '';

    sortedUsers.forEach(u => {
        let actionBtn = '';
        if (u.role !== 'admin') {
            actionBtn = `
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                    <button onclick="resetarSenha(${u.id}, '${u.username}')" style="background: #1f6feb; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 0.85em; cursor: pointer; white-space: nowrap;">🔑 Reset Password</button>
                    <button onclick="deletarUsuario(${u.id}, '${u.username}')" style="background: #da3633; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 0.85em; cursor: pointer; white-space: nowrap;">🗑️ Delete</button>
                </div>
            `;
        } else {
            actionBtn = `<div style="display: flex; justify-content: flex-end;"><span style="color: #8b949e; font-size: 0.8em; font-style: italic; padding: 6px 0;">Protected</span></div>`;
        }

        const isOnline = activeUsernames.has(u.username);
        const statusDot = isOnline
            ? '<span style="color: #2ea043; margin-right: 8px; font-size: 1.2em;" title="Online">●</span>'
            : '<span style="color: #da3633; margin-right: 8px; font-size: 1.2em;" title="Offline">●</span>';

        const email = u.email || 'N/A';

        tbody.innerHTML += `
            <tr style="border-bottom: 1px solid #21262d;">
                <td style="padding: 10px;">${statusDot} #${u.id}</td>
                <td style="padding: 10px; color: #58a6ff; font-weight: bold;">${u.username}</td>
                <td style="padding: 10px; font-size: 0.9em; color: #8b949e;">${email}</td>
                <td style="padding: 10px;">${u.full_name}</td>
                <td style="padding: 10px;"><span style="background: ${u.role === 'admin' ? '#da3633' : '#1f6feb'}; padding: 3px 8px; border-radius: 4px; font-size: 0.8em;">${u.role.toUpperCase()}</span></td>
                <td style="padding: 10px;">${u.is_2fa_verified ? '✅ Verified' : '⏳ Pending'}</td>
                <td style="padding: 10px; text-align: right;">${actionBtn}</td>
            </tr>
        `;
    });
}

async function deletarUsuario(userId, username) {
    if (!confirm(`Are you sure you want to delete the regular user '${username}'?`)) return;

    try {
        const res = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            carregarUsuarios();
        } else {
            alert('Error: ' + result.detail);
        }
    } catch (e) {
        alert('Communication error while trying to delete the user.');
    }
}

document.getElementById('createUserForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
        full_name: document.getElementById('full_name').value,
        email: document.getElementById('email').value,
        role: document.getElementById('roleSelect').value,
        department: 'Infrastructure'
    };

    const res = await fetch('/api/admin/users', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    });

    const result = await res.json();
    if (res.ok) {
        alert(result.message);
        document.getElementById('createUserForm').reset();
        carregarUsuarios();
    } else {
        alert('Erro: ' + result.detail);
    }
});

async function killWorkspace(username) {
    if (!confirm(`Are you sure you want to terminate the session for '${username}' with the kill switch?`)) return;

    try {
        const res = await fetch(`/api/admin/workspaces/kill/${username}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            carregarWorkspaces();
        } else {
            alert('Error: ' + result.detail);
        }
    } catch (e) {
        alert('Communication error while trying to terminate the session.');
    }
}

async function carregarClusterNodes() {
    try {
        const res = await fetch('/api/admin/cluster/nodes', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (data.status === 'success') {
            const tbody = document.getElementById('nodesTableBody');
            tbody.innerHTML = '';

            let totalCpus = 0;
            let totalRam = 0;
            let activeNodes = 0;

            // Counters para os gráficos das Marcas de Processador
            let countIntel = 0;
            let countAmd = 0;
            let countOutros = 0;

            data.nodes.forEach(n => {
                totalCpus += n.cpus;
                totalRam += n.memory_gb;
                if (n.status === 'ready') activeNodes++;

                // Checa se o agente no Worker mandou a telemetria rica
                const hasTelemetry = n.cpu_percent !== undefined && n.ram_percent !== undefined;

                let cpuDisplay, ramDisplay, cpuBar, ramBar, storageDisplay, cpuModelStr;

                if (hasTelemetry) {
                    // Contabiliza arquiteturas apenas de nós responsivos
                    if (n.marca_cpu === 'Intel') countIntel++;
                    else if (n.marca_cpu === 'AMD') countAmd++;
                    else countOutros++;

                    cpuModelStr = `<div style="font-size: 0.8em; color: #8b949e; margin-top: 4px; line-height: 1.2;">💻 ${n.marca_cpu} <br>${n.modelo_cpu}</div>`;

                    const cpuUsed = ((n.cpu_percent / 100) * n.cpus).toFixed(1);
                    const ramUsed = ((n.ram_percent / 100) * n.memory_gb).toFixed(1);

                    const cpuColor = n.cpu_percent > 85 ? 'fill-danger' : (n.cpu_percent > 65 ? 'fill-warning' : 'fill-normal');
                    const ramColor = n.ram_percent > 85 ? 'fill-danger' : (n.ram_percent > 65 ? 'fill-warning' : 'fill-normal');

                    cpuDisplay = `<span><span style="color: #c9d1d9;">${cpuUsed}</span> / ${n.cpus} Cores</span><span>${n.cpu_percent}%</span>`;
                    cpuBar = `<div class="progress-fill ${cpuColor}" style="width: ${n.cpu_percent}%;"></div>`;

                    ramDisplay = `<span><span style="color: #c9d1d9;">${ramUsed}</span> / ${n.memory_gb} GB</span><span>${n.ram_percent}%</span>`;
                    ramBar = `<div class="progress-fill ${ramColor}" style="width: ${n.ram_percent}%;"></div>`;

                    // Cálculo da barra de Storage
                    const diskPercent = n.disk_gb > 0 ? ((n.disk_usado_gb / n.disk_gb) * 100).toFixed(1) : 0;
                    const diskColor = diskPercent > 85 ? 'fill-danger' : (diskPercent > 65 ? 'fill-warning' : 'fill-normal');
                    storageDisplay = `
                        <div class="resource-container">
                            <div class="resource-header">
                                <span><span style="color: #c9d1d9;">${n.disk_usado_gb}</span> / ${n.disk_gb} GB</span>
                                <span>${diskPercent}%</span>
                            </div>
                            <div class="progress-bg">
                                <div class="progress-fill ${diskColor}" style="width: ${diskPercent}%;"></div>
                            </div>
                        </div>
                    `;
                } else {
                    cpuModelStr = `<div style="font-size: 0.8em; color: #da3633; margin-top: 4px; font-style: italic;">CPU Info Unavailable</div>`;

                    cpuDisplay = `<span><span style="color: #da3633; font-style: italic;">Offline / No Data</span> / ${n.cpus} Cores</span><span style="color: #8b949e;">--%</span>`;
                    cpuBar = `<div class="progress-fill" style="width: 0%; background: #30363d;"></div>`;

                    ramDisplay = `<span><span style="color: #da3633; font-style: italic;">Offline / No Data</span> / ${n.memory_gb} GB</span><span style="color: #8b949e;">--%</span>`;
                    ramBar = `<div class="progress-fill" style="width: 0%; background: #30363d;"></div>`;

                    storageDisplay = `
                        <div class="resource-container">
                            <div class="resource-header">
                                <span><span style="color: #da3633; font-style: italic;">Offline / No Data</span></span>
                                <span style="color: #8b949e;">--%</span>
                            </div>
                            <div class="progress-bg">
                                <div class="progress-fill" style="width: 0%; background: #30363d;"></div>
                            </div>
                        </div>
                    `;
                }

                tbody.innerHTML += `
                    <tr style="border-bottom: 1px solid #21262d;">
                        <td style="padding: 15px 10px;">
                            <div style="font-family: monospace; color: #58a6ff; font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">${n.hostname}</div>
                            <span style="background: ${n.role === 'MANAGER' ? '#8957e5' : '#1f6feb'}; padding: 3px 8px; border-radius: 4px; font-size: 0.75em; color: white;">${n.role}</span>
                            ${cpuModelStr}
                        </td>
                        <td style="padding: 15px 10px;">
                            ${n.status === 'ready' ? '<span style="color: #2ea043; font-weight: bold;">🟢 Ready</span>' : '<span style="color: #da3633; font-weight: bold;">🔴 Down</span>'}
                        </td>
                        <td style="padding: 15px 10px;">
                            <div class="resource-container">
                                <div class="resource-header">${cpuDisplay}</div>
                                <div class="progress-bg">${cpuBar}</div>
                            </div>
                        </td>
                        <td style="padding: 15px 10px;">
                            <div class="resource-container">
                                <div class="resource-header">${ramDisplay}</div>
                                <div class="progress-bg">${ramBar}</div>
                            </div>
                        </td>
                        <td style="padding: 15px 10px;">
                            ${storageDisplay}
                        </td>
                    </tr>
                `;
            });

            // --- Preenche os KPIs Superiores ---
            document.getElementById('kpi-nodes-count').innerText = `${activeNodes} / ${data.nodes.length}`;
            document.getElementById('kpi-total-cpu').innerText = totalCpus;
            document.getElementById('kpi-total-ram').innerText = `${totalRam.toFixed(1)} GB`;

            const healthEl = document.getElementById('kpi-cluster-health');
            if (activeNodes === data.nodes.length && activeNodes > 0) {
                healthEl.innerText = "Healthy";
                healthEl.style.color = "#2ea043";
            } else if (activeNodes > 0) {
                healthEl.innerText = "Degraded";
                healthEl.style.color = "#d29922";
            } else {
                healthEl.innerText = "Critical";
                healthEl.style.color = "#da3633";
            }

            // --- Preenche os KPIs de Arquitetura de Processador ---
            const totalCpusWithTelemetry = countIntel + countAmd + countOutros;
            const intelPct = totalCpusWithTelemetry > 0 ? Math.round((countIntel / totalCpusWithTelemetry) * 100) : 0;
            const amdPct = totalCpusWithTelemetry > 0 ? Math.round((countAmd / totalCpusWithTelemetry) * 100) : 0;
            const outrosPct = totalCpusWithTelemetry > 0 ? Math.round((countOutros / totalCpusWithTelemetry) * 100) : 0;

            document.getElementById('kpi-cpu-intel').innerHTML = `Intel: ${countIntel} <span style="font-size: 0.6em; color: #8b949e;">(${intelPct}%)</span>`;
            document.getElementById('kpi-cpu-amd').innerHTML = `AMD: ${countAmd} <span style="font-size: 0.6em; color: #8b949e;">(${amdPct}%)</span>`;
            document.getElementById('kpi-cpu-outros').innerHTML = `Outros: ${countOutros} <span style="font-size: 0.6em; color: #8b949e;">(${outrosPct}%)</span>`;
        }
    } catch (e) {
        console.error('Error on load cluster nodes', e);
    }
}

async function auditarArquivos() {
    const username = document.getElementById('auditUsername').value.trim();
    const outputBox = document.getElementById('auditOutput');
    if (!username) {
        alert('Enter a valid username for auditing.');
        return;
    }

    outputBox.style.display = 'block';
    outputBox.innerText = 'Looking up files in the user\'s volume...';

    try {
        const res = await fetch(`/api/admin/files/${username}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (res.ok) {
            outputBox.innerText = data.files.join('\n');
        } else {
            outputBox.innerText = 'Error: ' + data.detail;
        }
    } catch (e) {
        outputBox.innerText = 'Connection error while inspecting the volume.';
    }
}

async function executarAutodestruicao() {
    const confirmUser = document.getElementById('confirmDestroyUser').value.trim();
    if (!confirmUser) {
        alert('You need to type your username to confirm self-destruction.');
        return;
    }

    if (!confirm('WARNING: Do you really want to purge all active sessions and workspaces in the cluster? This action is irreversible!')) return;

    try {
        const res = await fetch('/api/admin/danger/destroy', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ confirm_username: confirmUser })
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            document.getElementById('confirmDestroyUser').value = '';
            carregarWorkspaces();
        } else {
            alert('Critical error: ' + result.detail);
        }
    } catch (e) {
        alert('Communication error with the server.');
    }
}

let globalAdminCatalog = {};

async function carregarDataCatalog() {
    try {
        const res = await fetch('/api/admin/catalog', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (data.status === 'success') {
            globalAdminCatalog = data.data;
            atualizarDropdownBuckets();
            renderizarCatalog();
        }
    } catch (e) {
        console.error('Error on load Data Catalog', e);
    }
}

function atualizarDropdownBuckets() {
    const dropdown = document.getElementById('bucketDropdown');
    const currentSelection = dropdown.value;

    const buckets = Object.keys(globalAdminCatalog);
    let optionsHtml = '<option value="all">📁 All Buckets</option>';

    buckets.forEach(b => {
        optionsHtml += `<option value="${b}">📦 ${b}</option>`;
    });

    dropdown.innerHTML = optionsHtml;

    // Mantém o filtro ativo se um bucket já estivesse selecionado
    if (currentSelection && currentSelection !== "all" && buckets.includes(currentSelection)) {
        dropdown.value = currentSelection;
    }
}

function handleFilterChange() {
    renderizarCatalog();
}

function renderizarCatalog() {
    const container = document.getElementById('catalogContainer');
    const filter = document.getElementById('bucketDropdown').value;
    container.innerHTML = '';

    let bucketsToRender = Object.keys(globalAdminCatalog);

    if (bucketsToRender.length === 0) {
        container.innerHTML = '<p style="color: #8b949e;">No buckets found in MinIO.</p>';
        return;
    }

    if (filter !== "all") {
        bucketsToRender = [filter];
    }

    bucketsToRender.forEach(bucket => {
        let filesHtml = '';
        const files = globalAdminCatalog[bucket];

        if (files.length === 0) {
            filesHtml = '<tr><td colspan="2" style="padding: 15px; color: #8b949e; font-style: italic;">Bucket is empty.</td></tr>';
        } else {
            files.forEach(file => {
                filesHtml += `
                    <tr style="border-bottom: 1px solid #21262d; transition: background 0.2s;" onmouseover="this.style.background='#1c2128'" onmouseout="this.style.background='transparent'">
                        <td style="padding: 10px; font-family: monospace; color: #58a6ff; font-size: 0.9em;">${file}</td>
                        <td style="padding: 10px; text-align: right; white-space: nowrap;">
                            <button onclick="abrirPreview('${bucket}', '${file}')" style="background: #21262d; color: #58a6ff; border: 1px solid #30363d; padding: 4px 10px; border-radius: 4px; font-size: 0.85em; cursor: pointer; margin-right: 5px;">👁️ Preview</button>
                            <button onclick="deletarArquivoCatalog('${bucket}', '${file}')" style="background: #da3633; color: white; border: none; padding: 5px 10px; border-radius: 4px; font-size: 0.85em; cursor: pointer;">🗑️ Delete</button>
                        </td>
                    </tr>
                `;
            });
        }

        container.innerHTML += `
            <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #21262d; padding-bottom: 10px;">
                    <h4 style="margin: 0; color: #79c0ff; font-size: 1.1em;">📦 Bucket: ${bucket}</h4>
                    <button onclick="deletarBucketAdmin('${bucket}')" style="background: transparent; color: #f85149; border: 1px solid #f85149; padding: 4px 12px; border-radius: 4px; font-size: 0.8em; font-weight: bold; cursor: pointer;">❌ Excluir Bucket</button>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <tbody>${filesHtml}</tbody>
                </table>
            </div>
        `;
    });
}

async function deletarBucketAdmin(bucket) {
    if (!confirm(`ATENÇÃO: Você está prestes a excluir o bucket '${bucket}'. Isso removerá TODOS os arquivos dentro dele e quebrará análises que dependem desses dados.\n\nDeseja prosseguir?`)) return;

    // Dupla verificação
    const confirmacao = prompt(`Para confirmar a exclusão, digite o nome do bucket exatamente como está escrito (${bucket}):`);
    if (confirmacao !== bucket) {
        alert('Nome incorreto. Exclusão cancelada por segurança.');
        return;
    }

    try {
        const res = await fetch(`/api/admin/catalog/bucket/${bucket}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            document.getElementById('bucketDropdown').value = 'all'; // Reseta o filtro
            carregarDataCatalog();
        } else {
            alert('Erro: ' + result.detail);
        }
    } catch (e) {
        alert('Erro de comunicação ao tentar excluir o bucket.');
    }
}

async function abrirPreview(bucket, filename) {
    document.getElementById('adminSidePanel').classList.add('open');
    document.getElementById('prevFilename').innerText = filename;
    document.getElementById('prevBucket').innerText = bucket;
    document.getElementById('prevContent').innerHTML = "<div style='color:#8b949e'>Gerando preview da amostra de dados...</div>";
    document.getElementById('prevShape').style.display = 'none';

    try {
        const res = await fetch(`/api/admin/catalog/preview/${bucket}/${filename}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (result.status === 'success') {
            document.getElementById('prevDate').innerText = result.data.last_modified;
            document.getElementById('prevSize').innerText = result.data.size;
            document.getElementById('prevUploader').innerText = result.data.uploader;

            if (result.data.type === 'table') {
                document.getElementById('prevShape').style.display = 'block';
                document.getElementById('prevRows').innerText = result.data.total_rows;
                document.getElementById('prevCols').innerText = result.data.total_cols;
            }

            let contentHtml = result.data.type === 'image'
                ? `<img src="${result.data.preview_content}" class="preview-img">`
                : result.data.preview_content;

            document.getElementById('prevContent').innerHTML = contentHtml;
        } else {
            document.getElementById('prevContent').innerHTML = "<div style='color:#f85149'>Falha na leitura do arquivo.</div>";
        }
    } catch (e) {
        document.getElementById('prevContent').innerHTML = "<div style='color:#da3633'>Erro de rede ao carregar preview.</div>";
    }
}

function fecharPreview() {
    document.getElementById('adminSidePanel').classList.remove('open');
}

async function handleCreateBucket() {
    const input = document.getElementById("newBucketInput");
    const bucketName = input.value.trim();

    if (!bucketName) {
        alert("Please enter a valid bucket name.");
        return;
    }

    try {
        const res = await fetch('/api/admin/catalog/bucket', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bucket_name: bucketName })
        });

        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            input.value = "";

            // Recarrega o catálogo e já força o dropdown a focar no novo bucket
            carregarDataCatalog().then(() => {
                const cleanName = bucketName.toLowerCase().replace(/_/g, "-");
                document.getElementById('bucketDropdown').value = cleanName;
                renderizarCatalog();
            });
        } else {
            alert("Error: " + result.detail);
        }
    } catch (error) {
        alert("Communication error while creating the bucket.");
    }
}

async function deletarArquivoCatalog(bucket, filename) {
    if (!confirm(`Are you sure you want to delete the file '${filename}' from bucket '${bucket}'?`)) return;

    const formData = new URLSearchParams();
    formData.append('bucket', bucket);
    formData.append('filename', filename);

    try {
        const res = await fetch('/api/admin/catalog/file', {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            carregarDataCatalog();
        } else {
            alert('Error: ' + result.detail);
        }
    } catch (e) {
        alert('Communication error while trying to delete the file.');
    }
}

document.getElementById('uploadCatalogForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const bucket = document.getElementById('bucketDropdown').value;
    const fileInput = document.getElementById('uploadFile').files[0];

    // Trava de segurança solicitada: obriga a escolher o bucket.
    if (bucket === "all") {
        alert("Please select a specific bucket from the dropdown to upload this file.");
        document.getElementById('bucketDropdown').focus();
        return;
    }

    if (!fileInput) {
        alert('Select a file.');
        return;
    }

    const formData = new FormData();
    formData.append('bucket', bucket);
    formData.append('file', fileInput);

    try {
        const res = await fetch('/api/admin/catalog/upload', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            document.getElementById('uploadFile').value = '';
            carregarDataCatalog();
        } else {
            alert('Error: ' + result.detail);
        }
    } catch (e) {
        alert('Error while uploading the file to the Data Lake.');
    }
});

async function executarAutodelecao() {
    const inputVal = document.getElementById('selfDeleteInput').value.trim();

    if (!confirm('WARNING: Do you really want to delete your own administrator account? This action is irreversible!')) return;

    try {
        const res = await fetch('/api/admin/account/self', {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ confirmation_phrase: inputVal })
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            sessionStorage.removeItem('access_token');
            window.location.href = '/';
        } else {
            alert('Error: ' + result.detail);
        }
    } catch (e) {
        alert('Communication error with the server.');
    }
}

async function resetarSenha(userId, username) {
    const novaSenha = prompt(`Enter the temporary new password for '${username}' (Min. 8 characters):`);
    if (!novaSenha) return;

    if (novaSenha.length < 8) {
        alert('The temporary password must be at least 8 characters long.');
        return;
    }

    try {
        const res = await fetch(`/api/admin/users/${userId}/reset-password`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ new_password: novaSenha })
        });
        const result = await res.json();

        if (res.ok) {
            alert(result.message);
            carregarUsuarios();
        } else {
            alert('Error: ' + result.detail);
        }
    } catch (e) {
        alert('Communication error while resetting the password.');
    }
}

async function carregarTailscale() {
    try {
        const res = await fetch('/api/admin/tailscale/status', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (data.status === 'success') {
            const tbody = document.getElementById('tailscaleTableBody');
            const select = document.getElementById('ts-terminal-select');

            tbody.innerHTML = '';
            select.innerHTML = '<option value="">Selecione um Servidor...</option>';

            data.network.forEach(node => {
                // Popula a Tabela
                const statusColor = node.status === 'Connected' ? '#2ea043' : '#8b949e';

                tbody.innerHTML += `
                    <tr style="border-bottom: 1px solid #21262d;">
                        <td style="padding: 15px 10px;">
                            <div style="color: #c9d1d9; font-weight: bold;">${node.hostname} ${node.is_self ? '<span style="font-size: 0.7em; background: #30363d; padding: 2px 6px; border-radius: 10px; margin-left: 5px;">This Node</span>' : ''}</div>
                            <div style="font-size: 0.8em; margin-top: 5px;">
                                <span style="background: #1f6feb; padding: 2px 6px; border-radius: 4px; color: white;">tag:servers</span>
                            </div>
                        </td>
                        <td style="padding: 15px 10px; font-family: monospace; color: #58a6ff;">
                            ${node.ip} ⌵
                        </td>
                        <td style="padding: 15px 10px; color: #8b949e; font-size: 0.9em;">
                            v${node.version}<br>${node.os}
                        </td>
                        <td style="padding: 15px 10px; color: ${statusColor};">
                            ● ${node.status}
                        </td>
                    </tr>
                `;

                // Popula o Dropdown do Terminal
                if (node.status === 'Connected') {
                    select.innerHTML += `<option value="${node.ip}">${node.hostname} (${node.ip})</option>`;
                }
            });
        }
    } catch (e) {
        console.error('Erro ao carregar rede Tailscale', e);
    }
}

// Ações dos Botões (Rascunhos para a próxima fase)
function addTailscaleNode() {
    const link = document.getElementById('ts-add-link').value;
    if (!link) return alert("Cole o link primeiro!");
    window.open(link, '_blank');
}

let currentTerm = null;
let currentWs = null;

function openWebTerminal() {
    const ip = document.getElementById('ts-terminal-select').value;
    if (!ip) return alert("Selecione um servidor na lista!");

    document.getElementById('terminal-container').style.display = 'block';
    document.getElementById('terminal-title').innerText = `Root Shell ➔ root@${ip}`;

    const screen = document.getElementById('terminal-screen');
    screen.innerHTML = ''; // Limpa o canvas

    // Inicializa a interface gráfica do Terminal
    currentTerm = new Terminal({
        cursorBlink: true,
        fontFamily: 'Consolas, monospace',
        theme: { background: '#0d1117' }
    });
    const fitAddon = new FitAddon.FitAddon();
    currentTerm.loadAddon(fitAddon);
    currentTerm.open(screen);
    fitAddon.fit();

    // Inicia o WebSocket apontando para o FastAPI
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    currentWs = new WebSocket(`${wsProtocol}//${window.location.host}/api/admin/terminal/${ip}?token=${token}`);

    currentWs.onopen = () => {
        currentTerm.write(`\r\n[ ArenaLake Web Terminal ] Conectando via SSH em ${ip}...\r\n`);
    };

    // Imprime na tela tudo que o servidor responder
    currentWs.onmessage = (event) => {
        currentTerm.write(event.data);
    };

    // Envia para o servidor tudo que o usuário digitar
    currentTerm.onData(data => {
        if (currentWs.readyState === WebSocket.OPEN) {
            currentWs.send(data);
        }
    });

    currentWs.onclose = () => {
        currentTerm.write('\r\n\r\n[!] Conexão Encerrada.\r\n');
    };
}

function closeWebTerminal() {
    if (currentWs) {
        currentWs.close();
        currentWs = null;
    }
    if (currentTerm) {
        currentTerm.dispose();
        currentTerm = null;
    }
    document.getElementById('terminal-container').style.display = 'none';
}

async function init() {
    carregarDataCatalog();
    await carregarWorkspaces();
    await carregarUsuarios();
    await carregarClusterNodes();
    await carregarTailscale();

    // Atualiza as sessões e o monitoramento de Nodes em TEMPO REAL (a cada 10 seg)
    setInterval(() => {
        carregarWorkspaces();
        carregarClusterNodes();
    }, 10000);
}

async function baixarRelatorioCatalog(event) {
    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.innerHTML = "⏳ Gerando Análise...";
    btn.disabled = true;

    try {
        const res = await fetch('/api/admin/catalog/export', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (result.status === 'success') {
            const data = result.report;
            if (data.length === 0) {
                alert("Nenhum arquivo encontrado no catálogo.");
                return;
            }

            // Cabeçalhos do CSV
            const headers = ["Nome do Bucket", "Nome do Arquivo", "Tipo", "Data e Hora do Upload", "Qtd. Linhas", "Qtd. Colunas", "Uploader", "Tamanho (BD)"];
            const csvRows = [headers.join(",")];

            // Inserção dos dados processados
            data.forEach(row => {
                const values = [
                    `"${row.Bucket}"`,
                    `"${row.Arquivo}"`,
                    `"${row.Tipo}"`,
                    `"${row.Data_Hora}"`,
                    `"${row.Linhas}"`,
                    `"${row.Colunas}"`,
                    `"${row.Uploader}"`,
                    `"${row.Tamanho}"`
                ];
                csvRows.push(values.join(","));
            });

            // Tratamento do Blob para Download
            const csvContent = csvRows.join("\n");
            const blob = new Blob(["\uFEFF" + csvContent], { type: 'text/csv;charset=utf-8;' }); // \uFEFF força o suporte a acentos no Excel
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');

            a.setAttribute('href', url);
            a.setAttribute('download', `datalake_inventory_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            alert("Erro ao gerar relatório: " + result.message);
        }
    } catch (e) {
        alert("Erro de comunicação ao baixar relatório.");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

init();