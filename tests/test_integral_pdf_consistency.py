import pandas as pd

import all_events_statistics_calc as ats
import lpr_statistics_calc as lprs
from all_events_pdf_report import (
    CONTENT_WIDTH,
    _anonimizar_matricula,
    _tabla_estadistica,
    _texto_espanol,
    exportar_reporte_integral_pdf,
)


def test_matriculas_se_anonimizan_para_el_pdf():
    assert _anonimizar_matricula("ABC-1234") == "A*****4"
    assert _anonimizar_matricula("X1") == "***"


def test_fechas_del_pdf_no_dependan_del_locale_del_servidor():
    assert _texto_espanol("Tuesday 15/09") == "martes 15/09"
    assert _texto_espanol("Monday, September 7") == "lunes, septiembre 7"


def test_tablas_editoriales_respetan_el_ancho_util():
    tabla = _tabla_estadistica(
        [["Ubicación", "Eventos"], ["Acceso con un nombre deliberadamente largo", "123"]],
        [3, 1],
        columnas_numericas=(1,),
    )
    assert sum(tabla._colWidths) <= CONTENT_WIDTH + 0.01
    assert tabla.repeatRows == 1


def test_integral_pdf_uses_shared_lpr_metrics_and_generates_bytes():
    hora = pd.to_datetime(
        ["2026-09-07 06:01", "2026-09-07 06:01", "2026-09-08 06:02", "2026-09-08 07:00"]
    )
    lpr = pd.DataFrame(
        {
            "Fecha": hora.date,
            "Hora": hora,
            "Hora_Dia": hora.hour,
            "Dia_Semana": ["Lunes", "Lunes", "Martes", "Martes"],
            "Matricula": ["AAA001", "BBB002", "AAA001", "CCC003"],
            "Direccion": ["ENTRADA", "SALIDA", "ENTRADA", "SALIDA"],
            "Camara": ["25 JUNIO ING VEH 1", "25 JUNIO SAL VEH 1", "FERROV ING VEH 1", "FERROV SAL VEH 1"],
            "Punto_Acceso": ["25 de Junio", "25 de Junio", "Ferroviaria", "Ferroviaria"],
            "Ubicacion_Ingreso": ["25 de Junio", "25 de Junio", "Ferroviaria", "Ferroviaria"],
            "Sitio": ["25 de Junio", "25 de Junio", "Ferroviaria", "Ferroviaria"],
            "Propietario": ["Sin propietario"] * 4,
        }
    )
    tasas = ats.calcular_tasas_generales(pd.DataFrame(columns=["Resultado"]))
    stats_lpr = lprs.calcular_estadisticas_generales_lpr(lpr, pd.DataFrame(), lpr)
    huella = lprs.generar_huella_movilidad(pd.DataFrame(), lpr)

    pdf = exportar_reporte_integral_pdf(
        df=lpr,
        tasas=tasas,
        stats_base={},
        stats_nuevas={},
        conclusiones=[],
        calidad={},
        stats_gen_lpr=stats_lpr,
        df_lpr_f=lpr,
        conclusiones_lpr=lprs.generar_conclusiones_lpr(stats_lpr, lpr),
        huella_dashboard=huella,
    )

    contenido = pdf.getvalue()
    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 10_000

