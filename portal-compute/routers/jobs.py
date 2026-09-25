import urllib.request
import urllib.error
import json
import re
from fastapi import APIRouter, Form, Depends
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from core.docker_mgr import list_spark_jobs, run_spark_job, verify_idle_workspaces
from core.security import get_current_user
from core.models import User

router = APIRouter(prefix="/api")

scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    verify_idle_workspaces,
    "interval",
    minutes=1,
    id="idle_monitor",
    name="Monitor de Ociosidade",
)


@router.get("/jobs")
async def get_all_jobs(current_user: User = Depends(get_current_user)):
    """List available Python jobs and schedules held by the process scheduler."""[cite: 23]
    scripts = list_spark_jobs()

    scheduled_jobs = []
    for job in scheduler.get_jobs():
        scheduled_jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": (
                    job.next_run_time.strftime("%d/%m/%Y %H:%M:%S")
                    if job.next_run_time
                    else "Pausado"
                ),
            }
        )

    return JSONResponse(
        content={"status": "success", "scripts": scripts, "scheduled": scheduled_jobs}
    )


@router.post("/jobs/run/{job_name}")
async def execute_job_now(job_name: str, current_user: User = Depends(get_current_user)):
    """Submit a selected Spark script for immediate asynchronous execution."""[cite: 23]
    success = run_spark_job(job_name, origin="UI Manual")
    if success:
        return JSONResponse(
            content={
                "status": "success",
                "message": f"A ordem para executar '{job_name}' foi enviada ao Spark!",
            }
        )
    return JSONResponse(
        content={"status": "error", "message": "Erro ao disparar job."}, status_code=500
    )


@router.post("/jobs/schedule")
async def schedule_job_cron(
    job_name: str = Form(...), 
    cron_expr: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """Create or replace an in-memory recurring schedule for a Spark job."""[cite: 23]
    try:
        trigger = CronTrigger.from_crontab(cron_expr)
        job_id = f"job_{job_name.replace('.py', '')}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        scheduler.add_job(
            func=run_spark_job,
            trigger=trigger,
            args=[job_name, "Cron Scheduler"],
            id=job_id,
            name=job_name,
        )
        return JSONResponse(
            content={
                "status": "success",
                "message": f"Job {job_name} agendado! (Cron: {cron_expr})",
            }
        )
    except ValueError:
        return JSONResponse(
            content={"status": "error", "message": "Formato Cron inválido."},
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.delete("/jobs/schedule/{job_id}")
async def remove_scheduled_job(job_id: str, current_user: User = Depends(get_current_user)):
    """Remove a scheduled Spark job from the process scheduler."""[cite: 23]
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        return JSONResponse(
            content={"status": "success", "message": "Agendamento cancelado com sucesso."}
        )
    return JSONResponse(
        content={"status": "error", "message": "Agendamento não encontrado."},
        status_code=404,
    )


@router.get("/spark/status")
async def get_spark_status(current_user: User = Depends(get_current_user)):
    """Proxy the Spark master status page as a compact JSON payload."""[cite: 23]
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
    """Resolve a Spark application's driver and return its job metadata."""[cite: 23]
    try:
        app_page_url = f"http://spark-master:8080/app/?appId={app_id}"
        req_page = urllib.request.Request(app_page_url)
        with urllib.request.urlopen(req_page) as response:
            app_html = response.read().decode("utf-8")

        match = re.search(
            r'href="(http://[^"]+)">(Application Detail UI|Application UI)</a>',
            app_html,
            re.IGNORECASE,
        )

        if not match:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "O processamento finalizou ou não possui UI ativa.",
                }
            )

        driver_url = match.group(1).rstrip("/")
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
        jobs_url = f"{driver_api_base}/{real_driver_app_id}/jobs"
        req_jobs = urllib.request.Request(jobs_url)
        with urllib.request.urlopen(req_jobs) as response:
            jobs_data = json.loads(response.read().decode("utf-8"))

        return JSONResponse(content={"status": "success", "jobs": jobs_data})

    except urllib.error.URLError:
        return JSONResponse(
            content={
                "status": "error",
                "message": "Driver parou de responder na porta 4040 (Job Concluído).",
            }
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"Erro interno: {str(e)}"}
        )