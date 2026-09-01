document.addEventListener('DOMContentLoaded', async () => {
    // 1. Pega o token JWT do cofre (se não tiver, expulsa pro login)
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    // 2. Busca o QR Code gerado pelo backend
    try {
        const resQr = await fetch('/api/auth/2fa/generate', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (resQr.ok) {
            const dataQr = await resQr.json();
            document.getElementById('qr-code-img').src = dataQr.qr_code_base64;
        } else {
            const err = await resQr.json();
            alert("Erro ao gerar 2FA: " + (err.detail || "Consulte o admin."));
        }
    } catch (e) {
        alert("Erro de conexão com o servidor.");
    }

    // 3. Intercepta o formulário para validar a senha e o código
    const form = document.getElementById('first-access-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const new_password = document.getElementById('new_password').value;
        const otp_code = document.getElementById('otp_code').value;

        try {
            const resSetup = await fetch('/api/auth/first-access', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ new_password, otp_code })
            });

            if (resSetup.ok) {
                alert("Segurança configurada com sucesso! Bem-vindo ao ArenaLake.");
                // Opcional: Atualiza o localStorage para refletir que o usuário não precisa mais trocar a senha

                // Redireciona para a tela de hardware (Setup)
                window.location.href = '/setup';
            } else {
                const err = await resSetup.json();
                alert(err.detail || "Código inválido ou senha fraca.");
            }
        } catch (error) {
            alert("Erro ao validar dados.");
        }
    });
});