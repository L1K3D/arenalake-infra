/* ============================================================================
   ArenaLake — Script de Seleção de Perfil de Hardware (setup.js)
   Identidade Visual Oficial: Lago de Partículas, Telemetria de Recursos,
   Seleção Interativa e Provisionamento de Workspace
   ============================================================================ */

document.addEventListener('DOMContentLoaded', () => {
    // ------------------------------------------------------------------------
    // 1. GUARDA DE AUTENTICAÇÃO E LEITURA DE USUÁRIO
    // ------------------------------------------------------------------------
    const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.sub) {
            const userInput = document.querySelector('input[name="usuario"]');
            if (userInput && (!userInput.value || userInput.value.includes('{{'))) {
                userInput.value = payload.sub;
            }

            const welcomeEl = document.getElementById('welcome-username');
            if (welcomeEl && (!welcomeEl.innerText.trim() || welcomeEl.innerText.includes('{{'))) {
                welcomeEl.innerText = payload.sub;
            }
        }
    } catch (e) {
        console.warn('Erro ao ler dados da sessão:', e);
    }

    // ------------------------------------------------------------------------
    // 2. INICIALIZAÇÃO DAS ONDAS DO LAGO DE PARTÍCULAS
    // ------------------------------------------------------------------------
    initParticleLake();

    // ------------------------------------------------------------------------
    // 3. TELEMETRIA DE RECURSOS EM TEMPO REAL
    // ------------------------------------------------------------------------
    fetchSystemResources();
    setInterval(fetchSystemResources, 5000);
});

/**
 * Consulta recursos disponíveis no host / cluster via JWT
 */
async function fetchSystemResources() {
    const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    try {
        const response = await fetch('/api/system/resources', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.status === 401) {
            window.location.href = '/';
            return;
        }

        const result = await response.json();
        if (result.status === 'success' && result.data) {
            updateResourcesUI(result.data);
            verificarDisponibilidade(result.data.available_cpus, result.data.available_mem_gb);
        }
    } catch (error) {
        console.error('Erro ao consultar capacidade do cluster:', error);
    }
}

/**
 * Atualiza o banner com as métricas do cluster
 */
function updateResourcesUI(data) {
    const metricsContainer = document.getElementById('resource-metrics-content');
    if (!metricsContainer) return;

    metricsContainer.innerHTML = `
        <div class="metric-pill">
            <span class="metric-pill-label">CPU:</span>
            <span class="metric-pill-val-cpu">${data.available_cpus.toFixed(1)} Cores livres</span>
        </div>
        <div class="metric-pill">
            <span class="metric-pill-label">RAM:</span>
            <span class="metric-pill-val-ram">${data.available_mem_gb.toFixed(1)} GB livres</span>
        </div>
    `;
}

/**
 * Verifica se os nós possuem capacidade mínima para cada perfil
 */
function verificarDisponibilidade(cpusLivres, ramLivre) {
    const cardStandard = document.getElementById('card-standard');
    const warnStandard = document.getElementById('warn-standard');

    const cardExtreme = document.getElementById('card-extreme');
    const warnExtreme = document.getElementById('warn-extreme');

    const btnLaunch = document.getElementById('btnLaunch');
    const perfilInput = document.getElementById('perfilInput');

    // Standard requer 2 Cores e 4 GB RAM
    if (cpusLivres < 2 || ramLivre < 4) {
        if (cardStandard) {
            cardStandard.classList.add('is-disabled');
            cardStandard.style.opacity = '0.4';
            cardStandard.style.pointerEvents = 'none';
        }
        if (warnStandard) warnStandard.style.display = 'block';

        if (perfilInput && perfilInput.value === 'standard') {
            cardStandard.classList.remove('selected');
            perfilInput.value = '';
            if (btnLaunch) {
                btnLaunch.disabled = true;
                btnLaunch.innerText = 'Selecione um perfil acima';
            }
        }
    } else {
        if (cardStandard) {
            cardStandard.classList.remove('is-disabled');
            cardStandard.style.opacity = '1';
            cardStandard.style.pointerEvents = 'auto';
        }
        if (warnStandard) warnStandard.style.display = 'none';
    }

    // Extreme requer 6 Cores e 8 GB RAM
    if (cpusLivres < 6 || ramLivre < 8) {
        if (cardExtreme) {
            cardExtreme.classList.add('is-disabled');
            cardExtreme.style.opacity = '0.4';
            cardExtreme.style.pointerEvents = 'none';
        }
        if (warnExtreme) warnExtreme.style.display = 'block';

        if (perfilInput && perfilInput.value === 'extreme') {
            cardExtreme.classList.remove('selected');
            perfilInput.value = '';
            if (btnLaunch) {
                btnLaunch.disabled = true;
                btnLaunch.innerText = 'Selecione um perfil acima';
            }
        }
    } else {
        if (cardExtreme) {
            cardExtreme.classList.remove('is-disabled');
            cardExtreme.style.opacity = '1';
            cardExtreme.style.pointerEvents = 'auto';
        }
        if (warnExtreme) warnExtreme.style.display = 'none';
    }
}

/**
 * Seleciona o perfil de hardware e atualiza o botão
 */
function selectCard(perfil) {
    const cardStd = document.getElementById('card-standard');
    const cardExt = document.getElementById('card-extreme');
    const perfilInput = document.getElementById('perfilInput');
    const btnLaunch = document.getElementById('btnLaunch');

    if (cardStd) cardStd.classList.remove('selected');
    if (cardExt) cardExt.classList.remove('selected');

    const targetCard = document.getElementById('card-' + perfil);
    if (targetCard && !targetCard.classList.contains('is-disabled')) {
        targetCard.classList.add('selected');
        if (perfilInput) perfilInput.value = perfil;

        if (btnLaunch) {
            btnLaunch.disabled = false;
            if (perfil === 'standard') {
                btnLaunch.innerText = 'Inicializar Ambiente Standard';
            } else {
                btnLaunch.innerText = 'Inicializar Ambiente Extreme';
            }
        }
    }
}

/**
 * Encerra a sessão e retorna ao login
 */
function logoutSession() {
    sessionStorage.removeItem('access_token');
    localStorage.removeItem('access_token');
    window.location.href = '/';
}
