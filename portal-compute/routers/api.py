import urllib.request
import json
import re
import pandas as pd
import os
import io

from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel
from core.s3_mgr import get_s3_client


class BiColumnsRequest(BaseModel):
    bucket: str
    filename: str


class VisualRequest(BaseModel):
    bucket: str
    filename: str
    eixo_x: str
    eixo_y: str
    agregacao: str
    tipo_grafico: str
    eixo_z: str = ""


from core.s3_mgr import fetch_catalog_data, upload_file_to_datalake, get_file_details
from core.docker_mgr import (
    get_workspace_metrics,
    list_spark_jobs,
    run_spark_job,
    get_allocatable_resources,
    update_workspace_activity,
    verify_idle_workspaces,
)

router = APIRouter(prefix="/api")

# --- INICIALIZA O MOTOR DE AGENDAMENTO (CRON) ---
scheduler = BackgroundScheduler()
scheduler.start()


@router.get("/catalog")
async def get_catalog():
    try:
        return JSONResponse(content={"status": "success", "data": fetch_catalog_data()})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/metrics/{usuario}")
async def get_metrics(usuario: str):
    try:
        metrics = get_workspace_metrics(usuario)
        if metrics.get("status") == "offline":
            return JSONResponse(content=metrics, status_code=404)

        # O workspace está online e o usuário está com a aba aberta! Atualiza o timer.
        update_workspace_activity(usuario)

        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/upload")
async def upload_file(
    bucket: str = Form(...), usuario: str = Form(...), file: UploadFile = File(...)
):
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
    try:
        details = get_file_details(bucket, filename)
        return JSONResponse(content={"status": "success", "data": details})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


# ==========================================
# ROTAS DO ARENALAKE SCHEDULER E JOBS
# ==========================================


@router.get("/jobs")
async def get_all_jobs():
    """Lista os scripts .py disponíveis e os agendamentos ativos na memória"""
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
async def execute_job_now(job_name: str):
    """Executa o script imediatamente"""
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


@router.post("/bi/colunas")
async def get_bi_columns(req: BiColumnsRequest):
    try:
        # Usa o cliente Boto3 nativo do seu sistema (Zero timeouts na rede)
        s3_client = get_s3_client()
        obj = s3_client.get_object(Bucket=req.bucket, Key=req.filename)

        if req.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(obj["Body"].read()), nrows=0)
        else:
            df = pd.read_parquet(io.BytesIO(obj["Body"].read()))

        return JSONResponse(
            content={"status": "success", "colunas": df.columns.tolist()}
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/bi/gerar_dados")
async def gerar_dados_bi(req: VisualRequest):
    try:
        from core.s3_mgr import get_s3_client
        import io

        s3_client = get_s3_client()
        obj = s3_client.get_object(Bucket=req.bucket, Key=req.filename)
        file_data = io.BytesIO(obj["Body"].read())

        cols_to_use = [req.eixo_x, req.eixo_y]
        if req.eixo_z:
            cols_to_use.append(req.eixo_z)

        if req.filename.endswith(".csv"):
            df = pd.read_csv(file_data, usecols=cols_to_use)
        else:
            df = pd.read_parquet(file_data, columns=cols_to_use)

        # Remove nulos e converte métrica
        df = df.dropna(subset=cols_to_use)
        if req.agregacao != "count":
            df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(0)

        # SE O USUÁRIO ESCOLHER UMA SÉRIE (EMPILHADO)
        if req.eixo_z:
            if req.agregacao == "sum":
                df_agrupado = (
                    df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].sum().reset_index()
                )
            elif req.agregacao == "avg":
                df_agrupado = (
                    df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y]
                    .mean()
                    .reset_index()
                )
            else:
                df_agrupado = (
                    df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y]
                    .count()
                    .reset_index()
                )

            # Faz o pivot para preparar os dados pro Echarts
            df_pivot = df_agrupado.pivot(
                index=req.eixo_x, columns=req.eixo_z, values=req.eixo_y
            ).fillna(0)
            df_pivot = df_pivot.head(50)

            series_data = []
            for col in df_pivot.columns:
                series_data.append({"name": str(col), "data": df_pivot[col].tolist()})

            resposta = {
                "categorias": df_pivot.index.astype(str).tolist(),
                "series": series_data,
                "is_stacked": True,
            }

        if req.tipo_grafico == 'table':
            cols_table = [req.eixo_x, req.eixo_y]
            if req.eixo_z: cols_table.append(req.eixo_z)
            df_table = df[cols_table].head(50)
            
            resposta = {
                "colunas": cols_table,
                "linhas": df_table.values.tolist(),
                "is_table": True
            }

        # SE FOR MATRIZ (MATRIX / PIVOT)
        elif req.tipo_grafico == 'matrix':
            if not req.eixo_z:
                # Se não passar eixo Z para a matriz, usamos o eixo Y como valor e cruzamos X com outra dimensão se houver, ou criamos um resumo
                df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].count().reset_index()
                df_pivot = pd.DataFrame({req.eixo_y: df_agrupado[req.eixo_y].values}, index=df_agrupado[req.eixo_x].values)
            else:
                if req.agregacao == "sum":
                    df_agg = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].sum().reset_index()
                elif req.agregacao == "avg":
                    df_agg = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].mean().reset_index()
                else:
                    df_agg = df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y].count().reset_index()
                
                df_pivot = df_agg.pivot(index=req.eixo_x, columns=req.eixo_z, values=req.eixo_y).fillna(0)

            resposta = {
                "colunas": [str(c) for c in df_pivot.columns],
                "index_nome": req.eixo_x,
                "linhas": df_pivot.reset_index().values.tolist(),
                "is_matrix": True
            }

        # SE FOR GRÁFICO SIMPLES
        else:
            if req.agregacao == "sum":
                df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].sum().reset_index()
            elif req.agregacao == "avg":
                df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].mean().reset_index()
            else:
                df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].count().reset_index()

            resposta = {
                "categorias": df_agrupado[req.eixo_x].astype(str).tolist(),
                "valores": df_agrupado[req.eixo_y].tolist(),
                "is_stacked": False,
            }

        return JSONResponse(content={"status": "success", "data": resposta})

    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/system/resources")
async def get_system_resources():
    data = get_allocatable_resources()
    if "error" in data:
        return JSONResponse(
            content={"status": "error", "message": data["error"]}, status_code=500
        )
    return JSONResponse(content={"status": "success", "data": data})


@router.post("/jobs/schedule")
async def schedule_job_cron(job_name: str = Form(...), cron_expr: str = Form(...)):
    """Agenda um script usando padrão Cron"""
    try:
        # Valida e cria a regra de agendamento (Ex: "0 2 * * *")
        trigger = CronTrigger.from_crontab(cron_expr)
        job_id = f"job_{job_name.replace('.py', '')}"

        # Se já existir um agendamento pra esse script, remove o antigo
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
            content={
                "status": "error",
                "message": "Formato Cron inválido. Use algo como '0 2 * * *'.",
            },
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.delete("/jobs/schedule/{job_id}")
async def remove_scheduled_job(job_id: str):
    """Cancela um agendamento"""
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        return JSONResponse(
            content={
                "status": "success",
                "message": "Agendamento cancelado com sucesso.",
            }
        )
    return JSONResponse(
        content={"status": "error", "message": "Agendamento não encontrado."},
        status_code=404,
    )


# ==========================================
# ROTAS DO CLUSTER SPARK (MONITORAMENTO)
# ==========================================


@router.get("/spark/status")
async def get_spark_status():
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
    import urllib.error

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


scheduler.add_job(
    verify_idle_workspaces,
    "interval",
    minutes=1,
    id="idle_monitor",
    name="Monitor de Ociosidade",
)