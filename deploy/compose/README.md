# Docker Compose / Swarm stack

`docker-compose.yml` is the canonical service definition. Its relative build
contexts are resolved from this directory. The `.env` file remains at the
repository root; pass it explicitly when invoking Docker Compose:

```bash
docker compose --env-file .env -f deploy/compose/docker-compose.yml config
```

The stack is deployed with `docker stack deploy`; build locally declared images
first because Swarm deployment does not build images.
