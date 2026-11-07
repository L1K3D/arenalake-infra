# Security notes

- Never commit `.env`, production credentials, JWT signing keys, tokens, or
  private keys. Use unique, high-entropy values and restrict access to backups.
- Do not expose the Docker API socket or socket proxy to untrusted networks.
  The Portal can provision containers through the proxy, so treat it as a
  privileged control plane.
- The telemetry agent runs privileged and mounts host `/sys` and `/proc`.
  Restrict the Swarm and review whether this access is required in your
  deployment.
- Limit published service ports with firewall rules. Restrict or disable the
  Traefik dashboard and MinIO console for public-facing environments.
- Use TLS and an authenticated edge configuration before exposing the Portal
  outside a trusted network.
- Review image tags, dependency updates, and container permissions regularly.
  CI builds and syntax checks do not replace a security review or runtime
  hardening.
