import os
import sys
import shutil
import subprocess
import time
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)


def check_root():
    """Ensure the script is executed with administrator rights."""
    if os.geteuid() != 0:
        print("[ERROR] This script requires administrator privileges.")
        print("Run it again with: sudo python3 helpers/add_worker.py")
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

def mount_nfs_datalake(master_ip):
    """Instala o cliente NFS e monta o HD do Master via VPN do Tailscale."""
    print("\n============================================================")
    print(" STEP 3: DISTRIBUTED STORAGE (NFS)")
    print("============================================================")
    print("[*] This worker needs to mount the Master's storage disk to sync data.")
    
    datalake_path = ""
    while not datalake_path.startswith("/"):
        datalake_path = input("What is the absolute DataLake path configured on the Master? (e.g., /mnt/hd/arenalake): ").strip()

    print(f"[*] Installing NFS Client and mounting {master_ip}:{datalake_path}...")
    try:
        subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL)
        subprocess.run(["apt-get", "install", "-y", "nfs-common"], check=True, stdout=subprocess.DEVNULL)
        
        # Cria a mesma estrutura de pastas localmente
        os.makedirs(datalake_path, exist_ok=True)
        
        # Monta a partilha na rede
        subprocess.run(["mount", "-t", "nfs", f"{master_ip}:{datalake_path}", datalake_path], check=True)
        
        # Adiciona ao fstab para montar automaticamente caso o Worker seja reiniciado
        fstab_entry = f"{master_ip}:{datalake_path} {datalake_path} nfs defaults 0 0\n"
        with open("/etc/fstab", "r") as f:
            fstab = f.read()
        if f"{master_ip}:{datalake_path}" not in fstab:
            with open("/etc/fstab", "a") as f:
                f.write(fstab_entry)
                
        print(f"[+] Distributed storage mounted successfully at {datalake_path}!")
    except Exception as e:
        print(f"[ERROR] Failed to mount NFS storage. Check if the Master is online: {e}")
        sys.exit(1)
        
def build_local_agent():
    """Build the telemetry agent image locally so Swarm can deploy it on this node."""
    print("\n[*] Building the Telemetry Agent image locally for this worker...")
    agent_dir = os.path.join(PROJECT_ROOT, "telemetry-agent")
    
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

def build_local_workspace():
    """Build the workspace image locally so user services can run on this worker."""
    print("\n[*] Building the Workspace image locally for this worker...")
    dockerfile = os.path.join(PROJECT_ROOT, "docker", "Dockerfile.workspace")

    if not os.path.isfile(dockerfile):
        print(f"\n[ERROR] Dockerfile not found: {dockerfile}")
        print("Please ensure you cloned the full ArenaLake repository to this worker.")
        sys.exit(1)

    try:
        subprocess.run(
            [
                "docker",
                "build",
                "-t",
                "arenalake-workspace:latest",
                "-f",
                dockerfile,
                PROJECT_ROOT,
            ],
            check=True,
        )
        print("[+] Workspace image built successfully!")
    except subprocess.CalledProcessError:
        print("\n[ERROR] Failed to build the Workspace image.")
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
    build_local_workspace()
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

        mount_nfs_datalake(master_ip)

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