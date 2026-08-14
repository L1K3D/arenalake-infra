# ============================================================================
# Docker Workspace Manager
# ============================================================================
# This module manages the lifecycle of user workspace containers.
# Responsibilities:
# - Provision dedicated VS Code IDE and Spark Worker containers per user
# - Apply CPU/RAM limits based on hardware profile selection
# - Manage container networking and volume mounting
# - Monitor real-time resource usage (CPU, memory) of running workspaces
# - Cleanup old containers before provisioning new ones
# ============================================================================

import os
import docker

# Initialize Docker client (connects to the local Docker daemon)
try:
    client = docker.from_env()
except Exception as e:
    print(f"Erro ao conectar no Docker: {e}")
    client = None


def provision_workspace(usuario: str, perfil: str = "standard"):
    """Provision Docker containers for a user's workspace.
    
    Creates two dedicated containers per user:
    1. VS Code IDE container: web-based development environment
    2. Spark Worker container: distributed computing node
    
    Hardware profiles:
    - standard: 2 CPU cores, 4GB total RAM (VS Code 1GB, Worker 3GB)
    - extreme: 6 CPU cores, 8GB total RAM (VS Code 2GB, Worker 6GB)
    
    Args:
        usuario: Username (used in container names and subdomain)
        perfil: Hardware profile ("standard" or "extreme")
    
    Returns:
        domain: The user's domain name (username.localhost)
    """
    if not client:
        raise Exception("Cliente Docker não inicializado.")

    # Define container names for this user
    # Each user gets a dedicated IDE and Spark worker
    container_name_vscode = f"vscode-{usuario}"
    container_name_worker = f"spark-worker-{usuario}"
    domain = f"{usuario}.localhost"

    # Set resource limits based on selected hardware profile
    if perfil == "extreme":
        vscode_ram = "2g"
        worker_ram = "6g"
        spark_ram = "6g"
        cpu_limit = 6 * 1000000000  # 6 CPU cores in nanoseconds
        spark_cores = "6"
    else:
        # Standard profile (default)
        vscode_ram = "1g"
        worker_ram = "3g"
        spark_ram = "3g"
        cpu_limit = 2 * 1000000000  # 2 CPU cores in nanoseconds
        spark_cores = "2"

    # Stop and remove old containers if they exist
    # Ensures clean state before provisioning new workspace
    for c_name in [container_name_vscode, container_name_worker]:
        try:
            container = client.containers.get(c_name)
            if container.status == "running":
                container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass

    # Create user project directory on host filesystem
    base_path = os.getenv("HOST_PROJECT_PATH", "/tmp/arenalake-infra")
    host_dir = f"{base_path}/projects_data/{usuario}"
    os.makedirs(host_dir, exist_ok=True)
    os.chmod(host_dir, 0o777)

    # Retrieve MinIO credentials from environment (set in docker-compose)
    # Fail fast if credentials are missing
    minio_ak = os.environ.get("MINIO_ACCESS_KEY")
    minio_sk = os.environ.get("MINIO_SECRET_KEY")

    if not minio_ak or not minio_sk:
        raise ValueError(
            "ERRO CRÍTICO: Credenciais do MinIO (MINIO_ACCESS_KEY e MINIO_SECRET_KEY) não encontradas no ambiente!"
        )

    # 1. Sobe o container do VS Code (A Interface)
    client.containers.run(
        image="arenalake-workspace:latest",
        name=container_name_vscode,
        detach=True,

        command="--auth none --user-data-dir /home/coder/project/.vscode-data/data --extensions-dir /home/coder/project/.vscode-data/extensions",
        environment=[
            "SPARK_MASTER=spark://spark-master:7077",
            f"MINIO_ACCESS_KEY={minio_ak}",
            f"MINIO_SECRET_KEY={minio_sk}",
            f"WORKSPACE_RAM={spark_ram}",
            f"WORKSPACE_CORES={spark_cores}",
        ],
        # Mount user project directory (persists work across container restarts)
        volumes={host_dir: {"bind": "/home/coder/project", "mode": "rw"}},
        network="arenalake-infra_arenalake-net",
        mem_limit=vscode_ram,
        nano_cpus=cpu_limit,
        labels={
            # Traefik reverse proxy configuration
            # Makes VS Code accessible at http://username.localhost
            "traefik.enable": "true",
            f"traefik.http.routers.vscode-{usuario}.rule": f"Host(`{domain}`)",
            f"traefik.http.services.vscode-{usuario}.loadbalancer.server.port": "8080",
        },
    )

    # ========================================================================
    # 2. Launch Spark Worker Container
    # ========================================================================
    # Runs a Spark worker that connects to the Spark master for distributed computing
    startup_worker_cmd = (
        # Dynamically detect Spark installation path from PySpark module
        "echo 'Descobrindo o SPARK_HOME via Python...'; "
        "export SPARK_HOME=$(python3 -c 'import pyspark; print(pyspark.__path__[0])'); "
        # Redirect temporary work files to /tmp (avoid disk space issues)
        "export SPARK_WORKER_DIR=/tmp/spark-work; "
        'echo "SPARK_HOME definido como: $SPARK_HOME"; '
        'if [ ! -f "$SPARK_HOME/bin/spark-class" ]; then '
        "echo 'ERRO FATAL: spark-class nao encontrado dentro do SPARK_HOME!'; "
        "sleep 3600; "
        "else "
        "echo 'Iniciando Spark Worker...'; "
        # Connect to Spark master node with allocated CPU and RAM
        f'exec "$SPARK_HOME/bin/spark-class" org.apache.spark.deploy.worker.Worker -c {spark_cores} -m {spark_ram} spark://spark-master:7077; '
        "fi"
    )

    client.containers.run(
        image="arenalake-workspace:latest",
        name=container_name_worker,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", startup_worker_cmd],
        environment=[f"MINIO_ACCESS_KEY={minio_ak}", f"MINIO_SECRET_KEY={minio_sk}"],
        volumes={host_dir: {"bind": "/home/coder/project", "mode": "rw"}},
        network="arenalake-infra_arenalake-net",
        mem_limit=worker_ram,
        nano_cpus=cpu_limit,
    )

    return domain


def get_workspace_metrics(usuario: str):
    """Fetch real-time resource usage metrics for a user's workspace.
    
    Aggregates CPU and memory usage from both VS Code and Spark Worker containers.
    
    Returns:
        Dictionary with status and metrics, or offline status if containers not running.
        Metrics include:
        - cpu_percent: Total CPU usage as percentage of allocated cores
        - memory_usage_mb: Total memory in use (MB)
        - memory_limit_mb: Total memory limit (MB)
        - memory_percent: Memory usage as percentage of limit
    """
    if not client:
        raise Exception("Cliente Docker não inicializado.")

    total_mem_usage = 0
    total_mem_limit = 0
    total_cpu_percent = 0.0
    is_online = False

    # Monitor both VS Code and Spark Worker containers for this user
    # Aggregate their metrics together for total workspace usage
    for c_name in [f"vscode-{usuario}", f"spark-worker-{usuario}"]:
        try:
            container = client.containers.get(c_name)
            # Collect real-time container statistics
            stats = container.stats(stream=False)
            is_online = True

            # Calculate memory usage (cache doesn't count as real usage)
            mem_usage_bytes = stats.get("memory_stats", {}).get("usage", 0)
            mem_limit_bytes = stats.get("memory_stats", {}).get("limit", 0)
            mem_cache = stats.get("memory_stats", {}).get("stats", {}).get("cache", 0)
            mem_usage_real = max(0, mem_usage_bytes - mem_cache)

            total_mem_usage += mem_usage_real
            total_mem_limit += mem_limit_bytes

            # Calculate CPU usage percentage
            # Docker provides cumulative CPU time, so we calculate the delta
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})

            cpu_delta = cpu_stats.get("cpu_usage", {}).get(
                "total_usage", 0
            ) - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
                "system_cpu_usage", 0
            )

            if system_delta > 0 and cpu_delta > 0:
                nano_cpus = container.attrs.get("HostConfig", {}).get("NanoCpus", 0)
                allocated_cpus = (nano_cpus / 1000000000) if nano_cpus > 0 else 2.0
                c_cpu = (cpu_delta / system_delta) * 100.0 / allocated_cpus
                total_cpu_percent += c_cpu

        except docker.errors.NotFound:
            continue

    if not is_online:
        return {"status": "offline", "message": "Workspace não está rodando"}

    total_cpu_percent = min(round(total_cpu_percent, 2), 100.0)

    if total_mem_limit == 0:
        total_mem_limit = 1

    mem_usage_mb = round(total_mem_usage / (1024 * 1024), 2)
    mem_limit_mb = round(total_mem_limit / (1024 * 1024), 2)
    mem_percent = round((total_mem_usage / total_mem_limit) * 100, 2)

    return {
        "status": "online",
        "cpu_percent": total_cpu_percent,
        "memory_usage_mb": mem_usage_mb,
        "memory_limit_mb": mem_limit_mb,
        "memory_percent": mem_percent,
    }