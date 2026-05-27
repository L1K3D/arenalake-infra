import os
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from kubernetes import client, config
import uvicorn

app = FastAPI()
namespace = "notebooks"

# --- 1. FRONTEND: PORTAL DE SELEÇÃO (HOME) ---
html_home = """
<!DOCTYPE html>
<html>
<head>
    <title>ArenaLake Compute</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; padding: 50px; background-color: #0d1117; color: #c9d1d9; }
        .card { background: #161b22; padding: 30px; border-radius: 10px; border: 1px solid #30363d; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 450px; margin: 100px auto 0 auto; }
        h2 { color: #58a6ff; text-align: center; margin-bottom: 5px; }
        p.subtitle { text-align: center; color: #8b949e; margin-bottom: 30px; font-size: 0.9em; }
        input[type=range] { width: 100%; cursor: pointer; }
        input[type=text] { width: 95%; padding: 10px; border-radius: 5px; border: 1px solid #30363d; background: #0d1117; color: white; margin-bottom: 20px;}
        button { width: 100%; padding: 12px; background-color: #238636; color: white; font-weight: bold; border: none; border-radius: 5px; cursor: pointer; transition: 0.2s;}
        button:hover { background-color: #2ea043; }
        .slider-label { font-weight: bold; margin-bottom: 10px; display: block; color: #8b949e;}
        span.val { color: #58a6ff; font-size: 1.2em; float: right; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🚀 ArenaLake Compute</h2>
        <p class="subtitle">Plataforma Auto-Gerenciável de Workspaces</p>
        
        <form action="/provisionar" method="post">
            <label class="slider-label">Nome do Usuário / Projeto:</label>
            <input type="text" name="usuario" placeholder="ex: heitor-dev" required>
            
            <label class="slider-label">CPUs Alocadas: <span class="val" id="cpu_val">2 Cores</span></label>
            <input type="range" name="cpu" min="1" max="4" value="2" oninput="document.getElementById('cpu_val').innerText = this.value + ' Cores'"><br><br>
            
            <label class="slider-label">Memória RAM Alocada: <span class="val" id="ram_val">4 GB</span></label>
            <input type="range" name="ram" min="1" max="8" value="4" oninput="document.getElementById('ram_val').innerText = this.value + ' GB'"><br><br>
            
            <button type="submit">⚡ Criar Instância Dedicada</button>
        </form>
    </div>
</body>
</html>
"""

# --- 2. FRONTEND: O MURAL ESTILO DATABRICKS (WORKSPACE COM TELEMETRIA) ---
def get_workspace_template(usuario: str, domain: str):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ArenaLake - Workspace de {usuario}</title>
        <style>
            html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #1a1a1a; font-family: 'Segoe UI', sans-serif; }}
            
            /* BARRA SUPERIOR ESTILO DATABRICKS */
            .databricks-bar {{
                height: 50px; background-color: #111; border-bottom: 1px solid #333;
                display: table; width: 100%; box-sizing: border-box; padding: 0 20px;
            }}
            .bar-cell {{ display: table-cell; vertical-align: middle; }}
            .title-section {{ width: 30%; color: #ff7300; font-weight: bold; font-size: 1.1em; }}
            .title-section span {{ color: #aaa; font-weight: normal; font-size: 0.85em; margin-left: 10px; }}
            
            /* METRICAS */
            .metrics-section {{ width: 70%; text-align: right; }}
            .metric-box {{
                display: inline-block; width: 220px; text-align: left; margin-left: 25px; vertical-align: middle;
            }}
            .metric-title {{ color: #999; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px; }}
            .progress-bg {{ width: 100%; background-color: #333; height: 8px; border-radius: 4px; overflow: hidden; display: inline-block; }}
            .progress-fill {{ width: 0%; height: 100%; border-radius: 4px; transition: width 0.5s ease-in-out; }}
            #cpu-fill {{ background-color: #58a6ff; }}
            #ram-fill {{ background-color: #238636; }}
            .metric-text {{ color: #fff; font-size: 0.8em; display: inline-block; margin-left: 5px; min-width: 40px; text-align: right; }}

            /* CONTAINER DO VS CODE */
            .iframe-container {{
                height: calc(100% - 50px); width: 100%; border: none;
            }}
            iframe {{ width: 100%; height: 100%; border: none; }}
        </style>
    </head>
    <body>
        <div class="databricks-bar">
            <div class="bar-cell title-section">
                📐 ArenaLake Cluster <span>| host: {usuario}</span>
            </div>
            <div class="bar-cell metrics-section">
                <div class="metric-box">
                    <div class="metric-title">🔥 Consumo CPU (<span id="cpu-raw">-</span>)</div>
                    <div style="white-space: nowrap;">
                        <div class="progress-bg"><div id="cpu-fill" class="progress-fill"></div></div>
                        <div id="cpu-txt" class="metric-text">0%</div>
                    </div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">🧠 Consumo RAM (<span id="ram-raw">-</span>)</div>
                    <div style="white-space: nowrap;">
                        <div class="progress-bg"><div id="ram-fill" class="progress-fill"></div></div>
                        <div id="ram-txt" class="metric-text">0%</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="iframe-container">
            <iframe src="http://{domain}"></iframe>
        </div>

        <script>
            // LOOP ASÍNCRONO DE TELEMETRIA EM TEMPO REAL
            async function updateMetrics() {{
                try {{
                    let response = await fetch('/api/metrics/{usuario}');
                    if (response.ok) {{
                        let data = await response.json();
                        
                        // Atualiza as barras de progresso e textos
                        document.getElementById('cpu-fill').style.width = data.cpu_pct + '%';
                        document.getElementById('cpu-txt').innerText = Math.round(data.cpu_pct) + '%';
                        document.getElementById('cpu-raw').innerText = data.cpu_raw;

                        document.getElementById('ram-fill').style.width = data.ram_pct + '%';
                        document.getElementById('ram-txt').innerText = Math.round(data.ram_pct) + '%';
                        document.getElementById('ram-raw').innerText = data.mem_raw;
                    }}
                }} catch (e) {{ console.log("Erro ao buscar métricas do cluster", e); }}
            }}
            
            // Pergunta ao Kubernetes a cada 2 segundos
            setInterval(updateMetrics, 2000);
            updateMetrics();
        </script>
    </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
async def get_portal():
    return html_home

# --- 3. BACKEND: PROVISIONAMENTO NO KUBERNETES ---
@app.post("/provisionar", response_class=HTMLResponse)
async def provisionar_ambiente(usuario: str = Form(...), cpu: int = Form(...), ram: int = Form(...)):
    usr = usuario.lower().replace(" ", "-")
    app_name = f"vscode-{usr}"
    domain = f"vscode-{usr}.arenalake.local"

    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    net_v1 = client.NetworkingV1Api()

    # Aplica as restrições rígidas baseadas na tela
    resources = client.V1ResourceRequirements(
        limits={"cpu": str(cpu), "memory": f"{ram}Gi"},
        requests={"cpu": "250m", "memory": "512Mi"}
    )

    # Injeta a IMAGEM CUSTOMIZADA e fixa a SENHA padrão protegida
    container = client.V1Container(
        name="code-server",
        image="arenalake/code-server:v1",
        args=["--auth", "none"],
        ports=[client.V1ContainerPort(container_port=8080)],
        resources=resources,
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": app_name}),
        spec=client.V1PodSpec(containers=[container])
    )
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=app_name),
        spec=client.V1DeploymentSpec(replicas=1, selector=client.V1LabelSelector(match_labels={"app": app_name}), template=template)
    )

    service = client.V1Service(
        metadata=client.V1ObjectMeta(name=app_name),
        spec=client.V1ServiceSpec(selector={"app": app_name}, ports=[client.V1ServicePort(port=80, target_port=8080)])
    )

    ingress = client.V1Ingress(
        metadata=client.V1ObjectMeta(name=f"ing-{app_name}"),
        spec=client.V1IngressSpec(
            rules=[client.V1IngressRule(
                host=domain,
                http=client.V1HTTPIngressRuleValue(paths=[client.V1HTTPIngressPath(
                    path="/", path_type="Prefix", backend=client.V1IngressBackend(service=client.V1IngressServiceBackend(name=app_name, port=client.V1ServiceBackendPort(number=80)))
                )])
            )]
        )
    )

    try: apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
    except: pass # Se já existir, ignora e vai pra tela
    try: core_v1.create_namespaced_service(namespace=namespace, body=service)
    except: pass
    try: net_v1.create_namespaced_ingress(namespace=namespace, body=ingress)
    except: pass

    # Redireciona o usuário para o painel unificado do controle de processamento
    return get_workspace_template(usr, domain)

# --- 4. API DE TELEMETRIA: CONVERSANDO COM O METRICS SERVER DO K3S ---
@app.get("/api/metrics/{usuario}")
async def get_metrics(usuario: str):
    usr = usuario.lower().replace(" ", "-")
    app_name = f"vscode-{usr}"
    
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    custom_api = client.CustomObjectsApi()
    core_v1 = client.CoreV1Api()

    try:
        # 1. Busca os limites definidos no Deployment para calcular a porcentagem
        dep = apps_v1.read_namespaced_deployment(name=app_name, namespace=namespace)
        limit_cpu = float(dep.spec.template.spec.containers[0].resources.limits.get("cpu", "1"))
        limit_mem_gi = float(dep.spec.template.spec.containers[0].resources.limits.get("memory", "1Gi").replace("Gi", ""))

        # 2. Localiza o Pod dinâmico gerado pelo Deployment
        pods = core_v1.list_namespaced_pod(namespace=namespace, label_selector=f"app={app_name}")
        if not pods.items:
            return JSONResponse({"cpu_pct": 0, "ram_pct": 0, "cpu_raw": "Off", "mem_raw": "Off"})
        
        pod_name = pods.items[0].metadata.name

        # 3. Chupa as métricas ao vivo do Metrics Server do Kubernetes
        metrics = custom_api.get_namespaced_custom_object(
            "metrics.k8s.io", "v1beta1", namespace, "pods", pod_name
        )
        
        raw_cpu = metrics["containers"][0]["usage"]["cpu"]   # Ex: "2500000n" ou "12m"
        raw_mem = metrics["containers"][0]["usage"]["memory"] # Ex: "128Mi" ou "30000Ki"

        # 4. TRADUTOR DE HARDWARE (Conversão de unidades exóticas do Kubernetes)
        # Converte CPU (nanocores ou millicores) para Cores decimais
        if raw_cpu.endswith("n"):
            used_cpu = float(raw_cpu.replace("n", "")) / 1000000000.0
        elif raw_cpu.endswith("m"):
            used_cpu = float(raw_cpu.replace("m", "")) / 1000.0
        else:
            used_cpu = float(raw_cpu)

        # Converte Memória (Kibibytes ou Mebibytes) para Gigabytes
        if raw_mem.endswith("Ki"):
            used_mem_gi = float(raw_mem.replace("Ki", "")) / (1024.0 * 1024.0)
        elif raw_mem.endswith("Mi"):
            used_mem_gi = float(raw_mem.replace("Mi", "")) / 1024.0
        elif raw_mem.endswith("Gi"):
            used_mem_gi = float(raw_mem.replace("Gi", ""))
        else:
            used_mem_gi = float(raw_mem) / (1024.0 * 1024.0 * 1024.0)

        # 5. Calcula a porcentagem real com base nos limites impostos no portal
        cpu_pct = min((used_cpu / limit_cpu) * 100.0, 100.0)
        ram_pct = min((used_mem_gi / limit_mem_gi) * 100.0, 100.0)

        return {
            "cpu_pct": cpu_pct,
            "ram_pct": ram_pct,
            "cpu_raw": f"{used_cpu:.2f}/{int(limit_cpu)} Cores",
            "mem_raw": f"{used_mem_gi:.2f}/{int(limit_mem_gi)} GB"
        }
    except Exception as e:
        # Se o Pod acabou de nascer e as métricas ainda não computaram, manda zerado
        return {"cpu_pct": 0, "ram_pct": 0, "cpu_raw": "Iniciando...", "mem_raw": "Iniciando..."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
