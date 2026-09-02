import os
import sys
import subprocess
import shutil
import time


def check_root():
    """Ensure the script runs with administrator privileges."""
    if os.geteuid() != 0:
        print("[ERROR] This script requires administrator privileges.")
        print("Run it again with: sudo python3 uninstall.py")
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


def handle_data_volume():
    """Optionally remove the physical DataLake storage directory."""
    print("\n============================================================")
    print(" STEP 4: DATALAKE DATA (MAXIMUM ATTENTION)")
    print("============================================================")

    # This path matches the dynamic storage layout used by the current architecture.
    current_project_dir = os.path.dirname(os.path.abspath(__file__))
    datalake_path = os.path.join(current_project_dir, "datalake_data")

    if os.path.exists(datalake_path):
        print(f"We detected the physical storage folder at: {datalake_path}")
        print("This folder contains database files, MinIO data, workspace content, and jobs.")
        print(
            "\n⚠️  If you delete it, ALL COMPANY DATA WILL BE LOST FOREVER."
        )

        resp = (
            input(
                "Do you want to permanently DELETE the physical DataLake data? (Y/N) [Default: N]: "
            )
            .strip()
            .lower()
        )
        if resp == "y":
            print(f"[*] Deleting {datalake_path}...")
            shutil.rmtree(datalake_path)
            print("[+] Data deleted successfully. There is no undo.")
        else:
            print(
                "[*] Physical data kept. The system was removed, but the data remains on disk."
            )
    else:
        print(f"[-] Directory {datalake_path} not found. Skipping.")


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
    handle_data_volume()
    handle_tailscale()

    print("\n" + "=" * 60)
    print(" 🧹 Uninstallation completed successfully!")
    print(" ArenaLake was removed from this server.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()