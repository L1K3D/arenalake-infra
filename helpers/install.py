import os
import re
import subprocess
import sys
import shutil
import time
import json
import socket
import secrets

# Terminal color codes.
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)


def run_live(command, description="Executing"):
    """Executa um comando e exibe os logs em tempo real para não parecer que o script travou."""
    print(f"\n[*] {description}...")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            print(f"    {line.strip()}")
            
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
            
    except Exception as e:
        print(f"{YELLOW}[ERROR]{RESET} Failed during: {description} | {e}")
        sys.exit(1)


def check_root():
    if os.geteuid() != 0:
        print(f"{YELLOW}[ERROR]{RESET} This script requires administrator privileges.")
        print(f"{CYAN}Run it again with: sudo python3 helpers/install.py{RESET}")
        sys.exit(1)


def check_existing_install():
    if os.path.exists(".env"):
        print("\n" + "!" * 60)
        print(" CRITICAL WARNING: AN INSTALLATION HAS ALREADY BEEN DETECTED!")
        print(" A .env file already exists. If you continue, the current credentials")
        print(" and settings will be overwritten.")
        print("!" * 60)
        resp = input("Are you absolutely sure you want to overwrite the current installation? (Y/N) [Default: N]: ").strip().lower()
        if resp != "y":
            print("\n[*] Installation aborted for safety. No changes were made.")
            sys.exit(0)


def check_ports_available():
    print("\n[*] Checking the server's critical ports...")
    vital_ports = [80, 443, 8000, 8080, 9000, 9001, 7077]
    ports_in_use = []
    for port in vital_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) == 0:
                ports_in_use.append(port)
    if ports_in_use:
        print("\n[CRITICAL ERROR] The following ports are already in use by another program:")
        for p in ports_in_use:
            print(f" - Port {p}")
        print("\nStop the conflicting service and try again.")
        sys.exit(1)
    print("[+] All required ports are free!")


def check_compose_file():
    if not os.path.isfile("docker-compose.yml"):
        print("[ERROR] The 'docker-compose.yml' file was not found in this directory.")
        sys.exit(1)


def check_telemetry_folder():
    if not os.path.isdir("telemetry-agent"):
        print("[ERROR] The 'telemetry-agent' directory was not found.")
        sys.exit(1)


def install_dependencies():
    print("\n[*] Verifying system dependencies (Ubuntu)...")
    if shutil.which("docker") is None:
        run_live("curl -fsSL https://get.docker.com | sh", "Installing Docker Engine")
    else:
        docker_v = subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.strip()
        print(f"[+] Docker OK! | {docker_v}")

    if shutil.which("tailscale") is None:
        run_live("curl -fsSL https://tailscale.com/install.sh | sh", "Installing Tailscale VPN")
    else:
        ts_v = subprocess.run(["tailscale", "version"], capture_output=True, text=True).stdout.strip().split("\n")[0]
        print(f"[+] Tailscale OK! | {ts_v}")
    time.sleep(1)


def format_company_name(name):
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]", "_", name)
    return re.sub(r"_+", "_", name)


def is_valid_password(password):
    if len(password) < 10: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"[0-9]", password): return False
    return True


def get_tailscale_url():
    try:
        result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, check=True)
        dns_name = json.loads(result.stdout).get("Self", {}).get("DNSName", "")
        if dns_name: return f"https://{dns_name.rstrip('.')}"
    except Exception:
        pass
    return ""


def configure_storage():
    print("\n============================================================")
    print(" STEP 1.5: STORAGE CONFIGURATION")
    print("============================================================")
    print("[*] Mapping available storage devices...")

    project_datalake = os.path.join(PROJECT_ROOT, "datalake_data")

    if os.path.lexists(project_datalake):
        try:
            if os.path.islink(project_datalake) or os.path.isfile(project_datalake):
                os.unlink(project_datalake)
            else:
                shutil.rmtree(project_datalake)
        except Exception as e:
            print(f"[WARNING] Could not clean old path: {e}")

    result = subprocess.run(["df", "-h", "--output=target,avail,pcent"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    mounts = [
        {"path": p[0], "free": p[1], "pcent": p[2]} 
        for line in lines if len((p := line.split())) >= 3 and not p[0].startswith(('/run', '/sys', '/dev', '/proc', '/snap', '/boot'))
    ]

    print("\nAvailable Partitions:")
    for i, m in enumerate(mounts):
        print(f" [{i+1}] {m['path']} (Free: {m['free']} / Used: {m['pcent']})")

    while True:
        try:
            choice = int(input(f"\nSelect a storage location [1-{len(mounts)}]: ").strip())
            if 1 <= choice <= len(mounts): break
        except ValueError:
            pass
        print(f"{YELLOW}[ERROR]{RESET} Invalid choice.")

    base_path = mounts[choice-1]["path"]
    
    quota_gb = 0
    while quota_gb < 5:
        try:
            quota_gb = int(input("How many GBs do you want to allocate? (Minimum 5): ").strip())
            if quota_gb < 5: print(f"{YELLOW}[ERROR]{RESET} You must allocate at least 5GB.")
        except ValueError:
            print(f"{YELLOW}[ERROR]{RESET} Please enter a valid number.")

    project_partition = subprocess.run(["df", "--output=target", PROJECT_ROOT], capture_output=True, text=True).stdout.strip().split("\n")[-1]

    if base_path == project_partition:
        os.makedirs(project_datalake, exist_ok=True)
    else:
        physical_path = os.path.join(base_path, "arenalake_data")
        os.makedirs(physical_path, exist_ok=True)
        os.symlink(physical_path, project_datalake)

    print(f"\n[+] Storage configured successfully! Access it at: {project_datalake} (Quota: {quota_gb}GB)")
    return project_datalake, quota_gb


def setup_glusterfs_master(datalake_path):
    """Instala o GlusterFS, limpa vestígios anteriores e cria o Volume Distribuído."""
    print("\n============================================================")
    print(" STEP 1.6: CONFIGURING GLUSTERFS (HIGH AVAILABILITY)")
    print("============================================================")
    
    # Truque ninja: Impede o apt-get de fazer perguntas e não instala dependências inúteis
    run_live("DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends glusterfs-server", "Installing GlusterFS Server (Turbo Mode)")
    run_live("systemctl enable --now glusterd", "Starting GlusterFS Daemon")
    
    try:
        # BLINDAGEM: Para e remove qualquer volume ou montagem anterior remanescente
        subprocess.run(["umount", "-f", datalake_path], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.run(["gluster", "volume", "stop", "datalake", "force"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.run(["gluster", "volume", "delete", "datalake"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        shutil.rmtree("/var/lib/glusterd/vols/datalake", ignore_errors=True)
        
        master_ip = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True).stdout.strip()
        
        real_physical_path = os.path.realpath(datalake_path)
        brick_path = f"{real_physical_path}_brick"
        
        if os.path.exists(brick_path):
            shutil.rmtree(brick_path, ignore_errors=True)
            
        os.makedirs(brick_path, exist_ok=True)
        os.makedirs(datalake_path, exist_ok=True)
        
        subprocess.run(["gluster", "volume", "create", "datalake", f"{master_ip}:{brick_path}", "force"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["gluster", "volume", "start", "datalake"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["mount", "-t", "glusterfs", "localhost:/datalake", datalake_path], check=True)
        
        with open("/etc/fstab", "r") as f:
            fstab_lines = f.readlines()
        with open("/etc/fstab", "w") as f:
            for line in fstab_lines:
                if "localhost:/datalake" not in line:
                    f.write(line)
            f.write(f"localhost:/datalake {datalake_path} glusterfs defaults,_netdev 0 0\n")
            
        print("[+] GlusterFS Master Volume created! Ready for HA Replication.")
        print(f"{CYAN} 💡 TIP FOR WORKERS:{RESET} When asked for the physical path, type: {real_physical_path}")
    except Exception as e:
        print(f"[ERROR] Failed to configure GlusterFS: {e}")
        sys.exit(1)


def main():
    check_root()
    check_compose_file()
    check_telemetry_folder()

    print("=" * 60)
    print("      ArenaLake - Enterprise Interactive Setup")
    print("=" * 60)

    check_existing_install()

    # TRUQUE NINJA: Lança o update dos repositórios em background sem bloquear o ecrã.
    # Enquanto o utilizador responde às perguntas, o Linux já está a tratar da lista de pacotes.
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

    print("\n--- DataLake Credentials ---")
    minio_user = f"arenalake_{safe_company_name}_minio_admin"
    print(f"[*] MinIO login defined as: {minio_user}")

    minio_pass = ""
    while not is_valid_password(minio_pass):
        minio_pass = input("Password (Min. 10 chars, uppercase, lowercase, and numbers): ").strip()
        if not is_valid_password(minio_pass): print("[ERROR] Password too weak. Please try again.\n")

    print("\n--- Database Credentials ---")
    dba_user = f"arenalake_{safe_company_name}_dba_admin"
    print(f"[*] Database login defined as: {dba_user}")

    dba_pass = ""
    while not is_valid_password(dba_pass):
        dba_pass = input("Password (Min. 10 chars, uppercase, lowercase, and numbers): ").strip()
        if not is_valid_password(dba_pass): print("[ERROR] Password too weak. Please try again.\n")

    print("\n--- Update Policies ---")
    auto_update_ws = "false" if input("Automatically update Workspace? (Y/N) [Default: Y]: ").strip().lower() == "n" else "true"
    auto_update_core = "true" if input("Automatically update Core/Portal? (Y/N) [Default: N]: ").strip().lower() == "y" else "false"

    print("\n============================================================")
    print(" STEP 2: NETWORK AUTHENTICATION (TAILSCALE)")
    print("============================================================")
    print("[*] We need to link this server to your Tailscale account.")
    input("\nPress ENTER to generate the authentication link...")

    try:
        subprocess.run("tailscale up", shell=True, check=True)
        print("\n[+] Tailscale authenticated successfully!")
    except subprocess.CalledProcessError:
        print("\n[ERROR] There was a problem starting Tailscale.")
        sys.exit(1)

    tailscale_url = get_tailscale_url()
    if tailscale_url:
        print(f"[+] URL identified automatically: {tailscale_url}")
    else:
        print("\n[!] We could not capture your URL automatically.")
        while not tailscale_url:
            tailscale_url = input("Paste the complete server URL (example: https://machine.tailnet.ts.net): ").strip()

    print("\n============================================================")
    print(" STEP 3: FINALIZING AND STARTING THE CLUSTER")
    print("============================================================")

    datalake_path, datalake_quota = configure_storage()

    os.makedirs(datalake_path, exist_ok=True)
    os.chmod(datalake_path, 0o755)

    # Garante que o update em background já terminou antes de avançar para o Gluster
    update_proc.wait()

    setup_glusterfs_master(datalake_path)

    print(f"\n[*] Provisioning directories in {datalake_path}...")
    subfolders = ["minio_data", "spark_jobs", "projects_data", "database"]
    for folder in subfolders:
        folder_path = os.path.join(datalake_path, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        if folder == "database":
            os.chmod(folder_path, 0o700)
            try:
                os.chown(folder_path, 70, 70)
            except PermissionError:
                pass
        else:
            os.chmod(folder_path, 0o777)
            
        print(f"    [+] Created: {folder}")

    print("\n[*] Generating the environment file (.env)...")
    env_content = f"""# --- DataLake Configurations ---
MINIO_ACCESS_KEY={minio_user}
MINIO_SECRET_KEY={minio_pass}
DATALAKE_STORAGE_PATH={datalake_path}
DATALAKE_QUOTA_GB={datalake_quota}

# --- Core Security & Database ---
DATABASE_URL=postgresql://${dba_user}:${dba_pass}@postgres:5432/arenalake_core
JWT_SECRET_KEY={jwt_secret}
DBA_USERNAME={dba_user}
DBA_PASSWORD={dba_pass}

# --- Spark Cluster ---
SPARK_MASTER_URL=spark://spark-master:7077

# --- Network & Ports ---
PORTAL_PORT=8088
TRAEFIK_WEB_PORT=80
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
SPARK_UI_PORT=8080
TRAEFIK_DASH_PORT=8089

WORKSPACE_NETWORK={workspace_network}
WORKSPACE_IMAGE=arenalake-workspace:latest
TAILSCALE_BASE_URL={tailscale_url}

# --- Enterprise Auto-Update Policies ---
AUTO_UPDATE_WORKSPACE={auto_update_ws}
AUTO_UPDATE_CORE={auto_update_core}
"""
    with open(".env", "w") as env_file:
        env_file.write(env_content.replace('    ', ''))
    os.chmod(".env", 0o600)

    print("[*] Preparing Docker Swarm...")
    if subprocess.run(["docker", "info"], capture_output=True, text=True).stdout.find("Swarm: active") == -1:
        subprocess.run(["docker", "swarm", "init"], check=False, stdout=subprocess.DEVNULL)

    print("\n[*] Building local Portal and Workspace Builder images (Native BuildKit output)...")
    try:
        subprocess.run(["docker", "compose", "build"], check=True)
        print("[+] Images built successfully!")
    except subprocess.CalledProcessError:
        print("\n[WARNING] The direct docker compose build failed. Attempting cleanup...")
        subprocess.run(["docker", "image", "prune", "-f"], stdout=subprocess.DEVNULL)

    print("\n[*] Deploying the cluster...")
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key] = value

    try:
        subprocess.run(["docker", "stack", "deploy", "-c", "docker-compose.yml", "arenalake-prod"], check=True, stdout=subprocess.DEVNULL)

        print(f"\n[*] Waiting for PostgreSQL and Portal to initialize", end="")
        sys.stdout.flush()
        
        portal_id = ""
        for _ in range(40):
            print(".", end="")
            sys.stdout.flush()
            result = subprocess.run("docker ps -q -f name=arenalake-prod_portal | head -n 1", shell=True, capture_output=True, text=True)
            if result.stdout.strip():
                portal_id = result.stdout.strip()
                break
            time.sleep(2)
        
        print()

        if portal_id:
            run_live(f"docker exec {portal_id} python -m core.init_db", "Initializing Super Admin & Core Database")
            print(f"[+] Database and super admin configured successfully!")
        else:
            print(f"[{YELLOW}Warning{RESET}] The Portal container took too long to start.")
        
        print(f"\n[*] Configuring public exposure (Tailscale Funnel for port 8088)...")
        funnel_result = subprocess.run(["tailscale", "funnel", "--bg", "http://127.0.0.1:8088"], capture_output=True, text=True)
        funnel_output = funnel_result.stdout + funnel_result.stderr

        if "To enable, visit:" in funnel_output:
            print(f"\n{YELLOW}============================================================{RESET}")
            print(f"{YELLOW} ACTION REQUIRED: The Funnel requires authorization in your account!{RESET}")
            print(f"{YELLOW}============================================================{RESET}")
            for line in funnel_output.split("\n"):
                if "https://login.tailscale.com" in line:
                    print(f"{CYAN} -> {line.strip()}{RESET}")
        else:
            print(f"[+] {CYAN}Tailscale Funnel enabled successfully! Your site is already public.{RESET}")

        print("\n" + "=" * 60)
        print(f"  {raw_company} DataLake installed and running successfully! 🚀")
        print(f"  Public endpoint: {tailscale_url}")
        print("=" * 60)

    except subprocess.CalledProcessError:
        print("\n[ERROR] There was a problem starting Docker Swarm or the deployment.")

if __name__ == "__main__":
    main()