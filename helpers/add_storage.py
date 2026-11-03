#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def check_root():
    if os.geteuid() != 0:
        print(f"{YELLOW}[ERROR]{RESET} This script requires administrator privileges.")
        sys.exit(1)

def install_mergerfs():
    """Garante que o MergerFS e o suporte a FUSE estão instalados."""
    if shutil.which("mergerfs") is None:
        print("[*] Installing MergerFS pooling system...")
        subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL)
        subprocess.run(["apt-get", "install", "-y", "mergerfs", "fuse"], check=True, stdout=subprocess.DEVNULL)
        
    # Habilita a permissão global para o Docker aceder ao disco virtual
    if os.path.exists("/etc/fuse.conf"):
        with open("/etc/fuse.conf", "r") as f:
            content = f.read()
        if "#user_allow_other" in content:
            with open("/etc/fuse.conf", "w") as f:
                f.write(content.replace("#user_allow_other", "user_allow_other"))
        print("[+] MergerFS subsystem ready.")

def select_new_disk():
    """Mapeia os discos e permite escolher qual será adicionado ao Pool."""
    print("\n[*] Mapping available storage devices...")
    result = subprocess.run(["df", "-h", "--output=target,avail,pcent"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    mounts = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and not parts[0].startswith(('/run', '/sys', '/dev', '/proc', '/snap', '/boot')):
            mounts.append({"path": parts[0], "free": parts[1], "pcent": parts[2]})

    print("\nAvailable Partitions to Add:")
    for i, m in enumerate(mounts):
        print(f" [{i+1}] {m['path']} (Free: {m['free']} / Used: {m['pcent']})")

    choice = 0
    while True:
        try:
            choice = int(input(f"\nSelect a partition to expand the DataLake [1-{len(mounts)}]: ").strip())
            if 1 <= choice <= len(mounts):
                break
        except ValueError:
            pass
        print(f"{YELLOW}[ERROR]{RESET} Invalid choice.")

    return mounts[choice-1]["path"]

def patch_nfs_exports(target_path):
    """O NFS exige um ID virtual (fsid) ao partilhar discos FUSE/MergerFS."""
    if not os.path.exists("/etc/exports"):
        return
    with open("/etc/exports", "r") as f:
        exports = f.read()
    
    # Se a linha existe, mas não tem fsid=111, fazemos o patch para estabilidade
    if target_path in exports and "fsid=" not in exports:
        new_exports = []
        for line in exports.splitlines():
            if target_path in line:
                line = line.replace("(", "(fsid=111,")
            new_exports.append(line)
        with open("/etc/exports", "w") as f:
            f.write("\n".join(new_exports) + "\n")
        subprocess.run(["exportfs", "-a"], check=False, stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "restart", "nfs-kernel-server"], check=False, stderr=subprocess.DEVNULL)

def main():
    check_root()
    print("=" * 60)
    print("      ArenaLake - Storage Expansion (MergerFS)")
    print("=" * 60)

    install_mergerfs()

    # 1. Identificar o alvo atual (Físico ou Symlink)
    datalake_link = os.path.join(PROJECT_ROOT, "datalake_data")
    if os.path.islink(datalake_link):
        current_target = os.path.realpath(datalake_link)
    else:
        current_target = datalake_link

    # 2. Descobrir se já estamos num Pool (Expansões subsequentes)
    is_pooled = False
    branches = []
    if os.path.exists("/etc/fstab"):
        with open("/etc/fstab", "r") as f:
            for line in f:
                if "fuse.mergerfs" in line and current_target in line.split()[1]:
                    is_pooled = True
                    branches = line.split()[0].split(":")
                    break

    if not is_pooled:
        # É a PRIMEIRA expansão. Vamos converter o HD atual na Shard 1.
        parent_dir = os.path.dirname(current_target)
        base_name = os.path.basename(current_target)
        shard_1_path = os.path.join(parent_dir, f"{base_name}_shard_1")

        print(f"\n[*] 1st Expansion Detected! Converting current storage to {shard_1_path}...")
        
        print("[*] Stopping ArenaLake stack to prevent data corruption...")
        subprocess.run(["docker", "stack", "rm", "arenalake-prod"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5) # Esperar os containers largarem os volumes

        # O truque de mestre: Renomeia o real, recria o vazio para montar por cima
        os.rename(current_target, shard_1_path)
        os.makedirs(current_target, exist_ok=True)
        branches = [shard_1_path]
    else:
        print(f"\n[*] Existing Pool Detected. Current drives in pool: {len(branches)}")
        print("[*] Stopping ArenaLake stack to prevent data corruption...")
        subprocess.run(["docker", "stack", "rm", "arenalake-prod"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)

    # 3. Pedir o novo disco
    new_base_path = select_new_disk()

    # Evitar que o usuário selecione um disco que já faz parte do pool
    for b in branches:
        if new_base_path in b:
            print(f"\n{YELLOW}[WARNING]{RESET} This partition is already part of the DataLake!")
            sys.exit(0)

    new_shard_path = os.path.join(new_base_path, f"arenalake_shard_{len(branches)+1}")
    os.makedirs(new_shard_path, exist_ok=True)
    print(f"[+] Created new storage shard at: {new_shard_path}")
    branches.append(new_shard_path)

    # 4. Configurar o MergerFS
    branches_str = ":".join(branches)
    fstab_entry = f"{branches_str} {current_target} fuse.mergerfs defaults,allow_other,use_ino,category.create=mfs,dropcacheonclose=true 0 0\n"

    # Limpar entrada antiga do fstab, se existir
    with open("/etc/fstab", "r") as f:
        lines = f.readlines()
    with open("/etc/fstab", "w") as f:
        for line in lines:
            if current_target in line and "fuse.mergerfs" in line:
                continue
            f.write(line)

    # Injetar a nova regra que soma os HDs
    with open("/etc/fstab", "a") as f:
        f.write(fstab_entry)

    # 5. Montar e Aplicar Patch no NFS
    if is_pooled:
        subprocess.run(["umount", current_target], check=False, stderr=subprocess.DEVNULL)
    subprocess.run(["mount", current_target], check=True)
    print(f"[+] MergerFS Virtual Pool mounted successfully at {current_target}!")

    patch_nfs_exports(current_target)

    # 6. Reiniciar a Stack
    print("\n[*] Restarting ArenaLake cluster...")
    subprocess.run(["python3", "helpers/restart.py", "--yes"], check=True)

    print("\n" + "=" * 60)
    print(" 🚀 DataLake Storage successfully expanded!")
    print(" Run 'df -h' to see your new merged storage capacity.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()