from datetime import date

import pandas as pd

from dashboard_filters import (
    MECANISMO_BIOMETRICO,
    MECANISMO_LPR,
    aplicar_filtros_integrales,
    mecanismo_incluido,
)


def _fuentes_sinteticas():
    bio = pd.DataFrame(
        {
            "Fecha": [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 2)],
            "Resultado": ["Exitoso", "Denegado", "Exitoso"],
            "Ingreso": ["A", "B", "C"],
            "Tipo_Usuario": ["ESTUDIANTE", "DOCENTE", "ESTUDIANTE"],
            "Ubicacion_Ingreso": ["25 de Junio", "Ferroviaria", "25 de Junio"],
        }
    )
    lpr = pd.DataFrame(
        {
            "Fecha": [date(2026, 1, 1), date(2026, 1, 2)],
            "Ubicacion_Ingreso": ["25 de Junio", "Ferroviaria"],
        }
    )
    return bio, lpr


def test_filtros_integrales_aplican_fecha_y_ubicacion_a_ambas_fuentes():
    bio, lpr = _fuentes_sinteticas()
    filtros = {
        "rango_fechas": (date(2026, 1, 1), date(2026, 1, 2)),
        "resultados": [],
        "ingresos": [],
        "tipos_usuario": [],
        "ubicaciones": ["25 de Junio"],
        "mecanismos": [],
    }

    bio_filtrado, lpr_filtrado = aplicar_filtros_integrales(bio, lpr, filtros)

    assert len(bio_filtrado) == 2
    assert len(lpr_filtrado) == 1
    assert set(bio_filtrado["Ubicacion_Ingreso"]) == {"25 de Junio"}
    assert set(lpr_filtrado["Ubicacion_Ingreso"]) == {"25 de Junio"}


def test_filtros_biometricos_no_eliminan_lpr():
    bio, lpr = _fuentes_sinteticas()
    filtros = {
        "rango_fechas": (),
        "resultados": ["Denegado"],
        "ingresos": [],
        "tipos_usuario": ["DOCENTE"],
        "ubicaciones": [],
        "mecanismos": [],
    }

    bio_filtrado, lpr_filtrado = aplicar_filtros_integrales(bio, lpr, filtros)

    assert len(bio_filtrado) == 1
    assert len(lpr_filtrado) == len(lpr)


def test_mecanismo_vacio_equivale_a_todas_las_fuentes():
    filtros = {"mecanismos": []}

    assert mecanismo_incluido(filtros, MECANISMO_BIOMETRICO)
    assert mecanismo_incluido(filtros, MECANISMO_LPR)


def test_mecanismo_confirmado_se_aplica_solo_al_consolidado():
    filtros = {"mecanismos": [MECANISMO_LPR]}

    assert not mecanismo_incluido(filtros, MECANISMO_BIOMETRICO)
    assert mecanismo_incluido(filtros, MECANISMO_LPR)
