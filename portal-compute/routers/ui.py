from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.docker_mgr import provision_workspace

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"request": request}
    )


@router.post("/login")
async def login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    usr_formatado = usuario.lower().strip().replace(" ", "-")
    # Mudança importante: Em vez de logar direto no dashboard, levamos para a escolha de hardware (Setup)
    return templates.TemplateResponse(
        request=request,
        name="setup.html",
        context={"request": request, "usuario": usr_formatado},
    )


@router.post("/provisionar")
async def provisionar_ambiente(
    usuario: str = Form(...), perfil: str = Form("standard")
):
    # O provisionador agora recebe o perfil (standard ou extreme) e aplica os limites do Docker
    domain = provision_workspace(usuario, perfil)
    return RedirectResponse(url=f"/dashboard/{usuario}", status_code=303)


@router.get("/dashboard/{usuario}", response_class=HTMLResponse)
async def dashboard(request: Request, usuario: str):
    domain = f"{usuario}.localhost"
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "usuario": usuario, "domain": domain},
    )