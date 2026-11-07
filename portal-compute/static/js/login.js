/* ============================================================================
   ArenaLake — Script de Autenticação e Ondas do Lago (Portal Compute)
   Funcionalidades: Lago de Partículas, 'Lembrar Dispositivo', Toggle de Senha,
   Submissão de Credenciais e Redirecionamento RBAC
   ============================================================================ */

document.addEventListener('DOMContentLoaded', () => {
    // ------------------------------------------------------------------------
    // 1. INICIALIZAÇÃO DAS ONDAS DO LAGO DE PARTÍCULAS (ArenaLake)
    // ------------------------------------------------------------------------
    initParticleLake();

    // ------------------------------------------------------------------------
    // 2. ELEMENTOS DA INTERFACE
    // ------------------------------------------------------------------------
    const form = document.getElementById('login-form') || document.querySelector('form');
    if (!form) return;

    const usernameInput = document.getElementById('usuario') || document.getElementById('username');
    const passwordInput = document.getElementById('senha') || document.getElementById('password');
    const submitBtn = document.getElementById('submit-btn') || form.querySelector('button[type="submit"]');
    const togglePassBtn = document.getElementById('toggle-password');
    const rememberCheckbox = document.getElementById('remember');
    const alertBox = document.getElementById('login-alert');
    const alertMsg = document.getElementById('alert-message');

    // ------------------------------------------------------------------------
    // 3. RECUPERAR LOGIN SALVO ('Lembrar neste dispositivo')
    // ------------------------------------------------------------------------
    try {
        const savedLogin = localStorage.getItem('arenalake_saved_login');
        if (savedLogin && usernameInput) {
            usernameInput.value = savedLogin;
            if (rememberCheckbox) {
                rememberCheckbox.checked = true;
            }
            // Foca na senha se o login já estiver preenchido
            if (passwordInput && !passwordInput.value) {
                passwordInput.focus();
            }
        }
    } catch (e) {
        console.warn("Storage inacessível para recuperar login salvo:", e);
    }

    // ------------------------------------------------------------------------
    // 4. TOGGLE DE VISIBILIDADE DE SENHA
    // ------------------------------------------------------------------------
    if (togglePassBtn && passwordInput) {
        togglePassBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const isPassword = passwordInput.type === 'password';
            passwordInput.type = isPassword ? 'text' : 'password';

            const eyeShow = togglePassBtn.querySelector('.eye-show');
            const eyeHide = togglePassBtn.querySelector('.eye-hide');

            if (eyeShow && eyeHide) {
                eyeShow.style.display = isPassword ? 'none' : 'block';
                eyeHide.style.display = isPassword ? 'block' : 'none';
            }
        });
    }

    // ------------------------------------------------------------------------
    // 5. CONTROLE DE ALERTA DE ERRO
    // ------------------------------------------------------------------------
    function showError(message) {
        if (alertBox && alertMsg) {
            alertMsg.textContent = message;
            alertBox.hidden = false;
        } else {
            alert(message);
        }
    }

    function clearError() {
        if (alertBox) {
            alertBox.hidden = true;
        }
    }

    if (usernameInput) usernameInput.addEventListener('input', clearError);
    if (passwordInput) passwordInput.addEventListener('input', clearError);

    // ------------------------------------------------------------------------
    // 6. SUBMISSÃO DE CREDENCIAIS E ARMAZENAMENTO DO LOGIN
    // ------------------------------------------------------------------------
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearError();

        const username = usernameInput ? usernameInput.value.trim().toLowerCase() : '';
        const password = passwordInput ? passwordInput.value : '';

        if (!username || !password) {
            showError("Por favor, preencha o login e a senha.");
            return;
        }

        // Persistência de 'Lembrar neste dispositivo'
        try {
            if (rememberCheckbox && rememberCheckbox.checked) {
                localStorage.setItem('arenalake_saved_login', username);
            } else {
                localStorage.removeItem('arenalake_saved_login');
            }
        } catch (e) {
            console.warn("Storage inacessível para salvar login:", e);
        }

        // Estado de carregamento
        if (submitBtn) {
            submitBtn.classList.add('is-loading');
            submitBtn.disabled = true;
            const textSpan = submitBtn.querySelector('.btn-text');
            if (textSpan) {
                textSpan.dataset.origText = textSpan.textContent;
                textSpan.textContent = "Entrando...";
            }
        }

        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

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
                sessionStorage.setItem('access_token', data.access_token);

                // Redirecionamento RBAC
                if (data.next_step === 'first_access') {
                    window.location.href = '/first-access';
                } else if (data.next_step === 'verify_otp') {
                    window.location.href = '/verify-otp';
                } else if (data.next_step === 'admin') {
                    window.location.href = '/admin';
                } else {
                    window.location.href = '/setup';
                }
            } else {
                const errorDetail = data.detail || "Credenciais inválidas. Verifique seu login e senha.";
                showError(errorDetail);
                resetButton();
                if (passwordInput) passwordInput.focus();
            }
        } catch (error) {
            console.error("Erro no login:", error);
            showError("Erro de comunicação com o servidor. Tente novamente.");
            resetButton();
        }
    });

    function resetButton() {
        if (submitBtn) {
            submitBtn.classList.remove('is-loading');
            submitBtn.disabled = false;
            const textSpan = submitBtn.querySelector('.btn-text');
            if (textSpan && textSpan.dataset.origText) {
                textSpan.textContent = textSpan.dataset.origText;
            }
        }
    }
});

/**
 * ----------------------------------------------------------------------------
 * ONDAS DO LAGO DE PARTÍCULAS (ArenaLake Particle Lake)
 * Malha senoidal de pontos com perspectiva e fluxo suave.
 * ----------------------------------------------------------------------------
 */