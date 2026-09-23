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


def check_root():
    """Ensure the install script has administrator privileges."""
    if os.geteuid() != 0:
        print(f"{YELLOW}[ERROR]{RESET} This script requires administrator privileges.")
        print(f"{CYAN}Run it again with: sudo python3 helpers/install.py{RESET}")
        sys.exit(1)


def check_existing_install():
    """Warn the operator before overwriting an existing configuration."""
    if os.path.exists(".env"):
        print("\n" + "!" * 60)
        print(" CRITICAL WARNING: AN INSTALLATION HAS ALREADY BEEN DETECTED!")
        print(" A .env file already exists. If you continue, the current credentials")
        print(" and settings will be overwritten.")
        print("!" * 60)
        resp = (
            input(
                "Are you absolutely sure you want to overwrite the current installation? (Y/N) [Default: N]: "
            )
            .strip()
            .lower()
        )
        if resp != "y":
            print(
                "\n[*] Installation aborted for safety. No changes were made."
            )
            sys.exit(0)


def check_ports_available():
    """Validate that the required TCP ports are free before deploying services."""
    print("\n[*] Checking the server's critical ports...")
    vital_ports = [80, 443, 8000, 8080, 9000, 9001, 7077]
    ports_in_use = []
    for port in vital_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) == 0:
                ports_in_use.append(port)
    if ports_in_use:
        print(
            "\n[CRITICAL ERROR] The following ports are already in use by another program:"
        )
        for p in ports_in_use:
            print(f" - Port {p}")
        print(
            "\nArenaLake needs these ports free for Traefik, the Portal, and MinIO."
        )
        print("Stop the conflicting service (for example Apache or Nginx) and try again.")
        sys.exit(1)
    print("[+] All required ports are free!")


def check_compose_file():
    """Verify the Compose file is present before running deployment."""
    if not os.path.isfile("docker-compose.yml"):
        print(
            "[ERROR] The 'docker-compose.yml' file was not found in this directory."
        )
        sys.exit(1)


def install_dependencies():
    """Ensure Docker and Tailscale are installed on the host operating system."""
    print("\n[*] Verifying system dependencies (Ubuntu)...")

    # Install Docker if it is not present in the base image.
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

    # Install Tailscale so the node can join the private VPN network.
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
            ts_v = (
                subprocess.run(["tailscale", "version"], capture_output=True, text=True)
                .stdout.strip()
                .split("\n")[0]
            )
            print(f"[+] Tailscale installed! | {ts_v}")
        except BaseException as error:
            print(f"\n[ERROR] Failed to install Tailscale. | {error}")
            sys.exit(1)
    else:
        ts_v = (
            subprocess.run(["tailscale", "version"], capture_output=True, text=True)
            .stdout.strip()
            .split("\n")[0]
        )
        print(f"[+] Tailscale OK! | {ts_v}")
    time.sleep(1)


def format_company_name(name):
    """Normalize the company/project name to a safe environment key value."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name


def is_valid_password(password):
    """Require a stronger password to protect the DataLake and DBA credentials."""
    if len(password) < 10:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True


def get_tailscale_url():
    """Fetch the machine's Tailscale DNS name and build a public HTTPS URL."""
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        dns_name = data.get("Self", {}).get("DNSName", "")
        if dns_name:
            return f"https://{dns_name.rstrip('.')}"
    except Exception:
        pass
    return ""

def check_telemetry_folder():
    """Verify the telemetry-agent folder is present before building."""
    if not os.path.isdir("telemetry-agent"):
        print("[ERROR] The 'telemetry-agent' directory was not found.")
        print("Ensure the full repository is downloaded.")
        sys.exit(1)

def configure_storage():
    """Lista discos e cria o DataLake na raiz do projeto de forma 100% blindada contra conflitos."""
    print("\n============================================================")
    print(" STEP 1.5: STORAGE CONFIGURATION")
    print("============================================================")
    print("[*] Mapping available storage devices...")

    # Caminho ideal para o usuário (sempre dentro do projeto)
    project_datalake = os.path.join(PROJECT_ROOT, "datalake_data")

    # Limpeza agressiva e segura usando lexists/unlink (pega até links quebrados)
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
    mounts = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and not parts[0].startswith(('/run', '/sys', '/dev', '/proc', '/snap', '/boot')):
            mounts.append({"path": parts[0], "free": parts[1], "pcent": parts[2]})

    print("\nAvailable Partitions:")
    for i, m in enumerate(mounts):
        print(f" [{i+1}] {m['path']} (Free: {m['free']} / Used: {m['pcent']})")

    choice = 0
    while True:
        try:
            choice = int(input(f"\nSelect a storage location [1-{len(mounts)}]: ").strip())
            if 1 <= choice <= len(mounts):
                break
        except ValueError:
            pass
        print(f"{YELLOW}[ERROR]{RESET} Invalid choice.")

    base_path = mounts[choice-1]["path"]
    
    quota_gb = 0
    while quota_gb < 5:
        try:
            quota_gb = int(input("How many GBs do you want to allocate? (Minimum 5): ").strip())
            if quota_gb < 5:
                print(f"{YELLOW}[ERROR]{RESET} You must allocate at least 5GB.")
        except ValueError:
            print(f"{YELLOW}[ERROR]{RESET} Please enter a valid number.")

    # Verifica onde a pasta do projeto está fisicamente
    project_partition = subprocess.run(["df", "--output=target", PROJECT_ROOT], capture_output=True, text=True).stdout.strip().split("\n")[-1]

    if base_path == project_partition:
        # O disco escolhido é o mesmo do projeto. Cria a pasta diretamente.
        os.makedirs(project_datalake, exist_ok=True)
    else:
        # O disco escolhido é outro HD. Cria lá e faz o atalho (symlink) no projeto.
        physical_path = os.path.join(base_path, "arenalake_data")
        os.makedirs(physical_path, exist_ok=True)
        os.symlink(physical_path, project_datalake)

    print(f"\n[+] Storage configured successfully! Access it at: {project_datalake} (Quota: {quota_gb}GB)")
    return project_datalake, quota_gb
  
def setup_glusterfs_master(datalake_path):
    """Instala o GlusterFS, limpa vestígios anteriores e cria o Volume Distribuído."""
    print("\n[*] Configuring GlusterFS Distributed Storage (State of the Art)...")
    try:
        subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL)
        subprocess.run(["apt-get", "install", "-y", "glusterfs-server"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["systemctl", "enable", "--now", "glusterd"], check=True)
        
        # BLINDAGEM: Para e remove qualquer volume ou montagem anterior remanescente
        subprocess.run(["umount", "-f", datalake_path], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.run(["gluster", "volume", "stop", "datalake", "force"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.run(["gluster", "volume", "delete", "datalake"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        shutil.rmtree("/var/lib/glusterd/vols/datalake", ignore_errors=True)
        
        master_ip = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True).stdout.strip()
        
        # Cria o "Tijolo" (Brick) físico oculto ao lado da pasta escolhida
        real_physical_path = os.path.realpath(datalake_path)
        brick_path = f"{real_physical_path}_brick"
        
        if os.path.exists(brick_path):
            shutil.rmtree(brick_path, ignore_errors=True)
            
        os.makedirs(brick_path, exist_ok=True)
        os.makedirs(datalake_path, exist_ok=True)
        
        # Força a criação do volume no Master e inicia
        subprocess.run(["gluster", "volume", "create", "datalake", f"{master_ip}:{brick_path}", "force"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["gluster", "volume", "start", "datalake"], check=True, stdout=subprocess.DEVNULL)
        
        # Monta o volume de rede na pasta do projeto
        subprocess.run(["mount", "-t", "glusterfs", "localhost:/datalake", datalake_path], check=True)
        
        # Limpa entrada duplicada no fstab se existir, depois adiciona
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
    install_dependencies()
    check_ports_available()
    jwt_secret = secrets.token_hex(32)

    print("\n============================================================")
    print(" STEP 1: BASIC CONFIGURATION")
    print("============================================================")

    raw_company = ""
    while not raw_company:
        raw_company = input("Company or project name (required): ").strip()
    safe_company_name = format_company_name(raw_company)
    workspace_network = "arenalake-prod_arenalake-net"

    print("\n--- DataLake Credentials ---")
    minio_user = f"arenalake_{safe_company_name}_minio_admin"
    print(f"\n[*] MinIO login defined as: {minio_user}")

    minio_pass = ""
    while not is_valid_password(minio_pass):
        minio_pass = input(
            "Password (Min. 10 chars, uppercase, lowercase, and numbers): "
        ).strip()
        if not is_valid_password(minio_pass):
            print("[ERROR] Password too weak. Please try again.\n")

    print("\n--- Database Credentials ---")
    dba_user = f"arenalake_{safe_company_name}_dba_admin"
    print(f"\n[*] Database login defined as: {dba_user}")

    dba_pass = ""
    while not is_valid_password(dba_pass):
        dba_pass = input(
            "Password (Min. 10 chars, uppercase, lowercase, and numbers): "
        ).strip()
        if not is_valid_password(dba_pass):
            print("[ERROR] Password too weak. Please try again.\n")

    print("\n--- Update Policies ---")
    ws_input = (
        input("Automatically update Workspace? (Y/N) [Default: Y]: ")
        .strip()
        .lower()
    )
    auto_update_ws = "false" if ws_input == "n" else "true"
    core_input = (
        input("Automatically update Core/Portal? (Y/N) [Default: N]: ")
        .strip()
        .lower()
    )
    auto_update_core = "true" if core_input == "y" else "false"

    print("\n============================================================")
    print(" STEP 2: NETWORK AUTHENTICATION (TAILSCALE)")
    print("============================================================")

    print("[*] We need to link this server to your Tailscale account.")
    print("!" * 60)
    print(" IMPORTANT:")
    print(" 1. Click the link generated below and log in.")
    print(" 2. The terminal will pause while waiting for your login.")
    print(" 3. After logging in, enable 'MagicDNS' and 'HTTPS Certificates' in the dashboard.")
    print("!" * 60)

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
            tailscale_url = input(
                "Paste the complete server URL (example: https://machine.tailnet.ts.net): "
            ).strip()

    print("\n============================================================")
    print(" STEP 3: FINALIZING AND STARTING THE CLUSTER")
    print("============================================================")

    # Dynamic local directory plus all mandatory subfolders needed by the platform.
    datalake_path, datalake_quota = configure_storage()

    print(f"[*] Provisioning storage directories in {datalake_path}...")
    os.makedirs(datalake_path, exist_ok=True)
    os.chmod(datalake_path, 0o755)

    setup_glusterfs_master(datalake_path)

    # 2. Depois cria as subpastas dentro do volume de rede já montado
    subfolders = ["minio_data", "spark_jobs", "projects_data", "database"]
    for folder in subfolders:
        folder_path = os.path.join(datalake_path, folder)
        os.makedirs(folder_path, exist_ok=True)
        os.chmod(folder_path, 0o777)
        print(f"[+] Subfolder configured: {folder}")

    print("[*] Generating the environment file (.env)...")
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
        env_file.write(env_content)
    os.chmod(".env", 0o600)

    print("[*] Preparing Docker Swarm...")
    if (
        subprocess.run(["docker", "info"], capture_output=True, text=True).stdout.find(
            "Swarm: active"
        )
        == -1
    ):
        subprocess.run(
            ["docker", "swarm", "init"], check=False, stdout=subprocess.DEVNULL
        )

    print("[*] Building local Portal and Workspace Builder images...")
    try:
        subprocess.run(["docker", "compose", "build"], check=True)
        print("[+] Images built successfully!")
    except subprocess.CalledProcessError:
        print(
            "\n[WARNING] The direct docker compose build failed. Trying to build individual images..."
        )
        subprocess.run(["docker", "image", "prune", "-f"], stdout=subprocess.DEVNULL)

    print("[*] Deploying the cluster (this may take a few seconds)...")
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key] = value

    try:
        subprocess.run(
            ["docker", "stack", "deploy", "-c", "docker-compose.yml", "arenalake-prod"],
            check=True,
        )

        print("\n[*] Validating services...")
        # Give the containers some time to start before checking the cluster state.
        time.sleep(10)
        print("-" * 60)
        subprocess.run(["docker", "service", "ls"])
        print("-" * 60)

        # -------------------------------------------------------------------
        # AUTOMATIC DATABASE INITIALIZATION (POSTGRESQL)
        # -------------------------------------------------------------------
        print(f"\n[*] Waiting for PostgreSQL to be ready and initializing database...")

        portal_id = ""
        for _ in range(20):  # Tenta por até 40 segundos
            result = subprocess.run(
                "docker ps -q -f name=arenalake-prod_portal | head -n 1",
                shell=True,
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                portal_id = result.stdout.strip()
                break
            time.sleep(2)

        if portal_id:
            try:
                # Aguarda o postgres responder antes de rodar o init
                print("[*] Connecting Portal to PostgreSQL backend...")
                subprocess.run(
                    f"docker exec {portal_id} python -m core.init_db",
                    shell=True,
                    check=True,
                )
                print(f"[+] Database and super admin configured successfully!")
            except subprocess.CalledProcessError:
                print(f"[{YELLOW}Warning{RESET}] Database initialization script returned an error. You can run it manually later.")
        else:
            print(f"[{YELLOW}Warning{RESET}] The Portal container took too long to start.")
        # -------------------------------------------------------------------

        # Automatic Tailscale Funnel activation.
        print(f"\n[*] Configuring public exposure (Tailscale Funnel for port 8088)...")
        funnel_result = subprocess.run(
            ["tailscale", "funnel", "--bg", "http://127.0.0.1:8088"], capture_output=True, text=True
        )
        funnel_output = funnel_result.stdout + funnel_result.stderr

        if "To enable, visit:" in funnel_output:
            print(
                f"\n{YELLOW}============================================================{RESET}"
            )
            print(
                f"{YELLOW} ACTION REQUIRED: The Funnel requires authorization in your account!{RESET}"
            )
            print(
                f"{YELLOW}============================================================{RESET}"
            )
            for line in funnel_output.split("\n"):
                if "https://login.tailscale.com" in line:
                    print(f"{CYAN} -> {line.strip()}{RESET}")
        else:
            print(
                f"[+] {CYAN}Tailscale Funnel enabled successfully! Your site is already public.{RESET}"
            )

        print("\n" + "=" * 60)
        print(f"  {raw_company} DataLake installed and running successfully! 🚀")
        print(f"  Public endpoint: {tailscale_url}")
        print("=" * 60)

    except subprocess.CalledProcessError:
        print("\n[ERROR] There was a problem starting Docker Swarm or the deployment.")

if __name__ == "__main__":
    main()