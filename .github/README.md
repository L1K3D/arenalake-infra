# GitHub Repository Automation

This directory contains the GitHub Actions workflows and Dependabot
configuration used to validate, secure, release, and deploy ArenaLake. The
repository keeps workflow and contribution guidance here, application and
deployment documentation in `docs/`, and shared project configuration in
`config/`.

## Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| [`ci.yml`](workflows/ci.yml) | Pull requests and pushes to `main`; reusable by other workflows | Validates Python, YAML, Compose, and Dockerfiles; runs tests and coverage; audits dependencies; builds and smoke-tests images; scans images for high and critical vulnerabilities. |
| [`security.yml`](workflows/security.yml) | Pull requests and pushes to `main`, weekly schedule, manual dispatch; reusable by release workflow | Scans repository history for committed secrets with Gitleaks and analyzes Python code with CodeQL. |
| [`release.yml`](workflows/release.yml) | Push of a `v*` tag | Verifies that the tag matches the semantic version in the `- Version:` field of `version.txt`, runs CI and security analysis for that tag, publishes versioned container images with provenance and an SBOM, and creates a GitHub Release. |
| [`deploy-production.yml`](workflows/deploy-production.yml) | Manual dispatch with a release version | Deploys a validated release to the protected `production` environment over SSH, pulls immutable images, deploys the Swarm stack, and checks service health. |

Production deployment requires a GitHub environment named `production`, reviewer
protection, and the SSH secrets documented in
[`docs/release-and-deploy.md`](../docs/release-and-deploy.md). Workflow files
alone do not enable branch protection or environment approval rules; configure
those settings in the repository.

## Dependabot

[`dependabot.yml`](dependabot.yml) checks weekly for updates to GitHub Actions,
Python dependencies, and Docker images used by the Portal, telemetry agent,
shared Dockerfiles, and deployment Compose configuration.

## Permissions and secret handling

Workflows declare the minimum GitHub token permissions needed for their jobs.
Production credentials belong in the protected GitHub environment, not in
workflow files or repository variables. Never add production secrets, private
keys, or `.env` files to this directory.
