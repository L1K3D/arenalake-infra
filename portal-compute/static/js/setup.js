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
    const token = sessionStorage.getItem('access_token');
    const resourcesContainer = document.getElementById('resources-status') || document.querySelector('.resources-info');

    if (!token) {
        console.warn('JWT token not found. Redirecting to login...');
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
            console.error('Session expired or unauthorized.');
            window.location.href = '/';
            return;
        }

        if (!response.ok) {
            throw new Error(`Error ${response.status}: Failed to fetch cluster resources.`);
        }

        const result = await response.json();

        if (result.status === 'success' && result.data) {
            updateResourcesUI(result.data);
        }
    } catch (error) {
        console.error('Error loading system resources:', error);
        if (resourcesContainer) {
            resourcesContainer.innerHTML = `<span style="color: #ff7b72;">⚠️ Error loading server resources.</span>`;
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
            <span>💡 <strong>Resources available in the cluster:</strong> ${data.available_cpus} CPU cores | ${data.available_mem_gb} GB RAM free</span>
        `;
    }
}

/**
 * Handle machine card selection for hardware profile
 * @param {string} perfil - Selected profile ('standard' or 'extreme')
 */
function selectCard(perfil) {
    document.getElementById('card-standard').classList.remove('selected');
    document.getElementById('card-extreme').classList.remove('selected');

    document.getElementById('card-' + perfil).classList.add('selected');

    const profileInput = document.getElementById('perfilInput');
    if (profileInput) {
        profileInput.value = perfil;
    }

    const btn = document.getElementById('btnLaunch');
    if (btn) {
        btn.disabled = false;
        if (perfil === 'standard') {
            btn.innerText = "🚀 Start Standard Environment";
        } else {
            btn.innerText = "🚀 Start Extreme Environment";
        }
    }
}