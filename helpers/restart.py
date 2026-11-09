"""Rebuild and redeploy the ArenaLake Docker Swarm stack safely."""

import argparse
import os
import shutil
import subprocess
import sys
import time
import concurrent.futures

if __package__:
    from .env_file import read_env_file
else:
    from env_file import read_env_file


STACK_NAME = "arenalake-prod"
COMPOSE_FILE = os.path.join("deploy", "compose", "docker-compose.yml")
AGENT_COMPOSE_FILE = os.path.join("deploy", "docker-compose.agent.yml")
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


def ensure_overlay_network():
    """Garante que a rede overlay global arenalake-net esteja criada para evitar conflitos no deploy."""
    net_name = "arenalake-net"
    print(f"\n[*] Garantindo existência da rede overlay global '{net_name}'...")
    result = subprocess.run(
        [
            "docker",
            "network",
            "ls",
            "--filter",
            f"name={net_name}",
            "--format",
            "{{.Name}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    if net_name not in result.stdout.splitlines():
        subprocess.run(
            [
                "docker",
                "network",
                "create",
                "-d",
                "overlay",
                "--attachable",
                net_name,
            ],
            check=True,
        )
        print(f"[+] Rede overlay '{net_name}' criada com sucesso.")
    else:
        print(f"[+] Rede overlay '{net_name}' já está ativa.")


def cleanup_orphaned_workspaces():
    """Remove stranded user workspaces and services."""
    print("[*] Cleaning up orphaned user workspaces...")
    try:
        result = subprocess.run(
            ["docker", "service", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        services = result.stdout.splitlines()

        orphans = [
            s
            for s in services
            if s.startswith("vscode-") or s.startswith("spark-worker-")
        ]

        if orphans:
            for orphan in orphans:
                run_command(["docker", "service", "rm", orphan])
            print(f"[+] Removed {len(orphans)} orphaned services.")
            time.sleep(3)
        else:
            print("[+] No orphaned workspaces found.")

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


def deploy_stack():
    """Deploy the rebuilt images and external services through Swarm."""
    if os.path.isfile(".env"):
        os.environ.update(read_env_file(".env"))

    ensure_overlay_network()
    prepare_datalake_permissions()

    run_command(
        [
            sys.executable,
            os.path.join("helpers", "deploy_stack.py"),
            "--with-registry-auth",
        ]
    )
    print("[+] ArenaLake stack deployed.")
    subprocess.run(["docker", "service", "ls"], check=False)


def deploy_agent():
    """Deploy the privileged telemetry-agent using Docker Compose."""
    print("\n[*] Deploying telemetry-agent with privileged access...")
    if os.path.isfile(AGENT_COMPOSE_FILE):
        run_command(
            [
                "docker",
                "compose",
                "--env-file",
                ".env",
                "-f",
                AGENT_COMPOSE_FILE,
                "up",
                "-d",
            ]
        )
        print("[+] Telemetry agent deployed successfully.")
    else:
        print(f"[!] Warning: Agent compose file '{AGENT_COMPOSE_FILE}' not found.")


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
        help="skip Docker restart for a fast deploy",
    )
    return parser.parse_args()


def prepare_datalake_permissions():
    """Ensure MinIO directory has correct permissions for Chainguard nonroot user."""
    print("[*] Verifying DataLake security permissions...")
    datalake_path = os.environ.get(
        "DATALAKE_STORAGE_PATH", os.path.join(PROJECT_ROOT, "datalake_data")
    )
    minio_path = os.path.join(datalake_path, "minio_data")

    os.makedirs(minio_path, exist_ok=True)
    try:
        subprocess.run(
            ["chown", "-R", "65532:65532", minio_path],
            check=False,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        print(
            "[!] Warning: Failed to adjust MinIO permissions. The container may crash."
        )


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
        check_swarm()
        cleanup_orphaned_workspaces()
        remove_stack()
    else:
        check_swarm()
        cleanup_orphaned_workspaces()
        remove_stack()
        restart_docker()
        check_swarm()

    deploy_stack()
    deploy_agent()

    print("\n[+] Restart completed. Existing persistent data was preserved.")


if __name__ == "__main__":
    main()
