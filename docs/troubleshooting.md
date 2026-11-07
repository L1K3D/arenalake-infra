# Troubleshooting

## Services fail to start

```bash
docker info
docker stack services arenalake-prod
docker service ps arenalake-prod_portal --no-trunc
docker service logs arenalake-prod_portal
```

Check that Swarm is active, the images are available, and each required bind
mount is reachable on the node where its service is scheduled.

## Validate Compose configuration

```bash
docker compose --env-file .env -f deploy/compose/docker-compose.yml config
```

Confirm `.env` exists at the repository root and that required values such as
`DATALAKE_STORAGE_PATH`, database credentials, MinIO credentials, and
`WORKSPACE_NETWORK` are set.

## Portal cannot reach PostgreSQL or MinIO

Check the internal Swarm network and service state. The Portal should use the
service DNS names `postgres` and `minio`, not host-published ports. Keep
`DATABASE_URL` consistent with the PostgreSQL environment and use matching
MinIO access and secret keys.

## Ports are already in use

The host ports for Spark, MinIO, and the Traefik dashboard are configurable
through `.env`. Traefik's HTTP host port is currently fixed at `8088` in the
Compose file.

## Telemetry is missing

The telemetry service is deployed globally, one task per eligible Swarm node.
Check its service tasks and logs:

```bash
docker service ps arenalake-prod_telemetry-agent --no-trunc
docker service logs arenalake-prod_telemetry-agent
```
