# ArenaLake documentation

This directory is the documentation index for ArenaLake. It brings together
the system's architecture, configuration, deployment, operation, security,
release, and maintenance guidance. The repository is experimental; follow the
deployment and security caveats before using it beyond local evaluation.

## Recommended reading paths

### New users and evaluators

1. Start with the [repository README](../README.md) for the project overview
   and local quickstart.
2. Read [Architecture](architecture.md) to understand the services, their
   responsibilities, and data persistence.
3. Review [Configuration](configuration.md) and the
   [environment example](../config/environment/README.md) before changing
   environment variables.
4. For a production deployment, follow [Deployment](deployment.md) in order.

### Operators

1. Follow the [Deployment guide](deployment.md) before initial installation.
2. Use [Operations](operations.md) for maintenance, backups, and administrative
   commands.
3. Consult [Troubleshooting](troubleshooting.md) when a service or deployment
   does not behave as expected.
4. Read [Upgrade and rollback](upgrade-and-rollback.md) before changing a
   running installation.
5. Review [Security notes](security.md) when configuring access or exposing
   services.

### Maintainers and release managers

1. Read the [contribution guide](../.github/CONTRIBUTING.md) and
   [Code of Conduct](../.github/CODE_OF_CONDUCT.md).
2. Review [Release and production deployment](release-and-deploy.md) before
   publishing images or deploying a release.
3. Update the [changelog](CHANGELOG.md) with notable changes.
4. Consult the [GitHub automation guide](../.github/README.md) for CI,
   security, Dependabot, release, and protected-deployment workflows.
5. Use the [test suite guide](../tests/README.md) and
   [Python tooling guide](../config/python/README.md) when validating changes.

## System and configuration

| Document | What it covers |
|---|---|
| [Architecture](architecture.md) | Components, service responsibilities, network relationships, and persistent data. |
| [Configuration](configuration.md) | Environment variables, required values, defaults, and configuration consumers. |
| [Environment example guide](../config/environment/README.md) | Purpose and safe use of the placeholder `.env.example` file. |

## Deployment and operations

| Document | What it covers |
|---|---|
| [Deployment](deployment.md) | Host prerequisites, initial installation, installer prompts, validation, and data preservation. |
| [Operations](operations.md) | Operational helper commands, backups, and routine maintenance. |
| [Upgrade and rollback](upgrade-and-rollback.md) | Safe upgrade and rollback procedures, including persistent-data limitations. |
| [Troubleshooting](troubleshooting.md) | Diagnostic commands and common service, configuration, networking, and port issues. |
| [Security notes](security.md) | Secrets, Docker API exposure, privileged telemetry, network boundaries, and hardening considerations. |

## Releases and project history

| Document | What it covers |
|---|---|
| [Release and production deployment](release-and-deploy.md) | Semantic-version releases, container publishing, GitHub environment protection, and production deployment setup. |
| [Changelog](CHANGELOG.md) | Notable project changes and release history. |

## Other repository documentation

The following READMEs describe the scope and contents of their respective
directories. They are part of the project documentation and are linked here
for a complete navigation map.

| Document | Directory or topic |
|---|---|
| [Repository README](../README.md) | Project overview, quickstart, architecture summary, contribution entry point, and license status. |
| [GitHub automation](../.github/README.md) | GitHub Actions, Dependabot, workflow permissions, and production secrets. |
| [Contribution guide](../.github/CONTRIBUTING.md) | Local development setup, checks, and pull-request expectations. |
| [Code of Conduct](../.github/CODE_OF_CONDUCT.md) | Community expectations and enforcement. |
| [Applications](../apps/README.md) | Portal and telemetry-agent application layout. |
| [Portal](../apps/portal/README.md) | Portal application purpose and image build context. |
| [Telemetry agent](../apps/telemetry-agent/README.md) | Host-metrics service, runtime behavior, and image build context. |
| [Shared configuration](../config/README.md) | Overview of environment and Python development configuration. |
| [Python development configuration](../config/python/README.md) | Development dependencies, Ruff settings, and local validation commands. |
| [Deployment directory](../deploy/README.md) | Deployment definitions and configuration layout. |
| [Compose and Swarm stack](../deploy/compose/README.md) | Canonical stack definition, environment file location, and deployment command. |
| [Traefik configuration](../deploy/traefik/README.md) | Standalone static configuration and its distinction from the production stack. |
| [Docker images](../docker/README.md) | Shared workspace and Spark-worker image build contexts. |
| [Operational helpers](../helpers/README.md) | Installation, maintenance, backup, and diagnostic scripts. |
| [Test suite](../tests/README.md) | Test scope, prerequisites, execution, and coverage threshold. |

## Important limitations

- `.env.example` is a documentation and CI fixture; production credentials
  are generated by the installer and must not be committed.
- Swarm rollback can revert service versions but cannot undo database or
  persistent-data changes.
- CI and automated scans improve consistency but do not constitute an
  independent security audit or guarantee a secure deployment.
- The project currently has no declared license. See the repository
  [README](../README.md#license) before reusing or redistributing code.
