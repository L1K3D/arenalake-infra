import os
import sys
import shutil
import subprocess
import time
import re


def check_root():
    """Ensure the script is executed with administrator rights."""
    if os.geteuid() != 0:
        print("[ERROR] This script requires administrator privileges.")
        print("Run it again with: sudo python3 add_worker.py")
        sys.exit(1)


def install_dependencies():
    """Install Docker and Tailscale on the worker node if they are not present."""
    print("\n[*] Checking system dependencies (Ubuntu)...")

    # Install Docker if it is missing from the base system.
    if shutil.which("docker") is None:
        print("\n[*] Docker not found. Installing... (This may take a few minutes)")
        try:
            subprocess.run(
                "curl -fsSL https://get.docker.com | sh",
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            docker_v = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True
            ).stdout.strip()
            print(f"[+] Docker installed! | {docker_v}")
        except BaseException as error:
            print(f"\n[ERROR] Failed to install Docker. | {error}")
            sys.exit(1)
    else:
        docker_v = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True
        ).stdout.strip()
        print(f"[+] Docker OK! | {docker_v}")

    # Install Tailscale if it is missing; the worker needs it to reach the cluster network.
    if shutil.which("tailscale") is None:
        print("\n[*] Tailscale not found. Installing...")
        try:
            subprocess.run(
                "curl -fsSL https://tailscale.com/install.sh | sh",
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            ts_output = subprocess.run(
                ["tailscale", "version"], capture_output=True, text=True
            ).stdout.strip()
            ts_v = ts_output.split("\n")[0]
            print(f"[+] Tailscale installed! | {ts_v}")
        except BaseException as error:
            print(f"\n[ERROR] Failed to install Tailscale. | {error}")
            sys.exit(1)
    else:
        ts_output = subprocess.run(
            ["tailscale", "version"], capture_output=True, text=True
        ).stdout.strip()
        ts_v = ts_output.split("\n")[0]
        print(f"[+] Tailscale OK! | {ts_v}")

    time.sleep(1)


def check_swarm_status():
    """Check whether the machine is already part of a Swarm cluster and leave it if necessary."""
    info = subprocess.run(["docker", "info"], capture_output=True, text=True).stdout
    if "Swarm: active" in info or "Swarm: pending" in info:
        print("\n" + "!" * 60)
        print(" WARNING: This machine is already part of an old Swarm cluster!")
        print(
            " To add it to ArenaLake, we need to force it to leave the current cluster."
        )
        print("!" * 60)
        resp = (
            input("Do you want to leave the old cluster now? (Y/N) [Default: Y]: ")
            .strip()
            .lower()
        )
        if resp != "n":
            print("[*] Cleaning old Swarm configuration...")
            subprocess.run(["docker", "swarm", "leave", "--force"], capture_output=True)
            print("[+] Machine cleaned and ready for a new cluster.")
        else:
            print("\n[!] Operation canceled. We cannot continue while Swarm is active.")
            sys.exit(0)


def extract_token(raw_input):
    """Extract the Docker Swarm worker token from CLI output."""
    match = re.search(r"(SWMTKN-1-[a-z0-9]+-[a-z0-9]+)", raw_input)
    if match:
        return match.group(1)
    return raw_input.strip()


def test_connection(ip):
    """Ping the master twice to confirm the VPN route is working."""
    print(f"\n[*] Testing VPN connectivity with the master ({ip})...")
    result = subprocess.run(["ping", "-c", "2", "-W", "2", ip], capture_output=True)
    return result.returncode == 0


def provision_storage():
    """Mirror the essential folders required by the worker container runtime."""
    current_project_dir = os.path.dirname(os.path.abspath(__file__))
    datalake_path = os.path.join(current_project_dir, "datalake_data")

    print(f"[*] Mirroring the worker's essential directories ({datalake_path})...")
    os.makedirs(datalake_path, exist_ok=True)
    os.chmod(datalake_path, 0o755)

    subfolders = ["minio_data", "spark_jobs", "projects_data", "database"]
    for folder in subfolders:
        folder_path = os.path.join(datalake_path, folder)
        os.makedirs(folder_path, exist_ok=True)
        os.chmod(folder_path, 0o777)
        print(f"[+] Mirrored subfolder: {folder}")
        
def build_local_agent():
    """Build the telemetry agent image locally so Swarm can deploy it on this node."""
    print("\n[*] Building the Telemetry Agent image locally for this worker...")
    agent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telemetry-agent")
    
    if os.path.exists(agent_dir):
        try:
            subprocess.run(
                ["docker", "build", "-t", "arenalake-telemetry:latest", agent_dir],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[+] Telemetry Agent built successfully!")
        except subprocess.CalledProcessError:
            print("\n[ERROR] Failed to build the Telemetry Agent image.")
            sys.exit(1)
    else:
        print(f"\n[ERROR] Directory {agent_dir} not found.")
        print("Please ensure you cloned the full ArenaLake repository to this worker.")
        sys.exit(1)

def main():
    check_root()

    print("=" * 60)
    print("      ArenaLake - Worker Node Installer")
    print("=" * 60)
    print("Welcome! We are adding this machine to your cluster.\n")

    install_dependencies()
    check_swarm_status()
    provision_storage()
    build_local_agent()

    print("\n============================================================")
    print(" STEP 1: NETWORK AUTHENTICATION (TAILSCALE)")
    print("============================================================")

    print("[*] We need this worker to join the same VPN network as the master.")
    print("!" * 60)
    print(" IMPORTANT:")
    print(" 1. Click the link generated below and log in.")
    print(" 2. The terminal will pause and wait for your login.")
    print("!" * 60)

    input("\nPress ENTER to generate the authentication link...")

    try:
        subprocess.run("tailscale up", shell=True, check=True)
        print("\n[+] Worker connected to the VPN successfully!")
    except subprocess.CalledProcessError:
        print("\n[ERROR] There was a problem connecting to Tailscale.")
        sys.exit(1)

    print("\n============================================================")
    print(" STEP 2: CLUSTER CONNECTION (SWARM)")
    print("============================================================")

    print("Go to the terminal on your MASTER server and run the commands below")
    print("to get the access credentials.\n")

    # Capture the master IP first and validate the route before joining the cluster.
    master_ip = ""
    while not master_ip:
        print("On the MASTER, run: tailscale ip -4")
        master_ip = input("Paste the master IP here (example: 100.105.x.x): ").strip()
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", master_ip):
            print("[ERROR] Invalid IP format. Please try again.\n")
            master_ip = ""
        else:
            if not test_connection(master_ip):
                print(f"[ERROR] The IP {master_ip} is unreachable.")
                print("Check whether the master is running and connected to Tailscale.")
                master_ip = ""  # Force the user to enter a valid IP again
            else:
                print("[+] VPN network route verified successfully!")

    # Retrieve the worker join token from the master.
    print("\nOn the MASTER, run: docker swarm join-token worker -q")
    raw_token = ""
    while not raw_token:
        raw_token = input("Paste the generated token here: ").strip()

    token = extract_token(raw_token)

    print("\n[*] Joining the ArenaLake cluster...")
    try:
        join_cmd = ["docker", "swarm", "join", "--token", token, f"{master_ip}:2377"]
        subprocess.run(join_cmd, check=True, stdout=subprocess.DEVNULL)

        print("\n" + "=" * 60)
        print("  Worker successfully joined the cluster! 🚀")
        print("  The master can now distribute workloads to this machine.")
        print("=" * 60)

    except subprocess.CalledProcessError:
        print("\n[ERROR] Failed to join the cluster.")
        print(
            "Port 2377 on the master may be blocked by the firewall. Open it and try again."
        )


if __name__ == "__main__":
    main()