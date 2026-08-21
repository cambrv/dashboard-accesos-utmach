"""
Módulo de visualizaciones de "Todos los Eventos".
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from visualizations import _aplicar_layout, PALETA_PRINCIPAL
from config import COLORES_RESULTADO

# Usamos los colores definidos en config.py para garantizar consistencia
ORDER_RESULTADO = list(COLORES_RESULTADO.keys())

def grafico_resultados_generales(df_stats: pd.DataFrame) -> go.Figure:
    fig = px.pie(
        df_stats,
        names="Resultado",
        values="Eventos",
        color="Resultado",
        color_discrete_map=COLORES_RESULTADO,
        hole=0.4
    )
    _aplicar_layout(fig, "Distribución General de Eventos")
    fig.update_traces(textinfo="percent+label")
    return fig

def grafico_cruce_ingreso_resultado(df_cruce: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    # Añadir barras para cada resultado
    for res in ORDER_RESULTADO:
        if res in df_cruce.columns:
            fig.add_trace(go.Bar(
                x=df_cruce["Ingreso"],
                y=df_cruce[res],
                name=res,
                marker_color=COLORES_RESULTADO[res]
            ))
            
    _aplicar_layout(fig, "Eventos por Ingreso y Resultado")
    fig.update_layout(
        barmode='stack',
        xaxis_title="Ingreso",
        yaxis_title="Cantidad de Eventos"
    )
    return fig

def grafico_cruce_hora_resultado(df_cruce: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    for res in ORDER_RESULTADO:
        if res in df_cruce.columns:
            fig.add_trace(go.Scatter(
                x=df_cruce["Hora_Dia"],
                y=df_cruce[res],
                mode='lines+markers',
                name=res,
                line=dict(color=COLORES_RESULTADO[res], width=2)
            ))
            
    _aplicar_layout(fig, "Flujo Horario por Resultado")
    fig.update_layout(
        xaxis_title="Hora del Día", 
        yaxis_title="Eventos"
    )
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=1)
    return fig

def grafico_evolucion_resultado(df_cruce: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    for res in ORDER_RESULTADO:
        if res in df_cruce.columns:
            fig.add_trace(go.Bar(
                x=df_cruce["Fecha"],
                y=df_cruce[res],
                name=res,
                marker_color=COLORES_RESULTADO[res]
            ))
            
    _aplicar_layout(fig, "Evolución Diaria por Resultado")
    fig.update_layout(
        barmode='stack',
        xaxis_title="Fecha",
        yaxis_title="Eventos"
    )
    return fig

def grafico_dia_semana_resultado(df_cruce: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    for res in ORDER_RESULTADO:
        if res in df_cruce.columns:
            fig.add_trace(go.Bar(
                x=df_cruce["Dia"],
                y=df_cruce[res],
                name=res,
                marker_color=COLORES_RESULTADO[res]
            ))
            
    _aplicar_layout(fig, "Eventos por Día de la Semana y Resultado")
    fig.update_layout(
        barmode='group',
        xaxis_title="Día de la Semana",
        yaxis_title="Eventos"
    )
    return fig

def grafico_tipo_usuario_resultado(df_cruce: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    for res in ORDER_RESULTADO:
        if res in df_cruce.columns:
            fig.add_trace(go.Bar(
                x=df_cruce[res],
                y=df_cruce["Tipo_Usuario"],
                name=res,
                orientation='h',
                marker_color=COLORES_RESULTADO[res]
            ))
            
    _aplicar_layout(fig, "Eventos por Tipo de Usuario y Resultado", height=max(400, len(df_cruce)*35))
    fig.update_layout(
        barmode='stack',
        xaxis_title="Eventos",
        yaxis_title="Tipo de Usuario"
    )
    fig.update_yaxes(categoryorder="total ascending")
    return fig

def grafico_punto_acceso_resultado(df_cruce: pd.DataFrame) -> go.Figure:
    # Solo mostrar Top 15 para evitar saturar el gráfico
    from access_names import obtener_nombre_corto_pdf
    df_top = df_cruce.head(15).copy()
    if "Punto de acceso" in df_top.columns:
        df_top["Punto de acceso"] = df_top["Punto de acceso"].apply(obtener_nombre_corto_pdf)
    
    fig = go.Figure()
    for res in ORDER_RESULTADO:
        if res in df_top.columns:
            fig.add_trace(go.Bar(
                x=df_top[res],
                y=df_top["Punto de acceso"],
                name=res,
                orientation='h',
                marker_color=COLORES_RESULTADO[res]
            ))
            
    _aplicar_layout(fig, "Top 15 Puntos de Acceso por Flujo (Apilado)", height=max(400, len(df_top)*35))
    fig.update_layout(
        barmode='stack',
        xaxis_title="Eventos",
        yaxis_title="Punto de Acceso"
    )
    fig.update_yaxes(categoryorder="total ascending")
    return fig

def grafico_device_resultado(df_cruce: pd.DataFrame) -> go.Figure:
    df_top = df_cruce.head(15).copy()
    
    fig = go.Figure()
    for res in ORDER_RESULTADO:
        if res in df_top.columns:
            fig.add_trace(go.Bar(
                x=df_top[res],
                y=df_top["Device Name"],
                name=res,
                orientation='h',
                marker_color=COLORES_RESULTADO[res]
            ))
            
    _aplicar_layout(fig, "Top 15 Dispositivos por Flujo (Apilado)", height=max(400, len(df_top)*35))
    fig.update_layout(
        barmode='stack',
        xaxis_title="Eventos",
        yaxis_title="Dispositivo (Device Name)"
    )
    fig.update_yaxes(categoryorder="total ascending")
    return fig

def grafico_heatmap_todos(pivot: pd.DataFrame) -> go.Figure:
    from access_names import obtener_nombre_corto_pdf
    pivot_plot = pivot.copy()
    pivot_plot.index = [obtener_nombre_corto_pdf(idx) for idx in pivot_plot.index]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_plot.values,
        x=pivot_plot.columns,
        y=pivot_plot.index,
        colorscale="Blues",
        hoverongaps=False
    ))
    _aplicar_layout(fig, "Mapa de Calor: Total de Eventos", height=350)
    fig.update_layout(
        xaxis_title="Hora del Día",
        yaxis_title="Día de la Semana"
    )
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=1)
    return fig
