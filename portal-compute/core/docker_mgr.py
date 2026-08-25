# ============================================================================
# Docker Swarm Workspace Manager
# ============================================================================
import os
import docker
import time as tm
from docker.types import Mount, Resources

try:
    client = docker.from_env()
except Exception as e:
    print(f"Erro ao conectar no Docker: {e}")
    client = None

network_name = os.getenv("WORKSPACE_NETWORK")
tailscale_url = os.getenv("TAILSCALE_BASE_URL")
vscode_port = os.getenv("VSCODE_EXTERNAL_PORT")
WORKSPACE_LAST_SEEN = {}

def parse_memory(mem_str: str):
    """Converte string de memória (ex: '2g', '512m') para bytes"""
    if mem_str.lower().endswith('g'):
        return int(mem_str[:-1]) * 1024**3
    elif mem_str.lower().endswith('m'):
        return int(mem_str[:-1]) * 1024**2
    return int(mem_str)

def provision_workspace(usuario: str, perfil: str = "standard"):
    if not client:
        raise Exception("Cliente Docker não inicializado.")

    container_name_vscode = f"vscode-{usuario}"
    container_name_worker = f"spark-worker-{usuario}"
    domain = f"{tailscale_url}:{vscode_port}"

    if perfil == "extreme":
        vscode_ram = "2g"
        worker_ram = "6g"
        spark_ram = "6g"
        cpu_limit = 6 * 1000000000  # 6 cores em nanoCPUs
        spark_cores = "6"
    else:
        vscode_ram = "1g"
        worker_ram = "3g"
        spark_ram = "3g"
        cpu_limit = 2 * 1000000000
        spark_cores = "2"

    # Derruba serviços antigos caso existam
    for s_name in [container_name_vscode, container_name_worker]:
        try:
            service = client.services.get(s_name)
            service.remove()
            tm.sleep(2) # Pausa dramática para o Swarm matar as tasks antigas
        except docker.errors.NotFound:
            pass

    # Usamos Volumes nomeados (Docker gerencia sozinho no disco do Worker)
    vol_name = f"arena-vol-{usuario}"

    minio_ak = os.environ.get("MINIO_ACCESS_KEY")
    minio_sk = os.environ.get("MINIO_SECRET_KEY")

    if not minio_ak or not minio_sk:
        raise ValueError("ERRO CRÍTICO: Credenciais do MinIO não encontradas!")

    # 1. Serviço do VS Code (A Interface)
    startup_vscode_cmd = (
        f"sudo chown -R coder:coder /home/coder/project && "
        f"echo 'PS1=\"{usuario}@\\h:\\w\\$ \"' >> /home/coder/.bashrc && "
        f"/usr/bin/entrypoint.sh --bind-addr 0.0.0.0:8080 --auth none "
        f"--user-data-dir /home/coder/project/.vscode-data/data "
        f"--extensions-dir /home/coder/project/.vscode-data/extensions "
        f"/home/coder/project"
    )

    client.services.create(
        image="arenalake-workspace:latest",
        name=container_name_vscode,
        command=["/bin/sh", "-c", startup_vscode_cmd],
        env=[
            "SPARK_MASTER=spark://spark-master:7077",
            f"MINIO_ACCESS_KEY={minio_ak}",
            f"MINIO_SECRET_KEY={minio_sk}",
            f"WORKSPACE_RAM={spark_ram}",
            f"WORKSPACE_CORES={spark_cores}",
        ],
        mounts=[Mount(target="/home/coder/project", source=vol_name, type="volume")],
        networks=[network_name],
        resources=Resources(
            cpu_limit=cpu_limit, mem_limit=parse_memory(vscode_ram),
            cpu_reservation=cpu_limit, mem_reservation=parse_memory(vscode_ram)
        ),
        constraints=["node.labels.papel == worker"],
        labels={
            "traefik.enable": "true",
            f"traefik.http.routers.vscode-{usuario}.rule": f"PathPrefix(`/workspace/{usuario}`)",
            f"traefik.http.routers.vscode-{usuario}.entrypoints": "web",
            f"traefik.http.middlewares.strip-{usuario}.stripprefix.prefixes": f"/workspace/{usuario}",
            f"traefik.http.routers.vscode-{usuario}.middlewares": f"strip-{usuario}",
            f"traefik.http.services.vscode-{usuario}.loadbalancer.server.port": "8080",
        }
    )

    # 2. Serviço do Spark Worker
    startup_worker_cmd = (
        "export SPARK_HOME=$(python3 -c 'import pyspark; print(pyspark.__path__[0])'); "
        "export SPARK_WORKER_DIR=/tmp/spark-work; "
        "if [ ! -f \"$SPARK_HOME/bin/spark-class\" ]; then "
        "sleep 3600; else "
        f"exec \"$SPARK_HOME/bin/spark-class\" org.apache.spark.deploy.worker.Worker -c {spark_cores} -m {spark_ram} spark://spark-master:7077; fi"
    )

    client.services.create(
        image="arenalake-workspace:latest",
        name=container_name_worker,
        command=["/bin/sh", "-c", startup_worker_cmd],
        env=[
            f"MINIO_ACCESS_KEY={minio_ak}",
            f"MINIO_SECRET_KEY={minio_sk}"
        ],
        mounts=[Mount(target="/home/coder/project", source=vol_name, type="volume")],
        networks=[network_name],
        resources=Resources(
            cpu_limit=cpu_limit, mem_limit=parse_memory(worker_ram),
            cpu_reservation=cpu_limit, mem_reservation=parse_memory(worker_ram)
        ),
        constraints=["node.labels.papel == worker"]
    )

    return domain

def get_workspace_metrics(usuario: str):
    if not client:
        return {"status": "offline", "message": "Cliente offline"}

    is_online = False
    allocated_mem = 0
    allocated_cpu = 0

    # No Swarm, o get(container) quebra se a task não estiver no master.
    # Por isso, checamos o status da Task do Serviço distribuído.
    for s_name in [f"vscode-{usuario}", f"spark-worker-{usuario}"]:
        try:
            service = client.services.get(s_name)
            tasks = service.tasks(filters={"desired-state": "running"})
            for task in tasks:
                if task["Status"]["State"] == "running":
                    is_online = True
                    res = service.attrs.get("Spec", {}).get("TaskTemplate", {}).get("Resources", {}).get("Limits", {})
                    allocated_cpu += res.get("NanoCPUs", 0) / 1e9
                    allocated_mem += res.get("MemoryBytes", 0)
        except docker.errors.NotFound:
            continue

    if not is_online:
        return {"status": "offline", "message": "Workspace inativo"}

    mem_mb = round(allocated_mem / (1024 * 1024), 2)
    # Como fallback para a UI não quebrar sem a métrica em tempo real do Worker, enviamos um load placeholder
    return {
        "status": "online",
        "cpu_percent": 1.0,
        "memory_usage_mb": round(mem_mb * 0.05, 2),
        "memory_limit_mb": max(mem_mb, 1),
        "memory_percent": 5.0,
    }

def list_spark_jobs():
    if not client:
        return []
    try:
        master_container = None
        for c in client.containers.list(filters={"status": "running"}):
            if "spark-master" in c.name:
                master_container = c
                break
        if not master_container:
            return []
        res = master_container.exec_run("sh -c 'ls -1 /jobs/*.py 2>/dev/null'")
        if res.exit_code == 0:
            output = res.output.decode("utf-8").strip()
            if output:
                return [f.split("/")[-1] for f in output.split("\n")]
        return []
    except Exception as e:
        return []

def run_spark_job(job_name: str, origin: str = "manual"):
    if not client:
        return False
    try:
        master_container = None
        for c in client.containers.list(filters={"status": "running"}):
            if "spark-master" in c.name:
                master_container = c
                break
        if not master_container:
            raise Exception("Spark Master offline")
        cmd = f"spark-submit --master spark://spark-master:7077 /jobs/{job_name}"
        master_container.exec_run(cmd, detach=True)
        return True
    except Exception as e:
        return False

def get_allocatable_resources():
    if not client:
        return {"error": "Cliente Docker offline"}
    try:
        nodes = client.nodes.list()
        total_cpus = 0.0
        total_mem_bytes = 0

        # 1. Soma recursos de todos os nós (Master + Worker)
        for node in nodes:
            if node.attrs.get("Status", {}).get("State") == "ready":
                res = node.attrs.get("Description", {}).get("Resources", {})
                total_cpus += res.get("NanoCPUs", 0) / 1e9
                total_mem_bytes += res.get("MemoryBytes", 0)

        allocated_cpus = 0.0
        allocated_mem_bytes = 0

        # 2. Soma recursos alocados pelos Serviços no Swarm
        for svc in client.services.list():
            if svc.name.startswith("vscode-") or svc.name.startswith("spark-worker-"):
                task_tmpl = svc.attrs.get("Spec", {}).get("TaskTemplate", {})
                res_limits = task_tmpl.get("Resources", {}).get("Limits", {})
                
                allocated_cpus += res_limits.get("NanoCPUs", 0) / 1e9
                allocated_mem_bytes += res_limits.get("MemoryBytes", 0)

        available_cpus = max(0.0, total_cpus - allocated_cpus)
        available_mem_bytes = max(0, total_mem_bytes - allocated_mem_bytes)

        return {
            "total_cpus": round(total_cpus, 2),
            "total_mem_gb": round(total_mem_bytes / (1024**3), 2),
            "allocated_cpus": round(allocated_cpus, 2),
            "allocated_mem_gb": round(allocated_mem_bytes / (1024**3), 2),
            "available_cpus": round(available_cpus, 2),
            "available_mem_gb": round(available_mem_bytes / (1024**3), 2),
        }
    except Exception as e:
        return {"error": str(e)}

def update_workspace_activity(usuario: str):
    WORKSPACE_LAST_SEEN[usuario] = tm.time()

def shutdown_workspace(usuario: str):
    if not client:
        return
    for s_name in [f"vscode-{usuario}", f"spark-worker-{usuario}"]:
        try:
            service = client.services.get(s_name)
            service.remove()
            print(f"Serviço {s_name} removido com sucesso.")
        except:
            pass
    if usuario in WORKSPACE_LAST_SEEN:
        del WORKSPACE_LAST_SEEN[usuario]

def verify_idle_workspaces():
    current_time = tm.time()
    idle_timeout = 15 * 60
    for usuario, last_seen in list(WORKSPACE_LAST_SEEN.items()):
        if (current_time - last_seen) > idle_timeout:
            print(f"Workspace de '{usuario}' ocioso. Desligando...")
            shutdown_workspace(usuario)