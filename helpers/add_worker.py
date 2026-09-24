import os
import sys
import shutil
import subprocess
import time
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

def check_root():
    if os.geteuid() != 0:
        print("[ERROR] This script requires administrator privileges.")
        sys.exit(1)

def install_dependencies():
    print("\n[*] Checking system dependencies (Ubuntu)...")
    if shutil.which("docker") is None:
        subprocess.run("curl -fsSL https://get.docker.com | sh", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if shutil.which("tailscale") is None:
        subprocess.run("curl -fsSL https://tailscale.com/install.sh | sh", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

def check_swarm_status():
    if "Swarm: active" in subprocess.run(["docker", "info"], capture_output=True, text=True).stdout:
        if input("Machine is in an old Swarm cluster. Leave it? (Y/N) [Y]: ").strip().lower() != "n":
            subprocess.run(["docker", "swarm", "leave", "--force"], capture_output=True)
        else: sys.exit(0)

def extract_token(raw_input):
    match = re.search(r"(SWMTKN-1-[a-z0-9]+-[a-z0-9]+)", raw_input)
    return match.group(1) if match else raw_input.strip()

def setup_nfs_and_replication(master_ip, is_manager):
    """Monta o NFS. Se for Manager, configura uma cópia assíncrona recorrente (rsync + cron)."""
    print("\n============================================================")
    print(" STEP 3: DISTRIBUTED STORAGE & REPLICATION")
    print("============================================================")
    
    subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL)
    subprocess.run(["apt-get", "install", "-y", "nfs-common", "rsync", "cron"], check=True, stdout=subprocess.DEVNULL)

    datalake_path = os.path.join(PROJECT_ROOT, "datalake_data")
    os.makedirs(datalake_path, exist_ok=True)

    master_nfs_path = ""
    while not master_nfs_path.startswith("/"):
        master_nfs_path = input("What is the absolute physical DataLake path configured on the Master? (e.g., /arenalake_data): ").strip()

    print(f"[*] Mounting Master's DataLake via NFS...")
    subprocess.run(["mount", "-t", "nfs", f"{master_ip}:{master_nfs_path}", datalake_path], check=True)

    # Persiste o mount point
    fstab_entry = f"{master_ip}:{master_nfs_path} {datalake_path} nfs defaults,_netdev 0 0\n"
    with open("/etc/fstab", "a") as f:
        f.write(fstab_entry)

    if is_manager:
        print("\n[*] Manager Node: Configuring Async Backup Replication...")
        backup_path = ""
        while not backup_path.startswith("/"):
            backup_path = input("Enter the absolute path to store the backups on this node (e.g., /arenalake_backup): ").strip()
        os.makedirs(backup_path, exist_ok=True)

        sync_interval = 0
        while not (30 <= sync_interval <= 240):
            try:
                sync_interval = int(input("How often (in minutes) should this node sync data from the Master? (30-240): ").strip())
            except ValueError:
                pass

        print(f"[*] Setting up cron job for rsync every {sync_interval} minutes...")
        # Cria um script cron que executa a cópia incremental sincronizada de NFS -> Pasta Local
        cron_cmd = f"*/{sync_interval} * * * * root rsync -aq --delete {datalake_path}/ {backup_path}/ > /dev/null 2>&1\n"
        cron_file = "/etc/cron.d/arenalake_replication"
        
        with open(cron_file, "w") as f:
            f.write(cron_cmd)
        os.chmod(cron_file, 0o644)
        subprocess.run(["systemctl", "restart", "cron"], check=False)
        print(f"[+] Replication scheduled! Master data will be backed up locally to {backup_path}.")
    else:
        print("[+] Standard Worker Storage configured (NFS Client mode).")

def build_local_images():
    print("\n[*] Building local Node images...")
    agent_dir = os.path.join(PROJECT_ROOT, "telemetry-agent")
    dockerfile = os.path.join(PROJECT_ROOT, "docker", "Dockerfile.workspace")
    if os.path.exists(agent_dir):
        subprocess.run(["docker", "build", "-t", "arenalake-telemetry:latest", agent_dir], stdout=subprocess.DEVNULL)
    if os.path.isfile(dockerfile):
        subprocess.run(["docker", "build", "-t", "arenalake-workspace:latest", "-f", dockerfile, PROJECT_ROOT], stdout=subprocess.DEVNULL)

def main():
    check_root()
    print("=" * 60)
    print("      ArenaLake - Worker Node Installer")
    print("=" * 60)

    install_dependencies()
    check_swarm_status()
    build_local_images()

    print("\n============================================================")
    print(" STEP 1: NETWORK AUTHENTICATION (TAILSCALE)")
    print("============================================================")
    input("\nPress ENTER to generate the authentication link...")
    subprocess.run("tailscale up", shell=True, check=True)

    print("\n============================================================")
    print(" STEP 2: CLUSTER CONNECTION")
    print("============================================================")
    print(" - [W]orker: Runs heavy workloads but holds no replica.")
    print(" - [M]anager: Holds a local ASYNC REPLICA of the DataLake.")
    
    is_manager = input("\nWill this node be a [W]orker or a [M]anager? [Default: W]: ").strip().lower() == 'm'
    role_name = "manager" if is_manager else "worker"

    master_ip = input("\nPaste the master Tailscale IP (e.g. 100.105.x.x): ").strip()
    raw_token = input(f"Paste the {role_name} token from the Master: ").strip()

    try:
        subprocess.run(["docker", "swarm", "join", "--token", extract_token(raw_token), f"{master_ip}:2377"], check=True, stdout=subprocess.DEVNULL)
        setup_nfs_and_replication(master_ip, is_manager)
        print("\n" + "=" * 60)
        print(f"  Node successfully joined the cluster as a {role_name.upper()}! 🚀")
        print("=" * 60)
    except:
        print("\n[ERROR] Failed to join the cluster.")

if __name__ == "__main__":
    main()