
"""Guía visual de uso e interpretación del dashboard."""

from pathlib import Path

import streamlit as st


RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
GUIA_IMAGEN = RESOURCES_DIR / "GUIA.png"


@st.dialog("Guía de interpretación", width="large")
def mostrar_dialogo_guia() -> None:
    """Muestra la guía sin recalcular el dashboard."""

    if GUIA_IMAGEN.is_file():
        st.image(
            str(GUIA_IMAGEN),
            width="stretch",
            caption="Guía de uso e interpretación del Dashboard de Accesos UTMACH",
        )
    else:
        st.info(
            "La imagen de la guía estará disponible cuando se incorpore "
            "`resources/GUIA.png`.",
            icon=":material/image:",
        )

    st.caption(
        "Para cerrar la guía, utiliza la X de la esquina superior derecha."
    )


@st.fragment
def mostrar_boton_guia_sidebar() -> None:
    """
    El botón se ejecuta dentro de un fragmento independiente.

    Al presionarlo, Streamlit vuelve a ejecutar únicamente
    este fragmento, no el dashboard completo.
    """

    if st.button(
        "Guía de interpretación",
        icon=":material/help:",
        help="Consulte las instrucciones de uso e interpretación del dashboard.",
        width="stretch",
        key="abrir_guia_interpretacion",
    ):
        mostrar_dialogo_guia()
