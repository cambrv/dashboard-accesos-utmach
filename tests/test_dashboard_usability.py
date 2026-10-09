import ast
from pathlib import Path

import pandas as pd

from visualizations import grafico_flujo_hora, grafico_flujo_punto_acceso


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")


def _literal_assignment(nombre):
    tree = ast.parse(APP_SOURCE)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == nombre for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"No se encontró {nombre}")


def test_todas_las_secciones_estaticas_tienen_descripcion():
    descripciones = _literal_assignment("DESCRIPCIONES_SECCIONES")
    tree = ast.parse(APP_SOURCE)
    titulos = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "mostrar_seccion"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert titulos <= descripciones.keys()


def test_ranking_vehicular_usa_posiciones_legibles_y_separa_mecanismos():
    assert 'st.markdown("#### Horarios con mayor actividad vehicular")' in APP_SOURCE
    assert '"Rango": "Posición"' in APP_SOURCE
    assert 'f"{int(valor)}.º"' in APP_SOURCE
    assert '["Consolidado", "Biométrico VEH", "LPR"]' in APP_SOURCE
    assert "circulación de una sola hora o fecha" in APP_SOURCE


def test_contexto_indica_que_procede_de_filtros_aplicados():
    assert "def mostrar_contexto_resultados" in APP_SOURCE
    assert "Los valores corresponden a los filtros ya aplicados" in APP_SOURCE


def test_cambios_de_etiquetas_no_alteran_datos_de_los_graficos():
    horario = pd.DataFrame({"Hora": [6, 7], "Eventos": [10, 15], "Usuarios_Unicos": [8, 12]})
    figura_hora = grafico_flujo_hora(horario)
    assert list(figura_hora.data[0].y) == [10, 15]

    accesos = pd.DataFrame({
        "Punto de acceso": ["Vehicular por LPR 25 de Junio"],
        "Eventos": [21],
        "Porcentaje": [100.0],
        "Ingreso": ["Vehicular por LPR 25 de Junio"],
    })
    figura_acceso = grafico_flujo_punto_acceso(accesos)
    assert list(figura_acceso.data[0].x) == [21]
