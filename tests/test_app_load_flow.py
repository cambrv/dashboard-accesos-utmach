from io import BytesIO

import pandas as pd
from streamlit.testing.v1 import AppTest

import app as app_module


EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _excel_bytes(df: pd.DataFrame, *, startrow: int = 0) -> bytes:
    output = BytesIO()
    df.to_excel(output, index=False, startrow=startrow, engine="openpyxl")
    return output.getvalue()


def test_prepared_data_survives_guide_modal_filters_and_theme_without_reload(monkeypatch):
    biometric = pd.DataFrame(
        {
            "Hora": pd.to_datetime(["2026-09-15 08:00", "2026-09-16 17:10"]),
            "Punto de acceso": ["25 JUNIO ING VEH 1", "FERROV SAL VEH 1"],
            "Device Name": ["BIO 1", "BIO 2"],
            "Tipo de evento": ["Autenticado", "Denegado"],
            "Nombre": ["Persona", "Persona"],
            "Apellido": ["Prueba", "Prueba"],
            "Departamento": ["UNIDAD/ESTUDIANTE", "UNIDAD/ESTUDIANTE"],
        }
    )
    lpr = pd.DataFrame(
        {
            "Número de matrícula": ["TEST001", "TEST002"],
            "Hora": pd.to_datetime(["2026-09-15 08:05", "2026-09-16 17:15"]),
            "Cámara": ["25 JUNIO ING VEH 1", "FERROV SAL VEH 1"],
            "Lista de vehículos": ["PRUEBA", "PRUEBA"],
            "Propietario del vehículo": ["Prueba", "Prueba"],
        }
    )
    lecturas = {"biometrico": 0, "lpr": 0}
    lector_biometrico = app_module.cargar_excel_todos
    lector_lpr = app_module.cargar_excel_lpr

    def contar_biometrico(*args, **kwargs):
        lecturas["biometrico"] += 1
        return lector_biometrico(*args, **kwargs)

    def contar_lpr(*args, **kwargs):
        lecturas["lpr"] += 1
        return lector_lpr(*args, **kwargs)

    monkeypatch.setattr(app_module, "cargar_excel_todos", contar_biometrico)
    monkeypatch.setattr(app_module, "cargar_excel_lpr", contar_lpr)

    source = """
from app import (
    configurar_tema_interfaz,
    mostrar_acceso_guia_sidebar,
    _guardar_borrador_filtros_todos,
    main,
)
import dashboard_help
configurar_tema_interfaz()
mostrar_acceso_guia_sidebar()
_guardar_borrador_filtros_todos()
main()
"""
    app = AppTest.from_string(source, default_timeout=60).run()
    uploaders = app.get("file_uploader")
    uploaders[0].set_value(("biometrico.xlsx", _excel_bytes(biometric), EXCEL_MIME))
    uploaders[1].set_value(("lpr.xlsx", _excel_bytes(lpr, startrow=6), EXCEL_MIME))
    app.run(timeout=60)

    assert not app.exception
    assert not app.get("progress")
    assert app.get("status")[0].state == "complete"
    assert "_biometrico_preparado" in app.session_state
    assert "_lpr_preparado" in app.session_state
    assert lecturas == {"biometrico": 1, "lpr": 1}

    app.multiselect(key="filt_ubicacion_todos").set_value(["25 de Junio"])
    next(button for button in app.button if button.label == "Aplicar filtros").click()
    app.run(timeout=60)

    assert not app.exception
    assert not app.get("progress")
    assert app.session_state["filtros_aplicados_todos"]["ubicaciones"] == [
        "25 de Junio"
    ]
    analitica_id = id(app.session_state["_analitica_integral"])

    app.button(key="abrir_guia_interpretacion").click().run(timeout=60)

    assert not app.exception
    assert len(app.get("image")) == 1
    assert not app.get("progress")
    assert lecturas == {"biometrico": 1, "lpr": 1}
    assert app.session_state["filtros_aplicados_todos"]["ubicaciones"] == [
        "25 de Junio"
    ]

    app.button(key="cerrar_guia_interpretacion").click().run(timeout=60)

    assert not app.exception
    assert len(app.get("image")) == 0
    assert not app.get("progress")
    assert lecturas == {"biometrico": 1, "lpr": 1}
    assert id(app.session_state["_analitica_integral"]) == analitica_id
    assert app.multiselect(key="filt_ubicacion_todos").value == ["25 de Junio"]
    assert app.session_state["filtros_aplicados_todos"]["ubicaciones"] == [
        "25 de Junio"
    ]

    app.session_state["tema_app"] = "Oscuro"
    app.run(timeout=60)

    assert not app.exception
    assert not app.get("progress")
    assert app.session_state["tema_app"] == "Oscuro"
    assert app.session_state["filtros_aplicados_todos"]["ubicaciones"] == [
        "25 de Junio"
    ]
    assert "_biometrico_preparado" in app.session_state
    assert "_lpr_preparado" in app.session_state
    assert lecturas == {"biometrico": 1, "lpr": 1}
