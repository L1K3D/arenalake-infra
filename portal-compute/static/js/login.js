/* ============================================================================
   ArenaLake Login JavaScript
   ============================================================================
   Handles user authentication via API and intelligent RBAC redirection.
   ============================================================================ */

document.addEventListener('DOMContentLoaded', () => {
    // Tenta encontrar o formulário de login por ID ou seletor genérico
    const form = document.getElementById('login-form') || document.querySelector('form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Identifica os campos de input do form de login
        const usernameInput = document.getElementById('usuario') || document.getElementById('username');
        const passwordInput = document.getElementById('senha') || document.getElementById('password');

        if (!usernameInput || !passwordInput) return;

        // O FastAPI OAuth2PasswordRequestForm exige application/x-www-form-urlencoded
        const formData = new URLSearchParams();
        formData.append('username', usernameInput.value.trim().toLowerCase());
        formData.append('password', passwordInput.value);

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                // Armazena o token JWT corporativo no cofre local
                sessionStorage.setItem('access_token', data.access_token);

                // 👑 Roteamento Inteligente baseado no RBAC e status de segurança
                if (data.must_change_password || !data.is_2fa_verified) {
                    window.location.href = '/first-access'; // Primeiro acesso / 2FA pendente
                } else if (data.role === 'admin') {
                    window.location.href = '/admin'; // Administrador vai direto para o Painel DBA
                } else {
                    window.location.href = '/setup'; // Usuário comum vai para o Setup do Workspace
                }
            } else {
                alert(data.detail || "Credenciais inválidas. Verifique usuário e senha.");
            }
        } catch (error) {
            console.error("Erro no login:", error);
            alert("Erro de conexão com o servidor.");
        }
    });
});