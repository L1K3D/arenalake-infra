/* ============================================================================
   ArenaLake — Scripts do Painel Administrativo (DBA Control Panel)
   Design System Oficial: Modais Customizados, Gestão de Acessos e Telemetria
   ============================================================================ */

function showSection(targetSection) {
    if (!targetSection) return;
    const secEl = document.getElementById('sec-' + targetSection);
    const navEl = document.getElementById('nav-' + targetSection);

    if (!secEl) return;

    document.querySelectorAll('.admin-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.menu-item').forEach(li => li.classList.remove('active'));

    secEl.classList.add('active');
    if (navEl) navEl.classList.add('active');

    if (targetSection === 'dldash') {
        carregarDataLakeDashboard();
    }

    // Persiste a aba selecionada no sessionStorage e na URL para sobreviver a F5 / Ctrl+R
    try {
        sessionStorage.setItem('arenalake_active_tab', targetSection);
        const url = new URL(window.location);
        url.searchParams.set('sec', targetSection);
        window.history.replaceState({ section: targetSection }, '', url);
    } catch (_) {}
}

function getInitialSection() {
    const params = new URLSearchParams(window.location.search);
    const urlSec = params.get('sec');
    const hashSec = window.location.hash ? window.location.hash.substring(1) : null;
    const storedSec = sessionStorage.getItem('arenalake_active_tab');

    const candidate = urlSec || hashSec || storedSec;
    if (candidate && document.getElementById('sec-' + candidate)) {
        return candidate;
    }
    return 'register';
}

const urlParams = new URLSearchParams(window.location.search);
let token = sessionStorage.getItem('access_token');
if (!token) {
    const queryToken = urlParams.get('token');
    if (queryToken) {
        token = queryToken;
        sessionStorage.setItem('access_token', token);
    }
}
if (window.location.pathname.includes('admin') && !token) {
    window.location.href = '/';
}

let loggedAdminUsername = '';
let allUsers = [];
let activeUsernames = new Set();
let currentSortCol = 'id';
let currentSortAsc = true;

function logoutAdmin() {
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('arenalake_active_tab');
    window.location.href = '/';
}

// ----------------------------------------------------------------------------
// SISTEMA DE MODAIS / POP-UPS DA IDENTIDADE VISUAL ARENALAKE
// ----------------------------------------------------------------------------
function createModalElement() {
    let backdrop = document.getElementById('arena-modal-backdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.id = 'arena-modal-backdrop';
        backdrop.className = 'arena-modal-backdrop';
        document.body.appendChild(backdrop);
    }
    backdrop.style.pointerEvents = '';
    return backdrop;
}

function arenaAlert({ title = 'Aviso', message, type = 'info' }) {
    return new Promise(resolve => {
        const backdrop = createModalElement();

        let iconClass = 'icon-info';
        let iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';

        if (type === 'success') {
            iconClass = 'icon-success';
            iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
        } else if (type === 'error' || type === 'danger') {
            iconClass = 'icon-danger';
            iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
        } else if (type === 'warning') {
            iconClass = 'icon-warning';
            iconSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
        }

        backdrop.innerHTML = `
            <div class="arena-modal-card" role="dialog" aria-modal="true">
                <div class="modal-header-row">
                    <div class="modal-icon-badge ${iconClass}">
                        ${iconSvg}
                    </div>
                    <div class="modal-title-area">
                        <h3 class="modal-title">${title}</h3>
                    </div>
                    <button class="modal-close-btn" id="modal-btn-close" aria-label="Fechar">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>
                <div class="modal-message">${message}</div>
                <div class="modal-footer">
                    <button class="btn-primary" id="modal-btn-ok">Entendi</button>
                </div>
            </div>
        `;

        requestAnimationFrame(() => backdrop.classList.add('is-visible'));

        function close() {
            window.removeEventListener('keydown', onKeyDown);
            backdrop.classList.remove('is-visible');
            backdrop.style.pointerEvents = 'none';
            setTimeout(() => {
                backdrop.remove();
                resolve();
            }, 200);
        }

        function onKeyDown(e) {
            if (e.key === 'Escape' || e.key === 'Enter') {
                close();
            }
        }

        window.addEventListener('keydown', onKeyDown);
        document.getElementById('modal-btn-ok').onclick = close;
        document.getElementById('modal-btn-close').onclick = close;
        backdrop.onclick = (e) => {
            if (e.target === backdrop) close();
        };
    });
}

function arenaConfirm({ title = 'Confirmação', message, confirmText = 'Confirmar', cancelText = 'Cancelar', isDanger = false }) {
    return new Promise(resolve => {
        const backdrop = createModalElement();

        const iconClass = isDanger ? 'icon-danger' : 'icon-warning';
        const iconSvg = isDanger
            ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
            : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>';

        const confirmBtnClass = isDanger ? 'btn-danger' : 'btn-primary';

        backdrop.innerHTML = `
            <div class="arena-modal-card" role="dialog" aria-modal="true">
                <div class="modal-header-row">
                    <div class="modal-icon-badge ${iconClass}">
                        ${iconSvg}
                    </div>
                    <div class="modal-title-area">
                        <h3 class="modal-title">${title}</h3>
                    </div>
                    <button class="modal-close-btn" id="modal-btn-close" aria-label="Fechar">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>
                <div class="modal-message">${message}</div>
                <div class="modal-footer">
                    <button class="btn-secondary" id="modal-btn-cancel">${cancelText}</button>
                    <button class="${confirmBtnClass}" id="modal-btn-confirm">${confirmText}</button>
                </div>
            </div>
        `;

        requestAnimationFrame(() => backdrop.classList.add('is-visible'));

        function finish(confirmed) {
            window.removeEventListener('keydown', onKeyDown);
            backdrop.classList.remove('is-visible');
            backdrop.style.pointerEvents = 'none';
            setTimeout(() => {
                backdrop.remove();
                resolve(confirmed);
            }, 200);
        }

        function onKeyDown(e) {
            if (e.key === 'Escape') finish(false);
        }

        window.addEventListener('keydown', onKeyDown);
        document.getElementById('modal-btn-confirm').onclick = () => finish(true);
        document.getElementById('modal-btn-cancel').onclick = () => finish(false);
        document.getElementById('modal-btn-close').onclick = () => finish(false);
        backdrop.onclick = (e) => {
            if (e.target === backdrop) finish(false);
        };
    });
}

function arenaPrompt({ title = 'Entrada de Dados', message, placeholder = '', inputType = 'text', confirmText = 'Confirmar', cancelText = 'Cancelar' }) {
    return new Promise(resolve => {
        const backdrop = createModalElement();

        backdrop.innerHTML = `
            <div class="arena-modal-card" role="dialog" aria-modal="true">
                <div class="modal-header-row">
                    <div class="modal-icon-badge icon-warning">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                    </div>
                    <div class="modal-title-area">
                        <h3 class="modal-title">${title}</h3>
                    </div>
                    <button class="modal-close-btn" id="modal-btn-close" aria-label="Fechar">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>
                <div class="modal-message">${message}</div>
                <div class="modal-input-area">
                    <input type="${inputType}" id="modal-prompt-input" placeholder="${placeholder}" autocomplete="off">
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" id="modal-btn-cancel">${cancelText}</button>
                    <button class="btn-primary" id="modal-btn-confirm">${confirmText}</button>
                </div>
            </div>
        `;

        requestAnimationFrame(() => {
            backdrop.classList.add('is-visible');
            const input = document.getElementById('modal-prompt-input');
            if (input) input.focus();
        });

        function finish(val) {
            backdrop.classList.remove('is-visible');
            backdrop.style.pointerEvents = 'none';
            setTimeout(() => {
                backdrop.remove();
                resolve(val);
            }, 200);
        }

        const input = document.getElementById('modal-prompt-input');
        input.onkeydown = (e) => {
            if (e.key === 'Enter') {
                finish(input.value);
            } else if (e.key === 'Escape') {
                finish(null);
            }
        };

        document.getElementById('modal-btn-confirm').onclick = () => finish(input.value);
        document.getElementById('modal-btn-cancel').onclick = () => finish(null);
        document.getElementById('modal-btn-close').onclick = () => finish(null);
        backdrop.onclick = (e) => {
            if (e.target === backdrop) finish(null);
        };
    });
}

// ----------------------------------------------------------------------------
// EXPORTAÇÃO DE USUÁRIOS (CSV)
// ----------------------------------------------------------------------------
function downloadCSV() {
    if (!allUsers || allUsers.length === 0) {
        arenaAlert({ title: 'Exportação', message: 'Nenhum usuário encontrado para download.', type: 'info' });
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

// ----------------------------------------------------------------------------
// GESTÃO DE WORKSPACES
// ----------------------------------------------------------------------------
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
                tbody.innerHTML = '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--arena-text-muted);">Nenhum workspace ativo no momento.</td></tr>';
                return;
            }

            data.workspaces.forEach(w => {
                tbody.innerHTML += `
                    <tr>
                        <td style="color: var(--arena-blue); font-weight: 600; font-family: var(--font-mono);">${w.username}</td>
                        <td style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--arena-text-muted);">${w.service_name}</td>
                        <td style="font-family: var(--font-mono); font-size: 0.85rem;">${w.cpu} | ${w.ram}</td>
                        <td style="text-align: right;">
                            <button onclick="killWorkspace('${w.username}')" class="btn-danger" style="padding: 5px 12px; font-size: 0.82rem;">Encerrar Sessão</button>
                        </td>
                    </tr>
                `;
            });
        }
    } catch (e) {
        console.error('Erro ao carregar workspaces:', e);
    }
}

async function killWorkspace(username) {
    const confirmed = await arenaConfirm({
        title: 'Encerrar Workspace',
        message: `Deseja realmente derrubar a sessão ativa e o container do colaborador '${username}'?`,
        confirmText: 'Encerrar Sessão',
        cancelText: 'Cancelar',
        isDanger: true
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/admin/workspaces/kill/${username}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (res.ok) {
            await arenaAlert({ title: 'Sessão Encerrada', message: result.message || 'Workspace derrubado com sucesso.', type: 'success' });
            carregarWorkspaces();
        } else {
            await arenaAlert({ title: 'Erro ao Encerrar', message: result.detail || 'Não foi possível derrubar o workspace.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação ao tentar encerrar a sessão.', type: 'error' });
    }
}

// ----------------------------------------------------------------------------
// GESTÃO DE USUÁRIOS
// ----------------------------------------------------------------------------
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
                const label = document.getElementById('expectedPhraseLabel');
                if (label) label.innerText = `DELETE ACCOUNT ${loggedAdminUsername}`;
            }

            renderUserTable();
        }
    } catch (e) {
        console.error('Erro ao carregar usuários:', e);
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
    const onlineCount = sortedUsers.filter(u => activeUsernames.has(u.username.toLowerCase().replace(/[^a-z0-9-]/g, '-'))).length;

    document.getElementById('kpi-total').innerText = total;
    document.getElementById('kpi-admins').innerText = `${admins} (${Math.round((admins / total) * 100)}%)`;
    document.getElementById('kpi-common').innerText = `${common} (${Math.round((common / total) * 100)}%)`;
    document.getElementById('kpi-online').innerText = onlineCount;

    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = '';

    if (sortedUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--arena-text-muted);">Nenhum colaborador registrado. Utilize o formulário para criar o primeiro acesso.</td></tr>';
        return;
    }

    sortedUsers.forEach(u => {
        let actionBtn = '';
        if (u.role !== 'admin') {
            actionBtn = `
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                    <button onclick="resetarSenha(${u.id}, '${u.username}')" class="btn-secondary" style="padding: 5px 10px; font-size: 0.8rem;">Redefinir Senha</button>
                    <button onclick="deletarUsuario(${u.id}, '${u.username}')" class="btn-danger" style="padding: 5px 10px; font-size: 0.8rem;">Excluir</button>
                </div>
            `;
        } else {
            actionBtn = `<div style="display: flex; justify-content: flex-end;"><span style="color: var(--arena-text-dim); font-size: 0.8rem; font-style: italic;">Protegido</span></div>`;
        }

        const isOnline = activeUsernames.has(u.username.toLowerCase().replace(/[^a-z0-9-]/g, '-'));
        const statusDot = isOnline
            ? '<span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--arena-ok); margin-right: 6px; vertical-align: middle; box-shadow: 0 0 6px var(--arena-ok);" title="Online"></span>'
            : '<span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--arena-text-dim); margin-right: 6px; vertical-align: middle;" title="Offline"></span>';

        const email = u.email || 'N/A';
        const roleBadge = u.role === 'admin' 
            ? '<span class="badge badge-admin">ADMIN</span>' 
            : '<span class="badge badge-common">COMMON</span>';

        tbody.innerHTML += `
            <tr>
                <td style="font-family: var(--font-mono); font-size: 0.85rem;">${statusDot} #${u.id}</td>
                <td style="color: var(--arena-blue); font-weight: 600;">${u.username}</td>
                <td style="color: var(--arena-text-muted); font-size: 0.85rem;">${email}</td>
                <td>${u.full_name}</td>
                <td>${roleBadge}</td>
                <td style="font-size: 0.85rem;">${u.is_2fa_verified ? '<span style="color: var(--arena-ok); font-weight: 500;">Verificado</span>' : '<span style="color: var(--arena-warning); font-weight: 500;">Pendente</span>'}</td>
                <td style="text-align: right;">${actionBtn}</td>
            </tr>
        `;
    });
}

async function deletarUsuario(userId, username) {
    const confirmed = await arenaConfirm({
        title: 'Excluir Colaborador',
        message: `Tem certeza que deseja excluir permanentemente o acesso de '${username}'? Esta operação não pode ser revertida.`,
        confirmText: 'Excluir Usuário',
        cancelText: 'Cancelar',
        isDanger: true
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (res.ok) {
            await arenaAlert({ title: 'Sucesso', message: result.message || 'Usuário excluído com sucesso.', type: 'success' });
            carregarUsuarios();
        } else {
            await arenaAlert({ title: 'Erro ao Excluir', message: result.detail || 'Não foi possível excluir o usuário.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação ao tentar excluir o usuário.', type: 'error' });
    }
}

async function resetarSenha(userId, username) {
    const novaSenha = await arenaPrompt({
        title: 'Redefinir Senha do Colaborador',
        message: `Informe uma nova senha temporária para '${username}' (mínimo de 8 caracteres):`,
        placeholder: '••••••••••••',
        inputType: 'password',
        confirmText: 'Salvar Nova Senha',
        cancelText: 'Cancelar'
    });

    if (!novaSenha) return;

    if (novaSenha.length < 8) {
        await arenaAlert({
            title: 'Senha Inválida',
            message: 'A senha temporária deve conter no mínimo 8 caracteres.',
            type: 'warning'
        });
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
            await arenaAlert({
                title: 'Senha Redefinida',
                message: result.message || `A senha de '${username}' foi redefinida com sucesso.`,
                type: 'success'
            });
            carregarUsuarios();
        } else {
            await arenaAlert({
                title: 'Erro ao Redefinir',
                message: result.detail || 'Não foi possível redefinir a senha.',
                type: 'error'
            });
        }
    } catch (e) {
        await arenaAlert({
            title: 'Erro de Conexão',
            message: 'Falha de comunicação ao tentar redefinir a senha.',
            type: 'error'
        });
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

    try {
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
            await arenaAlert({ title: 'Acesso Criado', message: result.message || 'Colaborador registrado com sucesso no ecossistema.', type: 'success' });
            document.getElementById('createUserForm').reset();
            carregarUsuarios();
        } else {
            await arenaAlert({ title: 'Erro no Registro', message: result.detail || 'Não foi possível cadastrar o colaborador.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação com o servidor.', type: 'error' });
    }
});

// ----------------------------------------------------------------------------
// TELEMETRIA DO CLUSTER SWARM
// ----------------------------------------------------------------------------
async function carregarClusterNodes() {
    try {
        const res = await fetch('/api/admin/cluster/nodes', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (data.status === 'success') {
            const tbody = document.getElementById('nodesTableBody');
            tbody.innerHTML = '';

            if (!data.nodes || data.nodes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--arena-text-muted);">Nenhum nó do Swarm detectado ou cluster offline.</td></tr>';
                document.getElementById('kpi-nodes-count').innerText = "0 / 0";
                document.getElementById('kpi-total-cpu').innerText = "0";
                document.getElementById('kpi-total-ram').innerText = "0 GB";
                const healthEl = document.getElementById('kpi-cluster-health');
                healthEl.innerText = "Offline";
                healthEl.style.color = "var(--arena-text-dim)";
                return;
            }

            let totalCpus = 0;
            let totalRam = 0;
            let activeNodes = 0;

            let countIntel = 0;
            let countAmd = 0;
            let countOutros = 0;

            data.nodes.forEach(n => {
                totalCpus += n.cpus;
                totalRam += n.memory_gb;
                if (n.status === 'ready') activeNodes++;

                const hasTelemetry = n.cpu_percent !== undefined && n.ram_percent !== undefined;

                if (hasTelemetry) {
                    if (n.marca_cpu === 'Intel') countIntel++;
                    else if (n.marca_cpu === 'AMD') countAmd++;
                    else countOutros++;
                }

                // 1. Identificação do Nó
                const nodeCell = `
                    <td>
                        <div class="node-hostname">${n.hostname}</div>
                        <div class="node-id-sub">#${n.id}</div>
                    </td>
                `;

                // 2. Função no Cluster
                const roleBadge = n.role === 'MANAGER'
                    ? '<span class="badge badge-admin">MANAGER</span>'
                    : '<span class="badge badge-common">WORKER</span>';
                const roleCell = `<td class="col-center">${roleBadge}</td>`;

                // 3. Processador (Hardware)
                let brandTagClass = 'cpu-brand-other';
                if (n.marca_cpu === 'Intel') brandTagClass = 'cpu-brand-intel';
                else if (n.marca_cpu === 'AMD') brandTagClass = 'cpu-brand-amd';

                let processorCell;
                if (hasTelemetry && n.modelo_cpu) {
                    const cleanModel = n.modelo_cpu
                        .replace('Intel(R) Core(TM) ', 'Core ')
                        .replace('AMD ', '');
                    const threadInfo = n.threads ? `${n.threads} Threads • ` : '';
                    processorCell = `
                        <td>
                            <div class="cpu-cell">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <span class="cpu-brand-tag ${brandTagClass}">${n.marca_cpu || 'CPU'}</span>
                                    <span class="cpu-model-title">${cleanModel}</span>
                                </div>
                                <div style="font-size: 0.74rem; font-family: var(--font-mono); color: var(--arena-text-dim); margin-top: 2px;">
                                    ${threadInfo}${n.cpus} Cores
                                </div>
                            </div>
                        </td>
                    `;
                } else {
                    processorCell = `
                        <td>
                            <div class="cpu-cell">
                                <span style="color: var(--arena-text-dim); font-size: 0.82rem; font-style: italic;">Indisponível</span>
                                <div style="font-size: 0.74rem; font-family: var(--font-mono); color: var(--arena-text-dim); margin-top: 2px;">
                                    ${n.cpus} Cores
                                </div>
                            </div>
                        </td>
                    `;
                }

                // 4. Status em Destaque
                const isReady = n.status === 'ready';
                const statusBadge = isReady
                    ? '<span class="node-status-badge status-operational"><span class="status-pulse-dot"></span>Operacional</span>'
                    : '<span class="node-status-badge status-inactive"><span class="status-inactive-dot"></span>Inativo</span>';
                const statusCell = `<td>${statusBadge}</td>`;

                // 5. Consumo de CPU
                let cpuCell;
                if (hasTelemetry) {
                    const cpuUsed = ((n.cpu_percent / 100) * n.cpus).toFixed(1);
                    const cpuColor = n.cpu_percent > 85 ? 'fill-danger' : (n.cpu_percent > 65 ? 'fill-warning' : 'fill-normal');
                    const cpuPctColor = n.cpu_percent > 85 ? 'var(--arena-danger)' : (n.cpu_percent > 65 ? 'var(--arena-orange)' : 'var(--arena-text-main)');
                    cpuCell = `
                        <td>
                            <div class="resource-metric-box">
                                <div class="resource-header-row">
                                    <span class="resource-pct" style="color: ${cpuPctColor};">${n.cpu_percent}%</span>
                                    <span class="resource-val">${cpuUsed} / ${n.cpus} cores</span>
                                </div>
                                <div class="progress-bg">
                                    <div class="progress-fill ${cpuColor}" style="width: ${n.cpu_percent}%;"></div>
                                </div>
                            </div>
                        </td>
                    `;
                } else {
                    cpuCell = `
                        <td>
                            <div class="resource-metric-box">
                                <div class="resource-header-row">
                                    <span class="resource-pct" style="color: var(--arena-text-dim);">--%</span>
                                    <span class="resource-val">${n.cpus} Cores</span>
                                </div>
                                <div class="progress-bg">
                                    <div class="progress-fill" style="width: 0%; background: var(--arena-lines);"></div>
                                </div>
                            </div>
                        </td>
                    `;
                }

                // 6. Consumo de Memória RAM
                let ramCell;
                if (hasTelemetry) {
                    const ramUsed = ((n.ram_percent / 100) * n.memory_gb).toFixed(1);
                    const ramColor = n.ram_percent > 85 ? 'fill-danger' : (n.ram_percent > 65 ? 'fill-warning' : 'fill-normal');
                    const ramPctColor = n.ram_percent > 85 ? 'var(--arena-danger)' : (n.ram_percent > 65 ? 'var(--arena-orange)' : 'var(--arena-text-main)');
                    ramCell = `
                        <td>
                            <div class="resource-metric-box">
                                <div class="resource-header-row">
                                    <span class="resource-pct" style="color: ${ramPctColor};">${n.ram_percent}%</span>
                                    <span class="resource-val">${ramUsed} / ${n.memory_gb} GB</span>
                                </div>
                                <div class="progress-bg">
                                    <div class="progress-fill ${ramColor}" style="width: ${n.ram_percent}%;"></div>
                                </div>
                            </div>
                        </td>
                    `;
                } else {
                    ramCell = `
                        <td>
                            <div class="resource-metric-box">
                                <div class="resource-header-row">
                                    <span class="resource-pct" style="color: var(--arena-text-dim);">--%</span>
                                    <span class="resource-val">${n.memory_gb} GB</span>
                                </div>
                                <div class="progress-bg">
                                    <div class="progress-fill" style="width: 0%; background: var(--arena-lines);"></div>
                                </div>
                            </div>
                        </td>
                    `;
                }

                // 7. Armazenamento (Disco)
                let storageCell;
                if (hasTelemetry && n.disk_gb > 0) {
                    const diskPercent = ((n.disk_usado_gb / n.disk_gb) * 100).toFixed(1);
                    const diskColor = diskPercent > 85 ? 'fill-danger' : (diskPercent > 65 ? 'fill-warning' : 'fill-normal');
                    const diskPctColor = diskPercent > 85 ? 'var(--arena-danger)' : (diskPercent > 65 ? 'var(--arena-orange)' : 'var(--arena-text-main)');
                    storageCell = `
                        <td>
                            <div class="resource-metric-box">
                                <div class="resource-header-row">
                                    <span class="resource-pct" style="color: ${diskPctColor};">${diskPercent}%</span>
                                    <span class="resource-val">${n.disk_usado_gb} / ${n.disk_gb} GB</span>
                                </div>
                                <div class="progress-bg">
                                    <div class="progress-fill ${diskColor}" style="width: ${diskPercent}%;"></div>
                                </div>
                            </div>
                        </td>
                    `;
                } else {
                    storageCell = `
                        <td>
                            <div class="resource-metric-box">
                                <div class="resource-header-row">
                                    <span class="resource-pct" style="color: var(--arena-text-dim);">--%</span>
                                    <span class="resource-val">Offline</span>
                                </div>
                                <div class="progress-bg">
                                    <div class="progress-fill" style="width: 0%; background: var(--arena-lines);"></div>
                                </div>
                            </div>
                        </td>
                    `;
                }

                tbody.innerHTML += `
                    <tr>
                        ${nodeCell}
                        ${roleCell}
                        ${processorCell}
                        ${statusCell}
                        ${cpuCell}
                        ${ramCell}
                        ${storageCell}
                    </tr>
                `;
            });

            document.getElementById('kpi-nodes-count').innerText = `${activeNodes} / ${data.nodes.length}`;
            document.getElementById('kpi-total-cpu').innerText = totalCpus;
            document.getElementById('kpi-total-ram').innerText = `${totalRam.toFixed(1)} GB`;

            const healthEl = document.getElementById('kpi-cluster-health');
            if (activeNodes === data.nodes.length && activeNodes > 0) {
                healthEl.innerText = "Saudável";
                healthEl.style.color = "var(--arena-ok)";
            } else if (activeNodes > 0) {
                healthEl.innerText = "Degradado";
                healthEl.style.color = "var(--arena-warning)";
            } else {
                healthEl.innerText = "Crítico";
                healthEl.style.color = "var(--arena-danger)";
            }

            const totalCpusWithTelemetry = countIntel + countAmd + countOutros;
            const intelPct = totalCpusWithTelemetry > 0 ? Math.round((countIntel / totalCpusWithTelemetry) * 100) : 0;
            const amdPct = totalCpusWithTelemetry > 0 ? Math.round((countAmd / totalCpusWithTelemetry) * 100) : 0;
            const outrosPct = totalCpusWithTelemetry > 0 ? Math.round((countOutros / totalCpusWithTelemetry) * 100) : 0;

            document.getElementById('kpi-cpu-intel').innerHTML = `Intel: ${countIntel} <span style="font-size: 0.6em; color: var(--arena-text-dim);">(${intelPct}%)</span>`;
            document.getElementById('kpi-cpu-amd').innerHTML = `AMD: ${countAmd} <span style="font-size: 0.6em; color: var(--arena-text-dim);">(${amdPct}%)</span>`;
            document.getElementById('kpi-cpu-outros').innerHTML = `Outros: ${countOutros} <span style="font-size: 0.6em; color: var(--arena-text-dim);">(${outrosPct}%)</span>`;
        }
    } catch (e) {
        console.error('Erro ao carregar telemetria do cluster:', e);
    }
}

// ----------------------------------------------------------------------------
// AUDITORIA DE ARQUIVOS (FILE SPY)
// ----------------------------------------------------------------------------
async function auditarArquivos() {
    const username = document.getElementById('auditUsername').value.trim();
    const outputBox = document.getElementById('auditOutput');
    if (!username) {
        await arenaAlert({ title: 'Atenção', message: 'Por favor, informe um nome de usuário para auditoria.', type: 'warning' });
        return;
    }

    outputBox.style.display = 'block';
    outputBox.innerText = 'Consultando arquivos no volume persistente do usuário...';

    try {
        const res = await fetch(`/api/admin/files/${username}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (res.ok) {
            outputBox.innerText = data.files.length > 0 ? data.files.join('\n') : 'Nenhum arquivo encontrado no volume.';
        } else {
            outputBox.innerText = 'Erro: ' + (data.detail || 'Não foi possível inspecionar o volume.');
        }
    } catch (e) {
        outputBox.innerText = 'Falha de comunicação ao inspecionar o volume.';
    }
}

// ----------------------------------------------------------------------------
// AUTODESTRUIÇÃO DO CLUSTER
// ----------------------------------------------------------------------------
async function executarAutodestruicao() {
    const confirmUser = document.getElementById('confirmDestroyUser').value.trim();
    if (!confirmUser) {
        await arenaAlert({ title: 'Atenção', message: 'Você precisa digitar seu nome de usuário para confirmar a autodestruição.', type: 'warning' });
        return;
    }

    const confirmed = await arenaConfirm({
        title: 'Autodestruição Crítica',
        message: 'AVISO CRÍTICO: Você tem certeza absoluta que deseja purgar todas as sessões e workspaces ativos em todo o cluster?',
        confirmText: 'Executar Autodestruição',
        cancelText: 'Cancelar',
        isDanger: true
    });
    if (!confirmed) return;

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
            await arenaAlert({ title: 'Comando Concluído', message: result.message || 'Todos os containers foram expurgados.', type: 'success' });
            document.getElementById('confirmDestroyUser').value = '';
            carregarWorkspaces();
        } else {
            await arenaAlert({ title: 'Erro Crítico', message: result.detail || 'Não foi possível executar a autodestruição.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação com o cluster.', type: 'error' });
    }
}

// ----------------------------------------------------------------------------
// DATA CATALOG (MINIO)
// ----------------------------------------------------------------------------
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
        console.error('Erro ao carregar Data Catalog:', e);
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

    // --- NOVO: Popula também o Dropdown de Buckets do Gateway ---
    const gwBucketSelect = document.getElementById('gwBucket');
    if (gwBucketSelect) {
        const currentGwSelection = gwBucketSelect.value;
        let gwOptionsHtml = '<option value="">Selecione o Bucket de Destino...</option>';
        buckets.forEach(b => {
            gwOptionsHtml += `<option value="${b}">📦 ${b}</option>`;
        });
        gwBucketSelect.innerHTML = gwOptionsHtml;
        if (currentGwSelection && buckets.includes(currentGwSelection)) {
            gwBucketSelect.value = currentGwSelection;
        }
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
        container.innerHTML = '<div style="background: var(--arena-surface-input); border: 1px dashed var(--arena-lines); border-radius: var(--r-md); padding: 32px; text-align: center; color: var(--arena-text-muted);"><div style="font-weight: 600; margin-bottom: 6px; color: var(--arena-text-main);">Nenhum bucket encontrado no MinIO</div><div>Crie um novo bucket acima para começar a armazenar datasets.</div></div>';
        return;
    }

    if (filter !== "all") {
        bucketsToRender = [filter];
    }

    bucketsToRender.forEach(bucket => {
        let filesHtml = '';
        const files = globalAdminCatalog[bucket];

        if (files.length === 0) {
            filesHtml = '<tr><td colspan="2" style="padding: 14px; color: var(--arena-text-dim); font-style: italic;">Bucket vazio.</td></tr>';
        } else {
            files.forEach(file => {
                filesHtml += `
                    <tr>
                        <td style="font-family: var(--font-mono); color: var(--arena-blue); font-size: 0.85rem;">${file}</td>
                        <td style="text-align: right; white-space: nowrap;">
                            <button type="button" onclick="abrirPreview('${bucket}', '${file}')" class="btn-secondary" style="padding: 4px 10px; font-size: 0.78rem; margin-right: 6px;">Preview</button>
                            <button type="button" onclick="deletarArquivoCatalog('${bucket}', '${file}')" class="btn-danger" style="padding: 4px 10px; font-size: 0.78rem;">Excluir</button>
                        </td>
                    </tr>
                `;
            });
        }

        container.innerHTML += `
            <div style="background: var(--arena-surface-input); border: 1px solid var(--arena-lines); border-radius: var(--r-md); padding: 16px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--arena-lines); flex-wrap: wrap; gap: 8px;">
                    <h4 style="margin: 0; color: var(--arena-text-main); font-size: 0.95rem; font-family: var(--font-mono); display: flex; align-items: center; gap: 8px;">
                        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" style="color: var(--arena-blue);"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                        <span>${bucket}</span>
                    </h4>
                    <button type="button" onclick="deletarBucketAdmin('${bucket}')" class="btn-danger" style="padding: 3px 10px; font-size: 0.78rem;">Excluir Bucket</button>
                </div>
                <table style="width: 100%;">
                    <tbody>${filesHtml}</tbody>
                </table>
            </div>
        `;
    });
}

async function deletarBucketAdmin(bucket) {
    const confirmed = await arenaConfirm({
        title: 'Excluir Bucket',
        message: `ATENÇÃO: Você está prestes a excluir o bucket '${bucket}'. Isso removerá todos os arquivos e partições contidos nele no MinIO.`,
        confirmText: 'Prosseguir',
        cancelText: 'Cancelar',
        danger: true
    });
    if (!confirmed) return;

    const confirmacao = await arenaPrompt({
        title: 'Confirmação de Segurança',
        message: `Para confirmar a exclusão definitiva, digite o nome exato do bucket (${bucket}):`,
        placeholder: bucket,
        confirmText: 'Excluir Bucket Definitivamente',
        cancelText: 'Cancelar'
    });

    if (confirmacao !== bucket) {
        await arenaAlert({ title: 'Operação Cancelada', message: 'Nome digitado não confere. Exclusão cancelada por segurança.', type: 'warning' });
        return;
    }

    try {
        const res = await fetch(`/api/admin/catalog/bucket/${bucket}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (res.ok) {
            await arenaAlert({ title: 'Bucket Excluído', message: result.message || 'Bucket excluído com sucesso.', type: 'success' });
            document.getElementById('bucketDropdown').value = 'all';
            carregarDataCatalog();
        } else {
            await arenaAlert({ title: 'Erro ao Excluir', message: result.detail || 'Não foi possível excluir o bucket.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação ao tentar excluir o bucket.', type: 'error' });
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
        await arenaAlert({ title: 'Atenção', message: 'Informe um nome válido para o novo bucket.', type: 'warning' });
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
            await arenaAlert({ title: 'Bucket Criado', message: result.message || 'Bucket criado com sucesso!', type: 'success' });
            input.value = "";

            carregarDataCatalog().then(() => {
                const cleanName = bucketName.toLowerCase().replace(/_/g, "-");
                document.getElementById('bucketDropdown').value = cleanName;
                renderizarCatalog();
            });
        } else {
            await arenaAlert({ title: 'Erro ao Criar Bucket', message: result.detail || 'Não foi possível criar o bucket.', type: 'error' });
        }
    } catch (error) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação ao criar o bucket.', type: 'error' });
    }
}

async function deletarArquivoCatalog(bucket, filename) {
    const confirmed = await arenaConfirm({
        title: 'Excluir Arquivo do Data Lake',
        message: `Deseja realmente excluir permanentemente o arquivo '${filename}' do bucket '${bucket}'?`,
        confirmText: 'Excluir Arquivo',
        cancelText: 'Cancelar',
        isDanger: true
    });
    if (!confirmed) return;

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
            await arenaAlert({ title: 'Arquivo Excluído', message: result.message || 'Arquivo removido com sucesso.', type: 'success' });
            carregarDataCatalog();
        } else {
            await arenaAlert({ title: 'Erro ao Excluir', message: result.detail || 'Falha ao remover o objeto.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação com o serviço MinIO.', type: 'error' });
    }
}

document.getElementById('uploadCatalogForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const bucket = document.getElementById('bucketDropdown').value;
    const fileInput = document.getElementById('uploadFile').files[0];

    if (bucket === "all" || !bucket) {
        await arenaAlert({ title: 'Atenção', message: 'Selecione um bucket específico para fazer o upload do arquivo.', type: 'warning' });
        document.getElementById('bucketDropdown').focus();
        return;
    }

    if (!fileInput) {
        await arenaAlert({ title: 'Atenção', message: 'Selecione um arquivo para upload.', type: 'warning' });
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
            await arenaAlert({ title: 'Upload Concluído', message: result.message || 'Arquivo enviado com sucesso para o Data Lake.', type: 'success' });
            document.getElementById('uploadFile').value = '';
            carregarDataCatalog();
        } else {
            await arenaAlert({ title: 'Erro no Upload', message: result.detail || 'Falha ao enviar arquivo.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação com o servidor de storage.', type: 'error' });
    }
});

// ----------------------------------------------------------------------------
// EXCLUSÃO DA CONTA DE ADMIN
// ----------------------------------------------------------------------------
async function executarAutodelecao() {
    const inputVal = document.getElementById('selfDeleteInput').value.trim();

    const confirmed = await arenaConfirm({
        title: 'Excluir Minha Conta de Administrador',
        message: 'AVISO: Você tem certeza que deseja excluir sua própria conta de administrador? Esta ação é irreversível!',
        confirmText: 'Excluir Minha Conta',
        cancelText: 'Cancelar',
        isDanger: true
    });
    if (!confirmed) return;

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
            await arenaAlert({ title: 'Conta Excluída', message: result.message || 'Sua conta foi excluída com sucesso.', type: 'info' });
            sessionStorage.removeItem('access_token');
            window.location.href = '/';
        } else {
            await arenaAlert({ title: 'Erro na Exclusão', message: result.detail || 'Não foi possível excluir sua conta.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação com o servidor.', type: 'error' });
    }
}

// ----------------------------------------------------------------------------
// REDE TAILSCALE E WEB TERMINAL
// ----------------------------------------------------------------------------
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

            if (!data.network || data.network.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="padding: 32px; text-align: center; color: var(--arena-text-muted);">Nenhuma máquina conectada à malha Tailscale no momento.</td></tr>';
                return;
            }

            data.network.forEach(node => {
                const statusBadge = node.status === 'Connected' 
                    ? '<span style="display: inline-flex; align-items: center; gap: 6px; color: var(--arena-ok); font-weight: 600;"><span style="width: 6px; height: 6px; border-radius: 50%; background: var(--arena-ok); box-shadow: 0 0 6px var(--arena-ok);"></span>Conectado</span>' 
                    : '<span style="display: inline-flex; align-items: center; gap: 6px; color: var(--arena-text-dim);"><span style="width: 6px; height: 6px; border-radius: 50%; background: var(--arena-text-dim);"></span>Desconectado</span>';

                tbody.innerHTML += `
                    <tr>
                        <td>
                            <div style="color: var(--arena-text-main); font-weight: 600; font-family: var(--font-mono);">${node.hostname} ${node.is_self ? '<span style="font-size: 0.68rem; background: var(--arena-surface-input); border: 1px solid var(--arena-lines); padding: 1px 6px; border-radius: 4px; color: var(--arena-orange); margin-left: 6px;">Este Nó</span>' : ''}</div>
                            <div style="font-size: 0.75rem; margin-top: 4px;">
                                <span class="badge badge-common">tag:servers</span>
                            </div>
                        </td>
                        <td style="font-family: var(--font-mono); color: var(--arena-blue); font-size: 0.85rem;">
                            ${node.ip}
                        </td>
                        <td style="color: var(--arena-text-muted); font-size: 0.85rem;">
                            v${node.version} · ${node.os}
                        </td>
                        <td style="font-size: 0.85rem;">
                            ${statusBadge}
                        </td>
                    </tr>
                `;

                if (node.status === 'Connected') {
                    select.innerHTML += `<option value="${node.ip}">${node.hostname} (${node.ip})</option>`;
                }
            });
        }
    } catch (e) {
        console.error('Erro ao carregar rede Tailscale:', e);
    }
}

async function addTailscaleNode() {
    const link = document.getElementById('ts-add-link').value.trim();
    if (!link) {
        await arenaAlert({ title: 'Atenção', message: 'Por favor, cole o link de autenticação do Tailscale primeiro.', type: 'warning' });
        return;
    }
    window.open(link, '_blank');
}

let currentTerm = null;
let currentWs = null;

async function openWebTerminal() {
    const ip = document.getElementById('ts-terminal-select').value;
    if (!ip) {
        await arenaAlert({ title: 'Atenção', message: 'Selecione um servidor na lista para conectar via SSH.', type: 'warning' });
        return;
    }

    document.getElementById('terminal-container').style.display = 'block';
    document.getElementById('terminal-title').innerText = `Root Shell: root@${ip}`;

    const screen = document.getElementById('terminal-screen');
    screen.innerHTML = '';

    currentTerm = new Terminal({
        cursorBlink: true,
        fontFamily: 'JetBrains Mono, Consolas, monospace',
        theme: { 
            background: '#090c12',
            foreground: '#f8fafc',
            cursor: '#f39200'
        }
    });
    const fitAddon = new FitAddon.FitAddon();
    currentTerm.loadAddon(fitAddon);
    currentTerm.open(screen);
    fitAddon.fit();

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    currentWs = new WebSocket(`${wsProtocol}//${window.location.host}/api/admin/terminal/${ip}?token=${token}`);

    currentWs.onopen = () => {
        currentTerm.write(`\r\n[ ArenaLake Web Terminal ] Conectando via SSH em ${ip}...\r\n`);
    };

    currentWs.onmessage = (event) => {
        currentTerm.write(event.data);
    };

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

// =========================================================
// DATALAKE DASHBOARD MGR
// =========================================================
let chartBucketsInst = null;
let chartTypesInst = null;
let chartBytesInst = null;

function formatBytesLabel(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function carregarDataLakeDashboard() {
    try {
        const res = await fetch('/api/admin/catalog/dashboard', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        const data = (result && result.status === 'success' && result.data) ? result.data : null;

        if (data) {
            document.getElementById('kpi-dl-size').innerText = data.total_bytes_fmt || '0 B';
            document.getElementById('kpi-dl-files').innerText = data.total_files ?? '0';
            document.getElementById('kpi-dl-buckets').innerText = data.total_buckets ?? '0';

            let topUser = "Nenhum";
            let topUserMax = 0;
            for (const [user, count] of Object.entries(data.files_by_uploader || {})) {
                if (count > topUserMax && user !== "Desconhecido") {
                    topUserMax = count;
                    topUser = user;
                }
            }
            document.getElementById('kpi-dl-topuser').innerText = topUser;

            Chart.defaults.color = '#8b949e';
            Chart.defaults.borderColor = '#30363d';
            const colors = ['#007acc', '#22c55e', '#a855f7', '#eab308', '#ef4444', '#38bdf8', '#f97316'];

            if (chartBucketsInst) chartBucketsInst.destroy();
            if (chartTypesInst) chartTypesInst.destroy();
            if (chartBytesInst) chartBytesInst.destroy();

            const canvasBuckets = document.getElementById('chartBuckets');
            if (canvasBuckets) {
                chartBucketsInst = new Chart(canvasBuckets.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: Object.keys(data.files_by_bucket || {}),
                        datasets: [{
                            label: 'Qtd. de Arquivos',
                            data: Object.values(data.files_by_bucket || {}),
                            backgroundColor: colors[0],
                            borderRadius: 4
                        }]
                    },
                    options: { responsive: true, plugins: { legend: { display: false } } }
                });
            }

            const canvasTypes = document.getElementById('chartTypes');
            if (canvasTypes) {
                chartTypesInst = new Chart(canvasTypes.getContext('2d'), {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(data.files_by_type || {}).map(x => x.toUpperCase()),
                        datasets: [{
                            data: Object.values(data.files_by_type || {}),
                            backgroundColor: colors,
                            borderWidth: 1,
                            borderColor: '#0b1424'
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
            }

            const canvasBytes = document.getElementById('chartBytes');
            if (canvasBytes) {
                chartBytesInst = new Chart(canvasBytes.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: Object.keys(data.bytes_by_type || {}).map(x => x.toUpperCase()),
                        datasets: [{
                            label: 'Volume em Bytes',
                            data: Object.values(data.bytes_by_type || {}),
                            backgroundColor: colors[2],
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function (context) { return formatBytesLabel(context.raw); }
                                }
                            },
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                ticks: { callback: function (value) { return formatBytesLabel(value); } }
                            }
                        }
                    }
                });
            }
        } else {
            // Storage vazio ou offline
            document.getElementById('kpi-dl-size').innerText = '0 B';
            document.getElementById('kpi-dl-files').innerText = '0';
            document.getElementById('kpi-dl-buckets').innerText = '0';
            document.getElementById('kpi-dl-topuser').innerText = 'Sem dados';

            renderEmptyDLDashboard();
        }
    } catch (e) {
        console.error("Erro ao carregar o dashboard do datalake", e);
        document.getElementById('kpi-dl-size').innerText = '0 B';
        document.getElementById('kpi-dl-files').innerText = '0';
        document.getElementById('kpi-dl-buckets').innerText = '0';
        document.getElementById('kpi-dl-topuser').innerText = 'Offline';
        renderEmptyDLDashboard();
    }
}

function renderEmptyDLDashboard() {
    if (chartBucketsInst) chartBucketsInst.destroy();
    if (chartTypesInst) chartTypesInst.destroy();
    if (chartBytesInst) chartBytesInst.destroy();

    const canvasBuckets = document.getElementById('chartBuckets');
    if (canvasBuckets) {
        chartBucketsInst = new Chart(canvasBuckets.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Nenhum Bucket'],
                datasets: [{
                    label: 'Arquivos',
                    data: [0],
                    backgroundColor: ['rgba(0, 122, 204, 0.25)'],
                    borderColor: ['#007acc'],
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                scales: {
                    y: { beginAtZero: true, max: 5, ticks: { stepSize: 1 } }
                }
            }
        });
    }

    const canvasTypes = document.getElementById('chartTypes');
    if (canvasTypes) {
        chartTypesInst = new Chart(canvasTypes.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Sem Arquivos'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['rgba(139, 148, 158, 0.15)'],
                    borderWidth: 1,
                    borderColor: '#30363d'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { enabled: false }
                }
            }
        });
    }

    const canvasBytes = document.getElementById('chartBytes');
    if (canvasBytes) {
        chartBytesInst = new Chart(canvasBytes.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Nenhum Registro'],
                datasets: [{
                    label: 'Bytes',
                    data: [0],
                    backgroundColor: ['rgba(168, 85, 247, 0.25)'],
                    borderColor: ['#a855f7'],
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                scales: {
                    y: { beginAtZero: true, max: 100 }
                }
            }
        });
    }
}

function baixarDashboardImagem() {
    const targetElement = document.getElementById('dashboard-export-area');
    if (!targetElement) return;

    html2canvas(targetElement, {
        backgroundColor: '#0b1424',
        scale: 2
    }).then(canvas => {
        const link = document.createElement('a');
        link.download = `datalake_dashboard_${new Date().toISOString().split('T')[0]}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    });
}

// =========================================================
// INICIALIZAÇÃO
// =========================================================
async function init() {
    // 1. Restaura imediatamente a aba em que o usuário estava (sem aguardar rede)
    const initialSec = getInitialSection();
    showSection(initialSec);

    // 2. Carrega todos os dados do painel em segundo plano
    carregarDataCatalog();
    carregarDataLakeDashboard();
    carregarGatewayEndpoints();
    carregarTailscale();
    await Promise.allSettled([
        carregarWorkspaces(),
        carregarUsuarios(),
        carregarClusterNodes()
    ]);

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
                await arenaAlert({ title: 'Exportação', message: 'Nenhum arquivo encontrado no catálogo para exportar.', type: 'info' });
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
            await arenaAlert({ title: "Erro na Exportação", message: result.message || "Erro ao gerar relatório.", type: "error" });
        }
    } catch (e) {
        await arenaAlert({ title: "Erro de Conexão", message: "Falha de comunicação ao baixar relatório.", type: "error" });
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// =========================================================
// API INGESTION GATEWAY MGR
// =========================================================
async function carregarGatewayEndpoints() {
    try {
        const res = await fetch('/api/admin/gateway/endpoints', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (result.status === 'success') {
            const tbody = document.getElementById('gwTableBody');
            tbody.innerHTML = '';

            if (!result.data || result.data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="padding: 32px; text-align: center; color: var(--arena-text-muted);">Nenhum endpoint de ingestão ativo. Crie um endpoint acima para receber dados externos via API.</td></tr>';
                return;
            }

            result.data.forEach(ep => {
                const urlGet = `${window.location.origin}/api/v1/get/${ep.endpoint_hash}/`;
                const urlPost = `${window.location.origin}/api/v1/post/${ep.endpoint_hash}/${ep.target_bucket}/${ep.target_format}`;
                const urlFormat = `${window.location.origin}/api/v1/format/${ep.endpoint_hash}/`;

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--arena-blue);">${ep.target_bucket}</td>
                    <td><span class="meta-tag" style="display:inline-block; margin:0; font-family: var(--font-mono);">${ep.target_format.toUpperCase()}</span></td>
                    <td style="font-size: 0.82rem;">
                        <div style="margin-bottom: 4px;"><span style="color:var(--arena-text-muted)">POST:</span> <a href="javascript:void(0)" style="color:var(--arena-blue); font-family: var(--font-mono);" onclick="arenaAlert({ title: 'Endpoint POST', message: '${urlPost}', type: 'info' })">${ep.endpoint_hash.substring(0, 8)}...</a></div>
                        <div style="margin-bottom: 4px;"><span style="color:var(--arena-text-muted)">GET:</span> <a href="javascript:void(0)" style="color:var(--arena-blue); font-family: var(--font-mono);" onclick="arenaAlert({ title: 'Endpoint GET', message: '${urlGet}', type: 'info' })">...${ep.endpoint_hash.substring(ep.endpoint_hash.length - 8)}</a></div>
                        <div style="margin-bottom: 4px;"><span style="color:var(--arena-text-muted)">Token:</span> <span style="color:var(--arena-gold); cursor:pointer; font-weight: 600;" onclick="arenaAlert({ title: 'Token Bearer', message: '${ep.access_token}', type: 'warning' })">Revelar Token</span></div>
                        <div><span style="color:var(--arena-text-muted)">Docs:</span> <a href="${urlFormat}" target="_blank" style="color:var(--arena-ok); font-family: var(--font-mono);">/format/</a></div>
                    </td>
                    <td style="font-family: var(--font-mono); font-size: 0.85rem;">${ep.request_count}</td>
                    <td style="text-align: right; color: var(--arena-text-dim); font-size: 0.8rem;">
                        <div>${ep.created_by}</div>
                        <div style="font-size: 0.75rem; margin-bottom: 6px;">${ep.created_at}</div>
                        <button type="button" onclick="deletarGatewayEndpoint(${ep.id})" class="btn-danger" style="padding: 4px 10px; font-size: 0.78rem;">Excluir</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error("Erro ao carregar endpoints do gateway", e);
    }
}

// =========================================================
// API INGESTION GATEWAY MGR (Construtor Visual)
// =========================================================
let currentGatewaySchema = {};

async function addSchemaColumn() {
    const colNameInput = document.getElementById('gwColName');
    const colType = document.getElementById('gwColType').value;
    let colName = colNameInput.value.trim();

    if (!colName) {
        await arenaAlert({ title: "Atenção", message: "Digite um nome para a coluna.", type: "warning" });
        return;
    }

    // Higieniza o nome da coluna para garantir compatibilidade com Parquet
    colName = colName.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '');

    if (colName.toLowerCase() === 'dathorrefcarga') {
        await arenaAlert({ title: "Campo Reservado", message: "A coluna 'datHorRefCarga' é reservada e gerenciada automaticamente pelo sistema.", type: "warning" });
        return;
    }

    if (currentGatewaySchema[colName]) {
        await arenaAlert({ title: "Coluna Existente", message: "Esta coluna já existe na estrutura do dado.", type: "warning" });
        return;
    }

    currentGatewaySchema[colName] = colType;
    colNameInput.value = '';
    renderGatewaySchema();
}

function removeSchemaColumn(colName) {
    delete currentGatewaySchema[colName];
    renderGatewaySchema();
}

function renderGatewaySchema() {
    const tbody = document.getElementById('gwSchemaTableBody');

    let html = `
        <tr>
            <td style="font-family: var(--font-mono); font-size: 0.85rem;">
                datHorRefCarga
                <span style="font-size: 0.7rem; background: rgba(34,197,94,0.15); color: var(--arena-ok); border: 1px solid rgba(34,197,94,0.3); padding: 2px 6px; border-radius: 4px; margin-left: 6px;">Sistema</span>
            </td>
            <td style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--arena-blue);">datetime</td>
            <td style="text-align: right; color: var(--arena-text-dim); font-size: 0.8rem; font-style: italic;">Automático</td>
        </tr>
    `;

    for (const [col, type] of Object.entries(currentGatewaySchema)) {
        html += `
            <tr>
                <td style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--arena-text-main);">${col}</td>
                <td style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--arena-blue);">${type}</td>
                <td style="text-align: right;">
                    <button type="button" onclick="removeSchemaColumn('${col}')" class="btn-danger" style="padding: 3px 8px; font-size: 0.75rem;">Remover</button>
                </td>
            </tr>
        `;
    }
    tbody.innerHTML = html;
}

async function criarGatewayEndpoint() {
    const bucket = document.getElementById('gwBucket').value;
    const format = document.getElementById('gwFormat').value;
    const filename = document.getElementById('gwFilename').value.trim()

    if (!bucket) {
        await arenaAlert({ title: "Atenção", message: "Selecione o bucket de destino.", type: "warning" });
        return;
    }

    if (!filename) {
        await arenaAlert({ title: "Atenção", message: "Defina o nome do arquivo para gravação.", type: "warning" });
        return;
    }

    if (Object.keys(currentGatewaySchema).length === 0) {
        await arenaAlert({ title: "Atenção", message: "Adicione pelo menos uma coluna além da coluna do sistema na estrutura do dado.", type: "warning" });
        return;
    }

    // Monta o schema final injetando a coluna de sistema obrigatoriamente
    const finalSchema = {
        datHorRefCarga: "datetime",
        ...currentGatewaySchema
    };

    try {
        const res = await fetch('/api/admin/gateway/endpoints', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                target_bucket: bucket,
                target_filename: filename,
                target_format: format,
                schema_definition: JSON.stringify(finalSchema)
            })
        });

        const result = await res.json();
        if (result.status === 'success') {
            await arenaAlert({ title: 'Endpoint Criado', message: result.message || 'Endpoint gerado com sucesso!', type: 'success' });
            document.getElementById('gwBucket').value = '';
            document.getElementById('gwFilename').value = '';
            currentGatewaySchema = {};
            renderGatewaySchema();
            carregarGatewayEndpoints();
        } else {
            await arenaAlert({ title: 'Erro na Criação', message: result.message || 'Não foi possível criar o endpoint.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: "Erro", message: "Falha ao criar o endpoint de ingestão.", type: "error" });
    }
}

async function deletarGatewayEndpoint(id) {
    const confirmed = await arenaConfirm({
        title: 'Revogar Endpoint',
        message: 'Tem certeza que deseja excluir este endpoint? O acesso externo (GET/POST) via token será revogado imediatamente.',
        confirmText: 'Revogar Endpoint',
        cancelText: 'Cancelar',
        danger: true
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/admin/gateway/endpoints/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await res.json();

        if (res.ok) {
            await arenaAlert({ title: 'Endpoint Revogado', message: result.message || 'Endpoint excluído com sucesso.', type: 'success' });
            carregarGatewayEndpoints();
        } else {
            await arenaAlert({ title: 'Erro ao Revogar', message: result.message || 'Não foi possível revogar o endpoint.', type: 'error' });
        }
    } catch (e) {
        await arenaAlert({ title: 'Erro de Conexão', message: 'Falha de comunicação ao excluir endpoint.', type: 'error' });
    }
}

// Suporte para navegação pelo histórico (botões Voltar / Avançar do navegador)
window.addEventListener('popstate', (e) => {
    const sec = (e.state && e.state.section) || getInitialSection();
    showSection(sec);
});

// Aplica a aba salva imediatamente antes do render completo para evitar piscar de tela
(() => {
    const startupSec = getInitialSection();
    if (startupSec && startupSec !== 'register') {
        showSection(startupSec);
    }
})();

document.addEventListener('DOMContentLoaded', init);
