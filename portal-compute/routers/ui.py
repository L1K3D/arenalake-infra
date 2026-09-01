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

# Initialize router and Jinja2 template engine
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the login page.
    Displays username and password inputs for user authentication.
    """
    return templates.TemplateResponse(
        request=request, name="login.html", context={"request": request}
    )


@router.post("/login")
async def login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    # Normalize username: lowercase, strip whitespace, replace spaces with hyphens
    usr_formatado = usuario.lower().strip().replace(" ", "-")
    # Redirect to setup page instead of directly to dashboard
    # Allows user to choose hardware profile (Standard or Extreme)
    return templates.TemplateResponse(
        request=request,
        name="setup.html",
        context={"request": request, "usuario": usr_formatado},
    )


@router.post("/shutdown")
async def shutdown_ambiente(usuario: str = Form(...)):
    # Desliga os containers imediatamente
    shutdown_workspace(usuario)
    # Joga o usuário de volta para a tela inicial de login
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
        context={"request": request, "usuario": usuario, "domain": domain},
    )
    
@router.get("/first-access")
async def first_access_page(request: Request):
    return templates.TemplateResponse("first-access.html", {"request": request})