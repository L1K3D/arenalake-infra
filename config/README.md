# Shared project configuration

This directory groups configuration files used across repository workflows:

- [`environment/.env.example`](environment/.env.example) documents expected
  deployment variables and provides non-production values for CI validation.
- [`python/requirements-dev.txt`](python/requirements-dev.txt) pins the
  repository's development and validation tools.
- [`python/ruff.toml`](python/ruff.toml) configures Python linting and
  formatting.

Production installation does not copy the example environment file. The
installer generates a protected `.env` file with installation-specific
credentials.
