from django.test import TestCase
from gestion.utils_otrosi import get_valores_polizas_vigentes, _CAMPOS_POLIZAS_EXPORTACION


class CamposPolizasExportacionTest(TestCase):

    def test_campos_proveedor_rce_en_lista(self):
        campos = [campo_nuevo for campo_nuevo, _ in _CAMPOS_POLIZAS_EXPORTACION]
        self.assertIn('nuevo_rce_cobertura_danos_materiales', campos)
        self.assertIn('nuevo_rce_cobertura_perjuicios_patrimoniales', campos)

    def test_campos_proveedor_cumplimiento_en_lista(self):
        campos = [campo_nuevo for campo_nuevo, _ in _CAMPOS_POLIZAS_EXPORTACION]
        self.assertIn('nuevo_cumplimiento_amparo_cumplimiento_contrato', campos)
        self.assertIn('nuevo_cumplimiento_amparo_sanciones_incumplimiento', campos)

    def test_total_campos_polizas(self):
        # 47 originales + 12 rce_cobertura + 11 cumplimiento_amparo = 70
        self.assertEqual(len(_CAMPOS_POLIZAS_EXPORTACION), 70)
