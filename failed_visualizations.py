"""
Módulo de visualizaciones de eventos fallidos.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from visualizations import _aplicar_layout, PALETA_PRINCIPAL
from config import COLORES_INGRESO

def grafico_fallos_por_ingreso(df_stats: pd.DataFrame) -> go.Figure:
    fig = px.pie(
        df_stats,
        names="Ingreso",
        values="Eventos",
        color="Ingreso",
        color_discrete_map=COLORES_INGRESO,
        hole=0.4
    )
    _aplicar_layout(fig, "Eventos Fallidos por Ingreso")
    fig.update_traces(textinfo="percent+label")
    return fig

def grafico_fallos_por_hora(df_stats: pd.DataFrame) -> go.Figure:
    fig = px.line(
        df_stats,
        x="Hora",
        y="Eventos",
        markers=True,
        line_shape="spline",
        color_discrete_sequence=[PALETA_PRINCIPAL[1]]
    )
    _aplicar_layout(fig, "Eventos Fallidos por Hora")
    fig.update_layout(xaxis_title="Hora del Día", yaxis_title="Eventos")
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=1)
    return fig

def grafico_fallos_evolucion_diaria(df_stats: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df_stats,
        x="Fecha",
        y="Eventos",
        text="Eventos",
        color_discrete_sequence=[PALETA_PRINCIPAL[0]]
    )
    _aplicar_layout(fig, "Evolución Diaria de Eventos Fallidos")
    fig.update_layout(xaxis_title="Fecha", yaxis_title="Eventos")
    fig.update_traces(textposition="outside")
    return fig

def grafico_fallos_por_punto(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras horizontal de fallos por punto de acceso."""
    from access_names import obtener_nombre_corto_pdf
    df_plot = df_stats.head(15).copy()
    if "Punto de acceso" in df_plot.columns:
        df_plot["Punto de acceso"] = df_plot["Punto de acceso"].apply(obtener_nombre_corto_pdf)
    
    fig = px.bar(
        df_plot,
        y="Punto de acceso",
        x="Eventos",
        orientation="h",
        text="Eventos",
        color_discrete_sequence=[PALETA_PRINCIPAL[2]]
    )
    fig.update_yaxes(categoryorder="total ascending")
    _aplicar_layout(fig, "Top 15 Puntos con Más Fallos", height=max(400, len(df_plot)*35))
    fig.update_layout(xaxis_title="Eventos", yaxis_title="Punto de Acceso")
    return fig
