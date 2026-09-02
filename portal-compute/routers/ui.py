# ============================================================================
# ArenaLake UI Router - Template Rendering
# ============================================================================
# This module handles all UI page requests and renders HTML templates.
# Routes:
# - GET /: Login page
# - POST /login: Authenticate user and redirect to setup page
# - POST /provisionar: Provision workspace containers (Docker)
# - GET /dashboard/{usuario}: Render user dashboard with Spark monitoring
# ============================================================================

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.docker_mgr import provision_workspace, shutdown_workspace
import os

from core.database import SessionLocal
from core.models import User
from core.security import verify_password

# Initialize router and Jinja2 template engine
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def login_page(request: Request):
    # Fixed: explicitly passing the request and template name.
    return templates.TemplateResponse(request=request, name="login.html")


@router.post("/login")
async def login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    # Normalize the username to the expected internal format.
    usr_formatado = usuario.lower().strip().replace(" ", "-")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == usr_formatado).first()

        # If the user does not exist or the password is wrong, send them back to login.
        if not user or not verify_password(senha, user.hashed_password):
            return RedirectResponse(url="/", status_code=303)

        # If the user must change password or has not completed 2FA, redirect to first-access.
        if user.must_change_password or not user.is_2fa_verified:
            return RedirectResponse(url="/first-access", status_code=303)

        # Admin users jump directly to the DBA control panel.
        if user.role == "admin":
            return RedirectResponse(url="/admin", status_code=303)

        # Standard users proceed to the hardware selection setup page.
        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context={"usuario": usr_formatado},
        )
    finally:
        db.close()


@router.post("/shutdown")
async def shutdown_ambiente(usuario: str = Form(...)):
    # Stop the user workspace containers immediately.
    shutdown_workspace(usuario)
    # Redirect the user back to the initial login screen.
    return RedirectResponse(url="/", status_code=303)


@router.post("/provisionar")
async def provisionar_ambiente(
    usuario: str = Form(...), perfil: str = Form("standard")
):
    # Provision Docker containers for the user's workspace
    # Applies hardware limits based on selected profile (standard=2CPU/4GB or extreme=6CPU/8GB)
    domain = provision_workspace(usuario, perfil)
    # Redirect to dashboard once containers are running
    return RedirectResponse(url=f"/dashboard/{usuario}", status_code=303)


@router.get("/dashboard/{usuario}", response_class=HTMLResponse)
async def dashboard(request: Request, usuario: str):
    tailscale_url = os.getenv("TAILSCALE_BASE_URL")
    vscode_port = os.getenv("VSCODE_EXTERNAL_PORT")

    # Monta a URL externa correta com a porta
    domain = f"{tailscale_url}:{vscode_port}/workspace/{usuario}"

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"usuario": usuario, "domain": domain},
    )
    
@router.get("/first-access")
async def first_access_page(request: Request):
    # Consertado: Passando nome e request explicitamente
    return templates.TemplateResponse(request=request, name="first-access.html")

@router.get("/setup")
async def setup_page(request: Request):
    # Consertado: Passando nome e request explicitamente
    return templates.TemplateResponse(request=request, name="setup.html")

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    # Retorna a interface do painel do DBA
    return templates.TemplateResponse(request=request, name="admin.html")

@router.get("/verify-otp", response_class=HTMLResponse)
async def verify_otp_page(request: Request):
    return templates.TemplateResponse(request=request, name="verify-otp.html")