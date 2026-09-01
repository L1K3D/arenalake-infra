/* ============================================================================
   ArenaLake Hardware Setup JavaScript
   ============================================================================
   Manages hardware profile selection (Standard vs Extreme) for workspace provisioning.
   Updates button state, fetches system resources with JWT, and provisions workspaces.
   ============================================================================ */

document.addEventListener('DOMContentLoaded', () => {
    fetchSystemResources();
});

/**
 * Fetches allocatable system resources (CPU/RAM) from API using JWT authentication
 */
async function fetchSystemResources() {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    const resourcesContainer = document.getElementById('resources-status') || document.querySelector('.resources-info');

    if (!token) {
        console.warn('Token JWT não encontrado. Redirecionando para o login...');
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
            console.error('Sessão expirada ou não autorizada.');
            window.location.href = '/';
            return;
        }

        if (!response.ok) {
            throw new Error(`Erro ${response.status}: Falha ao buscar recursos do cluster.`);
        }

        const result = await response.json();

        if (result.status === 'success' && result.data) {
            updateResourcesUI(result.data);
        }
    } catch (error) {
        console.error('Erro ao carregar recursos do sistema:', error);
        if (resourcesContainer) {
            resourcesContainer.innerHTML = `<span style="color: #ff7b72;">⚠️ Erro ao carregar recursos do servidor.</span>`;
        }
    }
}

/**
 * Updates the UI with CPU and Memory availability
 * @param {Object} data - Resource metrics from backend
 */
function updateResourcesUI(data) {
    const resourcesContainer = document.getElementById('resources-status') || document.querySelector('.resources-info');
    if (resourcesContainer) {
        resourcesContainer.innerHTML = `
            <span>💡 <strong>Recursos Disponíveis no Cluster:</strong> ${data.available_cpus} Cores CPU | ${data.available_mem_gb} GB RAM livres</span>
        `;
    }
}

/**
 * Handle machine card selection for hardware profile
 * @param {string} perfil - Selected profile ('standard' or 'extreme')
 */
function selectCard(perfil) {
    // Remove selected class from all cards
    document.getElementById('card-standard').classList.remove('selected');
    document.getElementById('card-extreme').classList.remove('selected');

    // Add selected class to clicked card
    document.getElementById('card-' + perfil).classList.add('selected');

    // Store selected profile in hidden input or data attribute if present
    const profileInput = document.getElementById('perfilInput');
    if (profileInput) {
        profileInput.value = perfil;
    }

    // Enable launch button and update button text based on profile
    const btn = document.getElementById('btnLaunch');
    if (btn) {
        btn.disabled = false;
        if (perfil === 'standard') {
            btn.innerText = "🚀 Iniciar Ambiente Standard";
        } else {
            btn.innerText = "🚀 Iniciar Ambiente Extreme";
        }
    }
}