# Telemetry agent

This FastAPI service reports host CPU, memory, operating-system, and disk
metrics. The Swarm service runs globally and reads host `/proc` and `/sys`.

Python packages are declared in `requirements.txt` and installed by the
Dockerfile. Build from the repository root with:

```bash
docker build -t arenalake-telemetry:latest apps/telemetry-agent
```

The service currently has no configurable environment variables.
