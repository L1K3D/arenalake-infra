# Applications

Application source and container build contexts are kept under this directory:

- [`portal/`](portal/): FastAPI control plane, UI, and workspace orchestration
- [`telemetry-agent/`](telemetry-agent/): per-node host metrics service

The images are built by the pull-request CI workflow and referenced by
[`deploy/compose/docker-compose.yml`](../deploy/compose/docker-compose.yml).
