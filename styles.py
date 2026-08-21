"""
Estilos visuales del dashboard de flujo de ingresos peatonales.
Tema oscuro institucional y técnico.
"""

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# PALETA
# ─────────────────────────────────────────────────────────────────────────────

COLOR_FONDO = "#0F1720"
COLOR_FONDO_SECUNDARIO = "#141E29"
COLOR_PANEL = "#182431"
COLOR_PANEL_HOVER = "#1C2A38"

COLOR_PRINCIPAL = "#3B82B8"
COLOR_PRINCIPAL_CLARO = "#5AA6D6"

COLOR_TEXTO = "#E8EEF3"
COLOR_TEXTO_SECUNDARIO = "#A8B5C1"
COLOR_TEXTO_SUAVE = "#738291"

COLOR_BORDE = "#263746"
COLOR_BORDE_SUAVE = "#202F3D"

COLOR_INFO_FONDO = "#142A38"
COLOR_INFO_BORDE = "#285775"
COLOR_INFO_TEXTO = "#9CC9E5"

COLOR_WARNING_FONDO = "#302A18"
COLOR_WARNING_BORDE = "#665526"
COLOR_WARNING_TEXTO = "#E4CD7A"

COLOR_EXITO = "#55A878"
COLOR_ERROR = "#D66A6A"

COLOR_BLANCO = "#FFFFFF"


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

CSS_DASHBOARD = f"""
<style>

    /* ================================================================
       TIPOGRAFÍA Y FONDO GENERAL
       ================================================================ */

    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css");

    /* Aplicar tipografía base de forma segura sin romper iconos */
    html, body, .stApp, .main, [data-testid="stAppViewContainer"] {{
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}
    
    h1, h2, h3, h4, h5, h6, p, label, li, a {{
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}

    /* PROTEGER ICONOS NATIVOS DE STREAMLIT */
    /* Forzar que los elementos que Streamlit usa para iconos mantengan su webfont original */
    [data-testid="stIconMaterial"], 
    .stIconMaterial, 
    .material-symbols-rounded, 
    [class*="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded' !important;
    }}

    .stApp {{
        background: {COLOR_FONDO};
        color: {COLOR_TEXTO};
    }}

    .main {{
        background: {COLOR_FONDO};
    }}

    /* Sobrescribir el layout de Streamlit para aprovechar todo el ancho */
    [data-testid="stMainBlockContainer"] {{
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }}


    /* ================================================================
       HEADER PRINCIPAL
       ================================================================ */

    .main-header {{
        background: {COLOR_PANEL};

        border: 1px solid {COLOR_BORDE};

        border-left: 4px solid {COLOR_PRINCIPAL};

        border-radius: 8px;

        padding: 1.35rem 1.6rem;

        margin-bottom: 1.5rem;

        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
    }}

    .main-header h1 {{
        margin: 0;

        color: {COLOR_TEXTO};

        font-size: 1.75rem;

        font-weight: 600;

        letter-spacing: -0.3px;
    }}

    .main-header p {{
        margin: 0.4rem 0 0 0;

        color: {COLOR_TEXTO_SECUNDARIO};

        font-size: 0.92rem;

        font-weight: 400;
    }}


    /* ================================================================
       TARJETAS DE MÉTRICAS
       ================================================================ */

    .metric-card {{
        background: {COLOR_PANEL};

        border: 1px solid {COLOR_BORDE};

        border-radius: 8px;

        padding: 1.15rem;

        text-align: left;

        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.15);

        transition:
            border-color 0.15s ease,
            transform 0.15s ease;
    }}

    .metric-card:hover {{
        border-color: #34536B;

        transform: translateY(-1px);
    }}

    .metric-card .value {{
        font-size: 1.75rem;

        font-weight: 700;

        color: {COLOR_PRINCIPAL_CLARO};

        line-height: 1.2;
    }}

    .metric-card .label {{
        font-size: 0.78rem;

        color: {COLOR_TEXTO_SECUNDARIO};

        margin-top: 0.45rem;

        font-weight: 500;

        text-transform: uppercase;

        letter-spacing: 0.4px;
    }}


    /* ================================================================
       SECCIONES
       ================================================================ */

    .section-header {{
        border-bottom: 1px solid {COLOR_BORDE};

        padding-bottom: 0.55rem;

        margin: 2rem 0 1rem 0;

        font-size: 1.2rem;

        font-weight: 600;

        color: {COLOR_TEXTO};
    }}

    .section-header::before {{
        content: "";

        display: inline-block;

        width: 4px;

        height: 19px;

        background: {COLOR_PRINCIPAL};

        margin-right: 9px;

        vertical-align: -3px;

        border-radius: 2px;
    }}


    /* ================================================================
       SIDEBAR
       ================================================================ */

    [data-testid="stSidebar"] {{
        background: {COLOR_FONDO_SECUNDARIO};

        border-right: 1px solid {COLOR_BORDE};
    }}

    [data-testid="stSidebar"] h1 {{
        color: {COLOR_TEXTO};

        font-size: 1.15rem;

        font-weight: 600;
    }}

    [data-testid="stSidebar"] h2 {{
        color: {COLOR_TEXTO};

        font-size: 1rem;

        font-weight: 600;
    }}

    [data-testid="stSidebar"] label {{
        color: {COLOR_TEXTO_SECUNDARIO};

        font-size: 0.84rem;
    }}


    /* ================================================================
       SELECTBOX / MULTISELECT
       ================================================================ */

    [data-baseweb="select"] > div {{
        background: {COLOR_PANEL};

        border-color: {COLOR_BORDE};

        color: {COLOR_TEXTO};

        border-radius: 6px;
    }}

    [data-baseweb="select"] span {{
        color: {COLOR_TEXTO};
    }}

    [data-baseweb="popover"] {{
        background: {COLOR_PANEL};
    }}


    /* ================================================================
       INPUTS
       ================================================================ */

    [data-baseweb="input"] > div {{
        background: {COLOR_PANEL};

        border-color: {COLOR_BORDE};

        border-radius: 6px;
    }}

    .stDateInput input {{
        background: {COLOR_PANEL};

        color: {COLOR_TEXTO};
    }}


    /* ================================================================
       INFO BOX
       ================================================================ */

    .info-box {{
        background: {COLOR_INFO_FONDO};

        border: 1px solid {COLOR_INFO_BORDE};

        border-radius: 6px;

        padding: 0.85rem 1rem;

        margin: 0.5rem 0;

        font-size: 0.88rem;

        color: {COLOR_INFO_TEXTO};

        line-height: 1.5;
    }}


    /* ================================================================
       WARNING BOX
       ================================================================ */

    .warning-box {{
        background: {COLOR_WARNING_FONDO};

        border: 1px solid {COLOR_WARNING_BORDE};

        border-radius: 6px;

        padding: 0.85rem 1rem;

        margin: 0.5rem 0;

        font-size: 0.88rem;

        color: {COLOR_WARNING_TEXTO};

        line-height: 1.5;
    }}


    /* ================================================================
       CONCLUSIONES
       ================================================================ */

    .conclusion-item {{
        background: {COLOR_PANEL};

        border: 1px solid {COLOR_BORDE_SUAVE};

        border-left: 3px solid {COLOR_PRINCIPAL};

        border-radius: 5px;

        padding: 0.8rem 1rem;

        margin: 0.45rem 0;

        color: {COLOR_TEXTO_SECUNDARIO};

        font-size: 0.89rem;

        line-height: 1.5;
    }}


    /* ================================================================
       TABLAS
       ================================================================ */

    .stDataFrame {{
        border: 1px solid {COLOR_BORDE};

        border-radius: 6px;

        overflow: hidden;
    }}


    /* ================================================================
       EXPANDERS
       ================================================================ */

    [data-testid="stExpander"] {{
        background: {COLOR_PANEL};

        border: 1px solid {COLOR_BORDE};

        border-radius: 6px;
    }}

    [data-testid="stExpander"] summary {{
        color: {COLOR_TEXTO};
    }}


    /* ================================================================
       TABS
       ================================================================ */

    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;

        border-bottom: 1px solid {COLOR_BORDE};
    }}

    .stTabs [data-baseweb="tab"] {{
        color: {COLOR_TEXTO_SECUNDARIO};

        font-weight: 500;
    }}

    .stTabs [aria-selected="true"] {{
        color: {COLOR_PRINCIPAL_CLARO};
    }}


    /* ================================================================
       DIVISORES
       ================================================================ */

    hr {{
        border: none;

        border-top: 1px solid {COLOR_BORDE};

        margin: 1.2rem 0;
    }}


    /* ================================================================
       MÉTRICAS NATIVAS DE STREAMLIT
       ================================================================ */

    [data-testid="stMetric"] {{
        background: {COLOR_PANEL};

        border: 1px solid {COLOR_BORDE};

        border-radius: 8px;

        padding: 0.85rem 1rem;
    }}

    [data-testid="stMetricLabel"] {{
        color: {COLOR_TEXTO_SECUNDARIO};
    }}

    [data-testid="stMetricValue"] {{
        color: {COLOR_PRINCIPAL_CLARO};
    }}


    /* ================================================================
       TEXTO GENERAL
       ================================================================ */

    h1, h2, h3, h4 {{
        color: {COLOR_TEXTO};
    }}


    /* ================================================================
       SCROLLBAR
       ================================================================ */

    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: {COLOR_FONDO};
    }}

    ::-webkit-scrollbar-thumb {{
        background: #334554;

        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: #40586B;
    }}


    /* ================================================================
       OCULTAR ELEMENTOS DE STREAMLIT
       ================================================================ */

    #MainMenu {{
        visibility: hidden;
    }}

    footer {{
        visibility: hidden;
    }}

</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# APLICAR ESTILOS
# ─────────────────────────────────────────────────────────────────────────────

def aplicar_estilos():
    """
    Aplica todos los estilos visuales del dashboard.
    """

    st.markdown(
        CSS_DASHBOARD,
        unsafe_allow_html=True,
    )