import os
import re
import subprocess
import sys
import shutil
import time
import json
import socket
import secrets


def check_root():
    if os.geteuid() != 0:
        print("[Erro] Este script precisa de privilégios de administrador.")
        print("Rode novamente usando: sudo python3 install.py")
        sys.exit(1)


def check_existing_install():
    """Evita que um usuário desatento destrua a configuração de produção"""
    if os.path.exists(".env"):
        print("\n" + "!" * 60)
        print(" ALERTA CRÍTICO: UMA INSTALAÇÃO JÁ FOI DETECTADA!")
        print(" Um arquivo .env já existe. Se você prosseguir, as credenciais")
        print(" e configurações atuais serão perdidas.")
        print("!" * 60)
        resp = (
            input(
                "Tem CERTEZA que deseja sobrescrever a instalação atual? (S/N) [Padrão: N]: "
            )
            .strip()
            .lower()
        )
        if resp != "s":
            print(
                "\n[*] Instalação abortada por segurança. Nenhuma alteração foi feita."
            )
            sys.exit(0)


def check_ports_available():
    """Verifica se as portas vitais estão livres no servidor"""
    print("\n[*] Checando portas vitais do servidor...")
    vital_ports = [80, 443, 8000, 8080, 9000, 9001, 7077]
    ports_in_use = []

    for port in vital_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) == 0:
                ports_in_use.append(port)

    if ports_in_use:
        print(
            "\n[Erro Crítico] As seguintes portas já estão em uso por outro programa:"
        )
        for p in ports_in_use:
            print(f" - Porta {p}")
        print(
            "\nO ArenaLake precisa dessas portas livres para o Traefik, Portal e MinIO."
        )
        print("Pare o serviço conflitante (ex: Apache, Nginx) e tente novamente.")
        sys.exit(1)
    print("[+] Todas as portas necessárias estão livres!")


def check_compose_file():
    if not os.path.isfile("docker-compose.yml"):
        print(
            "[Erro] O arquivo 'docker-compose.yml' não foi encontrado neste diretório."
        )
        sys.exit(1)


def install_dependencies():
    print("\n[*] Verificando dependências do sistema (Ubuntu)...")

    # --- DOCKER ---
    if shutil.which("docker") is None:
        print("\n[*] Docker não encontrado. Instalando... (Pode levar alguns minutos)")
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
            print(f"[+] Docker instalado! | {docker_v}")
        except BaseException as error:
            print(f"\n[Erro] Falha ao instalar o Docker. | {error}")
            sys.exit(1)
    else:
        docker_v = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True
        ).stdout.strip()
        print(f"[+] Docker OK! | {docker_v}")

    # --- TAILSCALE ---
    if shutil.which("tailscale") is None:
        print("\n[*] Tailscale não encontrado. Instalando...")
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
            print(f"[+] Tailscale instalado! | {ts_v}")
        except BaseException as error:
            print(f"\n[Erro] Falha ao instalar o Tailscale. | {error}")
            sys.exit(1)
    else:
        ts_output = subprocess.run(
            ["tailscale", "version"], capture_output=True, text=True
        ).stdout.strip()
        ts_v = ts_output.split("\n")[0]
        print(f"[+] Tailscale OK! | {ts_v}")

    time.sleep(1)


def format_company_name(name):
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name


def is_valid_password(password):
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


def main():
    check_root()
    check_compose_file()

    print("=" * 60)
    print("      ArenaLake - Enterprise Interactive Setup")
    print("=" * 60)

    check_existing_install()
    install_dependencies()
    check_ports_available()
    jwt_secret = secrets.token_hex(32)

    print("\n============================================================")
    print(" PASSO 1: CONFIGURAÇÕES BÁSICAS")
    print("============================================================")

    raw_company = ""
    while not raw_company:
        raw_company = input("Nome da Empresa ou Projeto (Obrigatório): ").strip()
    safe_company_name = format_company_name(raw_company)
    workspace_network = f"arenalake-prod_{safe_company_name}_arenalake-net"

    print("\n--- Credenciais do DataLake ---")
    minio_user = f"arenalake_{safe_company_name}_minio_admin"
    print(f"\n[*] Login do MinIO definido como: {minio_user}")

    minio_pass = ""
    while not is_valid_password(minio_pass):
        minio_pass = input(
            f"Senha (Mín. 10 chars, Maiúsculas, Minúsculas e Números): "
        ).strip()
        if not is_valid_password(minio_pass):
            print("[Erro] Senha muito fraca. Tente novamente.\n")

    print("\n--- Credenciais do Database ---")
    dba_user = f"arenalake_{safe_company_name}_dba_admin"
    print(f"\n[*] Login do Database definido como: {dba_user}")

    dba_pass = ""
    while not is_valid_password(dba_pass):
        dba_pass = input(
            f"Senha (Mín. 10 chars, Maiúsculas, Minúsculas e Números): "
        ).strip()
        if not is_valid_password(dba_pass):
            print("[Erro] Senha muito fraca. Tente novamente.\n")

    print("\n--- Políticas de Atualização ---")
    ws_input = (
        input("Atualizar Workspace automaticamente? (S/N) [Padrão: S]: ")
        .strip()
        .lower()
    )
    auto_update_ws = "false" if ws_input == "n" else "true"
    core_input = (
        input("Atualizar Core/Portal automaticamente? (S/N) [Padrão: N]: ")
        .strip()
        .lower()
    )
    auto_update_core = "true" if core_input == "s" else "false"

    print("\n============================================================")
    print(" PASSO 2: AUTENTICAÇÃO DE REDE (TAILSCALE)")
    print("============================================================")

    print("[*] Precisamos vincular este servidor à sua conta Tailscale.")
    print("!" * 60)
    print(" ATENÇÃO:")
    print(" 1. Clique no link que será gerado abaixo e faça login.")
    print(" 2. O terminal ficará pausado aguardando o seu login.")
    print(" 3. Após o login, ative 'MagicDNS' e 'HTTPS Certificates' no painel.")
    print("!" * 60)

    input("\nPressione ENTER para gerar o link de autenticação...")

    try:
        subprocess.run("tailscale up", shell=True, check=True)
        print("\n[+] Tailscale autenticado com sucesso!")
    except subprocess.CalledProcessError:
        print("\n[Erro] Problema ao iniciar o Tailscale.")
        sys.exit(1)

    tailscale_url = get_tailscale_url()
    if tailscale_url:
        print(f"[+] URL identificada automaticamente: {tailscale_url}")
    else:
        print("\n[!] Não conseguimos capturar sua URL automaticamente.")
        while not tailscale_url:
            tailscale_url = input(
                "Cole a URL completa do servidor (ex: https://maquina.rede.ts.net): "
            ).strip()

    print("\n============================================================")
    print(" PASSO 3: FINALIZANDO E SUBINDO O CLUSTER")
    print("============================================================")

    datalake_path = f"/mnt/arenalake_{safe_company_name}_datalake/prod"
    print(f"[*] Provisionando diretório de armazenamento em {datalake_path}...")
    os.makedirs(datalake_path, exist_ok=True)
    os.chmod(datalake_path, 0o755)

    print("[*] Gerando o arquivo de ambiente (.env)...")
    env_content = f"""# --- DataLake Configurations ---
MINIO_ACCESS_KEY={minio_user}
MINIO_SECRET_KEY={minio_pass}
DATALAKE_STORAGE_PATH={datalake_path}

# --- Core Security & Database ---
DATABASE_URL=sqlite:///./arenalake_{safe_company_name}_core.db
JWT_SECRET_KEY={jwt_secret}
DBA_USERNAME={dba_user}
DBA_PASSWORD={dba_pass}

# --- Spark Cluster ---
SPARK_MASTER_URL=spark://spark-master:7077

# --- Network & Ports ---
PORTAL_PORT=8000
TRAEFIK_WEB_PORT=80
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
SPARK_UI_PORT=8080

WORKSPACE_NETWORK={workspace_network}
TAILSCALE_BASE_URL={tailscale_url}

# --- Enterprise Auto-Update Policies ---
AUTO_UPDATE_WORKSPACE={auto_update_ws}
AUTO_UPDATE_CORE={auto_update_core}
"""
    with open(".env", "w") as env_file:
        env_file.write(env_content)

    os.chmod(".env", 0o600)

    print("[*] Preparando o Docker Swarm...")
    if (
        subprocess.run(["docker", "info"], capture_output=True, text=True).stdout.find(
            "Swarm: active"
        )
        == -1
    ):
        subprocess.run(
            ["docker", "swarm", "init"], check=False, stdout=subprocess.DEVNULL
        )

    print("[*] Disparando o deploy (Isso pode levar alguns segundos)...")
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
            stdout=subprocess.DEVNULL,
        )

        # Monitoramento Pós-Deploy
        print("\n[*] Validando os serviços...")
        time.sleep(4)
        print("-" * 60)
        subprocess.run(["docker", "service", "ls"])
        print("-" * 60)

        print("\n" + "=" * 60)
        print(f"  {raw_company} DataLake instalado e rodando com sucesso! 🚀")
        print("=" * 60)
    except subprocess.CalledProcessError:
        print("\n[Erro] Ocorreu um problema ao iniciar o Docker Swarm.")


if __name__ == "__main__":
    main()