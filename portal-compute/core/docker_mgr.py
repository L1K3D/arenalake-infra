import os
import docker

try:
    client = docker.from_env()
except Exception as e:
    print(f"Erro ao conectar no Docker: {e}")
    client = None

def provision_workspace(usuario: str, ram: int):
    if not client:
        raise Exception("Cliente Docker não inicializado.")
        
    container_name = f"vscode-{usuario}"
    domain = f"{usuario}.localhost"
    
    try:
        container = client.containers.get(container_name)
        if container.status != "running":
            container.start()
    except docker.errors.NotFound:
        host_dir = f"/home/heitor/projects/arenalake-infra/projects_data/{usuario}"
        os.makedirs(host_dir, exist_ok=True)
        
        client.containers.run(
            image="codercom/code-server:latest",
            name=container_name,
            detach=True,
            command="--auth none",
            environment=["SPARK_MASTER=spark://spark-master:7077"],
            volumes={host_dir: {'bind': '/home/coder/project', 'mode': 'rw'}},
            network="arenalake-infra_arenalake-net",
            mem_limit=f"{ram}g",
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
        
        # Memory Math
        mem_usage_bytes = stats.get('memory_stats', {}).get('usage', 0)
        mem_limit_bytes = stats.get('memory_stats', {}).get('limit', 1)
        mem_cache = stats.get('memory_stats', {}).get('stats', {}).get('cache', 0)
        mem_usage_real = mem_usage_bytes - mem_cache
        
        mem_usage_mb = round(mem_usage_real / (1024 * 1024), 2)
        mem_limit_mb = round(mem_limit_bytes / (1024 * 1024), 2)
        mem_percent = round((mem_usage_real / mem_limit_bytes) * 100, 2)
        
        # CPU Math
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        online_cpus = stats.get('cpu_stats', {}).get('online_cpus', 1)
        
        cpu_percent = 0.0
        if system_delta > 0.0 and cpu_delta > 0.0:
            cpu_percent = round((cpu_delta / system_delta) * online_cpus * 100.0, 2)
            
        return {
            "status": "online",
            "cpu_percent": cpu_percent,
            "memory_usage_mb": mem_usage_mb,
            "memory_limit_mb": mem_limit_mb,
            "memory_percent": mem_percent
        }
    except docker.errors.NotFound:
        return {"status": "offline", "message": "Workspace não está rodando"}
