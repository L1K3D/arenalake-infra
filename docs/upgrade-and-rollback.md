# Upgrade and rollback

## Upgrade

1. Review the change and its migration impact.
2. Back up persistent data and the root `.env` file:

   ```bash
   sudo python3 helpers/backup.py
   ```

3. Pull the intended source revision and rebuild/redeploy:

   ```bash
   sudo python3 helpers/restart.py
   ```

4. Verify Swarm service replicas, logs, Portal login, MinIO access, Spark status,
   and telemetry from each node.

The restart script stops the stack before rebuilding and redeploying local
images. Schedule downtime accordingly. Production deployments through the
release workflow use immutable image tags and Swarm rollback policies for the
Portal and telemetry services. Swarm cannot revert database contents or schema
changes.

## Rollback

1. Stop further changes and preserve logs and the failed deployment state.
2. Restore the previous application/configuration revision using version control.
3. Use the manual production deployment workflow with the prior release tag, or
   check out the prior source revision and rebuild/redeploy with
   `helpers/restart.py`.
4. Restore the database or DataLake backup only if the failed release changed
   persistent data incompatibly; restoring data can discard writes made after
   the backup.
5. Verify the services and data before reopening access.

The local installer still builds mutable `latest` tags. Production releases
publish both semantic version and commit-SHA tags; configure deployments to use
the release workflow so previous images remain addressable. Database schema
changes may not be reversible by changing code alone.
