# Release and production deployment

## Release process

1. Update the `- Version:` field in `version.txt` with the semantic version,
   without a leading `v` (for example `- Version: 1.2.3`). Keep the release tag
   in sync as `v1.2.3`.
2. Move the relevant entries in [`CHANGELOG.md`](CHANGELOG.md) into the release
   notes and merge the change to `main`.
3. Create and push the matching tag:

   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

4. `release.yml` validates the tag/version and re-runs both CI and security
   workflows against that exact tag before it builds the Portal, telemetry,
   workspace, and Spark worker images, then
   publishes version and commit-SHA tags with BuildKit provenance and an SBOM.
   `latest` is a convenience tag only. The workflow also creates GitHub release
   notes.
5. In GitHub Packages, enable immutable tags where available. Deployments use
   semantic version tags; do not overwrite a released version tag.

The former branch-triggered workspace-only publication workflow was removed.
Image publication now happens only from a validated semantic-version tag.
The release workflows read the semantic version from the `- Version:` field
in `version.txt`; the file may retain its other project metadata. The version
must match the tag after removing its leading `v`.

## Configure protected production deployment

Before using `.github/workflows/deploy-production.yml`:

1. In repository Settings → Environments, create `production`, require one or
   more reviewers, and restrict deployment branches/tags to approved releases.
2. Add these environment secrets:
   - `PRODUCTION_SSH_HOST`: DNS name or IP of the Swarm manager
   - `PRODUCTION_SSH_USER`: dedicated deployment account with Docker access
   - `PRODUCTION_SSH_PRIVATE_KEY`: private key for that account
   - `PRODUCTION_SSH_KNOWN_HOSTS`: pre-verified host-key entry (do not use
     unauthenticated `ssh-keyscan` at deploy time)
   - `PRODUCTION_DEPLOY_PATH`: absolute path for release directories and the
     existing root `.env`
3. On the manager, prepare the deployment directory, the root `.env` with
   production credentials and shared storage settings, and Docker Swarm. Grant
   the deployment account only the access required to deploy the stack and pull
   the GHCR images.
4. Ensure the GHCR packages are readable by the deployment credential. For
   private packages, the workflow uses its repository-scoped `GITHUB_TOKEN`;
   configure package access so that token can read them.
5. Manually run the workflow with an existing `vX.Y.Z` release tag. The workflow
   waits for the environment approval, transfers the exact tagged source into a
   versioned release directory, uses the manager's root `.env`, pulls immutable
   images, deploys to Swarm, and checks Portal and telemetry health.

The production workflow serializes deployments. It does not expose a general
remote shell input: version, host, user, and deployment path are validated.
Keep the deployment host's `.env`, persistent storage, and backups outside
release directories. Make and verify a data backup before starting a release;
application rollback cannot reverse database schema or user data changes.

## Security gates

- CI runs Python lint/format checks, syntax and repository tests, Compose and
  Dockerfile validation, dependency auditing, builds all local Dockerfiles, and
  scans resulting images for high/critical vulnerabilities.
- `security.yml` scans repository history for secrets and runs CodeQL for
  Python on pull requests, pushes to `main`, and weekly.
- Dependabot checks GitHub Actions, Python dependencies, and Docker base/service
  images weekly.
- Set branch protection on `main` to require CI and security checks before
  merging. Configure required environment reviewers separately; a workflow
  declaration alone does not turn on GitHub environment protection.
