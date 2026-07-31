import json
import os
import subprocess
import sys
import textwrap
import unittest


class SettingsDatabaseTests(unittest.TestCase):
    def run_wsgi_settings_module_check(self, env):
        script = textwrap.dedent(
            """
            import contratos.wsgi
            from django.conf import settings

            print(settings.SETTINGS_MODULE)
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            env=env,
            text=True,
        )

        return result.stdout.strip()

    def test_uses_mysql_when_database_name_is_configured(self):
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_NAME": "contratos_prod",
                "DATABASE_USER": "contratos_user",
                "DATABASE_PASSWORD": "secret",
                "DATABASE_HOST": "mysql",
                "DATABASE_PORT": "3306",
            }
        )

        script = textwrap.dedent(
            """
            import json
            import contratos.settings as settings

            database = settings.DATABASES["default"]
            print(json.dumps({
                "ENGINE": database.get("ENGINE"),
                "NAME": str(database.get("NAME")),
                "USER": database.get("USER"),
                "PASSWORD": database.get("PASSWORD"),
                "HOST": database.get("HOST"),
                "PORT": database.get("PORT"),
                "charset": database.get("OPTIONS", {}).get("charset"),
            }, sort_keys=True))
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            env=env,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "ENGINE": "django.db.backends.mysql",
                "NAME": "contratos_prod",
                "USER": "contratos_user",
                "PASSWORD": "secret",
                "HOST": "mysql",
                "PORT": "3306",
                "charset": "utf8mb4",
            },
        )

    def test_ssl_redirect_can_be_disabled_when_proxy_handles_https(self):
        env = os.environ.copy()
        env.update(
            {
                "DEBUG": "False",
                "SECURE_SSL_REDIRECT": "False",
            }
        )

        script = (
            "import contratos.settings as settings; "
            "print(settings.SECURE_SSL_REDIRECT)"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            env=env,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), "False")

    def test_wsgi_defaults_to_deployable_settings(self):
        env = os.environ.copy()
        env.pop("DJANGO_SETTINGS_MODULE", None)
        env["SECRET_KEY"] = "test-secret-key-for-wsgi-defaults"

        self.assertEqual(self.run_wsgi_settings_module_check(env), "contratos.settings")

    def test_wsgi_ignores_blank_settings_module(self):
        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = ""
        env["SECRET_KEY"] = "test-secret-key-for-wsgi-defaults"

        self.assertEqual(self.run_wsgi_settings_module_check(env), "contratos.settings")
