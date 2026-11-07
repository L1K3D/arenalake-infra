# Deployment

## Deployment model

The supported installation is a Docker Swarm stack managed by a Linux
manager. The interactive installer performs privileged operations on the
host: it installs dependencies, configures persistent storage, prepares NFS
and Tailscale, generates credentials, creates `.env` with restrictive
permissions, builds images, and deploys services. Review the installer source
before running it.

`.env.example` is only a reference and a CI fixture. **You do not need to copy
it for installation**: `helpers/install.py` generates `.env` with
installation-specific credentials during setup.

## Prerequisites

- Ubuntu LTS Linux with administrative access. WSL2 may be suitable for
  evaluation, but it must have systemd enabled and working Docker integration.
  For production, prefer a native Linux installation or a Linux virtual
  machine.
- Git, Python 3.11 or later, `curl`, and CA certificates.
- Docker Engine and Docker Compose v2, or network access that allows the
  installer to install them. The account performing these tasks must be able
  to access the Docker daemon.
- Internet access, sufficient space for images and data, and availability of
  the required ports.
- For a multi-node Swarm, plan for shared storage and connectivity between
  nodes. The installer configures an NFS export over the Tailscale network.

## Initial installation

### 1. Update the host

On Ubuntu or Debian, install pending updates and the required tools. Schedule
a maintenance window; kernel updates may require a reboot.

```bash
sudo apt-get update
sudo apt-get full-upgrade -y
sudo apt-get install -y git python3 python3-pip curl ca-certificates
sudo reboot
```

After rebooting, reconnect and confirm that Docker does not conflict with
another container runtime and that the service ports are available.

### 2. Create the project directory under `/opt`

Replace `my-project` with a short, lowercase name without spaces:

```bash
PROJECT_NAME=my-project
sudo mkdir -p "/opt/arenalake-${PROJECT_NAME}"
sudo chown "$USER":"$USER" "/opt/arenalake-${PROJECT_NAME}"
```

### 3. Clone the repository into that directory

```bash
git clone https://github.com/L1K3D/arenalake-infra.git \
  "/opt/arenalake-${PROJECT_NAME}"
cd "/opt/arenalake-${PROJECT_NAME}"
```

Check `git status` and review the scripts before running them. Never install
production from an unreviewed branch or fork.

### 4. Run the installer

```bash
sudo python3 helpers/install.py
```

The script requires administrative privileges. It may install Docker and
Tailscale if they are missing, configure NFS services, initialize Swarm, and
change host directories and permissions. Connecting to Tailscale may require
browser authentication.

### 5. Answer the installer prompts

Among other information, the installer requests:

1. Company or project name.
2. MinIO and PostgreSQL administrator passwords; use unique, strong
   passwords.
3. Automatic update options for the workspace and Portal.
4. Tailscale authentication or server URL.
5. Storage partition and quota in GB (minimum 5 GB).
6. Whether to reuse an existing `datalake_data` directory. If the data belongs
   to an earlier installation, recover the original `.env` before proceeding;
   new credentials do not replace credentials in an already initialized
   PostgreSQL database.

The installer generates a JWT secret, writes `.env` with mode `0600`, and
prepares persistent directories. Store credentials in a secure vault; do not
copy them into the repository or issue tickets.

### 6. Wait for installation and verify the services

The installer downloads or builds images, initializes the database, and
waits for the Portal. Duration depends on network and hardware. When it
finishes, verify the services:

```bash
docker stack services arenalake-prod
docker service ps arenalake-prod_portal
docker service logs --tail 100 arenalake-prod_portal
sudo python3 helpers/doctor.py
```

The Portal is published on port `8088`; MinIO uses `9000`/`9001`, the Spark
UI uses `8080`, and the Traefik dashboard uses `8089`. Restrict these
endpoints with firewall rules, and do not expose the dashboard or
administrative console without appropriate authentication and TLS. The
installer also configures Tailscale Funnel; confirm that this exposure
complies with your organization's policy.

## Reinstallation and data preservation

If `.env` already exists, the installer stops to avoid replacing credentials
for an existing database or MinIO deployment; use `helpers/restart.py` to
rebuild and redeploy a configured installation. If `datalake_data` exists
without `.env`, the installer asks for confirmation before reusing the
directory without deleting it. Proceed only after recovering the previous
configuration or confirming that the data can be initialized with new
credentials. Create and verify backups before any reinstallation or upgrade.

## Manually deploy a release

On a prepared Swarm with a persistent `.env` file and available images:

```bash
docker compose --env-file .env -f deploy/compose/docker-compose.yml pull
python3 helpers/deploy_stack.py --with-registry-auth
```

See [releases and protected deployment](release-and-deploy.md) to publish
images and configure the manual production workflow. Service rollback does
not revert database changes or persisted data.
