# Changelog

Notable changes to ArenaLake are documented here.

## Unreleased

- Reorganized application code under `apps/`, operations tools under `helpers/`,
  and the Swarm Compose configuration under `deploy/compose/`.
- Added repository CI, security scanning, semantic-version image publishing,
  protected deployment, and modular operations documentation.
- Replaced vulnerable JWT and SSH dependency versions and added Swarm health
  checks with rollback policies.
