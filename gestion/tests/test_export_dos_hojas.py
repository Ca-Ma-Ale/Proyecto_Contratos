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


from io import BytesIO
from openpyxl import load_workbook
from gestion.services.exportes import (
    ColumnaExportacion,
    ExportacionVaciaError,
    generar_excel_multi_hoja,
)


COLUMNAS_SIMPLES = [
    ColumnaExportacion('Columna A', ancho=15),
    ColumnaExportacion('Columna B', ancho=15, es_numerica=True),
]


class GenerarExcelMultiHojaTest(TestCase):

    def _cargar(self, resultado: bytes):
        return load_workbook(BytesIO(resultado))

    def test_crea_dos_hojas(self):
        resultado = generar_excel_multi_hoja([
            ('Clientes', COLUMNAS_SIMPLES, [('Acme', 100)]),
            ('Proveedores', COLUMNAS_SIMPLES, [('Beta', 200)]),
        ])
        wb = self._cargar(resultado)
        self.assertEqual(wb.sheetnames, ['Clientes', 'Proveedores'])

    def test_hoja_vacia_muestra_mensaje(self):
        resultado = generar_excel_multi_hoja([
            ('Clientes', COLUMNAS_SIMPLES, [('Acme', 100)]),
            ('Proveedores', COLUMNAS_SIMPLES, []),
        ])
        wb = self._cargar(resultado)
        hoja = wb['Proveedores']
        # Fila 1 = encabezados, fila 2 = mensaje
        self.assertEqual(hoja.cell(row=2, column=1).value, 'Sin contratos registrados')

    def test_error_si_todas_vacias(self):
        with self.assertRaises(ExportacionVaciaError):
            generar_excel_multi_hoja([
                ('Clientes', COLUMNAS_SIMPLES, []),
                ('Proveedores', COLUMNAS_SIMPLES, []),
            ])

    def test_datos_escritos_correctamente(self):
        resultado = generar_excel_multi_hoja([
            ('Clientes', COLUMNAS_SIMPLES, [('Texto', 42)]),
            ('Proveedores', COLUMNAS_SIMPLES, []),
        ])
        wb = self._cargar(resultado)
        hoja = wb['Clientes']
        self.assertEqual(hoja.cell(row=1, column=1).value, 'Columna A')
        self.assertEqual(hoja.cell(row=2, column=1).value, 'Texto')
        self.assertEqual(hoja.cell(row=2, column=2).value, 42)

    def test_error_si_registro_tiene_columnas_incorrectas(self):
        with self.assertRaises(ValueError):
            generar_excel_multi_hoja([
                ('Clientes', COLUMNAS_SIMPLES, [('solo uno',)]),  # esperaba 2 valores
            ])
