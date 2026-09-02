import os
import sys
import subprocess
import time
from datetime import datetime


def check_root():
    """Ensure the backup process has root privileges to read protected files."""
    if os.geteuid() != 0:
        print(
            "[ERROR] The backup process needs to read protected files. Run: sudo python3 backup.py"
        )
        sys.exit(1)


def main():
    check_root()

    print("=" * 60)
    print("      ArenaLake - Enterprise Backup Tool")
    print("=" * 60)
    print("This process will create a complete backup of the configuration and physical")
    print("data (DataLake). This may take a while depending on the stored data volume.")
    print("\n")

    # Use a dynamic project path so the tool still works with the new architecture.
    current_project_dir = os.path.dirname(os.path.abspath(__file__))
    datalake_path = os.path.join(current_project_dir, "datalake_data")

    # Verify that the required data volume exists before starting the archive.
    if not os.path.exists(datalake_path):
        print(
            f"[ERROR] The directory {datalake_path} does not exist. There is no data to back up."
        )
        sys.exit(1)

    if not os.path.exists(".env") or not os.path.exists("docker-compose.yml"):
        print("[WARNING] .env or docker-compose.yml was not found in this folder.")
        resp = (
            input(
                "Do you want to back up only the DataLake data? (Y/N) [Default: N]: "
            )
            .strip()
            .lower()
        )
        if resp != "y":
            sys.exit(0)

    # Create the backup directory if it does not already exist.
    backup_dir = "/opt/arenalake_backups"
    os.makedirs(backup_dir, exist_ok=True)

    # Generate the backup filename with the current timestamp.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"arenalake_backup_{timestamp}.tar.gz"
    backup_filepath = os.path.join(backup_dir, backup_filename)

    print(f"[*] Starting compression... Destination: {backup_filepath}")

    # Build the tar command to include the data lake, .env and compose file.
    tar_cmd = ["tar", "-czf", backup_filepath, datalake_path]

    if os.path.exists(".env"):
        tar_cmd.append(".env")
    if os.path.exists("docker-compose.yml"):
        tar_cmd.append("docker-compose.yml")

    try:
        # Run the backup and show progress as the archive is being created.
        print("[*] Compressing files (please wait)...")
        start_time = time.time()

        subprocess.run(tar_cmd, check=True)

        elapsed = time.time() - start_time
        file_size_mb = os.path.getsize(backup_filepath) / (1024 * 1024)

        print("\n" + "=" * 60)
        print(" ✅ BACKUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f" Generated file: {backup_filepath}")
        print(f" Final size: {file_size_mb:.2f} MB")
        print(f" Time spent: {elapsed:.1f} seconds")
        print("\n 💡 Tip: Store this file in a secure location (cloud, external disk).")
        print("    To restore it later, simply extract the archive.")
        print("=" * 60)

    except subprocess.CalledProcessError as e:
        print(f"\n[CRITICAL ERROR] Failed to generate the backup archive. {e}")
        # Remove an incomplete archive if the compression process failed mid-way.
        if os.path.exists(backup_filepath):
            os.remove(backup_filepath)


if __name__ == "__main__":
    main()