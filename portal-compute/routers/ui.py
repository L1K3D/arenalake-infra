from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.docker_mgr import provision_workspace

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(usuario: str = Form(...), senha: str = Form(...)):
    usr_formatado = usuario.lower().strip().replace(" ", "-")
    return RedirectResponse(url=f"/dashboard/{usr_formatado}", status_code=303)

@router.get("/dashboard/{usuario}", response_class=HTMLResponse)
async def dashboard(request: Request, usuario: str):
    domain = f"{usuario}.localhost"
    return templates.TemplateResponse("dashboard.html", {"request": request, "usuario": usuario, "domain": domain})

@router.post("/provisionar")
async def provisionar_ambiente(usuario: str = Form(...), ram: int = Form(...)):
    domain = provision_workspace(usuario, ram)
    return RedirectResponse(url=f"/dashboard/{usuario}", status_code=303)
