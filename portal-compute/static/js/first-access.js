/* ============================================================================
   ArenaLake First-Access JavaScript
   ============================================================================
   Handles QR code loading, JWT authentication verification, and secure
   onboarding submission (password change + 2FA token validation).
   ============================================================================ */

document.addEventListener('DOMContentLoaded', async () => {
    // Read the temporary token issued for the first-access security flow.
    const token = sessionStorage.getItem('sessionStorage' in window ? sessionStorage.getItem('access_token') : localStorage.getItem('access_token')) || sessionStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    try {
        // Request the QR code that links the account to an authenticator app.
        const resQr = await fetch('/api/auth/2fa/generate', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (resQr.ok) {
            // Display the base64-encoded QR image returned by the API.
            const dataQr = await resQr.json();
            document.getElementById('qr-code-img').src = dataQr.qr_code_base64;
        } else {
            const err = await resQr.json();
            alert("Error generating 2FA: " + (err.detail || "Contact the admin."));
        }
    } catch (e) {
        alert("Server connection error.");
    }

    const form = document.getElementById('first-access-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Submit the new password and one-time code for server-side validation.
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

            const result = await resSetup.json();

            if (resSetup.ok) {
                alert("Security configured successfully! Welcome to ArenaLake.");

                // Route administrators and standard users to their next workflow.
                if (result.role === 'admin') {
                    window.location.href = '/admin';
                } else {
                    window.location.href = '/setup';
                }
            } else {
                alert(result.detail || "Invalid code or weak password.");
            }
        } catch (error) {
            alert("Error while validating the data.");
        }
    });
});