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

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0');

    /* Aplicar tipografía base de forma segura sin romper iconos */
    html, body, .stApp, .main, [data-testid="stAppViewContainer"] {{
        font-family: 'Inter', sans-serif;
    }}
    
    h1, h2, h3, h4, h5, h6, p, label, li, a {{
        font-family: 'Inter', sans-serif;
    }}

    /* PROTEGER ICONOS NATIVOS DE STREAMLIT */
    /* Forzar que los elementos que Streamlit usa para iconos mantengan su webfont original */
    [data-testid="stIconMaterial"], 
    .stIconMaterial, 
    .material-symbols-rounded, 
    [class*="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded' !important;
        font-style: normal;
        font-weight: 400;
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
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

    .metric-card .metric-icon {{
        font-size: 1.45rem;
        margin-right: 0.25rem;
        vertical-align: -0.2rem;
        color: {COLOR_PRINCIPAL};
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

    .section-header .section-icon {{
        color: {COLOR_PRINCIPAL};
        font-size: 1.25rem;
        margin-right: 0.5rem;
        vertical-align: -0.22rem;
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

PALETAS_TEMA = {
    "Oscuro": {
        "fondo": "#0F1720",
        "fondo_secundario": "#141E29",
        "panel": "#182431",
        "panel_hover": "#1C2A38",
        "principal": "#3B82B8",
        "principal_claro": "#5AA6D6",
        "texto": "#E8EEF3",
        "texto_secundario": "#A8B5C1",
        "texto_suave": "#738291",
        "borde": "#263746",
        "borde_suave": "#202F3D",
        "info_fondo": "#142A38",
        "info_borde": "#285775",
        "info_texto": "#9CC9E5",
        "warning_fondo": "#302A18",
        "warning_borde": "#665526",
        "warning_texto": "#E4CD7A",
        "grid": "rgba(255,255,255,0.12)",
        "accent_blue": "#5AA6D6",
        "accent_orange": "#F5B041",
        "accent_green": "#32C7AE",
    },
    "Claro": {
        "fondo": "#F6F8FB",
        "fondo_secundario": "#EEF3F7",
        "panel": "#FFFFFF",
        "panel_hover": "#F7FAFC",
        "principal": "#246B9E",
        "principal_claro": "#1F6FA8",
        "texto": "#17212B",
        "texto_secundario": "#465568",
        "texto_suave": "#64748B",
        "borde": "#D7E0E8",
        "borde_suave": "#E4EAF0",
        "info_fondo": "#EAF5FC",
        "info_borde": "#A9D2EA",
        "info_texto": "#174F72",
        "warning_fondo": "#FFF8E6",
        "warning_borde": "#E7CF8A",
        "warning_texto": "#654E0C",
        "grid": "rgba(23,33,43,0.12)",
        "accent_blue": "#246B9E",
        "accent_orange": "#B45309",
        "accent_green": "#0F766E",
    },
}


def obtener_tema_actual() -> str:
    """Devuelve el tema visual elegido para la sesión actual."""
    return st.session_state.get("tema_app", "Claro")


def obtener_paleta(modo: str | None = None) -> dict:
    """Obtiene la paleta del tema sin compartir estado mutable."""
    return PALETAS_TEMA.get(modo or obtener_tema_actual(), PALETAS_TEMA["Claro"]).copy()


def _css_para_tema(modo: str) -> str:
    """Adapta el CSS histórico al tema elegido conservando sus selectores."""
    paleta = obtener_paleta(modo)
    sombra_tarjeta = "0 3px 12px rgba(15, 23, 32, 0.08)" if modo == "Claro" else "0 3px 12px rgba(0, 0, 0, 0.15)"
    reemplazos = {
        COLOR_FONDO: paleta["fondo"],
        COLOR_FONDO_SECUNDARIO: paleta["fondo_secundario"],
        COLOR_PANEL: paleta["panel"],
        COLOR_PANEL_HOVER: paleta["panel_hover"],
        COLOR_PRINCIPAL: paleta["principal"],
        COLOR_PRINCIPAL_CLARO: paleta["principal_claro"],
        COLOR_TEXTO: paleta["texto"],
        COLOR_TEXTO_SECUNDARIO: paleta["texto_secundario"],
        COLOR_TEXTO_SUAVE: paleta["texto_suave"],
        COLOR_BORDE: paleta["borde"],
        COLOR_BORDE_SUAVE: paleta["borde_suave"],
        COLOR_INFO_FONDO: paleta["info_fondo"],
        COLOR_INFO_BORDE: paleta["info_borde"],
        COLOR_INFO_TEXTO: paleta["info_texto"],
        COLOR_WARNING_FONDO: paleta["warning_fondo"],
        COLOR_WARNING_BORDE: paleta["warning_borde"],
        COLOR_WARNING_TEXTO: paleta["warning_texto"],
    }
    css = CSS_DASHBOARD
    for color_original, color_tema in reemplazos.items():
        css = css.replace(color_original, color_tema)

    variables = f"""
    <style>
    :root {{
        --dashboard-bg: {paleta['fondo']};
        --dashboard-sidebar: {paleta['fondo_secundario']};
        --dashboard-panel: {paleta['panel']};
        --dashboard-text: {paleta['texto']};
        --dashboard-text-secondary: {paleta['texto_secundario']};
        --dashboard-text-muted: {paleta['texto_suave']};
        --dashboard-border: {paleta['borde']};
        --dashboard-primary: {paleta['principal']};
        --card-bg: {paleta['panel']};
        --card-border: {paleta['borde']};
        --text-primary: {paleta['texto']};
        --text-secondary: {paleta['texto_secundario']};
        --text-muted: {paleta['texto_suave']};
        --metric-primary: {paleta['principal_claro']};
        --card-shadow: {sombra_tarjeta};
        --accent-blue: {paleta['accent_blue']};
        --accent-orange: {paleta['accent_orange']};
        --accent-green: {paleta['accent_green']};
    }}
    .mobility-heading {{
        text-align: center;
        margin-bottom: 30px;
        font-family: 'Inter', sans-serif;
    }}
    .mobility-heading__title {{
        color: var(--dashboard-primary);
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }}
    .mobility-heading__value {{
        color: var(--text-primary);
        font-size: 36px;
        font-weight: 700;
    }}
    .mobility-heading__label {{
        color: var(--text-muted);
        font-size: 18px;
        font-weight: 400;
    }}
    .mobility-card {{
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 8px;
        box-shadow: var(--card-shadow);
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
        height: 100%;
        padding: 20px;
        text-align: center;
    }}
    .mobility-card__title {{
        color: var(--text-secondary);
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 10px;
    }}
    .mobility-card__value {{ font-size: 32px; font-weight: 700; }}
    .mobility-card--blue .mobility-card__value {{ color: var(--accent-blue); }}
    .mobility-card--orange .mobility-card__value {{ color: var(--accent-orange); }}
    .mobility-card--green .mobility-card__value {{ color: var(--accent-green); }}
    .mobility-card__percentage {{
        color: var(--text-muted);
        font-size: 14px;
        margin-bottom: 15px;
    }}
    .mobility-card__description {{ color: var(--text-secondary); font-size: 12px; }}
    .mobility-card__details {{
        border-top: 1px solid var(--card-border);
        display: flex;
        justify-content: space-around;
        padding-top: 10px;
    }}
    .mobility-card__detail-label {{ color: var(--text-secondary); font-size: 11px; }}
    .mobility-card__detail-value {{ color: var(--text-primary); font-size: 16px; font-weight: 700; }}
    .peak-card {{
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-left: 4px solid var(--card-accent);
        border-radius: 6px;
        box-shadow: var(--card-shadow);
        font-family: 'Inter', sans-serif;
        padding: 15px 20px;
    }}
    .peak-card--blue {{ --card-accent: var(--accent-blue); }}
    .peak-card--orange {{ --card-accent: var(--accent-orange); }}
    .peak-card--green {{ --card-accent: var(--accent-green); }}
    .peak-card__label {{
        color: var(--text-secondary);
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 5px;
    }}
    .peak-card__value {{ color: var(--text-primary); font-size: 15px; font-weight: 700; }}
    .peak-card--large .peak-card__value {{ font-size: 18px; }}
    /* Compatibilidad con las tarjetas HTML históricas del dashboard. */
    [style*="background-color: #141E29"] {{
        background-color: var(--dashboard-panel) !important;
    }}
    [style*="border: 1px solid #263746"] {{
        border-color: var(--dashboard-border) !important;
    }}
    [style*="border-top: 1px solid #263746"] {{
        border-top-color: var(--dashboard-border) !important;
    }}
    [style*="color: #E8EEF3"] {{ color: var(--dashboard-text) !important; }}
    [style*="color: #A8B5C1"] {{ color: var(--dashboard-text-secondary) !important; }}
    [style*="color: #738291"] {{ color: var(--dashboard-text-muted) !important; }}
    </style>
    """
    return variables + css


def adaptar_figura_plotly(fig, modo: str | None = None):
    """Aplica contraste coherente a cualquier figura mostrada en Streamlit.

    Esta adaptación ocurre al renderizar, por lo que no altera las figuras que
    se generan para los reportes PDF.
    """
    if fig is None or not hasattr(fig, "update_layout"):
        return fig

    paleta = obtener_paleta(modo)
    transparente = "rgba(0,0,0,0)"
    fig.update_layout(
        paper_bgcolor=transparente,
        plot_bgcolor=transparente,
        font=dict(color=paleta["texto"], family="Inter, sans-serif"),
        title_font=dict(color=paleta["principal_claro"]),
        legend=dict(font=dict(color=paleta["texto"])),
        hoverlabel=dict(
            bgcolor=paleta["panel"],
            bordercolor=paleta["borde"],
            font=dict(color=paleta["texto"], family="Inter, sans-serif"),
        ),
    )
    fig.update_xaxes(
        color=paleta["texto"], gridcolor=paleta["grid"],
        linecolor=paleta["borde"], zerolinecolor=paleta["grid"],
    )
    fig.update_yaxes(
        color=paleta["texto"], gridcolor=paleta["grid"],
        linecolor=paleta["borde"], zerolinecolor=paleta["grid"],
    )
    fig.update_traces(
        selector=dict(type="heatmap"),
        colorbar=dict(
            tickfont=dict(color=paleta["texto"]),
            title=dict(font=dict(color=paleta["texto"])),
        ),
    )
    return fig


def aplicar_estilos(modo: str | None = None):
    """Aplica el tema claro u oscuro elegido para esta sesión."""
    st.markdown(_css_para_tema(modo or obtener_tema_actual()), unsafe_allow_html=True)
