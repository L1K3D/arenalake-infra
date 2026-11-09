/* ============================================================================
   ArenaLake — Script de Verificação em Duas Etapas (verify-otp)
   Identidade Visual Oficial: Lago de Partículas, Código de 6 Dígitos,
   Validação Instantânea e Redirecionamento RBAC
   ============================================================================ */

document.addEventListener('DOMContentLoaded', () => {
    // ------------------------------------------------------------------------
    // 1. GUARDA DE AUTENTICAÇÃO
    // ------------------------------------------------------------------------
    const token = sessionStorage.getItem('access_token');
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
    const form = document.getElementById('verify-otp-form');
    const otpInput = document.getElementById('otp_code');
    const submitBtn = document.getElementById('submit-btn');
    const alertBox = document.getElementById('otp-alert');
    const alertMsg = document.getElementById('alert-message');
    const cancelLink = document.getElementById('cancel-link');

    if (!form || !otpInput) return;

    // Foca automaticamente no campo
    otpInput.focus();

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

    // ------------------------------------------------------------------------
    // 5. MÁSCARA E FORMATAÇÃO DE 6 DÍGITOS
    // ------------------------------------------------------------------------
    otpInput.addEventListener('input', () => {
        // Permite apenas dígitos numéricos
        const clean = otpInput.value.replace(/\D/g, '').slice(0, 6);
        otpInput.value = clean;
        clearError();

        // Se o usuário digitou os 6 dígitos completos, submete automaticamente
        if (clean.length === 6) {
            submitOtp();
        }
    });

    // ------------------------------------------------------------------------
    // 6. SUBMISSÃO DO CÓDIGO OTP
    // ------------------------------------------------------------------------
    async function submitOtp() {
        const code = otpInput.value.trim();

        if (code.length !== 6) {
            showError('Por favor, informe os 6 dígitos do código autenticador.');
            otpInput.focus();
            return;
        }

        clearError();
        if (submitBtn) {
            submitBtn.classList.add('is-loading');
            submitBtn.disabled = true;
        }

        try {
            const res = await fetch('/api/auth/verify-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ otp_code: code })
            });

            const result = await res.json();

            if (res.ok && result.access_token) {
                // Atualiza o token na sessão com o token autenticado completo
                sessionStorage.setItem('access_token', result.access_token);

                // Redireciona conforme privilégios
                try {
                    const payload = JSON.parse(atob(result.access_token.split('.')[1]));
                    if (payload.role === 'admin') {
                        window.location.href = '/admin';
                        return;
                    }
                } catch (_) {}

                window.location.href = '/setup';
            } else {
                showError(result.detail || 'Código de verificação incorreto ou expirado. Tente novamente.');
                if (submitBtn) {
                    submitBtn.classList.remove('is-loading');
                    submitBtn.disabled = false;
                }
                otpInput.select();
            }
        } catch (err) {
            showError('Falha de comunicação com o servidor ao validar o código.');
            if (submitBtn) {
                submitBtn.classList.remove('is-loading');
                submitBtn.disabled = false;
            }
        }
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        submitOtp();
    });

    if (cancelLink) {
        cancelLink.addEventListener('click', () => {
            sessionStorage.removeItem('access_token');
        });
    }
});


