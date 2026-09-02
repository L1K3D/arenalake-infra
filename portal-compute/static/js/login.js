/* ============================================================================
   ArenaLake Login JavaScript
   ============================================================================
   Handles user authentication via API and intelligent RBAC redirection.
   ============================================================================ */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('login-form') || document.querySelector('form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const usernameInput = document.getElementById('usuario') || document.getElementById('username');
        const passwordInput = document.getElementById('senha') || document.getElementById('password');

        if (!usernameInput || !passwordInput) return;

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
                sessionStorage.setItem('access_token', data.access_token);

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
                alert(data.detail || "Invalid credentials.");
            }
        } catch (error) {
            console.error("Login error:", error);
            alert("Server connection error.");
        }
    });
});