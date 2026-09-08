"""
Módulo de visualización para eventos vehiculares LPR.
Soporta doble tema: 'dark' (Dashboard) y 'light' (PDF).
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import COLORES_INGRESO, DIAS_SEMANA_ORDEN

FONT_FAMILY = "Plus Jakarta Sans, sans-serif"

def _aplicar_estilo_base(fig: go.Figure, theme: str = "dark"):
    """
    Aplica el estilo dual a las figuras.
    theme="dark" para Streamlit
    theme="light" para PDF
    """
    if theme == "dark":
        bg_color = "rgba(0,0,0,0)"
        font_color = "#E8EEF3"
        grid_color = "rgba(255,255,255,0.1)"
        hover_bg = "#182431"
        title_color = "#5AA6D6"
    else:
        bg_color = "#FFFFFF"
        font_color = "#2C3E50"
        grid_color = "rgba(0,0,0,0.1)"
        hover_bg = "#FFFFFF"
        title_color = "#1B4F72"

    fig.update_layout(
        font_family=FONT_FAMILY,
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=font_color),
        margin=dict(t=50, l=40, r=20, b=40),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, 
            title=None, font=dict(color=font_color)
        ),
        hoverlabel=dict(bgcolor=hover_bg, font_size=13, font_family=FONT_FAMILY, font_color=font_color),
        title=dict(font=dict(size=16, color=title_color))
    )
    fig.update_xaxes(showgrid=True, gridcolor=grid_color, zeroline=False, showline=True, linewidth=1, linecolor=grid_color)
    fig.update_yaxes(showgrid=True, gridcolor=grid_color, zeroline=False, showline=False)
    return fig

def grafico_lpr_por_dia(df_dia: pd.DataFrame, theme: str = "dark") -> go.Figure:
    if df_dia.empty: return go.Figure()
    fig = px.bar(
        df_dia, x="Fecha", y="Eventos",
        title="Eventos Vehiculares por Día",
        labels={"Fecha": "Día", "Eventos": "Cantidad de Eventos"},
        color_discrete_sequence=["#3B82B8"]
    )
    fig.update_xaxes(tickformat="%d/%m")
    return _aplicar_estilo_base(fig, theme)

def grafico_heatmap_lpr(df_heatmap: pd.DataFrame, theme: str = "dark") -> go.Figure:
    if df_heatmap.empty: return go.Figure()
    fig = go.Figure(data=go.Heatmap(
        z=df_heatmap.values,
        x=[f"{int(h)}:00–{(int(h)+1)%24}:00" for h in df_heatmap.columns],
        y=df_heatmap.index,
        colorscale="Blues" if theme == "light" else "Teal",
        hoverongaps=False
    ))
    fig.update_layout(
        title="Mapa de Calor: Día vs Hora",
        xaxis_title="Hora del Día",
        yaxis_title="Día de la Semana"
    )
    return _aplicar_estilo_base(fig, theme)

def grafico_flujo_vehicular_por_hora(df_hora: pd.DataFrame, theme: str = "dark") -> go.Figure:
    if df_hora.empty: return go.Figure()
    
    # df_hora proviene de stats_flujo_vehicular_por_hora
    df_plot = df_hora.copy()
    df_plot["Horario"] = [f"{int(h)}:00–{(int(h)+1)%24}:00" for h in df_plot["Hora"]]
    
    # Destacar la hora pico
    max_registros = df_plot["Registros"].max()
    colores = []
    for r in df_plot["Registros"]:
        if r == max_registros and max_registros > 0:
            colores.append("#E67E22" if theme == "dark" else "#D35400") # Naranja para destacar
        else:
            colores.append("#3B82B8" if theme == "dark" else "#2E86C1") # Azul normal
            
    fig = px.bar(
        df_plot, x="Horario", y="Registros",
        title="Flujo Vehicular por Hora",
        labels={"Horario": "Franja Horaria", "Registros": "Registros Vehiculares"},
    )
    
    fig.update_traces(marker_color=colores)
    return _aplicar_estilo_base(fig, theme)

def grafico_lpr_por_sitio(df_sitio: pd.DataFrame, theme: str = "dark") -> go.Figure:
    if df_sitio.empty: return go.Figure()
    fig = px.bar(
        df_sitio, x="Eventos", y="Punto_Acceso", orientation="h",
        title="Volumen Vehicular por Punto de Acceso",
        color="Sitio", color_discrete_map=COLORES_INGRESO, text="Eventos"
    )
    fig.update_traces(textposition='outside', textfont=dict(color="#E8EEF3" if theme=="dark" else "#2C3E50"))
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    return _aplicar_estilo_base(fig, theme)



def grafico_top_placas(df_top: pd.DataFrame, theme: str = "dark") -> go.Figure:
    if df_top.empty: return go.Figure()
    df_plot = df_top.sort_values(by="Eventos", ascending=True)
    fig = px.bar(
        df_plot, x="Eventos", y="Matricula", orientation="h",
        title="Placas con Mayor Frecuencia",
        text="Eventos",
        color_discrete_sequence=["#1ABC9C" if theme=="dark" else "#16A085"]
    )
    fig.update_traces(textposition='outside', textfont=dict(color="#E8EEF3" if theme=="dark" else "#2C3E50"))
    return _aplicar_estilo_base(fig, theme)
