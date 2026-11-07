import argparse
import json
from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = Path("deploy") / "compose" / "docker-compose.yml"
STACK_NAME = "arenalake-prod"


def remove_null_values(value):
    if isinstance(value, dict):
        return {
            key: remove_null_values(nested_value)
            for key, nested_value in value.items()
            if nested_value is not None
        }
    if isinstance(value, list):
        return [remove_null_values(item) for item in value]
    return value


def normalize_stack_config(config):
    config = remove_null_values(config)
    config.pop("name", None)
    for service_name, service in config.get("services", {}).items():
        for port in service.get("ports", []):
            published = port.get("published")
            if isinstance(published, str):
                if not published.isdecimal():
                    raise ValueError(
                        f"Published port for service {service_name!r} "
                        f"must be numeric, got {published!r}"
                    )
                port["published"] = int(published)
    return config


def render_stack_config():
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env",
            "-f",
            str(COMPOSE_FILE),
            "config",
            "--format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return normalize_stack_config(json.loads(result.stdout))


def main():
    parser = argparse.ArgumentParser(
        description="Render and deploy the ArenaLake Swarm stack."
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Print normalized stack configuration without deploying it.",
    )
    parser.add_argument(
        "--with-registry-auth",
        action="store_true",
        help="Forward the current registry credentials to Swarm agents.",
    )
    args = parser.parse_args()
    config = render_stack_config()

    if args.validate_only:
        print(json.dumps(config))
        return

    command = ["docker", "stack", "deploy", "--compose-file", "-"]
    if args.with_registry_auth:
        command.append("--with-registry-auth")
    command.append(STACK_NAME)
    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        input=json.dumps(config),
        text=True,
        check=True,
    )


if __name__ == "__main__":
    main()
