import urllib.request
import json
import re
import pandas as pd
import os
import io

from fastapi import APIRouter, UploadFile, File, Form, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from core.s3_mgr import get_s3_client
from core.security import get_current_user
from core.models import User
from passlib.context import CryptContext

from core.s3_mgr import fetch_catalog_data, upload_file_to_datalake, get_file_details, delete_file_from_datalake
from core.docker_mgr import (
    get_workspace_metrics,
    list_spark_jobs,
    run_spark_job,
    get_allocatable_resources,
    update_workspace_activity,
    verify_idle_workspaces,
)
from core.database import get_db, SessionLocal

from core.docker_mgr import client as docker_client, shutdown_workspace

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class BiColumnsRequest(BaseModel):
    bucket: str
    filename: str


class VisualRequest(BaseModel):
    bucket: str
    filename: str
    tipo_grafico: str
    eixo_x: str = ""
    eixo_y: str = ""
    agregacao: str = ""
    eixo_z: str = ""
    colunas_tabela: list = []
    tema: str = "padrao"
    limite_linhas: int = 100
    ordenar_por: str = ""
    ordem: str = "asc"
    # NOVOS CAMPOS PARA O SLICER GLOBAL:
    filtro_coluna: str = ""
    filtro_valor: str = ""


class FilterRequest(BaseModel):
    bucket: str
    filename: str
    coluna: str
    
class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: str
    department: str = "General"
    role: str = "common"
    
class DangerDestroyRequest(BaseModel):
    confirm_username: str

router = APIRouter(prefix="/api")

# --- INICIALIZA O MOTOR DE AGENDAMENTO (CRON) ---
scheduler = BackgroundScheduler()
scheduler.start()


@router.get("/catalog")
async def get_catalog(current_user: User = Depends(get_current_user)): # <--- Protegido!
    try:
        return JSONResponse(content={"status": "success", "data": fetch_catalog_data()})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/metrics/{usuario}")
async def get_metrics(usuario: str, current_user: User = Depends(get_current_user)):
    try:
        metrics = get_workspace_metrics(usuario)
        if metrics.get("status") == "offline":
            return JSONResponse(content=metrics, status_code=404)

        update_workspace_activity(usuario)
        return JSONResponse(content=metrics)
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/upload")
async def upload_file(
    bucket: str = Form(...), 
    usuario: str = Form(...), 
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
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
async def preview_file(bucket: str, filename: str, current_user: User = Depends(get_current_user)):
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
async def get_all_jobs(current_user: User = Depends(get_current_user)): # <--- Protegido!
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
async def execute_job_now(job_name: str, current_user: User = Depends(get_current_user)):
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
async def get_bi_columns(req: BiColumnsRequest, current_user: User = Depends(get_current_user)):
    try:
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


@router.post("/bi/valores_coluna")
async def valores_coluna_bi(req: FilterRequest, current_user: User = Depends(get_current_user)):
    try:
        s3_client = get_s3_client()
        obj = s3_client.get_object(Bucket=req.bucket, Key=req.filename)
        df = (
            pd.read_csv(io.BytesIO(obj["Body"].read()), usecols=[req.coluna])
            if req.filename.endswith(".csv")
            else pd.read_parquet(io.BytesIO(obj["Body"].read()), columns=[req.coluna])
        )

        valores = df[req.coluna].dropna().unique().tolist()
        valores = sorted([str(v) for v in valores])
        return JSONResponse(content={"status": "success", "valores": valores})
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/bi/gerar_dados")
async def gerar_dados_bi(req: VisualRequest, current_user: User = Depends(get_current_user)):
    try:
        s3_client = get_s3_client()
        obj = s3_client.get_object(Bucket=req.bucket, Key=req.filename)
        file_data = io.BytesIO(obj["Body"].read())

        # Define quais colunas carregar do arquivo
        cols_to_use = (
            req.colunas_tabela.copy()
            if req.tipo_grafico == "table"
            else [c for c in [req.eixo_x, req.eixo_y, req.eixo_z] if c]
        )

        if req.ordenar_por and req.ordenar_por not in cols_to_use:
            cols_to_use.append(req.ordenar_por)
        if req.filtro_coluna and req.filtro_coluna not in cols_to_use:
            cols_to_use.append(req.filtro_coluna)

        if req.filename.endswith(".csv"):
            df = pd.read_csv(file_data, usecols=cols_to_use)
        else:
            df = pd.read_parquet(file_data, columns=cols_to_use)

        # APLICA O FILTRO GLOBAL ANTES DE TUDO!
        if req.filtro_coluna and req.filtro_valor:
            df = df[df[req.filtro_coluna].astype(str) == str(req.filtro_valor)]

        df = df.dropna(
            subset=[
                c
                for c in cols_to_use
                if c != req.ordenar_por and c != req.filtro_coluna
            ]
        )

        # 1. TABELA DE MÚLTIPLAS COLUNAS
        if req.tipo_grafico == "table":
            if req.ordenar_por and req.ordenar_por in df.columns:
                df = df.sort_values(by=req.ordenar_por, ascending=(req.ordem == "asc"))

            df_table = df[req.colunas_tabela].head(req.limite_linhas)
            resposta = {
                "colunas": req.colunas_tabela,
                "linhas": df_table.astype(str).values.tolist(),
                "is_table": True,
                "tema": req.tema,
            }

        # 2. CARTÃO KPI (NOVO)
        elif req.tipo_grafico == "kpi":
            if req.agregacao != "count":
                df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(
                    0
                )

            if req.agregacao == "sum":
                valor = df[req.eixo_y].sum()
            elif req.agregacao == "avg":
                valor = df[req.eixo_y].mean()
            else:
                valor = df[req.eixo_y].count()

            resposta = {"valor": float(valor), "is_kpi": True, "tema": req.tema}

        elif req.tipo_grafico == "scatter":
            # Força numérico no X e Y para garantir que o plano cartesiano funcione
            df[req.eixo_x] = pd.to_numeric(df[req.eixo_x], errors="coerce").fillna(0)
            df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(0)

            # Usa o limite de linhas para não travar o ECharts (milhões de pontos travam a tela)
            df_scatter = df.head(req.limite_linhas)

            if req.eixo_z:
                # Se tiver Eixo Z, separamos por categorias (Cores diferentes)
                series_data = []
                for categoria, grupo in df_scatter.groupby(req.eixo_z):
                    pontos = grupo[[req.eixo_x, req.eixo_y]].values.tolist()
                    series_data.append({"name": str(categoria), "data": pontos})
                resposta = {"series": series_data, "is_scatter": True, "has_z": True}
            else:
                # Sem categoria, todos da mesma cor
                pontos = df_scatter[[req.eixo_x, req.eixo_y]].values.tolist()
                resposta = {
                    "series": [{"name": "Distribuição", "data": pontos}],
                    "is_scatter": True,
                    "has_z": False,
                }

        # 2. TABELA MATRIZ
        elif req.tipo_grafico == "matrix":
            if req.agregacao != "count":
                df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(
                    0
                )

            if not req.eixo_z:
                df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].count().reset_index()
                df_pivot = pd.DataFrame(
                    {req.eixo_y: df_agrupado[req.eixo_y].values},
                    index=df_agrupado[req.eixo_x].values,
                )
            else:
                if req.agregacao == "sum":
                    df_agg = (
                        df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y]
                        .sum()
                        .reset_index()
                    )
                elif req.agregacao == "avg":
                    df_agg = (
                        df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y]
                        .mean()
                        .reset_index()
                    )
                else:
                    df_agg = (
                        df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y]
                        .count()
                        .reset_index()
                    )

                df_pivot = df_agg.pivot(
                    index=req.eixo_x, columns=req.eixo_z, values=req.eixo_y
                ).fillna(0)

            # Reseta o index para ele virar uma coluna normal e podermos ordená-la
            df_pivot = df_pivot.reset_index()

            if req.ordenar_por and req.ordenar_por in df_pivot.columns:
                df_pivot = df_pivot.sort_values(
                    by=req.ordenar_por, ascending=(req.ordem == "asc")
                )

            df_pivot = df_pivot.head(req.limite_linhas)

            # Pega as colunas da resposta ignorando o eixo X que é o nosso índice visual
            cols_for_response = [str(c) for c in df_pivot.columns if c != req.eixo_x]

            resposta = {
                "colunas": cols_for_response,
                "index_nome": req.eixo_x,
                "linhas": df_pivot.astype(str).values.tolist(),
                "is_matrix": True,
                "tema": req.tema,
            }

        # 3. TODOS OS OUTROS GRÁFICOS ECHARTS (MANTÉM IGUAL AO SEU)
        else:
            if req.agregacao != "count":
                df[req.eixo_y] = pd.to_numeric(df[req.eixo_y], errors="coerce").fillna(
                    0
                )

            if req.eixo_z:
                if req.agregacao == "sum":
                    df_agrupado = (
                        df.groupby([req.eixo_x, req.eixo_z])[req.eixo_y]
                        .sum()
                        .reset_index()
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

                df_pivot = df_agrupado.pivot(
                    index=req.eixo_x, columns=req.eixo_z, values=req.eixo_y
                ).fillna(0)
                df_pivot = df_pivot.head(50)
                series_data = [
                    {"name": str(col), "data": df_pivot[col].tolist()}
                    for col in df_pivot.columns
                ]
                resposta = {
                    "categorias": df_pivot.index.astype(str).tolist(),
                    "series": series_data,
                    "is_stacked": True,
                }
            else:
                if req.agregacao == "sum":
                    df_agrupado = df.groupby(req.eixo_x)[req.eixo_y].sum().reset_index()
                elif req.agregacao == "avg":
                    df_agrupado = (
                        df.groupby(req.eixo_x)[req.eixo_y].mean().reset_index()
                    )
                else:
                    df_agrupado = (
                        df.groupby(req.eixo_x)[req.eixo_y].count().reset_index()
                    )

                df_agrupado = df_agrupado.head(50)
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
async def get_system_resources(current_user: User = Depends(get_current_user)):
    data = get_allocatable_resources()
    if "error" in data:
        return JSONResponse(
            content={"status": "error", "message": data["error"]}, status_code=500
        )
    return JSONResponse(content={"status": "success", "data": data})


@router.post("/jobs/schedule")
async def schedule_job_cron(
    job_name: str = Form(...), 
    cron_expr: str = Form(...),
    current_user: User = Depends(get_current_user)
):
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
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        return JSONResponse(
            content={"status": "success", "message": "Agendamento cancelado com sucesso."}
        )
    return JSONResponse(
        content={"status": "error", "message": "Agendamento não encontrado."},
        status_code=404,
    )


# ==========================================
# ROTAS DO CLUSTER SPARK (MONITORAMENTO)
# ==========================================


@router.get("/spark/status")
async def get_spark_status(current_user: User = Depends(get_current_user)):
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
        
@router.get("/admin/users")
async def admin_list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista todos os usuários cadastrados no ecossistema (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    users = db.query(User).all()
    user_list = []
    for u in users:
        user_list.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "is_2fa_verified": u.is_2fa_verified
        })
    return JSONResponse(content={"status": "success", "users": user_list})

@router.post("/admin/users")
async def admin_create_user(req: UserCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cria um novo usuário comum com senha temporária e obriga troca no 1º acesso (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nome de usuário já existe.")

    hashed_pw = pwd_context.hash(req.password)
    new_user = User(
        username=req.username.lower().strip().replace(" ", "-"),
        hashed_password=hashed_pw,
        full_name=req.full_name,
        email=req.email,
        department=req.department,
        role="common", # Força a criação como comum por segurança
        must_change_password=True,
        is_2fa_verified=False
    )
    db.add(new_user)
    db.commit()

    return JSONResponse(content={"status": "success", "message": f"Usuário '{new_user.username}' criado com sucesso!"})

@router.get("/admin/workspaces")
async def admin_list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista todos os workspaces (containers de usuários) ativos no Docker Swarm (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    if not docker_client:
        return JSONResponse(content={"status": "success", "workspaces": []})

    active_workspaces = []
    try:
        # Lista serviços do swarm que começam com vscode-
        services = docker_client.services.list()
        for svc in services:
            if svc.name.startswith("vscode-"):
                username = svc.name.replace("vscode-", "")
                tasks = svc.tasks(filters={"desired-state": "running"})
                
                is_running = False
                node_id = "Desconhecido"
                for task in tasks:
                    if task["Status"]["State"] == "running":
                        is_running = True
                        node_id = task.get("NodeID", "N/A")
                        break
                
                if is_running:
                    # Pcura limites de recursos definidos no spec do serviço
                    spec = svc.attrs.get("Spec", {}).get("TaskTemplate", {}).get("Resources", {}).get("Limits", {})
                    cpu_cores = spec.get("NanoCPUs", 0) / 1e9
                    ram_mb = spec.get("MemoryBytes", 0) / (1024 * 1024)

                    active_workspaces.append({
                        "username": username,
                        "service_name": svc.name,
                        "cpu": f"{cpu_cores} Cores",
                        "ram": f"{round(ram_mb, 1)} MB",
                        "node": node_id
                    })
    except Exception as e:
        print(f"Erro ao inspecionar Docker Swarm: {e}")

    return JSONResponse(content={"status": "success", "workspaces": active_workspaces})

@router.post("/admin/workspaces/kill/{username}")
async def admin_kill_workspace(username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Executa o Kill Switch: derruba os containers do workspace do usuário imediatamente (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    try:
        shutdown_workspace(username)
        return JSONResponse(content={"status": "success", "message": f"Sessão do usuário '{username}' encerrada com sucesso pelo Kill Switch."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao encerrar sessão: {str(e)}")

@router.get("/admin/cluster/nodes")
async def admin_cluster_nodes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Inspeciona os nós do Docker Swarm (Master/Worker, Status e Hardware) (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    if not docker_client:
        return JSONResponse(content={"status": "success", "nodes": []})
    
    nodes_data = []
    try:
        nodes = docker_client.nodes.list()
        for node in nodes:
            attrs = node.attrs
            status = attrs.get("Status", {}).get("State", "unknown")
            role = attrs.get("Spec", {}).get("Role", "worker")
            labels = attrs.get("Spec", {}).get("Labels", {})
            papel = labels.get("papel", role)
            hostname = attrs.get("Description", {}).get("Hostname", "unknown")
            resources = attrs.get("Description", {}).get("Resources", {})
            total_cpus = resources.get("NanoCPUs", 0) / 1e9
            total_mem = resources.get("MemoryBytes", 0) / (1024**3)
            
            nodes_data.append({
                "id": node.id,
                "hostname": hostname,
                "role": papel.upper(),
                "status": status,
                "cpus": round(total_cpus, 1),
                "memory_gb": round(total_mem, 1)
            })
    except Exception as e:
        print(f"Erro ao ler nós do Swarm: {e}")
    
    return JSONResponse(content={"status": "success", "nodes": nodes_data})

@router.get("/admin/files/{username}")
async def admin_inspect_user_files(username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Espionagem de Arquivos: Inspeciona o volume persistente do usuário com segurança (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    if not docker_client:
        raise HTTPException(status_code=500, detail="Cliente Docker offline.")
    
    vol_name = f"arena-vol-{username}"
    files_list = []
    try:
        # Roda um container Alpine temporário montando o volume do usuário em modo somente leitura (ro)
        output = docker_client.containers.run(
            image="alpine:latest",
            command="find /data -maxdepth 3 -not -path '*/.*'",
            volumes={vol_name: {"bind": "/data", "mode": "ro"}},
            remove=True
        )
        files_list = output.decode("utf-8").splitlines()
    except Exception as e:
        files_list = [f"Volume não encontrado ou vazio para '{username}' ({str(e)})"]
        
    return JSONResponse(content={"status": "success", "username": username, "files": files_list})

@router.post("/admin/danger/destroy")
async def admin_self_destruct(req: DangerDestroyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Painel de Autodestruição Crítica: Purgar todos os workspaces ativos do cluster (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    
    if req.confirm_username != current_user.username:
        raise HTTPException(status_code=400, detail="O nome de usuário digitado não confere com o seu usuário admin atual.")
    
    try:
        if docker_client:
            services = docker_client.services.list()
            for svc in services:
                if svc.name.startswith("vscode-") or svc.name.startswith("spark-worker-"):
                    try:
                        svc.remove()
                    except:
                        pass
        print(f"[CRITICAL SECURITY] PROTOCOLO DE AUTODESTRUIÇÃO EXECUTADO PELO ADMIN: {current_user.username}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na execução da autodestruição: {str(e)}")
        
    return JSONResponse(content={"status": "success", "message": "Protocolo de Autodestruição executado com sucesso. Todos os workspaces ativos foram purgados."})

@router.get("/admin/catalog")
async def admin_get_catalog(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna o catálogo completo de buckets e arquivos do MinIO para auditoria do Admin (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    try:
        return JSONResponse(content={"status": "success", "data": fetch_catalog_data()})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.delete("/admin/catalog/file")
async def admin_delete_catalog_file(bucket: str = Form(...), filename: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exclui um arquivo/parquet do Data Catalog (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    try:
        delete_file_from_datalake(bucket, filename)
        return JSONResponse(content={"status": "success", "message": f"Arquivo '{filename}' removido do bucket '{bucket}' com sucesso!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao excluir arquivo: {str(e)}")

@router.post("/admin/catalog/upload")
async def admin_upload_catalog_file(
    bucket: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Faz upload de novos datasets ou scripts diretamente para o Data Lake (Apenas Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado. Requer privilégios de Administrador.")
    try:
        upload_file_to_datalake(bucket, file.file, file.filename, current_user.username)
        return JSONResponse(content={"status": "success", "message": f"Arquivo '{file.filename}' enviado para o bucket '{bucket}' com sucesso!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar arquivo: {str(e)}")

scheduler.add_job(
    verify_idle_workspaces,
    "interval",
    minutes=1,
    id="idle_monitor",
    name="Monitor de Ociosidade",
)