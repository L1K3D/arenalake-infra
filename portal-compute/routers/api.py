from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response
import urllib.request
from core.s3_mgr import fetch_catalog_data, upload_file_to_datalake, get_file_details
from core.docker_mgr import get_workspace_metrics

router = APIRouter(prefix="/api")

@router.get("/catalog")
async def get_catalog():
    try:
        return JSONResponse(content={"status": "success", "data": fetch_catalog_data()})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.get("/metrics/{usuario}")
async def get_metrics(usuario: str):
    try:
        metrics = get_workspace_metrics(usuario)
        if metrics.get("status") == "offline":
             return JSONResponse(content=metrics, status_code=404)
        return JSONResponse(content=metrics)
    except Exception as e:
         return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/upload")
async def upload_file(bucket: str = Form(...), usuario: str = Form(...), file: UploadFile = File(...)):
    try:
        upload_file_to_datalake(bucket, file.file, file.filename, usuario)
        return JSONResponse(content={"status": "success", "message": "Arquivo enviado com sucesso!"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.get("/preview/{bucket}/{filename:path}")
async def preview_file(bucket: str, filename: str):
    try:
        details = get_file_details(bucket, filename)
        return JSONResponse(content={"status": "success", "data": details})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

# --- SMART PROXY UNIVERSAL PARA O SPARK ---
@router.get("/proxy/spark")
@router.get("/proxy/spark/{path:path}")
async def proxy_spark(request: Request, path: str = ""):
    query_string = request.url.query
    
    # Roteamento inteligente para o Master ou para as UIs internas de Apps/Jobs
    url = f"http://spark-master:8080/{path}"
    if path.startswith("app/"):
        url = f"http://spark-master:8080/{path}"

    if query_string:
        url += f"?{query_string}"

    try:
        with urllib.request.urlopen(url) as response:
            content = response.read()
            content_type = response.headers.get('Content-Type', '')

            if 'text/html' in content_type:
                html = content.decode('utf-8')

                if path == "" or path == "/":
                    if "<head>" in html:
                        html = html.replace("<head>", "<head>\n    <meta http-equiv='refresh' content='5'>")

                    if "Running Applications (0)" in html and "Completed Applications (0)" in html:
                        aviso_vazio = """
                        <div style="padding: 40px; text-align: center; background: #161b22; border-radius: 8px; border: 1px solid #30363d; margin: 20px 0;">
                            <h3 style="color: #58a6ff; margin-bottom: 10px;">⚡ Nenhum Job Spark Ativo</h3>
                            <p style="color: #8b949e; margin: 0;">Aloque ou execute uma aplicação Spark a partir do seu workspace no VS Code para monitorá-la por aqui.</p>
                        </div>
                        """
                        html = html.replace("Running Applications (0)", f"Running Applications (0)<br>{aviso_vazio}")

                # Ajustes globais de rotas
                html = html.replace('href="/', 'href="/api/proxy/spark/')
                html = html.replace('src="/', 'src="/api/proxy/spark/')

                # Script avançado para reescrever os links internos da UI de Jobs, Stages e Tasks em tempo de execução
                script_corretor = """
                <script>
                    window.addEventListener('DOMContentLoaded', (event) => {
                        document.querySelectorAll('a').forEach(a => {
                            let href = a.getAttribute('href');
                            if (href && !href.startsWith('/api/proxy/spark') && !href.startsWith('http')) {
                                if (href.includes('app?appId=') || href.startsWith('app/')) {
                                    a.setAttribute('href', '/api/proxy/spark/' + href.replace(/^\\/+/, ''));
                                } else {
                                    let currentPath = window.location.pathname;
                                    if (currentPath.includes('/app/')) {
                                        let baseAppPath = currentPath.substring(0, currentPath.indexOf('/app/') + 5);
                                        let appIdMatch = currentPath.match(/app-[0-9]+/);
                                        // Garante que o caminho base mantenha o ID da aplicação ativo
                                        a.setAttribute('href', '/api/proxy/spark/app/?appId=' + window.location.search.split('=')[1] + '&' + href);
                                    }
                                }
                            }
                        });
                    });
                </script>
                """
                if "</body>" in html:
                    html = html.replace("</body>", f"{script_corretor}\n</body>")

                return HTMLResponse(content=html, status_code=response.status)

            return Response(content=content, media_type=content_type)

    except Exception as e:
        return HTMLResponse(content=f"<h3>Erro no Proxy do Spark: {str(e)}</h3>", status_code=500)
