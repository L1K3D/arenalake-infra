function selectCard(perfil) {
    document.getElementById('card-standard').classList.remove('selected');
    document.getElementById('card-extreme').classList.remove('selected');

    document.getElementById('card-' + perfil).classList.add('selected');

    const btn = document.getElementById('btnLaunch');
    btn.disabled = false;

    if (perfil === 'standard') {
        btn.innerText = "🚀 Iniciar Ambiente Standard";
    } else {
        btn.innerText = "🚀 Iniciar Ambiente Extreme";
    }
}
