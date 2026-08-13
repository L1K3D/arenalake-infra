import os
import docker

try:
    client = docker.from_env()
except Exception as e:
    print(f"Erro ao conectar no Docker: {e}")
    client = None


def provision_workspace(usuario: str, perfil: str = "standard"):
    if not client:
        raise Exception("Cliente Docker não inicializado.")

    # A sua ideia aplicada: Duas máquinas dedicadas por usuário!
    container_name_vscode = f"vscode-{usuario}"
    container_name_worker = f"spark-worker-{usuario}"
    domain = f"{usuario}.localhost"

    if perfil == "extreme":
        vscode_ram = "2g"
        worker_ram = "6g"
        spark_ram = "6g"
        cpu_limit = 6 * 1000000000
        spark_cores = "6"
    else:
        vscode_ram = "1g"
        worker_ram = "3g"
        spark_ram = "3g"
        cpu_limit = 2 * 1000000000
        spark_cores = "2"

    # Limpa os containers antigos (VS Code e Worker dedicado) se existirem
    for c_name in [container_name_vscode, container_name_worker]:
        try:
            container = client.containers.get(c_name)
            if container.status == "running":
                container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass

    base_path = os.getenv("HOST_PROJECT_PATH", "/tmp/arenalake-infra")

    host_dir = f"{base_path}/projects_data/{usuario}"
    os.makedirs(host_dir, exist_ok=True)
    os.chmod(host_dir, 0o777)

    # SEGURANÇA: Lê puramente do ambiente. Se não existir, trava a execução com um erro claro.
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
        # --- O PULO DO GATO: Salva as extensões ocultas (.vscode-data) dentro do projeto! ---
        command="--auth none --user-data-dir /home/coder/project/.vscode-data/data --extensions-dir /home/coder/project/.vscode-data/extensions",
        environment=[
            "SPARK_MASTER=spark://spark-master:7077",
            f"MINIO_ACCESS_KEY={minio_ak}",
            f"MINIO_SECRET_KEY={minio_sk}",
            f"WORKSPACE_RAM={spark_ram}",
            f"WORKSPACE_CORES={spark_cores}",
        ],
        # Voltamos a usar APENAS o volume do projeto (que já sabemos que funciona 100%)
        volumes={host_dir: {"bind": "/home/coder/project", "mode": "rw"}},
        network="arenalake-infra_arenalake-net",
        mem_limit=vscode_ram,
        nano_cpus=cpu_limit,
        labels={
            "traefik.enable": "true",
            f"traefik.http.routers.vscode-{usuario}.rule": f"Host(`{domain}`)",
            f"traefik.http.services.vscode-{usuario}.loadbalancer.server.port": "8080",
        },
    )

    # 2. Sobe o container do Spark Worker Dedicado (O Músculo)
    startup_worker_cmd = (
        "echo 'Descobrindo o SPARK_HOME via Python...'; "
        "export SPARK_HOME=$(python3 -c 'import pyspark; print(pyspark.__path__[0])'); "
        "export SPARK_WORKER_DIR=/tmp/spark-work; "  # <-- REDIRECIONA OS ARQUIVOS TEMPORÁRIOS AQUI
        'echo "SPARK_HOME definido como: $SPARK_HOME"; '
        'if [ ! -f "$SPARK_HOME/bin/spark-class" ]; then '
        "echo 'ERRO FATAL: spark-class nao encontrado dentro do SPARK_HOME!'; "
        "sleep 3600; "
        "else "
        "echo 'Iniciando Spark Worker...'; "
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
    if not client:
        raise Exception("Cliente Docker não inicializado.")

    total_mem_usage = 0
    total_mem_limit = 0
    total_cpu_percent = 0.0
    is_online = False

    # MÁGICA: Monitora a soma do VS Code + Spark Worker simultaneamente
    for c_name in [f"vscode-{usuario}", f"spark-worker-{usuario}"]:
        try:
            container = client.containers.get(c_name)
            stats = container.stats(stream=False)
            is_online = True

            # Memória
            mem_usage_bytes = stats.get("memory_stats", {}).get("usage", 0)
            mem_limit_bytes = stats.get("memory_stats", {}).get("limit", 0)
            mem_cache = stats.get("memory_stats", {}).get("stats", {}).get("cache", 0)
            mem_usage_real = max(0, mem_usage_bytes - mem_cache)

            total_mem_usage += mem_usage_real
            total_mem_limit += mem_limit_bytes

            # CPU
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