import os
import sys
import time
import shutil
import subprocess
import re


def check_root():
    """
    Garante que o script está sendo rodado como root (sudo),
    necessário para instalar o Docker e o Tailscale.
    """
    if os.geteuid() != 0:
        print(
            "[Erro] Este script precisa de privilégios de administrador para instalar dependências."
        )
        print("Por favor, rode o comando novamente usando: sudo python3 install.py")
        sys.exit(1)


def install_dependencies():
    """
    Verifica e instala o Docker e o Tailscale, exibindo logs e pedindo permissão para avançar.
    """
    print("\n[*] Verificando dependências do sistema (Ubuntu)...")

    # ==========================================
    # 1. Verifica/Instala Docker
    # ==========================================
    if shutil.which("docker") is None:
        print("\n[*] Docker não encontrado. Iniciando instalação automatizada...")
        print("[*] Acompanhe os logs de instalação abaixo:\n")
        print("-" * 60)
        try:
            # Roda o script de instalação do Docker jogando os logs nativos na tela do usuário
            subprocess.run(
                "curl -fsSL https://get.docker.com | sh", shell=True, check=True
            )
            print("-" * 60)

            docker_v = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True
            ).stdout.strip()
            print(f"\n[+] Docker instalado com sucesso! | {docker_v}")

            # Pausa interativa antes de ir para o próximo
            resp = (
                input(
                    "Deseja prosseguir com a verificação/instalação do Tailscale? (S/N) [Padrão: S]: "
                )
                .strip()
                .lower()
            )
            if resp == "n":
                print("\n[!] Instalação interrompida pelo usuário.")
                sys.exit(0)
        except BaseException as error:
            print("-" * 60)
            print(
                f"\n[Erro] Falha ao instalar o Docker. Verifique sua conexão com a internet ou os logs acima. | {error}"
            )
            sys.exit(1)
    else:
        docker_v = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True
        ).stdout.strip()
        print(f"[+] Docker já está instalado. | {docker_v}")
        time.sleep(2)  # Dei uma diminuída para 2s pra não ficar muito lento

    # ==========================================
    # 2. Verifica/Instala Tailscale
    # ==========================================
    if shutil.which("tailscale") is None:
        print("\n[*] Tailscale não encontrado. Iniciando instalação automatizada...")
        print("[*] Acompanhe os logs de instalação abaixo:\n")
        print("-" * 60)
        try:
            # Roda o script de instalação do Tailscale jogando os logs nativos na tela
            subprocess.run(
                "curl -fsSL https://tailscale.com/install.sh | sh",
                shell=True,
                check=True,
            )
            print("-" * 60)

            # Aqui no Tailscale ele retorna várias linhas, pegamos só a primeira (a versão)
            ts_output = subprocess.run(
                ["tailscale", "version"], capture_output=True, text=True
            ).stdout.strip()
            ts_v = ts_output.split("\n")[0]
            print(f"\n[+] Tailscale instalado com sucesso! | Versão: {ts_v}")

            # Pausa interativa final das dependências
            resp = (
                input(
                    "Deseja continuar com a configuração do ArenaLake? (S/N) [Padrão: S]: "
                )
                .strip()
                .lower()
            )
            if resp == "n":
                print("\n[!] Instalação interrompida pelo usuário.")
                sys.exit(0)
        except BaseException as error:
            print("-" * 60)
            print(
                f"\n[Erro] Falha ao instalar o Tailscale. Verifique sua conexão com a internet ou os logs acima. | {error}"
            )
            sys.exit(1)
    else:
        ts_output = subprocess.run(
            ["tailscale", "version"], capture_output=True, text=True
        ).stdout.strip()
        ts_v = ts_output.split("\n")[0]
        print(f"[+] Tailscale já está instalado. | Versão: {ts_v}")
        time.sleep(2)


def format_company_name(name):
    """
    Transforma 'Vozz Automotive' em 'vozz_automotive'
    """
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name


def is_valid_password(password):
    """
    Verifica se a senha tem pelo menos 10 caracteres, letras maiúsculas, minúsculas e números.
    """
    if len(password) < 10:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True


def main():
    # Garante que o usuário tem permissão para instalar pacotes
    check_root()

    print("=" * 60)
    print("      ArenaLake - Enterprise Interactive Setup")
    print("=" * 60)
    print("Bem-vindo! Vamos configurar o seu ambiente em poucos passos.\n")

    # Instala dependências exibindo logs e pedindo autorização a cada passo concluído
    install_dependencies()

    # 1. Nome da Empresa / Projeto (OBRIGATÓRIO)
    print("\n--- Configuração do Projeto ---")
    raw_company = ""
    while not raw_company:
        raw_company = input(
            "Nome da Empresa ou Projeto (Obrigatório, ex: Vozz Automotive): "
        ).strip()
        if not raw_company:
            print(
                "[Erro] O nome da empresa é obrigatório. Não podemos prosseguir sem ele."
            )

    safe_company_name = format_company_name(raw_company)
    workspace_network = f"arenalake-prod_{safe_company_name}_arenalake-net"

    # 3. MinIO (DataLake)
    print("\n--- Credenciais do Banco de Dados (DataLake) ---")
    default_minio_user = f"{safe_company_name}_minio_arenalake_prod"
    minio_user = input(
        f"Login do Administrador [Padrão: {default_minio_user}]: "
    ).strip()
    if not minio_user:
        minio_user = default_minio_user

    minio_pass = ""
    # Loop OBRIGATÓRIO para a senha
    while not is_valid_password(minio_pass):
        minio_pass = input(
            f"Senha do Administrador (Obrigatório, mín. 10 chars, Maiúsculas, Minúsculas e Números): "
        ).strip()

        if not is_valid_password(minio_pass):
            print("[Erro] Senha muito fraca ou em branco!")
            print(
                "A senha deve ter no mínimo 10 caracteres, incluindo letras maiúsculas, minúsculas e números.\n"
            )

    # 4. Políticas de Atualização Automática
    print("\n--- Políticas de Atualização (Watchtower) ---")
    print("Isso define se o seu sistema receberá melhorias automaticamente.")

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

    # 2. Tailscale com Tutorial Interativo
    print("\n--- Acesso Remoto (Tailscale) ---")
    print(
        "Para acessar o ArenaLake de forma segura pela internet, precisamos da sua URL do Tailscale."
    )

    print("\n" + "!" * 60)
    print(" ATENÇÃO: O Tailscale precisa ser ativado agora.")
    print(" Ele vai gerar um link aqui embaixo.")
    print(" 1. Clique no link (ou copie e cole no navegador).")
    print(" 2. Faça o login na sua conta do Tailscale.")
    print(" 3. O terminal vai ficar 'travado' esperando você logar.")
    print(" 4. Assim que você autorizar lá, o script continua sozinho!")
    print("!" * 60 + "\n")

    subprocess.run("tailscale up", shell=True, check=True)

    print("\n[+] Tailscale online e autenticado na sua rede!")
    print("-" * 60)

    tailscale_url = ""
    while not tailscale_url:
        tailscale_url = input(
            "Digite a URL do Tailscale (ou aperte ENTER vazio para ver o tutorial de como obter): "
        ).strip()

        if not tailscale_url:
            print("\n" + "-" * 50)
            print(" PASSO A PASSO: COMO OBTER SUA URL DO TAILSCALE")
            print("-" * 50)
            print(
                "1. Como já instalamos o Tailscale para você, rode o comando em outro terminal:"
            )
            print("   sudo tailscale up\n")
            print("2. Acesse o painel Admin: https://login.tailscale.com/admin")
            print("3. No menu lateral, vá em 'DNS' e ative 'MagicDNS'.")
            print("4. Role para baixo e ative 'HTTPS Certificates'.")
            print(
                "5. Vá na aba 'Machines', encontre este servidor e copie o nome completo dele."
            )
            print(
                "6. A URL será algo como: https://nome-da-maquina.nome-da-sua-rede.ts.net"
            )
            print("-" * 50)

            usar_padrao = (
                input(
                    "\nDeseja usar a URL de teste temporariamente para prosseguir? (S/N) [Padrão: N]: "
                )
                .strip()
                .lower()
            )
            if usar_padrao == "s":
                tailscale_url = "https://arenalakeserver.tail8b9a43.ts.net"
                print(f"[*] Usando URL padrão de testes: {tailscale_url}")
            else:
                print("\nVamos tentar de novo...")

    # 5. Geração do arquivo .env
    print(f"\n[*] Configurando o sistema para: {raw_company}")
    print("[*] Gerando o arquivo de ambiente (.env)...")

    env_content = f"""# --- DataLake Configurations ---
MINIO_ACCESS_KEY={minio_user}
MINIO_SECRET_KEY={minio_pass}
DATALAKE_STORAGE_PATH=/mnt/datalake/prod

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

    print("[Sucesso] Arquivo .env criado e personalizado!")

    # 6. Inicialização do Swarm
    print("\n[*] Preparando o Docker Swarm...")
    if (
        subprocess.run(["docker", "info"], capture_output=True)
        .stdout.decode("utf-8")
        .find("Swarm: active")
        == -1
    ):
        print("[*] Inicializando o Docker Swarm neste nó...")
        subprocess.run(["docker", "swarm", "init"], check=False)

    # 7. Carregar as variáveis e fazer o Deploy
    print("[*] Iniciando o cluster no Docker Swarm...")
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
        print("\n" + "=" * 60)
        print(f"  {raw_company} DataLake instalado e rodando com sucesso! 🚀")
        print("=" * 60)
    except subprocess.CalledProcessError:
        print(
            "\n[Erro] Ocorreu um problema ao iniciar o Docker Swarm. Verifique os logs acima."
        )


if __name__ == "__main__":
    main()