from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import deploy_stack
from helpers.install import (
    build_database_url,
    check_existing_install,
    configure_storage,
)
from helpers.env_file import format_env_value, read_env_file


class ComposeConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = os.environ.get("ARENALAKE_COMPOSE_CONFIG")
        if not config_path:
            raise unittest.SkipTest(
                "Set ARENALAKE_COMPOSE_CONFIG to rendered production Compose JSON."
            )
        with Path(config_path).open(encoding="utf-8-sig") as compose_file:
            cls.config = json.load(compose_file)
        cls.services = cls.config["services"]

    def test_service_images_are_configurable(self):
        expected_images = {
            "portal": "ghcr.io/l1k3d/arenalake-infra/portal:latest",
            "workspace-builder": "ghcr.io/l1k3d/arenalake-infra/workspace:latest",
        }
        for service_name, expected_image in expected_images.items():
            with self.subTest(service=service_name):
                self.assertEqual(self.services[service_name]["image"], expected_image)

    def test_operational_layout_has_one_script_directory(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.assertTrue((repository_root / "helpers").is_dir())
        self.assertFalse((repository_root / "scripts").exists())
        self.assertFalse((repository_root / "portal-compute").exists())
        self.assertFalse((repository_root / "telemetry-agent").exists())

    def test_portal_health_check_is_present(self):
        self.assertIn("healthcheck", self.services["portal"])
        self.assertTrue(self.services["portal"]["healthcheck"]["test"])


class DeploymentConfigTests(unittest.TestCase):
    def test_database_url_percent_encodes_reserved_credentials(self):
        self.assertEqual(
            build_database_url("lake_admin", "P@ss:/word?"),
            "postgresql://lake_admin:P%40ss%3A%2Fword%3F@postgres:5432/arenalake_core",
        )

    def test_environment_values_are_quoted_for_compose(self):
        self.assertEqual(
            format_env_value("P@ss$VAR"),
            '"P@ss$$VAR"',
        )

    def test_environment_file_roundtrips_compose_special_characters(self):
        values = {
            "DBA_PASSWORD": "P@ss$VAR#'\\word",
            "BACKSLASH_APOSTROPHE": r"slash\'quote",
            "DOUBLE_QUOTE": 'contains"quote',
            "DOLLAR_SIGNS": "cash$$",
        }
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "".join(
                    f"{key}={format_env_value(value)}\n"
                    for key, value in values.items()
                ),
                encoding="utf-8",
            )

            self.assertEqual(read_env_file(env_file), values)

    def test_existing_installation_is_not_overwritten(self):
        with (
            patch("helpers.install.os.path.exists", return_value=True),
            patch("builtins.input") as prompt,
            self.assertRaises(SystemExit) as exit_info,
        ):
            check_existing_install()

        self.assertEqual(exit_info.exception.code, 1)
        prompt.assert_not_called()

    def test_normalizes_published_ports_and_removes_compose_only_values(self):
        config = {
            "name": "arenalake-infra",
            "services": {
                "minio": {
                    "entrypoint": None,
                    "ports": [{"published": "9000"}],
                }
            },
        }

        normalized = deploy_stack.normalize_stack_config(config)
        service = normalized["services"]["minio"]

        self.assertEqual(service["ports"][0]["published"], 9000)
        self.assertIsInstance(service["ports"][0]["published"], int)
        self.assertNotIn("entrypoint", service)
        self.assertNotIn("name", normalized)

    def test_rejects_non_numeric_published_ports(self):
        config = {
            "services": {
                "minio": {
                    "ports": [{"published": "9000/tcp"}],
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "must be numeric"):
            deploy_stack.normalize_stack_config(config)

    def test_normalizes_nulls_and_leaves_integer_ports_unchanged(self):
        config = {
            "services": {
                "portal": {
                    "environment": {"OPTIONAL_VALUE": None, "PORT": 8000},
                    "ports": [{"published": 8088}],
                }
            }
        }

        normalized = deploy_stack.normalize_stack_config(config)

        self.assertEqual(
            normalized["services"]["portal"]["ports"][0]["published"], 8088
        )
        self.assertEqual(
            normalized["services"]["portal"]["environment"], {"PORT": 8000}
        )

    def test_render_stack_config_runs_compose_and_normalizes_output(self):
        compose_json = json.dumps(
            {
                "name": "arenalake",
                "services": {
                    "minio": {
                        "entrypoint": None,
                        "ports": [{"published": "9000"}],
                    }
                },
            }
        )
        completed = SimpleNamespace(stdout=compose_json)

        with patch.object(
            deploy_stack.subprocess, "run", return_value=completed
        ) as run:
            config = deploy_stack.render_stack_config()

        self.assertNotIn("name", config)
        self.assertEqual(config["services"]["minio"]["ports"][0]["published"], 9000)
        self.assertEqual(
            run.call_args.args[0][0:3], ["docker", "compose", "--env-file"]
        )

    def test_main_prints_normalized_config_in_validate_mode(self):
        with (
            patch("sys.argv", ["deploy_stack.py", "--validate-only"]),
            patch.object(
                deploy_stack, "render_stack_config", return_value={"services": {}}
            ),
            redirect_stdout(io.StringIO()) as output,
        ):
            deploy_stack.main()

        self.assertEqual(output.getvalue(), '{"services": {}}\n')

    def test_main_deploys_stack_with_registry_auth_when_requested(self):
        config = {"services": {}}
        with (
            patch("sys.argv", ["deploy_stack.py", "--with-registry-auth"]),
            patch.object(deploy_stack, "render_stack_config", return_value=config),
            patch.object(deploy_stack.subprocess, "run") as run,
        ):
            deploy_stack.main()

        command = run.call_args.args[0]
        self.assertIn("--with-registry-auth", command)
        self.assertEqual(command[-1], "arenalake-prod")
        self.assertEqual(run.call_args.kwargs["input"], json.dumps(config))

    def test_main_deploys_without_registry_auth_by_default(self):
        with (
            patch("sys.argv", ["deploy_stack.py"]),
            patch.object(
                deploy_stack, "render_stack_config", return_value={"services": {}}
            ),
            patch.object(deploy_stack.subprocess, "run") as run,
        ):
            deploy_stack.main()

        self.assertNotIn("--with-registry-auth", run.call_args.args[0])

    def test_existing_storage_is_reused_without_deleting_data(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "datalake_data"
            data_path.mkdir()
            sentinel = data_path / "keep.txt"
            sentinel.write_text("persistent data", encoding="utf-8")

            with (
                patch("helpers.install.PROJECT_ROOT", directory),
                patch("builtins.input", side_effect=["y", "10"]),
            ):
                path, quota = configure_storage()

            self.assertEqual(Path(path), data_path)
            self.assertEqual(quota, 10)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "persistent data")

    def test_declining_storage_reuse_exits_without_deleting_data(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "datalake_data"
            data_path.mkdir()
            sentinel = data_path / "keep.txt"
            sentinel.write_text("persistent data", encoding="utf-8")

            with (
                patch("helpers.install.PROJECT_ROOT", directory),
                patch("builtins.input", return_value="n"),
                self.assertRaises(SystemExit),
            ):
                configure_storage()

            self.assertTrue(sentinel.is_file())


if __name__ == "__main__":
    unittest.main()
