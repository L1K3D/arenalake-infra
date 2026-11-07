# Configuration reference

The [`.env.example`](../config/environment/.env.example) lists configuration keys and
placeholder values. For production, run `helpers/install.py`; it creates `.env` with fresh
installation-specific credentials and restrictive file permissions. Do not
copy `.env.example` into production: it contains placeholders for documentation
and CI only. The installer quotes values for Compose parsing and URL-encodes
database credentials. Never commit `.env`.

| Variable | Required | Default/example | Used by |
|---|---:|---|---|
| `DATALAKE_STORAGE_PATH` | Yes | `<repo>/datalake_data` (installed) | Compose bind mounts and installer |
| `DBA_USERNAME` | Yes | — | PostgreSQL and portal initialization |
| `DBA_PASSWORD` | Yes | — | PostgreSQL and portal initialization |
| `DATABASE_URL` | Yes | `postgresql://…@postgres:5432/arenalake_core` | Portal SQLAlchemy connection |
| `MINIO_ACCESS_KEY` | Yes | — | MinIO, portal, and workspaces |
| `MINIO_SECRET_KEY` | Yes | — | MinIO, portal, and workspaces |
| `JWT_SECRET_KEY` | Yes | — | Portal token signing |
| `WORKSPACE_NETWORK` | Yes | `arenalake-prod_arenalake-net` | Portal-created workspace services |
| `WORKSPACE_IMAGE` | No | `arenalake-workspace:latest` | Portal workspace provisioning |
| `PORTAL_IMAGE` | No | `arenalake-prod-portal:latest` | Portal service image |
| `TELEMETRY_IMAGE` | No | `arenalake-telemetry:latest` | Telemetry service image |
| `MINIO_ENDPOINT` | No | `http://minio:9000` | Ingestion API |
| `TRAEFIK_DASH_PORT` | No | `8089` | Host dashboard port |
| `SPARK_UI_PORT` | No | `8080` | Host Spark UI port |
| `SPARK_RPC_PORT` | No | `7077` | Host Spark master RPC port |
| `MINIO_API_PORT` | No | `9000` | Host MinIO API port |
| `MINIO_CONSOLE_PORT` | No | `9001` | Host MinIO console port |

`MINIO_API_PORT` and `MINIO_CONSOLE_PORT` affect published host ports; the
Portal and workspaces use the internal service address `minio:9000`.
`DATABASE_URL` must use the same credentials as `DBA_USERNAME` and
`DBA_PASSWORD`. The installer percent-encodes credentials when it constructs
`DATABASE_URL`.

The installer also writes `DATALAKE_QUOTA_GB`, `SPARK_MASTER_URL`,
`PORTAL_PORT`, `TRAEFIK_WEB_PORT`, `TAILSCALE_BASE_URL`, `AUTO_UPDATE_WORKSPACE`,
and `AUTO_UPDATE_CORE`. They are documented in `.env.example` for installer
compatibility but are not currently consumed by the application or Compose
stack. In particular, `DATALAKE_QUOTA_GB` records the operator's requested
capacity but does not enforce a filesystem quota. Traefik's HTTP host port is
currently fixed at `8088`.

The telemetry agent has no runtime environment variables at this time. Its
Python dependencies are listed in `apps/telemetry-agent/requirements.txt`.
