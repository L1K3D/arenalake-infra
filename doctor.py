import os
import subprocess
import json

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_status(component, status, message, tip=None):
    if status == "OK":
        print(f"[{GREEN} OK {RESET}] {component.ljust(20)} : {message}")
    elif status == "WARN":
        print(f"[{YELLOW}AVISO{RESET}] {component.ljust(20)} : {message}")
        if tip:
            print(f"         {CYAN}💡 Dica:{RESET} {tip}")
    else:
        print(f"[{RED}ERRO{RESET}] {component.ljust(20)} : {message}")
        if tip:
            print(f"         {CYAN}🔧 Solução:{RESET} {tip}")


def get_datalake_path():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("DATALAKE_STORAGE_PATH="):
                    return line.strip().split("=")[1]
    # Fallback caso o .env não exista
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "datalake_data")


def check_resources():
    print("\n--- 1. Recursos do Servidor ---")
    datalake_path = get_datalake_path()
    if os.path.exists(datalake_path):
        total, used, free = (
            os.statvfs(datalake_path).f_blocks * os.statvfs(datalake_path).f_frsize,
            (os.statvfs(datalake_path).f_blocks - os.statvfs(datalake_path).f_bfree)
            * os.statvfs(datalake_path).f_frsize,
            os.statvfs(datalake_path).f_bavail * os.statvfs(datalake_path).f_frsize,
        )
        free_gb = free / (2**30)
        if free_gb > 20:
            print_status(
                "Disco (DataLake)", "OK", f"{free_gb:.1f} GB livres (Caminho local)."
            )
        elif free_gb > 5:
            print_status(
                "Disco (DataLake)",
                "WARN",
                f"Apenas {free_gb:.1f} GB livres.",
                "Limpe arquivos não utilizados.",
            )
        else:
            print_status(
                "Disco (DataLake)",
                "ERROR",
                f"CRÍTICO! Apenas {free_gb:.1f} GB livres.",
                "Limpe o disco urgente.",
            )
    else:
        print_status(
            "Disco (DataLake)",
            "ERROR",
            f"Pasta {datalake_path} não encontrada!",
            "Rode o install.py.",
        )


def check_environment():
    print("\n--- 2. Configurações Base ---")
    if os.path.isfile(".env"):
        print_status("Arquivo .env", "OK", "Encontrado.")
    else:
        print_status(
            "Arquivo .env",
            "ERROR",
            "NÃO ENCONTRADO!",
            "Rode o install.py para recriar.",
        )

    if os.path.isfile("docker-compose.yml"):
        print_status("Docker Compose", "OK", "Encontrado.")
    else:
        print_status(
            "Docker Compose",
            "ERROR",
            "NÃO ENCONTRADO!",
            "Certifique-se de estar na raiz do projeto.",
        )


def check_tailscale():
    print("\n--- 3. Rede e VPN (Tailscale) ---")
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"], capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        backend_state = data.get("BackendState", "")
        if backend_state == "Running":
            ip = data.get("Self", {}).get("TailscaleIPs", [""])[0]
            print_status("VPN Conexão", "OK", f"Conectado. IP: {ip}")
        else:
            print_status(
                "VPN Conexão",
                "ERROR",
                f"Desconectado ({backend_state}).",
                "Rode 'sudo tailscale up'",
            )
    except Exception:
        print_status(
            "Tailscale", "ERROR", "Falha na leitura.", "Verifique se está instalado."
        )


def check_docker_swarm():
    print("\n--- 4. Orquestração (Docker Swarm) ---")
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if "Swarm: active" not in result.stdout:
        print_status(
            "Docker Swarm", "ERROR", "Cluster inativo.", "Rode: sudo docker swarm init"
        )
        return
    else:
        print_status("Docker Swarm", "OK", "Ativo.")

    print("\n--- 5. Status dos Serviços (ArenaLake) ---")
    try:
        services_raw = subprocess.run(
            ["docker", "service", "ls", "--format", "{{.Name}}|{{.Replicas}}"],
            capture_output=True,
            text=True,
        ).strip()
        for line in services_raw.split("\n"):
            if "arenalake-prod" in line:
                name, replicas = line.split("|")
                name = name.replace("arenalake-prod_", "")
                active, target = replicas.split("/")

                if active == target and int(target) > 0:
                    print_status(name, "OK", f"Operacional ({active}/{target}).")
                elif active == "0":
                    print_status(
                        name,
                        "ERROR",
                        f"CAIU! ({active}/{target}).",
                        f"Rode 'docker service logs arenalake-prod_{name}' para ver o que causou a queda.",
                    )
                else:
                    print_status(
                        name,
                        "WARN",
                        f"Instável ({active}/{target}).",
                        "O Docker está tentando reiniciar.",
                    )
    except Exception:
        print_status("Serviços", "ERROR", "Falha ao listar serviços.", "")


def main():
    print("=" * 60)
    print("      ArenaLake - System Doctor (Diagnóstico)")
    print("=" * 60)
    check_resources()
    check_environment()
    check_tailscale()
    check_docker_swarm()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()