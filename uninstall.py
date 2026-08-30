import os
import sys
import subprocess
import shutil
import time


def check_root():
    if os.geteuid() != 0:
        print("[Erro] Este script precisa de privilégios de administrador.")
        print("Rode novamente usando: sudo python3 uninstall.py")
        sys.exit(1)


def confirm_destruction():
    print("\n" + "!" * 60)
    print(" ⚠️  ALERTA DE DESTRUIÇÃO CRÍTICA (BOTÃO VERMELHO) ⚠️")
    print("!" * 60)
    print(" Você está prestes a desinstalar o ArenaLake deste servidor.")
    print(" Isso irá derrubar todos os serviços, desconectar do cluster")
    print(" e apagar as configurações locais.")
    print("\n Para prosseguir, digite a palavra: DESTRUIR")

    resp = input("> ").strip()
    if resp != "DESTRUIR":
        print("\n[*] Desinstalação abortada. Ufa! Seus dados e serviços estão a salvo.")
        sys.exit(0)


def remove_docker_stack(stack_name="arenalake-prod"):
    print(f"\n[*] Passo 1: Derrubando a stack '{stack_name}'...")
    try:
        # Tenta remover a stack
        subprocess.run(
            ["docker", "stack", "rm", stack_name],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        print(
            "[*] Aguardando os containers serem finalizados (pode levar uns segundos)..."
        )
        # Loop de verificação para não prosseguir enquanto a stack ainda estiver morrendo
        while True:
            result = subprocess.run(
                ["docker", "stack", "ls"], capture_output=True, text=True
            )
            if stack_name not in result.stdout:
                break
            time.sleep(2)
        print("[+] Serviços do ArenaLake encerrados com sucesso.")
    except Exception:
        print("[-] Nenhuma stack do ArenaLake rodando (ou já foi removida).")


def leave_swarm():
    print("\n[*] Passo 2: Desconectando do cluster Docker Swarm...")
    try:
        subprocess.run(
            ["docker", "swarm", "leave", "--force"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[+] Servidor removido do cluster Swarm.")
    except Exception:
        print("[-] Este servidor já não faz parte de um cluster Swarm.")


def clean_configs():
    print("\n[*] Passo 3: Limpando arquivos de configuração...")
    if os.path.exists(".env"):
        os.remove(".env")
        print("[+] Arquivo .env (credenciais e variáveis) removido.")
    else:
        print("[-] Arquivo .env não encontrado. Pulando.")


def handle_data_volume():
    print("\n============================================================")
    print(" PASSO 4: DADOS DO DATALAKE (ATENÇÃO MÁXIMA)")
    print("============================================================")
    datalake_path = "/mnt/datalake/prod"

    if os.path.exists(datalake_path):
        print(f"Detectamos a pasta de armazenamento físico em: {datalake_path}")
        print("Lá estão salvos os arquivos do MinIO, workspaces e jobs do Spark.")
        print(
            "\n⚠️  Se você apagar isso, TODOS OS DADOS DA EMPRESA SERÃO PERDIDOS PARA SEMPRE."
        )

        resp = (
            input(
                "Deseja DELETAR DEFINITIVAMENTE os dados físicos do DataLake? (S/N) [Padrão: N]: "
            )
            .strip()
            .lower()
        )
        if resp == "s":
            print(f"[*] Excluindo {datalake_path}...")
            shutil.rmtree(datalake_path)
            print("[+] Dados apagados com sucesso. Não há mais volta.")
        else:
            print(
                "[*] Dados físicos MANTIDOS. O sistema foi removido, mas os dados estão salvos no HD."
            )
    else:
        print(f"[-] Diretório {datalake_path} não encontrado. Pulando.")


def handle_tailscale():
    print("\n============================================================")
    print(" PASSO 5: ACESSO REMOTO (TAILSCALE)")
    print("============================================================")
    print("O Tailscale ainda está conectando este servidor à sua conta VPN.")
    resp = (
        input(
            "Deseja fazer LOGOUT e desconectar esta máquina da rede Tailscale? (S/N) [Padrão: N]: "
        )
        .strip()
        .lower()
    )

    if resp == "s":
        try:
            subprocess.run(["tailscale", "logout"], check=True)
            print("[+] Máquina desconectada da VPN Tailscale.")
        except Exception:
            print("[-] Falha ao desconectar (talvez o Tailscale não esteja rodando).")
    else:
        print("[*] Conexão Tailscale mantida.")


def main():
    check_root()

    print("=" * 60)
    print("      ArenaLake - Uninstaller (Modo de Limpeza)")
    print("=" * 60)

    confirm_destruction()

    remove_docker_stack()
    leave_swarm()
    clean_configs()
    handle_data_volume()
    handle_tailscale()
    #sudo rm -rf datalake_data
    subprocess.run(
            ["rm", "-rf", "datalake_data"], capture_output=True, text=True
    )

    print("\n" + "=" * 60)
    print(" 🧹 Desinstalação concluída com sucesso!")
    print(" O ArenaLake foi removido deste servidor.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()