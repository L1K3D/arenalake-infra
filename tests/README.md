# Test suite

This directory contains automated tests for repository layout, rendered
deployment configuration, Swarm stack normalization, installer safeguards, and
environment-file serialization.

## Requirements

- Python 3.11 or later.
- Development dependencies from
  [`config/python/requirements-dev.txt`](../config/python/requirements-dev.txt).
- Docker Engine with Compose v2 for validating rendered production and
  development configurations. The unit tests themselves can run without a
  Docker daemon; Compose-dependent tests are skipped unless the rendered
  production configuration is provided.

## Run the tests

From the repository root, install the development dependencies and run the
standard-library test runner:

```bash
python -m pip install -r config/python/requirements-dev.txt
python -m unittest discover -s tests -v
```

To match the coverage check used in CI, first render the production Compose
configuration and provide its path through `ARENALAKE_COMPOSE_CONFIG`:

```bash
test ! -e .env || { echo "Refusing to overwrite an existing .env file."; exit 1; }
cp config/environment/.env.example .env
compose_json="$(mktemp)"
trap 'rm -f .env "$compose_json"' EXIT
docker compose --env-file .env -f deploy/compose/docker-compose.yml config --format json > "$compose_json"
docker compose -f deploy/compose/docker-compose.dev.yml config --quiet
python helpers/deploy_stack.py --validate-only | docker stack config --compose-file - > /dev/null
export ARENALAKE_COMPOSE_CONFIG="$compose_json"
coverage run --branch --source=helpers.deploy_stack -m unittest discover -s tests -v
coverage report --fail-under=90
```

The example environment file contains placeholders for validation only. Never
use it for production or replace an existing `.env` file when following these
commands.

## Coverage scope

The CI threshold applies to `helpers.deploy_stack`, not to the entire Portal or
all project Python code. Tests that inspect build contexts and service health
checks use the rendered production Compose configuration. Other tests exercise
deployment normalization and safeguards without changing persistent data.

When modifying behavior, add or update focused tests and run the relevant
Compose validation. See the [contribution guide](../.github/CONTRIBUTING.md)
for the repository's review and pull-request process.
