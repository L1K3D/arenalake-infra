document.addEventListener('DOMContentLoaded', () => {
    // Pega o formulário pelo ID que vamos colocar no HTML
    const loginForm = document.getElementById('login-form');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault(); // Impede o navegador de recarregar a página

            // Captura os valores digitados nos inputs
            const usernameInput = document.getElementById('usuario').value;
            const passwordInput = document.getElementById('senha').value;

            // Prepara os dados no formato exato que o FastAPI exige (OAuth2)
            const formData = new URLSearchParams();
            formData.append('username', usernameInput);
            formData.append('password', passwordInput);

            try {
                // Dispara a requisição para a nossa nova API blindada
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();

                    // SUCESSO! Salva o Token JWT no cofre do navegador
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('username', data.username);
                    localStorage.setItem('role', data.role);

                    // Redireciona para a tela de escolha de hardware (Setup)
                    window.location.href = '/setup';

                } else {
                    const errorData = await response.json();
                    alert(errorData.detail || 'Usuário ou senha incorretos.');
                }
            } catch (error) {
                console.error("Erro na comunicação com o servidor:", error);
                alert("Erro ao tentar fazer login. Verifique se o servidor está rodando.");
            }
        });
    }
});