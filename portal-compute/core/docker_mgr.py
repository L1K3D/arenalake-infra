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

    container_name = f"vscode-{usuario}"
    domain = f"{usuario}.localhost"

    if perfil == "extreme":
        ram_limit = "8g"
        cpu_limit = 6 * 1000000000 
    else:
        ram_limit = "4g"
        cpu_limit = 2 * 1000000000 

    try:
        container = client.containers.get(container_name)
        if container.status == "running":
            container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass 

    host_dir = f"/home/heitor/projects/arenalake-infra/projects_data/{usuario}"
    os.makedirs(host_dir, exist_ok=True)
    os.chmod(host_dir, 0o777)

    # 1. Pega as credenciais que vieram do arquivo .env (escondido)
    minio_ak = os.getenv("MINIO_ACCESS_KEY", "arenalake")
    minio_sk = os.getenv("MINIO_SECRET_KEY", "arenalake123")

    # 2. Injeta essas variáveis dentro do SO do Workspace novo
    client.containers.run(
        image="arenalake-workspace:latest",
        name=container_name,
        detach=True,
        command="--auth none",
        environment=[
            "SPARK_MASTER=spark://spark-master:7077",
            f"MINIO_ACCESS_KEY={minio_ak}",  
            f"MINIO_SECRET_KEY={minio_sk}"   
        ],
        volumes={host_dir: {'bind': '/home/coder/project', 'mode': 'rw'}},
        network="arenalake-infra_arenalake-net",
        mem_limit=ram_limit,
        nano_cpus=cpu_limit,
        labels={
            "traefik.enable": "true",
            f"traefik.http.routers.vscode-{usuario}.rule": f"Host(`{domain}`)",
            f"traefik.http.services.vscode-{usuario}.loadbalancer.server.port": "8080"
        }
    )
    return domain

def get_workspace_metrics(usuario: str):
    if not client:
        raise Exception("Cliente Docker não inicializado.")

    container_name = f"vscode-{usuario}"
    try:
        container = client.containers.get(container_name)
        stats = container.stats(stream=False)

        # Cálculo de Memória (Mantém igual, já estava proporcional ao limite)
        mem_usage_bytes = stats.get('memory_stats', {}).get('usage', 0)
        mem_limit_bytes = stats.get('memory_stats', {}).get('limit', 1)
        mem_cache = stats.get('memory_stats', {}).get('stats', {}).get('cache', 0)
        mem_usage_real = mem_usage_bytes - mem_cache
        
        if mem_usage_real < 0:
            mem_usage_real = mem_usage_bytes

        mem_usage_mb = round(mem_usage_real / (1024 * 1024), 2)
        mem_limit_mb = round(mem_limit_bytes / (1024 * 1024), 2)
        mem_percent = round((mem_usage_real / mem_limit_bytes) * 100, 2)

        # Cálculo de CPU Ajustado
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']

        cpu_percent = 0.0
        if system_delta > 0.0 and cpu_delta > 0.0:
            # Descobre quantos núcleos foram alocados para este container especificamente
            # Lemos a configuração de nano_cpus do container rodando
            host_config = container.attrs.get('HostConfig', {})
            nano_cpus = host_config.get('NanoCpus', 0)
            
            if nano_cpus > 0:
                allocated_cpus = nano_cpus / 1000000000
            else:
                # Fallback seguro caso venha livre
                allocated_cpus = 2.0 

            # A proporção real dividida exclusivamente pelos núcleos do plano do usuário
            cpu_percent = round((cpu_delta / system_delta) * 100.0 / allocated_cpus, 2)

            # Trava o teto visualmente em 100% para evitar qualquer distorção gráfica
            if cpu_percent > 100.0:
                cpu_percent = 100.0

        return {
            "status": "online",
            "cpu_percent": cpu_percent,
            "memory_usage_mb": mem_usage_mb,
            "memory_limit_mb": mem_limit_mb,
            "memory_percent": mem_percent
        }
    except docker.errors.NotFound:
        return {"status": "offline", "message": "Workspace não está rodando"}
