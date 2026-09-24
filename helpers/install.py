import os
import re
import subprocess
import sys
import shutil
import time
import json
import socket
import secrets

YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

def run_live(command, description="Executing"):
    print(f"\n[*] {description}...")
    try:
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        for line in process.stdout: print(f"    {line.strip()}")
        process.wait()
        if process.returncode != 0: raise subprocess.CalledProcessError(process.returncode, command)
    except Exception as e:
        print(f"{YELLOW}[ERROR]{RESET} Failed during: {description} | {e}")
        sys.exit(1)

def check_root():
    if os.geteuid() != 0:
        print(f"{YELLOW}[ERROR]{RESET} This script requires administrator privileges.")
        sys.exit(1)

def check_existing_install():
    if os.path.exists(".env"):
        print("\n" + "!" * 60)
        print(" CRITICAL WARNING: AN INSTALLATION HAS ALREADY BEEN DETECTED!")
        resp = input("Are you absolutely sure you want to overwrite the current installation? (Y/N) [Default: N]: ").strip().lower()
        if resp != "y": sys.exit(0)

def check_ports_available():
    print("\n[*] Checking the server's critical ports...")
    vital_ports = [80, 443, 8000, 8080, 9000, 9001, 7077]
    ports_in_use = [port for port in vital_ports if socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(("localhost", port)) == 0]
    if ports_in_use:
        print("\n[CRITICAL ERROR] The following ports are already in use:", ports_in_use)
        sys.exit(1)
    print("[+] All required ports are free!")

def check_compose_file():
    if not os.path.isfile("docker-compose.yml"):
        print("[ERROR] The 'docker-compose.yml' file was not found.")
        sys.exit(1)

def check_telemetry_folder():
    if not os.path.isdir("telemetry-agent"):
        print("[ERROR] The 'telemetry-agent' directory was not found.")
        sys.exit(1)

def install_dependencies():
    print("\n[*] Verifying system dependencies (Ubuntu)...")
    if shutil.which("docker") is None:
        run_live("curl -fsSL https://get.docker.com | sh", "Installing Docker Engine")
    if shutil.which("tailscale") is None:
        run_live("curl -fsSL https://tailscale.com/install.sh | sh", "Installing Tailscale VPN")
    time.sleep(1)

def format_company_name(name):
    name = re.sub(r"[^a-z0-9]", "_", name.lower().strip())
    return re.sub(r"_+", "_", name)

def is_valid_password(password):
    return len(password) >= 10 and re.search(r"[A-Z]", password) and re.search(r"[a-z]", password) and re.search(r"[0-9]", password)

def get_tailscale_url():
    try:
        result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, check=True)
        dns_name = json.loads(result.stdout).get("Self", {}).get("DNSName", "")
        if dns_name: return f"https://{dns_name.rstrip('.')}"
    except: pass
    return ""

def configure_storage():
    print("\n============================================================")
    print(" STEP 1.5: STORAGE CONFIGURATION")
    print("============================================================")
    project_datalake = os.path.join(PROJECT_ROOT, "datalake_data")

    if os.path.lexists(project_datalake):
        try:
            os.unlink(project_datalake) if os.path.islink(project_datalake) or os.path.isfile(project_datalake) else shutil.rmtree(project_datalake)
        except: pass

    result = subprocess.run(["df", "-h", "--output=target,avail,pcent"], capture_output=True, text=True)
    mounts = [{"path": p[0], "free": p[1], "pcent": p[2]} for line in result.stdout.strip().split("\n")[1:] if len((p := line.split())) >= 3 and not p[0].startswith(('/run', '/sys', '/dev', '/proc', '/snap', '/boot'))]

    print("\nAvailable Partitions:")
    for i, m in enumerate(mounts): print(f" [{i+1}] {m['path']} (Free: {m['free']} / Used: {m['pcent']})")

    while True:
        try:
            choice = int(input(f"\nSelect a storage location [1-{len(mounts)}]: ").strip())
            if 1 <= choice <= len(mounts): break
        except ValueError: pass

    base_path = mounts[choice-1]["path"]
    quota_gb = 0
    while quota_gb < 5:
        try: quota_gb = int(input("How many GBs do you want to allocate? (Minimum 5): ").strip())
        except ValueError: pass

    project_partition = subprocess.run(["df", "--output=target", PROJECT_ROOT], capture_output=True, text=True).stdout.strip().split("\n")[-1]

    if base_path == project_partition:
        os.makedirs(project_datalake, exist_ok=True)
    else:
        physical_path = os.path.join(base_path, "arenalake_data")
        os.makedirs(physical_path, exist_ok=True)
        os.symlink(physical_path, project_datalake)

    return project_datalake, quota_gb

def setup_nfs_master(datalake_path):
    """Instala o NFS e partilha a pasta do DataLake apenas para a rede VPN do Tailscale."""
    print("\n============================================================")
    print(" STEP 1.6: CONFIGURING NFS SERVER (STORAGE SHARING)")
    print("============================================================")
    
    run_live("DEBIAN_FRONTEND=noninteractive apt-get install -y nfs-kernel-server", "Installing NFS Server")
    
    # Resolve the real path if it's a symlink
    real_path = os.path.realpath(datalake_path)
    
    # 100.64.0.0/10 é a sub-rede padrão do Tailscale
    exports_line = f"{real_path} 100.64.0.0/10(rw,sync,no_subtree_check,no_root_squash)\n"
    
    exports_content = ""
    if os.path.exists("/etc/exports"):
        with open("/etc/exports", "r") as f:
            exports_content = f.read()
            
    if real_path not in exports_content:
        with open("/etc/exports", "a") as f:
            f.write(exports_line)
            
    run_live("exportfs -a && systemctl restart nfs-kernel-server", "Starting NFS Service")
    print(f"[+] NFS Share created for {real_path} over the Tailscale VPN.")
    print(f"{CYAN} 💡 TIP FOR WORKERS:{RESET} When asked for the physical path, type: {real_path}")

def main():
    check_root()
    check_compose_file()
    check_telemetry_folder()

    print("=" * 60)
    print("      ArenaLake - Enterprise Interactive Setup")
    print("=" * 60)

    check_existing_install()

    print(f"\n{CYAN}[*] Firing up background system update to save time later...{RESET}")
    update_proc = subprocess.Popen(["apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    install_dependencies()
    check_ports_available()
    jwt_secret = secrets.token_hex(32)

    print("\n============================================================")
    print(" STEP 1: BASIC CONFIGURATION")
    print("============================================================")

    raw_company = ""
    while not raw_company: raw_company = input("Company or project name (required): ").strip()
    safe_company_name = format_company_name(raw_company)
    workspace_network = "arenalake-prod_arenalake-net"

    minio_user = f"arenalake_{safe_company_name}_minio_admin"
    minio_pass = ""
    while not is_valid_password(minio_pass):
        minio_pass = input("MinIO Password (Min. 10 chars, upper, lower, numbers): ").strip()

    dba_user = f"arenalake_{safe_company_name}_dba_admin"
    dba_pass = ""
    while not is_valid_password(dba_pass):
        dba_pass = input("Database Password (Min. 10 chars, upper, lower, numbers): ").strip()

    auto_update_ws = "false" if input("Automatically update Workspace? (Y/N) [Default: Y]: ").strip().lower() == "n" else "true"
    auto_update_core = "true" if input("Automatically update Core/Portal? (Y/N) [Default: N]: ").strip().lower() == "y" else "false"

    print("\n============================================================")
    print(" STEP 2: NETWORK AUTHENTICATION (TAILSCALE)")
    print("============================================================")
    input("\nPress ENTER to generate the authentication link...")
    subprocess.run("tailscale up", shell=True, check=True)
    tailscale_url = get_tailscale_url() or input("Paste the complete server URL (e.g. https://machine.tailnet.ts.net): ").strip()

    print("\n============================================================")
    print(" STEP 3: FINALIZING AND STARTING THE CLUSTER")
    print("============================================================")

    datalake_path, datalake_quota = configure_storage()
    os.makedirs(datalake_path, exist_ok=True)
    os.chmod(datalake_path, 0o755)

    update_proc.wait()
    setup_nfs_master(datalake_path)

    print(f"\n[*] Provisioning directories in {datalake_path}...")
    for folder in ["minio_data", "spark_jobs", "projects_data", "database"]:
        folder_path = os.path.join(datalake_path, folder)
        os.makedirs(folder_path, exist_ok=True)
        if folder == "database":
            os.chmod(folder_path, 0o700)
            try: os.chown(folder_path, 70, 70)
            except: pass
        else: os.chmod(folder_path, 0o777)
        print(f"    [+] Created: {folder}")

    env_content = f"""MINIO_ACCESS_KEY={minio_user}\nMINIO_SECRET_KEY={minio_pass}\nDATALAKE_STORAGE_PATH={datalake_path}\nDATALAKE_QUOTA_GB={datalake_quota}\nDATABASE_URL=postgresql://{dba_user}:{dba_pass}@postgres:5432/arenalake_core\nJWT_SECRET_KEY={jwt_secret}\nDBA_USERNAME={dba_user}\nDBA_PASSWORD={dba_pass}\nSPARK_MASTER_URL=spark://spark-master:7077\nPORTAL_PORT=8088\nTRAEFIK_WEB_PORT=80\nMINIO_API_PORT=9000\nMINIO_CONSOLE_PORT=9001\nSPARK_UI_PORT=8080\nTRAEFIK_DASH_PORT=8089\nWORKSPACE_NETWORK={workspace_network}\nWORKSPACE_IMAGE=arenalake-workspace:latest\nTAILSCALE_BASE_URL={tailscale_url}\nAUTO_UPDATE_WORKSPACE={auto_update_ws}\nAUTO_UPDATE_CORE={auto_update_core}\n"""
    with open(".env", "w") as f: f.write(env_content)
    os.chmod(".env", 0o600)

    if subprocess.run(["docker", "info"], capture_output=True, text=True).stdout.find("Swarm: active") == -1:
        subprocess.run(["docker", "swarm", "init"], check=False, stdout=subprocess.DEVNULL)

    try:
        subprocess.run(["docker", "compose", "build"], check=True)
        with open(".env", "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"): os.environ[line.split("=", 1)[0]] = line.strip().split("=", 1)[1]
        subprocess.run(["docker", "stack", "deploy", "-c", "docker-compose.yml", "arenalake-prod"], check=True, stdout=subprocess.DEVNULL)
        
        portal_id = ""
        for _ in range(40):
            result = subprocess.run("docker ps -q -f name=arenalake-prod_portal | head -n 1", shell=True, capture_output=True, text=True)
            if result.stdout.strip(): portal_id = result.stdout.strip(); break
            time.sleep(2)
        
        if portal_id: run_live(f"docker exec {portal_id} python -m core.init_db", "Initializing Super Admin & Core Database")
        subprocess.run(["tailscale", "funnel", "--bg", "http://127.0.0.1:8088"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print("\n" + "=" * 60)
        print(f"  {raw_company} DataLake installed and running successfully! 🚀")
        print("=" * 60)
    except: print("[ERROR] Failed to deploy cluster.")

if __name__ == "__main__":
    main()