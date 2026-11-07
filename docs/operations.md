# Operations

Run operational scripts from the repository root; the scripts also resolve the
root directory from their own file path.

| Task | Command |
|---|---|
| Diagnose environment and services | `sudo python3 helpers/doctor.py` |
| Rebuild images and redeploy the stack | `sudo python3 helpers/restart.py` |
| Back up configuration and data | `sudo python3 helpers/backup.py` |
| Add a Swarm worker | `sudo python3 helpers/add_worker.py` |
| Configure storage | `sudo python3 helpers/add_storage.py` |
| Restart telemetry service | `sudo python3 helpers/restart_telemetry_service.py` |
| Uninstall the stack | `sudo python3 helpers/uninstall.py` |

The backup script stores archives under `/opt/arenalake_backups`. Verify that a
backup completes and that the archive can be listed before relying on it. Keep
backups of `.env` protected because it contains secrets.

After updating the workspace image on a multi-node Swarm, ensure each worker can
pull or has received the required image before provisioning workspaces.
