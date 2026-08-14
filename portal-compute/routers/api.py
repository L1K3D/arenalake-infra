# ============================================================================
# ArenaLake API Router - REST Endpoints
# ============================================================================
# This module defines REST APIs for the dashboard frontend.
# Endpoints handle:
# - Data Catalog: list S3/MinIO buckets and files
# - Workspace Metrics: CPU, RAM usage for user containers
# - File Management: upload files to data lake
# - Spark Monitoring: real-time job tracking and worker status
# ============================================================================

from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
import urllib.request
import json
import re
from core.s3_mgr import fetch_catalog_data, upload_file_to_datalake, get_file_details
from core.docker_mgr import get_workspace_metrics

# Initialize router with /api prefix
# All endpoints will be prefixed with /api/
router = APIRouter(prefix="/api")


@router.get("/catalog")
async def get_catalog():
    """Fetch the complete data catalog from MinIO/S3.
    Returns all buckets and their files/datasets.
    """
    try:
        return JSONResponse(content={"status": "success", "data": fetch_catalog_data()})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/metrics/{usuario}")
async def get_metrics(usuario: str):
    """Retrieve real-time resource metrics (CPU, RAM) for a user's workspace.
    Returns offline status if the workspace container is not running.
    """
    try:
        metrics = get_workspace_metrics(usuario)
        if metrics.get("status") == "offline":
            return JSONResponse(content=metrics, status_code=404)
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/upload")
async def upload_file(
    bucket: str = Form(...), usuario: str = Form(...), file: UploadFile = File(...)
):
    """Upload a file to the MinIO data lake.
    The file is stored with metadata about who uploaded it.
    """
    try:
        upload_file_to_datalake(bucket, file.file, file.filename, usuario)
        return JSONResponse(
            content={"status": "success", "message": "Arquivo enviado com sucesso!"}
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/preview/{bucket}/{filename:path}")
async def preview_file(bucket: str, filename: str):
    """Fetch file metadata and preview content.
    Returns file size, last modified date, uploader info, and preview data.
    """
    try:
        details = get_file_details(bucket, filename)
        return JSONResponse(content={"status": "success", "data": details})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


# ============================================================================
# Spark Cluster Monitoring Endpoints
# ============================================================================

@router.get("/spark/status")
async def get_spark_status():
    """Fetch overall Apache Spark cluster status.
    Returns list of active workers, running jobs, and completed jobs.
    """
    try:
        url = "http://spark-master:8080/json/"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))

            payload = {
                "status": "success",
                "workers": data.get("workers", []),
                "active_apps": data.get("activeapps", []),
                "completed_apps": data.get("completedapps", [])[:10],
            }
            return JSONResponse(content=payload)
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/spark/app/{app_id}/jobs")
async def get_spark_app_jobs(app_id: str):
    """Fetch detailed job progress for a specific Spark application.
    
    Scrapes the Spark Master and Driver UIs to extract task progress in real-time.
    Requires connecting to the Driver's REST API on port 4040.
    
    Note: The Spark Master API doesn't expose the Driver URL, so HTML scraping is used.
    """
    import urllib.error

    try:
        # 1. O Master não expõe a URL via JSON, então raspamos a página HTML dele internamente!
        app_page_url = f"http://spark-master:8080/app/?appId={app_id}"
        req_page = urllib.request.Request(app_page_url)
        with urllib.request.urlopen(req_page) as response:
            app_html = response.read().decode("utf-8")

        # 2. Busca com Regex exatamente o link HTTP (ex: http://172.18.0.x:4040) do Driver UI
        match = re.search(
            r'href="(http://[^"]+)">(Application Detail UI|Application UI)</a>',
            app_html,
            re.IGNORECASE,
        )

        if not match:
            # Se o link sumiu do HTML, o Job terminou e o Spark fechou a porta 4040
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "O processamento finalizou e o Spark desativou o monitoramento ao vivo.",
                }
            )

        driver_url = match.group(1).rstrip("/")

        # 3. Bate na API do Driver (seu Jupyter) para achar o ID interno que ele está usando
        driver_api_base = f"{driver_url}/api/v1/applications"
        req_driver = urllib.request.Request(driver_api_base)
        with urllib.request.urlopen(req_driver) as response:
            driver_apps = json.loads(response.read().decode("utf-8"))

        if not driver_apps:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "API do Driver está online, mas vazia.",
                }
            )

        real_driver_app_id = driver_apps[0]["id"]

        # 4. Finalmente puxa os Jobs perfeitamente!
        jobs_url = f"{driver_api_base}/{real_driver_app_id}/jobs"
        req_jobs = urllib.request.Request(jobs_url)
        with urllib.request.urlopen(req_jobs) as response:
            jobs_data = json.loads(response.read().decode("utf-8"))

        return JSONResponse(content={"status": "success", "jobs": jobs_data})

    except urllib.error.URLError as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": "O Driver parou de responder na porta 4040 (Job Concluído).",
            }
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"Erro interno: {str(e)}"}
        )