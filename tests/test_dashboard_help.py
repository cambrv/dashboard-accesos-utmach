from pathlib import Path

from streamlit.testing.v1 import AppTest

import dashboard_help


ROOT = Path(__file__).resolve().parents[1]


def test_guia_usa_una_imagen_local_con_ruta_estable():
    assert dashboard_help.RESOURCES_DIR == ROOT / "resources"
    assert dashboard_help.GUIA_IMAGEN == ROOT / "resources" / "GUIA.png"
    assert dashboard_help.GUIA_IMAGEN.is_file()

    fuente = (ROOT / "dashboard_help.py").read_text(encoding="utf-8")
    assert "@st.dialog" in fuente
    assert fuente.count("st.image(") == 1
    assert 'width="stretch"' in fuente
    assert "base64" not in fuente.lower()
    assert "st.tabs" not in fuente
    assert "FERROVIARIA.png" not in fuente
    assert "PEATONAL.png" not in fuente
    assert "VEHICULAR.png" not in fuente


def test_boton_abre_modal_con_una_sola_imagen_y_permite_cerrarlo():
    fuente = f'''
import dashboard_help
guia_original = dashboard_help.GUIA_IMAGEN
dashboard_help.GUIA_IMAGEN = dashboard_help.RESOURCES_DIR / "FERROVIARIA.png"
dashboard_help.mostrar_boton_guia_sidebar()
dashboard_help.GUIA_IMAGEN = guia_original
'''
    app = AppTest.from_string(fuente).run(timeout=20)
    assert not app.exception
    assert len(app.get("image")) == 0
    assert app.button(key="abrir_guia_interpretacion").label == "Guía de interpretación"

    app.button(key="abrir_guia_interpretacion").click().run(timeout=20)
    assert not app.exception
    assert len(app.get("image")) == 1
    assert app.button(key="cerrar_guia_interpretacion").label == "Cerrar"

    app.button(key="cerrar_guia_interpretacion").click().run(timeout=20)
    assert not app.exception
    assert len(app.get("image")) == 0


def test_modal_informa_si_la_imagen_futura_aun_no_existe():
    app = AppTest.from_string(
        "import dashboard_help\n"
        "guia_original = dashboard_help.GUIA_IMAGEN\n"
        "dashboard_help.GUIA_IMAGEN = dashboard_help.RESOURCES_DIR / 'ARCHIVO_NO_EXISTE.png'\n"
        "dashboard_help.mostrar_boton_guia_sidebar()\n"
        "dashboard_help.GUIA_IMAGEN = guia_original"
    ).run(timeout=20)
    app.button(key="abrir_guia_interpretacion").click().run(timeout=20)
    assert not app.exception
    assert len(app.get("image")) == 0
    assert "GUIA.png" in "\n".join(item.value for item in app.info)


def test_imagen_de_guia_no_es_ignorada_por_git():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "!resources/GUIA.png" in gitignore
