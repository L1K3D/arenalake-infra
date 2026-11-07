# Contributing

Thank you for considering a contribution to ArenaLake. The project is
experimental; changes may affect interfaces or deployment requirements.
Please open an issue before making substantial changes, and never include
secrets, production data, or `.env` files.

## Local development environment

To run the integrated application, use the development Compose configuration:

```bash
docker compose -f deploy/compose/docker-compose.dev.yml up -d --build
```

To run Python linting, formatting, and tests:

```bash
python -m venv .venv
# Linux/macOS: . .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r config/python/requirements-dev.txt
ruff check --config config/python/ruff.toml .
ruff format --config config/python/ruff.toml --check .
coverage run --branch --source=helpers.deploy_stack -m unittest discover -s tests -v
coverage report
```

Before submitting changes to Compose or deployment configuration, validate
them in an available Docker environment. Container builds and tests require
the Docker daemon.

## Pull Requests

1. Create a branch from `main` and keep each pull request focused.
2. Describe the problem, solution, operational changes, and any compatibility
   or migration impact.
3. Update directly related guides and applicable tests.
4. Run Ruff, tests, and relevant validations; report any checks you could not
   run in the pull request.
5. Do not include credentials, keys, user data, built images, or automated
   dependency changes without justification.
6. Wait for CI and review. Never use a production deployment to validate a
   pull request.

Contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
Because the repository does not declare a license, a contribution must not be
interpreted as granting permission to use or redistribute the project.
