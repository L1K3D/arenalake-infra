# ============================================================================
# ArenaLake UI router for template rendering and workspace navigation.
# ============================================================================
# It serves login, onboarding, setup, dashboard, and administrator pages.
# ============================================================================

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.docker_mgr import provision_workspace, shutdown_workspace
import os

from core.database import SessionLocal
from core.models import User
from core.security import verify_password

# Initialize the router and Jinja2 template engine used by all page handlers.
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def login_page(request: Request):
    """Render the initial login page."""
    return templates.TemplateResponse(request=request, name="login.html")


@router.post("/login")
async def login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    """Authenticate a browser login and redirect according to the user's role."""
    # Normalize the username to the format used by the database and services.
    usr_formatado = usuario.lower().strip().replace(" ", "-")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == usr_formatado).first()

        # Return to login when the account or password cannot be validated.
        if not user or not verify_password(senha, user.hashed_password):
            return RedirectResponse(url="/", status_code=303)

        # Route incomplete security setup through the first-access page.
        if user.must_change_password or not user.is_2fa_verified:
            return RedirectResponse(url="/first-access", status_code=303)

        # Administrators go directly to the DBA control panel.
        if user.role == "admin":
            return RedirectResponse(url="/admin", status_code=303)

        # Standard users continue to hardware profile selection.
        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context={"usuario": usr_formatado},
        )
    finally:
        db.close()


@router.post("/shutdown")
async def shutdown_ambiente(usuario: str = Form(...)):
    """Stop the user's workspace services and return to the login page."""
    # Stop the user workspace services immediately.
    shutdown_workspace(usuario)
    # Return the browser to the initial login screen.
    return RedirectResponse(url="/", status_code=303)


@router.post("/provisionar")
async def provisionar_ambiente(
    usuario: str = Form(...), perfil: str = Form("standard")
):
    """Provision workspace services using the selected hardware profile."""
    # Apply profile-specific CPU and memory limits in the Docker manager.
    domain = provision_workspace(usuario, perfil)
    # Redirect to the dashboard after requesting the workspace services.
    return RedirectResponse(url=f"/dashboard/{usuario}", status_code=303)


@router.get("/dashboard/{usuario}", response_class=HTMLResponse)
async def dashboard(request: Request, usuario: str):
    """Render the user dashboard with the externally reachable workspace URL."""
    tailscale_url = os.getenv("TAILSCALE_BASE_URL")
    vscode_port = os.getenv("VSCODE_EXTERNAL_PORT")

    # Build the external workspace URL from the deployment configuration.
    domain = f"{tailscale_url}:{vscode_port}/workspace/{usuario}"

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"usuario": usuario, "domain": domain},
    )
    
@router.get("/first-access")
async def first_access_page(request: Request):
    """Render the first-access password and 2FA setup page."""
    return templates.TemplateResponse(request=request, name="first-access.html")

@router.get("/setup")
async def setup_page(request: Request):
    """Render the workspace profile selection page."""
    return templates.TemplateResponse(request=request, name="setup.html")

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    """Render the administrator control panel."""
    return templates.TemplateResponse(request=request, name="admin.html")

@router.get("/verify-otp", response_class=HTMLResponse)
async def verify_otp_page(request: Request):
    """Render the OTP verification page for standard-user login."""
    return templates.TemplateResponse(request=request, name="verify-otp.html")