/* ============================================================================
   ArenaLake Hardware Setup JavaScript
   ============================================================================
   Manages hardware profile selection (Standard vs Extreme) for workspace provisioning.
   Updates button state and text based on selected profile.
   ============================================================================ */

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

    // Enable launch button and update button text based on profile
    const btn = document.getElementById('btnLaunch');
    btn.disabled = false;

    if (perfil === 'standard') {
        btn.innerText = "🚀 Iniciar Ambiente Standard";
    } else {
        btn.innerText = "🚀 Iniciar Ambiente Extreme";
    }
}