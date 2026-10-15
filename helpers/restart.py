"""Rebuild and redeploy the ArenaLake Docker Swarm stack safely."""

import argparse
import os
import shutil
import subprocess
import sys
import time
import concurrent.futures


STACK_NAME = "arenalake-prod"
COMPOSE_FILE = "docker-compose.yml"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)


def run_command(command, **kwargs):
    """Run a command and stop immediately when it fails."""
    print(f"[*] {' '.join(command)}")
    return subprocess.run(command, check=True, **kwargs)


def check_prerequisites():
    """Validate that this script is running from a configured deployment."""
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        print("[ERROR] This script requires administrator privileges.")
        print("Run it again with: sudo python3 helpers/restart.py")
        sys.exit(1)

    if shutil.which("docker") is None:
        print("[ERROR] Docker was not found in PATH.")
        sys.exit(1)

    if not os.path.isfile(COMPOSE_FILE):
        print(f"[ERROR] The '{COMPOSE_FILE}' file was not found.")
        print("Run this script from the ArenaLake project directory.")
        sys.exit(1)

    if not os.path.isfile(".env"):
        print("[ERROR] The .env file was not found.")
        print("The installation configuration is required to restart the stack.")
        sys.exit(1)


def check_swarm():
    """Ensure the Docker daemon is running and Swarm is available."""
    result = subprocess.run(
        ["docker", "info"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        print("[ERROR] Docker is not running or cannot be accessed.")
        print(result.stderr.strip())
        sys.exit(1)

    if "Swarm: active" not in result.stdout:
        print("[ERROR] Docker Swarm is not active.")
        print("Run: sudo docker swarm init")
        sys.exit(1)


def cleanup_orphaned_workspaces():
    """Remove stranded user workspaces and the network to prevent FailedPrecondition errors."""
    print("[*] Cleaning up orphaned user workspaces...")
    try:
        # Pega a lista de serviços ativos
        result = subprocess.run(
            ["docker", "service", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, check=True
        )
        services = result.stdout.splitlines()
        
        # Filtra apenas as workspaces dinâmicas criadas pela API
        orphans = [s for s in services if s.startswith("vscode-") or s.startswith("spark-worker-")]

        if orphans:
            for orphan in orphans:
                run_command(["docker", "service", "rm", orphan])
            print(f"[+] Removed {len(orphans)} orphaned services.")
            time.sleep(3) # Dá um fôlego pro Swarm desvincular as redes
        else:
            print("[+] No orphaned workspaces found.")

        # Força a limpeza da rede caso ela tenha travado em execuções anteriores
        print(f"[*] Ensuring network {STACK_NAME}_arenalake-net is clear...")
        subprocess.run(
            ["docker", "network", "rm", f"{STACK_NAME}_arenalake-net"],
            capture_output=True, check=False
        )
    except Exception as e:
        print(f"[ERROR] Failed to clean up orphaned workspaces: {e}")


def restart_docker():
    """Restart the Docker daemon using the host's service manager."""
    print("[*] Restarting Docker daemon...")
    if shutil.which("systemctl"):
        run_command(["systemctl", "restart", "docker"])
    elif shutil.which("service"):
        run_command(["service", "docker", "restart"])
    else:
        print("[ERROR] Neither systemctl nor service was found.")
        sys.exit(1)

    for _ in range(30):
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("[+] Docker daemon is available again.")
            return
        time.sleep(2)

    print("[ERROR] Docker did not become available after the restart.")
    sys.exit(1)


def remove_stack():
    """Remove only ArenaLake services, leaving bind mounts and volumes intact."""
    stack_list = subprocess.run(
        ["docker", "stack", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    if STACK_NAME not in stack_list:
        print(f"[*] Stack '{STACK_NAME}' is not currently deployed.")
        return

    run_command(["docker", "stack", "rm", STACK_NAME])
    print("[*] Waiting for ArenaLake services to stop...")
    for _ in range(60):
        remaining = subprocess.run(
            ["docker", "stack", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if STACK_NAME not in remaining:
            print("[+] Existing ArenaLake stack removed.")
            return
        time.sleep(2)

    print("[ERROR] Timed out waiting for the existing stack to stop.")
    sys.exit(1)


def rebuild_images():
    """Rebuild every image defined with a local build context."""
    run_command(
        [
            "docker",
            "compose",
            "-f",
            COMPOSE_FILE,
            "build",
        ]
    )
    print("[+] Local images rebuilt successfully.")

def get_active_worker_nodes():
    """Verifica dinamicamente o Swarm em busca de nós do tipo Worker que estejam ativos."""
    try:
        result = subprocess.run(
            ["docker", "node", "ls", "-f", "role=worker", "--format", "{{.Hostname}} {{.Status}}"],
            capture_output=True, text=True, check=True
        )
        nodes = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "Ready":
                nodes.append(parts[0])
        return nodes
    except Exception:
        return []

def distribute_images():
    """Distribui as imagens compiladas de forma otimizada e em paralelo."""
    workers = get_active_worker_nodes()
    
    if not workers:
        print("\n[*] Nenhum Worker ativo detectado no cluster (Single-Node). Pulando distribuição.")
        return

    images_to_distribute = ["arenalake-workspace:latest", "arenalake-telemetry:latest"]
    print(f"\n[*] Preparando imagens para distribuição (compactando uma única vez)...")
    
    # Passo 1: Salvar as imagens no disco do Master apenas UMA vez
    tar_paths = {}
    for image in images_to_distribute:
        safe_name = image.replace(":", "_").replace("/", "_") + ".tar"
        tar_path = f"/tmp/{safe_name}"
        print(f"[*] Exportando {image} -> {tar_path}")
        subprocess.run(["docker", "save", "-o", tar_path, image], check=True)
        tar_paths[image] = tar_path

    # Passo 2: Função que envia o tarball para um nó específico
    def send_to_worker(node):
        for image, tar_path in tar_paths.items():
            print(f"[*] [Worker: {node}] Iniciando transferência de {image}...")
            # Usa 'cat' e pipe pelo SSH para evitar gravar duas vezes no disco do Worker
            cmd = f"cat {tar_path} | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{node} 'docker load'"
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if proc.returncode == 0:
                print(f"[+] [Worker: {node}] {image} recebida com sucesso.")
            else:
                print(f"[!] [Worker: {node}] Falha ao enviar {image}: {proc.stderr.strip()}")

    # Passo 3: Disparar o envio para todos os workers SIMULTANEAMENTE
    print(f"\n[*] Disparando transferências em paralelo para {len(workers)} worker(s)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(workers)) as executor:
        executor.map(send_to_worker, workers)

    # Passo 4: Limpeza do lixo temporário no Master
    for tar_path in tar_paths.values():
        if os.path.exists(tar_path):
            os.remove(tar_path)
    

def cleanup_docker():
    """Remove stopped containers, dangling images, and build cache to free up disk space."""
    print("[*] Cleaning up old Docker images and build cache...")
    run_command(["docker", "container", "prune", "-f"])
    run_command(["docker", "image", "prune", "-f"])
    subprocess.run(["docker", "builder", "prune", "-f", "--keep-storage", "3GB"], check=False)


def deploy_stack():
    """Deploy the rebuilt images and external services through Swarm."""
    if os.path.isfile(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    prepare_datalake_permissions()

    run_command(
        [
            "docker",
            "stack",
            "deploy",
            "-c",
            COMPOSE_FILE,
            STACK_NAME,
        ]
    )
    print("[+] ArenaLake stack deployed.")
    subprocess.run(["docker", "service", "ls"], check=False)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Restart Docker, rebuild ArenaLake images, and redeploy the stack."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the interactive confirmation",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="skip Docker restart, image rebuild, and SSH distribution for a lightning-fast deploy",
    )
    return parser.parse_args()

def prepare_datalake_permissions():
    """Ensure MinIO directory has correct permissions for Chainguard nonroot user."""
    print("[*] Verifying DataLake security permissions...")
    datalake_path = os.environ.get("DATALAKE_STORAGE_PATH", os.path.join(PROJECT_ROOT, "datalake_data"))
    minio_path = os.path.join(datalake_path, "minio_data")
    
    os.makedirs(minio_path, exist_ok=True)
    try:
        subprocess.run(["chown", "-R", "65532:65532", minio_path], check=False, stderr=subprocess.DEVNULL)
    except Exception:
        print("[!] Warning: Failed to adjust MinIO permissions. The container may crash.")

def main():
    args = parse_args()
    check_prerequisites()

    if not args.yes:
        print("!" * 60)
        print(" ArenaLake restart will temporarily stop all platform services.")
        print(" .env, DataLake data, database files, and workspace volumes are kept.")
        print("!" * 60)
        confirmation = input("Continue? (Y/N) [Default: N]: ").strip().lower()
        if confirmation != "y":
            print("[*] Restart cancelled. No changes were made.")
            return

    print("\n" + "=" * 60)
    print("      ArenaLake - Rebuild and Restart")
    print("=" * 60)
    
    if args.quick:
        print("[*] Quick mode enabled: skipping Docker restart, image rebuild, and SSH distribution.")
        print("=" * 60)
        check_swarm()
        cleanup_orphaned_workspaces()
        remove_stack()

    elif not args.quick:
        print("[*] Performing full restart: Docker will be restarted, images rebuilt, and stack redeployed.")
        print("=" * 60)
        check_swarm()
        cleanup_orphaned_workspaces()
        remove_stack()
        restart_docker()
        check_swarm()
        rebuild_images()
        distribute_images()
        cleanup_docker()
       
    deploy_stack()

    print("\n[+] Restart completed. Existing persistent data was preserved.")


if __name__ == "__main__":
    main()