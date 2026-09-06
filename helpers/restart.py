"""Rebuild and redeploy the ArenaLake Docker Swarm stack safely."""

import argparse
import os
import shutil
import subprocess
import sys
import time


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
            "--no-cache",
            "--pull",
        ]
    )
    print("[+] Local images rebuilt successfully.")


def deploy_stack():
    """Deploy the rebuilt images and external services through Swarm."""
    
    if os.path.isfile(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value

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
    return parser.parse_args()


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

    check_swarm()
    remove_stack()
    restart_docker()
    check_swarm()
    rebuild_images()
    deploy_stack()

    print("\n[+] Restart completed. Existing persistent data was preserved.")


if __name__ == "__main__":
    main()