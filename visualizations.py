"""
Módulo de visualizaciones con Plotly.
Genera todos los gráficos interactivos requeridos.
Trabaja con datos ya agregados para rendimiento.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from config import COLORES_INGRESO, COLORES_MOVIMIENTO, DIAS_SEMANA_ORDEN


# ─── Paleta de colores institucional ────────────────────────────────────────
PALETA_PRINCIPAL = [
    "#1B4F72", "#2E86C1", "#3498DB", "#5DADE2", "#85C1E9",
    "#1A5276", "#1F618D", "#2874A6", "#2980B9", "#5499C7",
    "#7FB3D8", "#A9CCE3", "#D4E6F1", "#21618C", "#2C3E50",
    "#34495E", "#5D6D7E", "#7F8C8D", "#95A5A6", "#BDC3C7",
]

LAYOUT_TEMPLATE = dict(
    font=dict(family="Plus Jakarta Sans, sans-serif", size=13),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=40, t=50, b=80),
    hoverlabel=dict(font=dict(family="Plus Jakarta Sans, sans-serif", size=12)),
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="center",
        x=0.5,
        font=dict(size=11)
    )
)


def _aplicar_layout(fig, titulo="", height=500):
    """Aplica estilo consistente a todas las figuras."""
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16, color="#1B4F72")),
        height=height,
        **LAYOUT_TEMPLATE,
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(200,200,200,0.3)", automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(200,200,200,0.3)", automargin=True, ticklabelposition="outside")
    return fig


# ─── 9.2 Gráfico de barras: Flujo por punto de acceso ──────────────────────
def grafico_flujo_punto_acceso(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras horizontal de flujo por punto de acceso."""
    from access_names import obtener_nombre_corto_pdf
    df_plot = df_stats.copy()
    if "Punto de acceso" in df_plot.columns:
        df_plot["Punto de acceso"] = df_plot["Punto de acceso"].apply(obtener_nombre_corto_pdf)
    df_plot = df_plot.sort_values("Eventos", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_plot["Punto de acceso"],
        x=df_plot["Eventos"],
        orientation="h",
        marker_color=[COLORES_INGRESO.get(c, "#7f7f7f") for c in df_plot["Ingreso"]],
        text=df_plot.apply(
            lambda r: f"{r['Eventos']:,} ({r['Porcentaje']}%)", axis=1
        ),
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Eventos: %{x:,}<br>"
            "<extra></extra>"
        ),
    ))
    _aplicar_layout(fig, "Flujo por Punto de Acceso", height=max(400, len(df_plot) * 35))
    fig.update_layout(xaxis_title="Eventos", yaxis_title="")
    return fig


# ─── 9.3 Gráfico de barras: Flujo por hora ─────────────────────────────────
def grafico_flujo_hora(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras de flujo por hora del día."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"{h:02d}:00" for h in df_stats["Hora"]],
        y=df_stats["Eventos"],
        marker_color="#2E86C1",
        text=df_stats["Eventos"].apply(lambda x: f"{x:,}"),
        textposition="outside",
        hovertemplate="Hora: %{x}<br>Eventos: %{y:,}<extra></extra>",
    ))
    _aplicar_layout(fig, "Distribución de Eventos por Hora del Día")
    fig.update_layout(xaxis_title="Hora", yaxis_title="Eventos")
    return fig


# ─── 9.4 Heatmap: Punto de acceso × Hora ───────────────────────────────────
def grafico_heatmap_punto_hora(pivot: pd.DataFrame) -> go.Figure:
    """Heatmap de punto de acceso × hora."""
    from access_names import obtener_nombre_corto_pdf
    pivot_plot = pivot.copy()
    pivot_plot.index = [obtener_nombre_corto_pdf(idx) for idx in pivot_plot.index]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_plot.values,
        x=[f"{h:02d}:00" for h in pivot_plot.columns],
        y=pivot_plot.index.tolist(),
        colorscale="Blues",
        hovertemplate=(
            "Punto: %{y}<br>"
            "Hora: %{x}<br>"
            "Eventos: %{z:,}<extra></extra>"
        ),
        colorbar=dict(title="Eventos"),
    ))
    _aplicar_layout(fig, "Flujo por Punto de Acceso y Hora", height=max(500, len(pivot) * 32))
    return fig


# ─── 9.5 Gráfico comparativo: Entradas vs Salidas ──────────────────────────
def grafico_entradas_salidas(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de dona de entradas vs salidas."""
    fig = go.Figure(data=[go.Pie(
        labels=df_stats["Movimiento"],
        values=df_stats["Eventos"],
        marker_colors=[COLORES_MOVIMIENTO.get(m, "#9467bd") for m in df_stats["Movimiento"]],
        hole=0.4,
        textinfo="label+percent+value",
        texttemplate="%{label}<br>%{value:,} (%{percent})",
        hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
    )])
    _aplicar_layout(fig, "Distribución de Entradas vs Salidas")
    return fig


def grafico_entradas_salidas_hora(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de líneas: entradas vs salidas por hora."""
    fig = go.Figure()
    for mov in df_stats["Movimiento"].unique():
        sub = df_stats[df_stats["Movimiento"] == mov]
        fig.add_trace(go.Scatter(
            x=[f"{h:02d}:00" for h in sub["Hora_Dia"]],
            y=sub["Eventos"],
            name=mov,
            mode="lines+markers",
            line=dict(color=COLORES_MOVIMIENTO.get(mov, "#9467bd"), width=2),
            hovertemplate="Hora: %{x}<br>Eventos: %{y:,}<extra></extra>",
        ))
    _aplicar_layout(fig, "Entradas vs Salidas por Hora")
    fig.update_layout(xaxis_title="Hora", yaxis_title="Eventos")
    return fig


def grafico_entradas_salidas_por_ingreso(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras agrupadas: entradas vs salidas por ingreso."""
    fig = px.bar(
        df_stats,
        x="Ingreso",
        y="Eventos",
        color="Movimiento",
        barmode="group",
        text="Eventos",
        color_discrete_map=COLORES_MOVIMIENTO,
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    _aplicar_layout(fig, "Entradas vs Salidas por Ingreso")
    fig.update_layout(xaxis_title="Ingreso", yaxis_title="Eventos")
    return fig


# ─── 9.6 Gráfico de ingreso ────────────────────────────────────────────────
def grafico_ingreso(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras de flujo por ingreso."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_stats["Ingreso"],
        y=df_stats["Eventos"],
        marker_color=[COLORES_INGRESO.get(c, "#7f7f7f") for c in df_stats["Ingreso"]],
        text=df_stats.apply(
            lambda r: f"{r['Eventos']:,} ({r['Porcentaje']}%)", axis=1
        ),
        textposition="outside",
        hovertemplate="Ingreso: %{x}<br>Eventos: %{y:,}<extra></extra>",
    ))
    _aplicar_layout(fig, "Flujo por Ingreso")
    fig.update_layout(xaxis_title="Ingreso", yaxis_title="Eventos")
    return fig


# ─── 9.7 Gráfico de tipo de usuario ────────────────────────────────────────
def grafico_tipo_usuario(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras de flujo por tipo de usuario."""
    df_plot = df_stats.sort_values("Eventos", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_plot["Tipo_Usuario"],
        x=df_plot["Eventos"],
        orientation="h",
        marker_color=PALETA_PRINCIPAL[:len(df_plot)],
        text=df_plot.apply(
            lambda r: f"{r['Eventos']:,} ({r['Porcentaje']}%)", axis=1
        ),
        textposition="outside",
        hovertemplate="Tipo: %{y}<br>Eventos: %{x:,}<extra></extra>",
    ))
    _aplicar_layout(fig, "Flujo por Tipo de Usuario")
    fig.update_layout(xaxis_title="Eventos", yaxis_title="")
    return fig


# ─── 9.8 Gráfico tipo de usuario × ingreso ─────────────────────────────────
def grafico_tipo_usuario_ingreso(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras agrupadas: tipo de usuario por ingreso."""
    fig = px.bar(
        df_stats,
        x="Tipo_Usuario",
        y="Eventos",
        color="Ingreso",
        barmode="group",
        text="Eventos",
        color_discrete_map=COLORES_INGRESO,
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    _aplicar_layout(fig, "Tipo de Usuario por Ingreso")
    fig.update_layout(xaxis_title="Tipo de Usuario", yaxis_title="Eventos")
    return fig


# ─── 9.9 Gráfico de flujo diario ───────────────────────────────────────────
def grafico_flujo_diario(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de líneas de flujo diario."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df_stats["Fecha"],
            y=df_stats["Eventos"],
            name="Eventos",
            marker_color="#2E86C1",
            opacity=0.7,
            hovertemplate="Fecha: %{x}<br>Eventos: %{y:,}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_stats["Fecha"],
            y=df_stats["Usuarios_Unicos"],
            name="Usuarios Únicos",
            mode="lines+markers",
            line=dict(color="#E74C3C", width=2),
            hovertemplate="Fecha: %{x}<br>Usuarios: %{y:,}<extra></extra>",
        ),
        secondary_y=True,
    )
    _aplicar_layout(fig, "Flujo Diario: Eventos y Usuarios Únicos")
    fig.update_yaxes(title_text="Eventos", secondary_y=False)
    fig.update_yaxes(title_text="Usuarios Únicos", secondary_y=True)
    return fig


def grafico_flujo_diario_por_ingreso(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de líneas comparativo de flujo diario por ingreso."""
    fig = go.Figure()
    for ingreso in df_stats["Ingreso"].unique():
        sub = df_stats[df_stats["Ingreso"] == ingreso]
        fig.add_trace(go.Scatter(
            x=sub["Fecha"],
            y=sub["Eventos"],
            name=ingreso,
            mode="lines+markers",
            line=dict(color=COLORES_INGRESO.get(ingreso, "#7f7f7f"), width=2.5),
            fill="tozeroy",
            opacity=0.6,
            hovertemplate=f"{ingreso}<br>Fecha: %{{x}}<br>Eventos: %{{y:,}}<extra></extra>",
        ))
    _aplicar_layout(fig, "Comparación Diaria: 25 de Junio vs Ferroviaria")
    fig.update_layout(xaxis_title="Fecha", yaxis_title="Eventos")
    return fig


# ─── 9.10 Gráfico día de la semana ─────────────────────────────────────────
def grafico_dia_semana(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras de flujo por día de la semana."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_stats["Dia_Semana"],
        y=df_stats["Eventos"],
        name="Total",
        marker_color="#2E86C1",
        text=df_stats["Eventos"].apply(lambda x: f"{x:,}"),
        textposition="outside",
        hovertemplate="Día: %{x}<br>Eventos: %{y:,}<extra></extra>",
    ))
    _aplicar_layout(fig, "Flujo por Día de la Semana")
    fig.update_layout(xaxis_title="Día", yaxis_title="Eventos")
    return fig


# ─── 9.11 Heatmap: Día de semana × Hora ────────────────────────────────────
def grafico_heatmap_dia_hora(pivot: pd.DataFrame) -> go.Figure:
    """Heatmap de día de semana × hora."""
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in pivot.columns],
        y=pivot.index.tolist(),
        colorscale="YlOrRd",
        hovertemplate=(
            "Día: %{y}<br>"
            "Hora: %{x}<br>"
            "Eventos: %{z:,}<extra></extra>"
        ),
        colorbar=dict(title="Eventos"),
    ))
    _aplicar_layout(fig, "Mapa de Calor: Día de la Semana × Hora", height=350)
    return fig


# ─── 9.12 Gráfico ingreso + hora ───────────────────────────────────────────
def grafico_ingreso_hora(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico comparativo de flujo horario por ingreso."""
    fig = go.Figure()
    for ingreso in df_stats["Ingreso"].unique():
        sub = df_stats[df_stats["Ingreso"] == ingreso]
        fig.add_trace(go.Scatter(
            x=[f"{h:02d}:00" for h in sub["Hora_Dia"]],
            y=sub["Eventos"],
            name=ingreso,
            mode="lines+markers",
            line=dict(color=COLORES_INGRESO.get(ingreso, "#7f7f7f"), width=2.5),
            hovertemplate=f"{ingreso}<br>Hora: %{{x}}<br>Eventos: %{{y:,}}<extra></extra>",
        ))
    _aplicar_layout(fig, "Comparación de Flujo Horario por Ingreso")
    fig.update_layout(xaxis_title="Hora", yaxis_title="Eventos")
    return fig


# ─── 9.13 Gráfico punto × tipo de usuario ──────────────────────────────────
def grafico_punto_tipo_usuario(df_stats: pd.DataFrame) -> go.Figure:
    """Gráfico de barras apiladas: tipo de usuario por punto de acceso."""
    from access_names import obtener_nombre_corto_pdf
    df_plot = df_stats.copy()
    if "Punto de acceso" in df_plot.columns:
        df_plot["Punto de acceso"] = df_plot["Punto de acceso"].apply(obtener_nombre_corto_pdf)
        
    fig = px.bar(
        df_plot,
        y="Punto de acceso",
        x="Eventos",
        color="Tipo_Usuario",
        orientation="h",
        color_discrete_sequence=PALETA_PRINCIPAL,
    )
    _aplicar_layout(fig, "Tipo de Usuario por Punto de Acceso", height=max(400, df_stats["Punto de acceso"].nunique() * 32))
    fig.update_layout(xaxis_title="Eventos", yaxis_title="")
    return fig


# ─── Gráfico de frecuencia de utilización ───────────────────────────────────
def grafico_frecuencia(df_rangos: pd.DataFrame) -> go.Figure:
    """Gráfico de barras de distribución de frecuencia."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_rangos["Rango"],
        y=df_rangos["Usuarios"],
        marker_color="#2E86C1",
        text=df_rangos["Usuarios"].apply(lambda x: f"{x:,}"),
        textposition="outside",
        hovertemplate="Rango: %{x}<br>Usuarios: %{y:,}<extra></extra>",
    ))
    _aplicar_layout(fig, "Distribución de Frecuencia de Utilización")
    fig.update_layout(xaxis_title="Rango de Eventos", yaxis_title="Usuarios")
    return fig


# ─── Contraste entre ingresos: gráfico de dona doble ───────────────────────
def grafico_contraste_ingresos(df: pd.DataFrame) -> go.Figure:
    """Gráfico de dona lado a lado para contrastar los dos ingresos."""
    ingresos = df.groupby("Ingreso").agg(
        Eventos=("Hora", "count"),
        Usuarios_Unicos=("Persona", lambda x: x[x != ""].nunique()),
    ).reset_index()

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=["Eventos por Ingreso", "Usuarios Únicos por Ingreso"],
    )
    fig.add_trace(
        go.Pie(
            labels=ingresos["Ingreso"],
            values=ingresos["Eventos"],
            marker_colors=[COLORES_INGRESO.get(i, "#7f7f7f") for i in ingresos["Ingreso"]],
            hole=0.45,
            texttemplate="%{label}<br>%{value:,}<br>(%{percent})",
            hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Pie(
            labels=ingresos["Ingreso"],
            values=ingresos["Usuarios_Unicos"],
            marker_colors=[COLORES_INGRESO.get(i, "#7f7f7f") for i in ingresos["Ingreso"]],
            hole=0.45,
            texttemplate="%{label}<br>%{value:,}<br>(%{percent})",
            hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
        ),
        row=1, col=2,
    )
    _aplicar_layout(fig, "Contraste entre Ingresos: Eventos y Usuarios", height=400)
    return fig
