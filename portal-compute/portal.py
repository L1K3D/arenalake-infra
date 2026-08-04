import os
import docker
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

# Conecta ao motor do Docker local
try:
    client = docker.from_env()
except Exception as e:
    print(f"Erro ao conectar no Docker: {e}")

# --- 1. FRONTEND: TELA INICIAL & LOGIN ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ArenaLake - Login</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background-color: #0d1117; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: #161b22; padding: 40px; border-radius: 10px; border: 1px solid #30363d; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 350px; text-align: center; }
            input { width: 90%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #30363d; background: #0d1117; color: white; }
            button { width: 95%; padding: 12px; background-color: #238636; color: white; font-weight: bold; border: none; border-radius: 5px; cursor: pointer; margin-top: 15px; }
            button:hover { background-color: #2ea043; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🚀 ArenaLake</h2>
            <p style="color: #8b949e; font-size: 0.9em; margin-bottom: 20px;">Plataforma Acadêmica de Big Data</p>
            <form action="/login" method="post">
                <input type="text" name="usuario" placeholder="Nome de usuário (ex: heitor)" required>
                <input type="password" name="senha" placeholder="Senha" required>
                <button type="submit">Entrar no Workspace</button>
            </form>
        </div>
    </body>
    </html>
    """

# --- 2. ROTA DE LOGIN ---
@app.post("/login")
async def login(usuario: str = Form(...), senha: str = Form(...)):
    usr_formatado = usuario.lower().strip().replace(" ", "-")
    return RedirectResponse(url=f"/dashboard/{usr_formatado}", status_code=303)

# --- 3. FRONTEND: DASHBOARD DE RECURSOS ---
@app.get("/dashboard/{usuario}", response_class=HTMLResponse)
async def dashboard(usuario: str):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - {usuario}</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #0d1117; color: white; padding: 40px; }}
            .container {{ max-width: 800px; margin: auto; }}
            .panel {{ background: #161b22; padding: 25px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px; }}
            h1 {{ color: #58a6ff; }}
            .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
            .stat-box {{ background: #0d1117; padding: 15px; border-radius: 8px; flex: 1; border: 1px solid #30363d; text-align: center; }}
            .stat-value {{ font-size: 1.5em; font-weight: bold; color: #2ea043; }}
            input[type=range] {{ width: 100%; }}
            button {{ width: 100%; padding: 15px; background-color: #238636; color: white; font-weight: bold; border: none; border-radius: 5px; cursor: pointer; font-size: 1.1em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Bem-vindo, {usuario} 👋</h1>
            
            <div class="stats">
                <div class="stat-box">Cluster Spark<br><span class="stat-value">Online</span></div>
                <div class="stat-box">Workers Disponíveis<br><span class="stat-value">1 / 2</span></div>
                <div class="stat-box">Storage MinIO<br><span class="stat-value">Conectado</span></div>
            </div>

            <div class="panel">
                <h3>Criar Novo Workspace (VS Code)</h3>
                <form action="/provisionar" method="post">
                    <input type="hidden" name="usuario" value="{usuario}">
                    
                    <label>Memória RAM (GB): <span id="ram_val">2 GB</span></label><br>
                    <input type="range" name="ram" min="1" max="4" value="2" oninput="document.getElementById('ram_val').innerText = this.value + ' GB'"><br><br>
                    
                    <button type="submit">⚡ Provisionar Cluster</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """

# --- 4. BACKEND: PROVISIONAMENTO VIA DOCKER ---
@app.post("/provisionar", response_class=HTMLResponse)
async def provisionar_ambiente(usuario: str = Form(...), ram: int = Form(...)):
    container_name = f"vscode-{usuario}"
    domain = f"{usuario}.localhost"
    
    try:
        container = client.containers.get(container_name)
        if container.status != "running":
            container.start()
    except docker.errors.NotFound:
        host_dir = f"/home/heitor/projects/arenalake-infra/projects_data/{usuario}"
        os.makedirs(host_dir, exist_ok=True)
        
        client.containers.run(
            image="codercom/code-server:latest",
            name=container_name,
            detach=True,
            command="--auth none",
            environment=[
                "SPARK_MASTER=spark://spark-master:7077"
            ],
            volumes={
                host_dir: {'bind': '/home/coder/project', 'mode': 'rw'}
            },
            network="arenalake-infra_arenalake-net",
            mem_limit=f"{ram}g",
            # Labels do Traefik corrigidas para apontar para a porta interna 8080 do code-server
            labels={
                "traefik.enable": "true",
                f"traefik.http.routers.vscode-{usuario}.rule": f"Host(`{domain}`)",
                f"traefik.http.services.vscode-{usuario}.loadbalancer.server.port": "8080"
            }
        )

    return f"""
    <html>
        <body style="background: #0d1117; color: white; text-align: center; padding-top: 100px; font-family: sans-serif;">
            <h2>✅ Workspace Provisionado com Sucesso!</h2>
            <p>Seus recursos de {ram}GB foram reservados.</p>
            <p>Acessando sua IDE...</p>
            <script>
                setTimeout(function() {{
                    window.location.href = "http://{domain}";
                }}, 3000);
            </script>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
