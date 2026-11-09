# Traefik configuration

This directory contains
[`traefik.yml`](traefik.yml), a standalone Traefik static-configuration
reference for local experimentation and future configuration work.

## Production stack behavior

The production Swarm stack does **not** mount or load this file. Traefik's
static options are currently supplied as command-line arguments in
[`deploy/compose/docker-compose.yml`](../compose/docker-compose.yml). That
stack disables the insecure dashboard API, enables the Docker Swarm provider,
and publishes the Portal through the `web` entry point.

Keep this distinction in mind when changing Traefik settings: editing
`traefik.yml` alone does not change the production deployment. Update and
validate the Compose service definition when changing production behavior.

The standalone configuration currently enables an insecure dashboard and
connects directly to the Docker socket. Treat it as a development/reference
configuration only; do not expose it to untrusted networks or use it as-is in
production. Review the [security notes](../../docs/security.md) and
[deployment guide](../../docs/deployment.md) before exposing any endpoint.
