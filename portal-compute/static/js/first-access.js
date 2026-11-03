/* ============================================================================
   ArenaLake — Script de Primeiro Acesso (first-access)
   Identidade Visual Oficial: Lago de Partículas, Geração de QR Code 2FA,
   Toggle de Senha, Validação e Inicialização de Segurança
   ============================================================================ */

document.addEventListener('DOMContentLoaded', async () => {
    // ------------------------------------------------------------------------
    // 1. GUARDA DE AUTENTICAÇÃO
    // ------------------------------------------------------------------------
    const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    // ------------------------------------------------------------------------
    // 2. INICIALIZAÇÃO DAS ONDAS DO LAGO DE PARTÍCULAS
    // ------------------------------------------------------------------------
    initParticleLake();

    // ------------------------------------------------------------------------
    // 3. ELEMENTOS DA INTERFACE
    // ------------------------------------------------------------------------
    const form = document.getElementById('first-access-form');
    const newPassInput = document.getElementById('new_password');
    const otpInput = document.getElementById('otp_code');
    const submitBtn = document.getElementById('submit-btn');
    const togglePassBtn = document.getElementById('toggle-password');
    const alertBox = document.getElementById('first-access-alert');
    const alertMsg = document.getElementById('alert-message');
    const qrImg = document.getElementById('qr-code-img');
    const cancelLink = document.getElementById('cancel-link');

    // ------------------------------------------------------------------------
    // 4. CONTROLE DE ALERTA DE ERRO
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

    if (newPassInput) newPassInput.addEventListener('input', clearError);
    if (otpInput) {
        otpInput.addEventListener('input', () => {
            otpInput.value = otpInput.value.replace(/\D/g, '').slice(0, 6);
            clearError();
        });
    }

    // ------------------------------------------------------------------------
    // 5. TOGGLE DE VISIBILIDADE DE SENHA
    // ------------------------------------------------------------------------
    if (togglePassBtn && newPassInput) {
        togglePassBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const isPassword = newPassInput.type === 'password';
            newPassInput.type = isPassword ? 'text' : 'password';

            const eyeShow = togglePassBtn.querySelector('.eye-show');
            const eyeHide = togglePassBtn.querySelector('.eye-hide');

            if (eyeShow && eyeHide) {
                eyeShow.style.display = isPassword ? 'none' : 'block';
                eyeHide.style.display = isPassword ? 'block' : 'none';
            }
        });
    }

    // ------------------------------------------------------------------------
    // 6. CARREGAMENTO DO QR CODE 2FA
    // ------------------------------------------------------------------------
    try {
        const resQr = await fetch('/api/auth/2fa/generate', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (resQr.ok) {
            const dataQr = await resQr.json();
            if (qrImg) qrImg.src = dataQr.qr_code_base64;
        } else {
            const err = await resQr.json();
            showError("Erro ao gerar QR Code do 2FA: " + (err.detail || "Consulte o administrador."));
        }
    } catch (e) {
        showError("Falha de conexão com o servidor ao carregar credenciais 2FA.");
    }

    // ------------------------------------------------------------------------
    // 7. SUBMISSÃO DE CADASTRO
    // ------------------------------------------------------------------------
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearError();

            const new_password = newPassInput ? newPassInput.value : '';
            const otp_code = otpInput ? otpInput.value.trim() : '';

            if (!new_password || new_password.length < 8) {
                showError("A nova senha deve conter no mínimo 8 caracteres.");
                if (newPassInput) newPassInput.focus();
                return;
            }

            if (!otp_code || otp_code.length !== 6) {
                showError("Informe o código de 6 dígitos gerado no aplicativo autenticador.");
                if (otpInput) otpInput.focus();
                return;
            }

            if (submitBtn) {
                submitBtn.classList.add('is-loading');
                submitBtn.disabled = true;
            }

            try {
                const resSetup = await fetch('/api/auth/first-access', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ new_password, otp_code })
                });

                const result = await resSetup.json();

                if (resSetup.ok) {
                    sessionStorage.removeItem('access_token');
                    localStorage.removeItem('access_token');
                    window.location.href = '/?configured=true';
                } else {
                    showError(result.detail || "Código de verificação incorreto ou senha inválida.");
                    if (submitBtn) {
                        submitBtn.classList.remove('is-loading');
                        submitBtn.disabled = false;
                    }
                }
            } catch (error) {
                showError("Falha de comunicação ao configurar a conta.");
                if (submitBtn) {
                    submitBtn.classList.remove('is-loading');
                    submitBtn.disabled = false;
                }
            }
        });
    }

    if (cancelLink) {
        cancelLink.addEventListener('click', () => {
            sessionStorage.removeItem('access_token');
            localStorage.removeItem('access_token');
        });
    }
});
