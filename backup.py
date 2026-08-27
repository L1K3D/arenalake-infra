import os
import sys
import subprocess
import time
from datetime import datetime


def check_root():
    if os.geteuid() != 0:
        print(
            "[Erro] O backup precisa ler arquivos protegidos. Rode: sudo python3 backup.py"
        )
        sys.exit(1)


def main():
    check_root()

    print("=" * 60)
    print("      ArenaLake - Enterprise Backup Tool")
    print("=" * 60)
    print("Este processo fará um backup completo das configurações e dos")
    print("dados físicos (DataLake). Isso pode demorar dependendo do")
    print("volume de dados armazenado.\n")

    # Verifica se os dados vitais existem
    datalake_path = "/mnt/datalake/prod"
    if not os.path.exists(datalake_path):
        print(
            f"[Erro] O diretório {datalake_path} não existe. Não há dados para backup."
        )
        sys.exit(1)

    if not os.path.exists(".env") or not os.path.exists("docker-compose.yml"):
        print("[Aviso] Arquivo .env ou docker-compose.yml não encontrados nesta pasta.")
        resp = (
            input(
                "Deseja fazer o backup apenas dos dados do DataLake? (S/N) [Padrão: N]: "
            )
            .strip()
            .lower()
        )
        if resp != "s":
            sys.exit(0)

    # Cria pasta de backups se não existir
    backup_dir = "/opt/arenalake_backups"
    os.makedirs(backup_dir, exist_ok=True)

    # Gera o nome do arquivo com a data e hora atual
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"arenalake_backup_{timestamp}.tar.gz"
    backup_filepath = os.path.join(backup_dir, backup_filename)

    print(f"[*] Iniciando compactação... Destino: {backup_filepath}")

    # Montando o comando do TAR
    # Ele vai "zipar" o /mnt/datalake/prod, o .env e o docker-compose.yml
    tar_cmd = ["tar", "-czf", backup_filepath, datalake_path]

    if os.path.exists(".env"):
        tar_cmd.append(".env")
    if os.path.exists("docker-compose.yml"):
        tar_cmd.append("docker-compose.yml")

    try:
        # Roda o comando e mostra um feedback visual enquanto processa
        print("[*] Compactando arquivos (Por favor, aguarde)...")
        start_time = time.time()

        subprocess.run(tar_cmd, check=True)

        elapsed = time.time() - start_time
        file_size_mb = os.path.getsize(backup_filepath) / (1024 * 1024)

        print("\n" + "=" * 60)
        print(" ✅ BACKUP CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f" Arquivo gerado : {backup_filepath}")
        print(f" Tamanho final  : {file_size_mb:.2f} MB")
        print(f" Tempo gasto    : {elapsed:.1f} segundos")
        print("\n 💡 Dica: Guarde este arquivo em um local seguro (nuvem, HD externo).")
        print("    Para restaurar no futuro, basta extrair este arquivo.")
        print("=" * 60)

    except subprocess.CalledProcessError as e:
        print(f"\n[Erro Crítico] Falha ao gerar o arquivo de backup. {e}")
        # Limpa o arquivo corrompido caso o tar tenha falhado no meio
        if os.path.exists(backup_filepath):
            os.remove(backup_filepath)


if __name__ == "__main__":
    main()