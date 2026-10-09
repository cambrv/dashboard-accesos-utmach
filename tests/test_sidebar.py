from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("nombre", "rol", "etiqueta"),
    [
        ("Usuario administrativo", "admin", "Rol: Administrador"),
        ("Usuario de consulta", "viewer", "Rol: Visor"),
    ],
)
def test_sidebar_muestra_nombre_rol_y_logout_reales(nombre, rol, etiqueta):
    fuente = f'''
import streamlit as st
from app import mostrar_acceso_guia_sidebar, mostrar_encabezado_sidebar, mostrar_perfil_sidebar

class AutenticadorPrueba:
    def logout(self, label, location, **kwargs):
        st.session_state["ubicacion_logout"] = location
        st.sidebar.button(label, key="logout_prueba")

st.session_state["name"] = {nombre!r}
st.session_state["rol"] = {rol!r}
mostrar_encabezado_sidebar()
mostrar_acceso_guia_sidebar()
mostrar_perfil_sidebar(AutenticadorPrueba())
'''
    app = AppTest.from_string(fuente).run(timeout=20)
    assert not app.exception
    contenido = "\n".join(
        elemento.value
        for coleccion in (app.markdown, app.caption, app.info)
        for elemento in coleccion
    )
    assert "Accesos UTMACH" in contenido
    assert "Panel institucional" in contenido
    assert "ESPACIO DE TRABAJO" in contenido
    assert nombre in contenido
    assert etiqueta in contenido
    assert app.session_state["ubicacion_logout"] == "sidebar"
    assert app.sidebar.button(key="logout_prueba").label == "Cerrar sesión"
    assert not [button for button in app.main.button if button.label == "Cerrar sesión"]


def test_sidebar_muestra_un_unico_boton_para_la_guia():
    app = AppTest.from_string(
        "from app import mostrar_acceso_guia_sidebar\n"
        "mostrar_acceso_guia_sidebar()"
    ).run(timeout=20)
    assert not app.exception
    botones = [boton for boton in app.button if boton.label == "Guía de interpretación"]
    assert len(botones) == 1
    assert len(app.radio) == 0


def test_sidebar_oculta_selector_redundante_y_conserva_enrutador():
    bloque_inicio = APP_SOURCE.index("def main(")
    bloque_fin = APP_SOURCE.index("def app_protegida():", bloque_inicio)
    bloque = APP_SOURCE[bloque_inicio:bloque_fin]
    assert 'modo = "Todos los Eventos"' in bloque
    assert "selector_modo_analisis" not in bloque
    assert "renderizar_guia" not in bloque
    assert "ejecutar_modo_todos(" in bloque


def test_uploaders_se_renderizan_solo_en_el_area_principal():
    app = AppTest.from_string(
        "from app import ejecutar_modo_todos\n"
        "ejecutar_modo_todos()"
    ).run(timeout=20)
    assert not app.exception
    assert len(app.main.get("file_uploader")) == 2
    assert len(app.sidebar.get("file_uploader")) == 0


def test_filtros_prioritarios_preceden_al_expander_avanzado():
    inicio = APP_SOURCE.index("# SIDEBAR: los widgets son un borrador")
    fin = APP_SOURCE.index('filtros_aplicados = st.session_state["filtros_aplicados_todos"]', inicio)
    bloque = APP_SOURCE[inicio:fin]
    assert bloque.index('"Rango de fechas"') < bloque.index('"Ubicación"')
    assert bloque.index('"Ubicación"') < bloque.index('"Mecanismo de identificación"')
    assert bloque.index('"Mecanismo de identificación"') < bloque.index(
        '"Filtros avanzados"'
    )
    assert bloque.index('"Filtros avanzados"') < bloque.index('"Aplicar filtros"')


def test_sidebar_se_construye_antes_del_panel_y_usa_logout_real():
    bloque = APP_SOURCE[APP_SOURCE.index('if st.session_state["authentication_status"]:'):]
    assert bloque.index("main()") < bloque.index("mostrar_perfil_sidebar(authenticator)")
    assert bloque.index("mostrar_selector_tema_sidebar()") < bloque.index(
        "mostrar_perfil_sidebar(authenticator)"
    )
    perfil = APP_SOURCE[
        APP_SOURCE.index("def mostrar_perfil_sidebar"):
        APP_SOURCE.index("def restablecer_widgets")
    ]
    assert '"sidebar"' in perfil
    assert "callback=limpiar_estado_datos_sesion" in perfil


def test_css_original_se_inyecta_y_conserva_tarjetas_e_iconos():
    bloque = APP_SOURCE[
        APP_SOURCE.index("def configurar_tema_interfaz"):
        APP_SOURCE.index("def _etiqueta_rol")
    ]
    assert "aplicar_estilos(obtener_tema_actual())" in bloque

    from styles import _css_para_tema

    for tema in ("Claro", "Oscuro"):
        css = _css_para_tema(tema)
        assert ".metric-card" in css
        assert "border-radius: 8px" in css
        assert "font-size: 1.75rem" in css
        assert ".metric-card .metric-icon" in css
        assert ".mobility-heading__value" in css
        assert ".mobility-card--blue .mobility-card__value" in css
        assert ".peak-card--green" in css
        assert "font-family: 'Material Symbols Rounded' !important" in css


def test_logout_limpia_datos_institucionales_sin_tocar_estado_auth():
    fuente = '''
import streamlit as st
from app import limpiar_estado_datos_sesion
st.session_state.setdefault("authentication_status", True)
st.session_state.setdefault("username", "usuario")
st.session_state.setdefault("_biometrico_preparado", {"df": "datos"})
st.session_state.setdefault("_lpr_preparado", {"df": "datos"})
st.session_state.setdefault("filt_ubicacion_todos", ["Ferroviaria"])
st.session_state.setdefault("filtros_aplicados_todos", {"ubicaciones": ["Ferroviaria"]})
if st.button("Ejecutar cierre", key="probar_limpieza"):
    limpiar_estado_datos_sesion()
'''
    app = AppTest.from_string(fuente).run(timeout=20)
    app.button(key="probar_limpieza").click().run(timeout=20)
    assert not app.exception
    assert app.session_state["authentication_status"] is True
    assert app.session_state["username"] == "usuario"
    for clave in (
        "_biometrico_preparado",
        "_lpr_preparado",
        "filt_ubicacion_todos",
        "filtros_aplicados_todos",
    ):
        assert clave not in app.session_state
