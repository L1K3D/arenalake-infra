import os
import sys
import shutil
import subprocess
import time
import re


def check_root():
    if os.geteuid() != 0:
        print("[Erro] Este script precisa de privilégios de administrador.")
        print("Rode novamente usando: sudo python3 add_worker.py")
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


def check_swarm_status():
    """Verifica se a máquina já faz parte de algum cluster e limpa se necessário"""
    info = subprocess.run(["docker", "info"], capture_output=True, text=True).stdout
    if "Swarm: active" in info or "Swarm: pending" in info:
        print("\n" + "!" * 60)
        print(" ALERTA: Esta máquina já faz parte de um cluster Swarm antigo!")
        print(
            " Para adicioná-la ao ArenaLake, precisamos forçar a saída do cluster atual."
        )
        print("!" * 60)
        resp = (
            input("Deseja sair do cluster antigo agora? (S/N) [Padrão: S]: ")
            .strip()
            .lower()
        )
        if resp != "n":
            print("[*] Limpando configurações de Swarm antigas...")
            subprocess.run(["docker", "swarm", "leave", "--force"], capture_output=True)
            print("[+] Máquina limpa e pronta para um novo cluster.")
        else:
            print("\n[!] Operação cancelada. Não podemos prosseguir com o Swarm ativo.")
            sys.exit(0)


def extract_token(raw_input):
    match = re.search(r"(SWMTKN-1-[a-z0-9]+-[a-z0-9]+)", raw_input)
    if match:
        return match.group(1)
    return raw_input.strip()


def test_connection(ip):
    """Tenta pingar o IP 2 vezes para garantir que há rota na VPN"""
    print(f"\n[*] Testando conectividade VPN com o Master ({ip})...")
    result = subprocess.run(["ping", "-c", "2", "-W", "2", ip], capture_output=True)
    return result.returncode == 0


def provision_storage():
    """Espelha as pastas vitais do Master para o Worker receber os containers"""
    datalake_path = "/mnt/datalake/prod"
    print(f"[*] Espelhando diretórios vitais no Worker ({datalake_path})...")
    os.makedirs(datalake_path, exist_ok=True)
    os.chmod(datalake_path, 0o755)


def main():
    check_root()

    print("=" * 60)
    print("      ArenaLake - Worker Node Installer")
    print("=" * 60)
    print("Bem-vindo! Vamos adicionar esta máquina ao seu Cluster.\n")

    install_dependencies()
    check_swarm_status()
    provision_storage()

    print("\n============================================================")
    print(" PASSO 1: AUTENTICAÇÃO DE REDE (TAILSCALE)")
    print("============================================================")

    print("[*] Precisamos colocar este Worker na mesma rede VPN do Master.")
    print("!" * 60)
    print(" ATENÇÃO:")
    print(" 1. Clique no link que será gerado abaixo e faça login.")
    print(" 2. O terminal ficará pausado aguardando o seu login.")
    print("!" * 60)

    input("\nPressione ENTER para gerar o link de autenticação...")

    try:
        subprocess.run("tailscale up", shell=True, check=True)
        print("\n[+] Worker conectado na VPN com sucesso!")
    except subprocess.CalledProcessError:
        print("\n[Erro] Problema ao conectar no Tailscale.")
        sys.exit(1)

    print("\n============================================================")
    print(" PASSO 2: CONEXÃO COM O CLUSTER (SWARM)")
    print("============================================================")

    print("Vá até o terminal do seu servidor MASTER e rode os comandos abaixo")
    print("para obter as credenciais de acesso.\n")

    # Pega o IP e testa antes de seguir
    master_ip = ""
    while not master_ip:
        print("No MASTER, rode: tailscale ip -4")
        master_ip = input("Cole o IP do Master aqui (ex: 100.105.x.x): ").strip()
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", master_ip):
            print("[Erro] Formato de IP inválido. Tente novamente.\n")
            master_ip = ""
        else:
            if not test_connection(master_ip):
                print(f"[Erro] O IP {master_ip} está inatingível.")
                print("Verifique se o Master está ligado e conectado no Tailscale.")
                master_ip = ""  # Força o usuário a digitar de novo
            else:
                print("[+] Rota de rede VPN verificada com sucesso!")

    # Pega o Token
    print("\nNo MASTER, rode: docker swarm join-token worker -q")
    raw_token = ""
    while not raw_token:
        raw_token = input("Cole o Token gerado aqui: ").strip()

    token = extract_token(raw_token)

    print("\n[*] Conectando ao Cluster ArenaLake...")
    try:
        join_cmd = ["docker", "swarm", "join", "--token", token, f"{master_ip}:2377"]
        subprocess.run(join_cmd, check=True, stdout=subprocess.DEVNULL)

        print("\n" + "=" * 60)
        print("  Worker adicionado ao Cluster com sucesso! 🚀")
        print("  O Master já pode distribuir carga para esta máquina.")
        print("=" * 60)

    except subprocess.CalledProcessError:
        print("\n[Erro] Falha ao ingressar no Cluster.")
        print(
            "A porta 2377 do Master pode estar bloqueada pelo firewall. Libere-a e tente novamente."
        )


if __name__ == "__main__":
    main()