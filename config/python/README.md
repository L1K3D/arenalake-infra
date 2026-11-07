# Python development configuration

This directory holds shared Python tooling configuration:

- [`requirements-dev.txt`](requirements-dev.txt) pins the tools used for
  linting, formatting, coverage, testing support, and dependency auditing.
- [`ruff.toml`](ruff.toml) sets the Python target version, line length, and
  enabled lint rules for Ruff.

From the repository root, install the development tools and run the checks:

```bash
python -m pip install -r config/python/requirements-dev.txt
ruff check --config config/python/ruff.toml .
ruff format --config config/python/ruff.toml --check .
python -m compileall -q apps helpers tests
python -m unittest discover -s tests -v
```

The CI workflow uses the same requirements and Ruff configuration. These are
development dependencies; application runtime dependencies are declared
separately in each application's `requirements.txt`.
