import os
import subprocess
import shutil
import json

# Color codes for terminal output.
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_status(component, status, message, tip=None):
    """Render a standardized health status line for the cluster check."""
    if status == "OK":
        print(f"[{GREEN} OK {RESET}] {component.ljust(20)} : {message}")
    elif status == "WARN":
        print(f"[{YELLOW}WARNING{RESET}] {component.ljust(20)} : {message}")
        if tip:
            print(f"         {CYAN}💡 Tip:{RESET} {tip}")
    else:
        print(f"[{RED}ERROR{RESET}] {component.ljust(20)} : {message}")
        if tip:
            print(f"         {CYAN}🔧 Fix:{RESET} {tip}")


def get_datalake_path():
    """Read the configured DataLake path from .env if available."""
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("DATALAKE_STORAGE_PATH="):
                    return line.strip().split("=")[1]
    # Fallback when the .env file is not present.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "datalake_data")


def check_resources():
    """Check whether the server has enough free storage for the DataLake."""
    print("\n--- 1. Server Resources ---")

    # Use the dynamic path aligned with the new architecture.
    current_project_dir = os.path.dirname(os.path.abspath(__file__))
    datalake_path = os.path.join(current_project_dir, "datalake_data")

    if os.path.exists(datalake_path):
        total, used, free = shutil.disk_usage(datalake_path)
        free_gb = free / (2**30)
        if free_gb > 20:
            print_status("Disk (DataLake)", "OK", f"{free_gb:.1f} GB free.")
        elif free_gb > 5:
            print_status(
                "Disk (DataLake)",
                "WARN",
                f"Only {free_gb:.1f} GB free.",
                "Clean unused files or add more disk space.",
            )
        else:
            print_status(
                "Disk (DataLake)",
                "ERROR",
                f"CRITICAL! Only {free_gb:.1f} GB free.",
                "The database may freeze. Run 'docker system prune -a --volumes' to clean Docker cache or remove old data.",
            )
    else:
        print_status(
            "Disk (DataLake)",
            "ERROR",
            f"Folder {datalake_path} not found!",
            "The base folder was removed. Run install.py again to recreate the infrastructure.",
        )


def check_environment():
    """Confirm the required environment files exist before the cluster runs."""
    print("\n--- 2. Base Configuration ---")
    if os.path.isfile(".env"):
        print_status(".env file", "OK", "Found.")
    else:
        print_status(
            ".env file",
            "ERROR",
            "NOT FOUND!",
            "You are running the script from the wrong folder or the file was deleted. Run 'install.py' to recreate it.",
        )

    if os.path.isfile("docker-compose.yml"):
        print_status("Docker Compose", "OK", "Found.")
    else:
        print_status(
            "Docker Compose",
            "ERROR",
            "NOT FOUND!",
            "Download docker-compose.yml from the repository and place it in this folder.",
        )
        
    if os.path.isdir("telemetry-agent"):
        print_status("Telemetry Agent", "OK", "Source folder found.")
    else:
        print_status(
            "Telemetry Agent",
            "ERROR",
            "NOT FOUND!",
            "The telemetry-agent folder is missing. Cluster hardware metrics will fail.",
        )


def check_tailscale():
    """Check whether Tailscale is installed and connected to the VPN."""
    print("\n--- 3. Network and VPN (Tailscale) ---")
    if shutil.which("tailscale") is None:
        print_status(
            "Tailscale",
            "ERROR",
            "Not installed.",
            "Run: curl -fsSL https://tailscale.com/install.sh | sh",
        )
        return

    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print_status(
                "Tailscale",
                "ERROR",
                "Service stopped.",
                "Try restarting it with: sudo systemctl restart tailscaled",
            )
            return

        data = json.loads(result.stdout)
        backend_state = data.get("BackendState", "")
        if backend_state == "Running":
            ip = data.get("Self", {}).get("TailscaleIPs", [""])[0]
            print_status("VPN connection", "OK", f"Connected. IP: {ip}")
        else:
            print_status(
                "VPN connection",
                "ERROR",
                f"Disconnected ({backend_state}).",
                "Run 'sudo tailscale up' to reconnect this machine to the network.",
            )
    except Exception:
        print_status("Tailscale", "ERROR", "Read failed.", "Restart the server.")


def check_docker_swarm():
    """Verify Docker Engine and Swarm are healthy and inspect active services."""
    print("\n--- 4. Orchestration (Docker Swarm) ---")

    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        print_status(
            "Docker Engine",
            "ERROR",
            "Docker is stopped or broken!",
            "Run: sudo systemctl start docker",
        )
        return
    else:
        print_status("Docker Engine", "OK", "Running.")

    if "Swarm: active" not in result.stdout:
        print_status(
            "Docker Swarm",
            "ERROR",
            "Cluster inactive.",
            "To activate it, run: sudo docker swarm init",
        )
        return
    else:
        print_status("Docker Swarm", "OK", "Active.")

    print("\n--- 5. Service Status (ArenaLake) ---")
    try:
        services_raw = subprocess.run(
            ["docker", "service", "ls", "--format", "{{.Name}}|{{.Replicas}}"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        if not services_raw:
            print_status(
                "Services",
                "WARN",
                "No services running.",
                "Run: docker stack deploy -c docker-compose.yml arenalake-prod",
            )
            return

        for line in services_raw.split("\n"):
            if "arenalake-prod" in line:
                name, replicas = line.split("|")
                name = name.replace("arenalake-prod_", "")

                active, target = replicas.split("/")

                if active == target and int(target) > 0:
                    print_status(name, "OK", f"Operational ({active}/{target}).")
                elif active == "0":
                    print_status(
                        name,
                        "ERROR",
                        f"DOWN! ({active}/{target}).",
                        f"Run 'docker service logs arenalake-prod_{name}' to find the root cause.",
                    )
                else:
                    print_status(
                        name,
                        "WARN",
                        f"Unstable ({active}/{target}).",
                        "Docker is restarting the service. Wait a few minutes.",
                    )

    except Exception:
        print_status(
            "Services",
            "ERROR",
            "Failed to list services.",
            "Verify the user has permission to run Docker commands.",
        )


def main():
    print("=" * 60)
    print("       ArenaLake - System Doctor")
    print("=" * 60)
    print("Checking your cluster health... \n")

    check_resources()
    check_environment()
    check_tailscale()
    check_docker_swarm()

    print("\n" + "=" * 60)
    print(" Diagnosis complete! Use the tips above to resolve the issue.")
    print(" If the error persists, capture a screenshot and contact support.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()