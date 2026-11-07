# Environment configuration example

[`.env.example`](.env.example) is the repository's non-production reference
for environment variables used by the installer, Docker Compose, and CI.
It contains placeholders, not usable production credentials.

Production installation does not require copying this file. Run
[`helpers/install.py`](../../helpers/install.py) as described in the
[deployment guide](../../docs/deployment.md); the installer generates a
protected `.env` with installation-specific credentials.

CI copies this example to the repository root temporarily to render and
validate the Compose configurations. Never commit a real `.env` file or put
production secrets in this directory.

See the [configuration reference](../../docs/configuration.md) for variable
requirements, defaults, and consumers.
