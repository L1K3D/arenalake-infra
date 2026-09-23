import os
import sys
import subprocess
import shutil
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)


def check_root():
    """Ensure the script runs with administrator privileges."""
    if os.geteuid() != 0:
        print("[ERROR] This script requires administrator privileges.")
        print("Run it again with: sudo python3 helpers/uninstall.py")
        sys.exit(1)


def confirm_destruction():
    """Double-check that the operator really wants to remove the platform."""
    print("\n" + "!" * 60)
    print(" ⚠️  CRITICAL DESTRUCTION ALERT (RED BUTTON) ⚠️")
    print("!" * 60)
    print(" You are about to uninstall ArenaLake from this server.")
    print(" This will stop all services, disconnect the node from the cluster,")
    print(" and delete the local configuration.")
    print("\n To continue, type the word: DESTROY")

    resp = input("> ").strip()
    if resp != "DESTROY":
        print("\n[*] Uninstall aborted. Your data and services are still safe.")
        sys.exit(0)


def remove_docker_stack(stack_name="arenalake-prod"):
    """Remove the deployed stack from the Docker Swarm cluster."""
    print(f"\n[*] Step 1: Removing stack '{stack_name}'...")
    try:
        subprocess.run(
            ["docker", "stack", "rm", stack_name],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        print(
            "[*] Waiting for the containers to finish shutting down (this may take a few seconds)..."
        )
        while True:
            result = subprocess.run(
                ["docker", "stack", "ls"], capture_output=True, text=True
            )
            if stack_name not in result.stdout:
                break
            time.sleep(2)
        print("[+] ArenaLake services shut down successfully.")
        
        print("[*] Removing compiled telemetry image...")
        subprocess.run(
            ["docker", "image", "rm", "arenalake-telemetry:latest", "-f"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
    except Exception:
        print("[-] No ArenaLake stack is running (or it has already been removed).")


def leave_swarm():
    """Disconnect the machine from the Docker Swarm network."""
    print("\n[*] Step 2: Disconnecting from the Docker Swarm cluster...")
    try:
        subprocess.run(
            ["docker", "swarm", "leave", "--force"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[+] Server removed from the Swarm cluster.")
    except Exception:
        print("[-] This server is not part of a Swarm cluster.")


def clean_configs():
    """Delete local configuration files that contain environment secrets."""
    print("\n[*] Step 3: Cleaning configuration files...")
    if os.path.exists(".env"):
        os.remove(".env")
        print("[+] .env file (credentials and variables) removed.")
    else:
        print("[-] .env file not found. Skipping.")

def cleanup_nfs():
    """Remove partilhas do Master e desmonta/limpa pontos de montagem dos Workers."""
    print("\n============================================================")
    print(" STEP 4: DISTRIBUTED STORAGE CLEANUP (NFS)")
    print("============================================================")
    
    # 1. Limpeza no lado do Master (/etc/exports)
    if os.path.exists("/etc/exports"):
        try:
            with open("/etc/exports", "r") as f:
                lines = f.readlines()
            
            with open("/etc/exports", "w") as f:
                for line in lines:
                    # Remove a linha se for a partilha gerada pelo nosso script
                    if "100.64.0.0/10" not in line and "arenalake" not in line.lower():
                        f.write(line)
                        
            subprocess.run(["exportfs", "-a"], check=False, stderr=subprocess.DEVNULL)
            print("[+] Master NFS exports cleaned (/etc/exports).")
        except Exception as e:
            print(f"[-] Failed to clean /etc/exports: {e}")

    # 2. Limpeza no lado do Worker (/etc/fstab)
    if os.path.exists("/etc/fstab"):
        try:
            with open("/etc/fstab", "r") as f:
                lines = f.readlines()
            
            cleaned_lines = []
            for line in lines:
                # Identifica se é uma montagem NFS do ArenaLake via Tailscale
                if "nfs" in line and ("100." in line or "arenalake" in line.lower()):
                    mount_point = line.split()[1]
                    print(f"[*] Force unmounting {mount_point}...")
                    subprocess.run(["umount", "-f", mount_point], check=False, stderr=subprocess.DEVNULL)
                    continue # Pula a escrita desta linha no novo fstab
                cleaned_lines.append(line)
                
            with open("/etc/fstab", "w") as f:
                f.writelines(cleaned_lines)
            print("[+] Worker NFS mounts cleaned (/etc/fstab).")
        except Exception as e:
            print(f"[-] Failed to clean /etc/fstab: {e}")

def handle_data_volume():
    """Optionally remove the physical DataLake storage directory."""
    print("\n============================================================")
    print(" STEP 4: DATALAKE DATA (MAXIMUM ATTENTION)")
    print("============================================================")

    # This path matches the dynamic storage layout used by the current architecture.
    current_project_dir = PROJECT_ROOT
    datalake_path = os.path.join(PROJECT_ROOT, "datalake_data")

    if os.path.exists(datalake_path):
        # Encontra onde os dados estão guardados de verdade
        real_path = os.path.realpath(datalake_path)
        print(f"We detected the storage folder at: {datalake_path} (Physical: {real_path})")
        
        resp = input("Do you want to permanently DELETE the physical DataLake data? (Y/N) [Default: N]: ").strip().lower()
        if resp == "y":
            print(f"[*] Deleting data...")
            shutil.rmtree(real_path) # Apaga os dados reais
            if os.path.islink(datalake_path):
                os.remove(datalake_path) # Apaga o atalho

            try:
                subprocess.run(["umount", "-f", datalake_path], stderr=subprocess.DEVNULL)
                subprocess.run(["gluster", "volume", "stop", "datalake", "force"], stderr=subprocess.DEVNULL)
                subprocess.run(["gluster", "volume", "delete", "datalake"], stderr=subprocess.DEVNULL)
                shutil.rmtree("/var/lib/glusterd/vols/datalake", ignore_errors=True)
                print("[+] GlusterFS cluster state and volumes cleaned successfully.")
            except Exception as e:
                print(f"[-] GlusterFS cleanup notice: {e}")
            
            print("[+] Data deleted successfully. There is no undo.")
        else:
            print("[*] Physical data kept.")


def handle_tailscale():
    """Optionally disconnect the server from the Tailscale VPN network."""
    print("\n============================================================")
    print(" STEP 5: REMOTE ACCESS (TAILSCALE)")
    print("============================================================")
    print("Tailscale is still connecting this server to your VPN account.")
    resp = (
        input(
            "Do you want to LOG OUT and disconnect this machine from the Tailscale network? (Y/N) [Default: N]: "
        )
        .strip()
        .lower()
    )

    if resp == "y":
        try:
            subprocess.run(["tailscale", "logout"], check=True)
            print("[+] Machine disconnected from the Tailscale VPN.")
        except Exception:
            print("[-] Failed to disconnect (maybe Tailscale is not running).")
    else:
        print("[*] Tailscale connection kept active.")


def main():
    check_root()

    print("=" * 60)
    print("      ArenaLake - Uninstaller (Cleanup Mode)")
    print("=" * 60)

    confirm_destruction()

    remove_docker_stack()
    leave_swarm()
    clean_configs()
    cleanup_nfs()
    handle_data_volume()
    handle_tailscale()

    print("\n" + "=" * 60)
    print(" 🧹 Uninstallation completed successfully!")
    print(" ArenaLake was removed from this server.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()