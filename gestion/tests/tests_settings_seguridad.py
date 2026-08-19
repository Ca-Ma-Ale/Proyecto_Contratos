"""
Regresion de seguridad (Cyber Neo CN-005): con DEBUG=False la aplicacion no
debe arrancar con una SECRET_KEY ausente o con el valor por defecto
'django-insecure-...'.
"""
import os
import subprocess
import sys
import textwrap
import unittest


SCRIPT = textwrap.dedent(
    """
    import contratos.settings as settings
    print(settings.SECRET_KEY[:8])
    """
)


class SecretKeyObligatoriaTests(unittest.TestCase):
    def _run(self, **overrides):
        env = os.environ.copy()
        env.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", SCRIPT], capture_output=True, env=env, text=True,
        )

    def test_produccion_sin_secret_key_falla_al_iniciar(self):
        result = self._run(DEBUG="False", SECRET_KEY="")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_produccion_con_secret_key_insegura_falla_al_iniciar(self):
        result = self._run(DEBUG="False", SECRET_KEY="django-insecure-abc")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_produccion_con_secret_key_valida_arranca(self):
        result = self._run(DEBUG="False", SECRET_KEY="clave-fuerte-de-prueba-0123456789")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_desarrollo_sin_secret_key_usa_valor_por_defecto(self):
        result = self._run(DEBUG="True", SECRET_KEY="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "django-i")
