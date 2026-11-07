# ArenaLake Portal

The Portal is the FastAPI application and user-facing control plane. Its
Dockerfile and `requirements.txt` are part of this directory's build context.

Build from the repository root with:

```bash
docker build -t arenalake-prod-portal:latest apps/portal
```

Runtime configuration is injected by the Swarm stack. See
[`docs/configuration.md`](../../docs/configuration.md).
