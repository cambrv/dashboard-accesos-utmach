"""
Aplicación principal Streamlit — Sistema de Reportes de Flujo de Ingresos Peatonales.

Ejecutar con: streamlit run app.py

Arquitectura modular:
- config.py:          Configuración central
- deprecated/eventos_normales/: implementación histórica fuera del arranque operativo
- statistics_calc.py: Cálculo de estadísticas
- visualizations.py:  Gráficos interactivos con Plotly
- export.py:          Exportación de reportes
"""

import streamlit as st
import pandas as pd
import os
import glob
import hashlib
import uuid
from datetime import datetime

from config import APP_TITULO, APP_ICON, APP_LAYOUT
from statistics_calc import (
    flujo_por_punto_acceso,
    flujo_por_hora,
    horas_pico,
    flujo_punto_hora,
    entradas_vs_salidas_general,
    entradas_vs_salidas_por_ingreso,
    entradas_vs_salidas_por_punto,
    entradas_vs_salidas_por_hora,
    flujo_por_ingreso,
    flujo_por_tipo_usuario,
    flujo_diario_por_ingreso,
    tipo_usuario_ingreso,
    flujo_diario,
    dias_pico,
    flujo_dia_semana,
    heatmap_dia_hora,
    ingreso_hora,
    punto_tipo_usuario,
    punto_movimiento,
    frecuencia_utilizacion,
    generar_conclusiones,
    flujo_consolidado,
    flujo_consolidado_hora,
)
from access_names import obtener_nombre_amigable
from visualizations import (
    grafico_flujo_punto_acceso,
    grafico_flujo_hora,
    grafico_heatmap_punto_hora,
    grafico_entradas_salidas,
    grafico_entradas_salidas_hora,
    grafico_ingreso,
    grafico_tipo_usuario,
    grafico_tipo_usuario_ingreso,
    grafico_flujo_diario,
    grafico_dia_semana,
    grafico_heatmap_dia_hora,
    grafico_ingreso_hora,
    grafico_punto_tipo_usuario,
    grafico_frecuencia,
    grafico_flujo_consolidado,
    grafico_heatmap_consolidado_hora,
)
from pdf_report import exportar_reporte_pdf, construir_graficos_reporte
from styles import aplicar_estilos, adaptar_figura_plotly, obtener_tema_actual

# ─── Monkey Patch para Plotly ───────────────────────────────────────────────
# Streamlit >= 1.16 sobrescribe por defecto el layout de Plotly con su propio tema.
# Para que los gráficos hereden "Inter" desde el layout de visualizations.py,
# forzamos globalmente que theme=None.
if not hasattr(st, "_original_plotly_chart"):
    st._original_plotly_chart = st.plotly_chart

def _patched_plotly_chart(*args, **kwargs):
    if args:
        adaptar_figura_plotly(args[0], obtener_tema_actual())
    elif "figure_or_data" in kwargs:
        adaptar_figura_plotly(kwargs["figure_or_data"], obtener_tema_actual())
    kwargs["theme"] = None
    return st._original_plotly_chart(*args, **kwargs)

st.plotly_chart = _patched_plotly_chart

# Etiquetas legibles aplicadas únicamente a la presentación de tablas.
ETIQUETAS_COLUMNAS = {
    "Punto_Acceso": "Punto de acceso",
    "Punto de acceso": "Punto de acceso",
    "Camara": "Cámara de acceso",
    "Direccion": "Sentido de circulación",
    "Sitio": "Ubicación",
    "Ubicacion": "Ubicación",
    "Ubicacion_Ingreso": "Ubicación",
    "Hora_Dia": "Hora del día",
    "Dia_Semana": "Día de la semana",
    "Usuarios_Unicos": "Usuarios identificados",
    "Registros": "Eventos registrados",
    "Eventos": "Eventos registrados",
    "Mecanismo": "Mecanismo de identificación",
    "Movimiento": "Sentido de circulación",
    "Fecha_mayor_actividad": "Fecha de mayor actividad",
    "Hora_pico": "Hora de mayor actividad",
    "Hora_Pico": "Horario con mayor actividad",
    "Eventos_hora_pico": "Eventos en la hora de mayor actividad",
    "Promedio_hora_pico_min": "Eventos por minuto durante la hora de mayor actividad",
    "Minuto_maximo": "Minuto de mayor actividad",
    "Maximo_observado_minuto": "Mayor número de eventos en un minuto",
    "Promedio_diario_sentido": "Promedio diario de eventos",
    "Dias_considerados": "Días con datos",
    "Promedio_registros_minuto": "Promedio acumulado por minuto",
    "Promedio_por_dia": "Promedio diario de la franja",
    "Cantidad_Fallos": "Fallos de reconocimiento",
    "Porcentaje_Total": "Porcentaje de fallos del período",
    "Puntos_Acceso": "Puntos de acceso relacionados",
    "Device Name": "Dispositivo",
    "Valores Nulos": "Registros sin información",
    "Matricula": "Matrícula",
}

if not hasattr(st, "_original_dataframe"):
    st._original_dataframe = st.dataframe


def _patched_dataframe(*args, **kwargs):
    data = args[0] if args else kwargs.get("data")
    base = getattr(data, "data", data)
    columnas = getattr(base, "columns", [])
    configuracion = dict(kwargs.get("column_config") or {})
    for columna in columnas:
        if columna in ETIQUETAS_COLUMNAS and columna not in configuracion:
            configuracion[columna] = ETIQUETAS_COLUMNAS[columna]
    if configuracion:
        kwargs["column_config"] = configuracion
    return st._original_dataframe(*args, **kwargs)


st.dataframe = _patched_dataframe

# ─── Configuración de página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Reportes Flujo Peatonal",
    page_icon=APP_ICON,
    initial_sidebar_state="expanded",
    layout="wide"
)

# Importaciones para el módulo de Todos los Eventos
from all_events_data_loader import cargar_excel_todos, detectar_columnas_todos, reporte_calidad_todos
from all_events_data_processing import procesar_datos_todos
import all_events_statistics_calc as ats
import all_events_visualizations as atv
from all_events_pdf_report import exportar_reporte_integral_pdf

# Importaciones para el módulo LPR (Vehicular)
from lpr_data_loader import cargar_excel_lpr, detectar_columnas_lpr, reporte_calidad_lpr
from lpr_data_processing import procesar_datos_lpr, deduplicar_eventos_vehiculares
import lpr_statistics_calc as lprs
import lpr_visualizations as lprv
from dashboard_filters import (
    MECANISMO_BIOMETRICO,
    MECANISMO_LPR,
    MECANISMOS_CONSOLIDADOS,
    aplicar_filtros_integrales,
    mecanismo_incluido,
)
from load_progress import LiveElapsedTimer, LoadProgress


def configurar_tema_interfaz():
    """Renderiza el selector de tema sin afectar los datos cargados."""
    st.session_state.setdefault("tema_app", "Claro")
    with st.sidebar:
        st.radio(
            ":material/palette: Apariencia",
            options=["Claro", "Oscuro"],
            horizontal=True,
            key="tema_app",
        )
    aplicar_estilos(obtener_tema_actual())


def restablecer_widgets(valores: dict):
    """Restaura valores de widgets antes de que Streamlit los renderice."""
    for key, value in valores.items():
        st.session_state[key] = value


def _session_scope() -> str:
    """Identificador efímero usado para aislar cachés con datos personales."""
    return st.session_state.setdefault("_cache_scope", uuid.uuid4().hex)


def _archivo_id(archivo) -> str:
    """Huella de contenido; no depende del nombre ni de una ruta local."""
    return hashlib.sha256(archivo.getvalue()).hexdigest()


def _preparar_biometrico_sesion(archivo, archivo_id=None, progreso=None):
    """Lee, valida y clasifica una sola vez por archivo y sesión."""
    archivo_id = archivo_id or _archivo_id(archivo)
    cache = st.session_state.get("_biometrico_preparado")
    if cache and cache["archivo_id"] == archivo_id:
        if progreso:
            progreso.start_stage("Recuperando el Excel biométrico preparado")
            progreso.finish_stage(50, "Excel biométrico recuperado desde la sesión")
        return cache

    if progreso:
        progreso.start_stage(
            "Lectura del Excel biométrico en curso",
            indeterminate=True,
        )
    df_crudo = cargar_excel_todos(archivo, _session_scope())
    if progreso:
        progreso.finish_stage(25, "Lectura del Excel biométrico completada")
        progreso.start_stage("Normalización y depuración biométrica en curso")
    mapeo = detectar_columnas_todos(df_crudo)
    calidad = reporte_calidad_todos(df_crudo, mapeo)
    if calidad["columnas_faltantes"]:
        return {
            "archivo_id": archivo_id,
            "columnas_faltantes": calidad["columnas_faltantes"],
        }

    df, metricas = procesar_datos_todos(df_crudo, mapeo)
    df = df[df["Tipo_Usuario"] != "25 DE JUNIO"].copy()
    if progreso:
        progreso.finish_stage(
            50,
            "Normalización, depuración y clasificación biométrica completadas",
        )
    cache = {
        "archivo_id": archivo_id,
        "columnas_faltantes": [],
        "df": df,
        "metricas": metricas,
        "calidad": calidad,
    }
    st.session_state["_biometrico_preparado"] = cache
    return cache


def _preparar_lpr_sesion(archivo, archivo_id=None, progreso=None):
    """Lee, normaliza y deduplica LPR una sola vez por archivo y sesión."""
    archivo_id = archivo_id or _archivo_id(archivo)
    cache = st.session_state.get("_lpr_preparado")
    if cache and cache["archivo_id"] == archivo_id:
        if progreso:
            progreso.start_stage("Recuperando el Excel LPR preparado")
            progreso.finish_stage(75, "Excel LPR recuperado desde la sesión")
        return cache

    if progreso:
        progreso.start_stage("Lectura del Excel LPR en curso", indeterminate=True)
    df_crudo = cargar_excel_lpr(archivo, _session_scope())
    if progreso:
        progreso.finish_stage(62, "Lectura del Excel LPR completada")
        progreso.start_stage("Normalización y deduplicación LPR en curso")
    mapeo = detectar_columnas_lpr(df_crudo)
    calidad = reporte_calidad_lpr(df_crudo, mapeo)
    if calidad["columnas_faltantes"]:
        return {
            "archivo_id": archivo_id,
            "columnas_faltantes": calidad["columnas_faltantes"],
        }

    df_procesado, metricas = procesar_datos_lpr(df_crudo, mapeo)
    df_valido, df_duplicados = deduplicar_eventos_vehiculares(df_procesado)
    if progreso:
        progreso.finish_stage(75, "Normalización, clasificación y deduplicación LPR completadas")
    cache = {
        "archivo_id": archivo_id,
        "columnas_faltantes": [],
        "df_crudo": df_crudo,
        "df_valido": df_valido,
        "df_duplicados": df_duplicados,
        "metricas": metricas,
        "calidad": calidad,
    }
    st.session_state["_lpr_preparado"] = cache
    return cache


def _aplicar_filtros_todos_desde_widgets():
    """Copia el borrador del formulario al estado efectivamente aplicado."""
    st.session_state["filtros_aplicados_todos"] = {
        "rango_fechas": tuple(st.session_state.get("filt_fechas_todos", ())),
        "resultados": list(st.session_state.get("filt_res", [])),
        "ingresos": list(st.session_state.get("filt_ingreso_todos", [])),
        "tipos_usuario": list(st.session_state.get("filt_tipo_usu_todos", [])),
        "ubicaciones": list(st.session_state.get("filt_ubicacion_todos", [])),
        "mecanismos": list(st.session_state.get("filt_mecanismo_todos", [])),
        "puntos_acceso": list(st.session_state.get("filt_punto_todos", [])),
        "movimientos": list(st.session_state.get("filt_movimiento_todos", [])),
    }


def _restablecer_filtros_todos(valores_widgets: dict, filtros_aplicados: dict):
    """Limpia a la vez etiquetas visibles y resultados aplicados."""
    restablecer_widgets(valores_widgets)
    st.session_state["filtros_aplicados_todos"] = filtros_aplicados.copy()

def formato_numero(n) -> str:
    """Formatea un número con separador de miles."""
    if isinstance(n, float):
        return f"{n:,.2f}"
    return f"{int(n):,}"


def mostrar_metrica(label: str, value, icon: str = ""):
    """Renderiza una tarjeta de métrica."""
    display = formato_numero(value) if isinstance(value, (int, float)) else str(value)
    icon_html = (
        f'<span class="material-symbols-rounded metric-icon">{icon}</span>'
        if icon else ""
    )
    st.markdown(f"""
    <div class="metric-card">
        <div class="value">{icon_html} {display}</div>
        <div class="label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


TITULOS_SECCIONES = {
    "Flujo por Punto de Acceso": "Registros por punto de acceso",
    "Flujo por Hora del Día": "Actividad registrada por hora del día",
    "Flujo por Punto de Acceso y Hora": "Actividad por punto de acceso y hora",
    "Flujo Diario": "Actividad diaria registrada",
    "Flujo por Día de la Semana": "Actividad por día de la semana",
    "Detalle Diario": "Detalle diario de registros y usuarios",
    "Entradas vs Salidas": "Comparación de entradas y salidas registradas",
    "Entradas vs Salidas por Hora": "Entradas y salidas registradas por hora",
    "Entradas vs Salidas por Ingreso": "Entradas y salidas por tipo de ingreso",
    "Entradas/Salidas por Punto de Acceso": "Entradas y salidas por punto de acceso",
    "Flujo por Tipo de Usuario": "Registros por tipo de usuario",
    "Tipo de Usuario por Ingreso": "Tipos de usuario por categoría de ingreso",
    "Tipo de Usuario por Punto de Acceso": "Tipos de usuario por punto de acceso",
    "Flujo por Ingreso": "Registros por categoría de ingreso",
    "Comparación de Flujo Horario por Ingreso": "Actividad horaria por categoría de ingreso",
    "Frecuencia de Utilización del Sistema": "Frecuencia de registros por usuario",
    "Frecuencia": "Frecuencia de registros por usuario",
    "Valores Nulos por Columna": "Campos sin información",
    "Puntos de Acceso Encontrados": "Puntos de acceso identificados en el archivo",
    "1. Comportamiento Temporal": "1. Evolución temporal de eventos anormales",
    "2. Análisis Geográfico": "2. Eventos anormales por ingreso y punto de acceso",
    "Resumen General de Movilidad": "Resumen institucional de movilidad registrada",
    "Estadísticas vehiculares consolidadas": "Eventos vehiculares por mecanismo de identificación",
    "Flujo General Consolidado": "Distribución general de registros por tipo de movilidad",
    "Distribución Detallada por Categoría de Acceso": "Distribución de registros por categoría de acceso",
    "Flujo por Punto de Acceso Físico": "Registros por punto de acceso físico",
    "Comportamiento Horario Consolidado": "Actividad horaria por tipo de movilidad",
    "Comportamiento Diario": "Evolución diaria de registros",
    "Comportamiento Detallado por Hora": "Actividad detallada por hora del día",
    "Usuarios por Tipo y Punto de Acceso": "Usuarios registrados por tipo y punto de acceso",
    "Análisis de Tasas de Fallo y Éxito": "Resultados de autenticación biométrica",
    "1. Distribución de Resultados": "1. Autenticaciones exitosas, fallidas y denegadas",
    "2. Comportamiento por Ingreso": "2. Resultados biométricos por tipo de ingreso",
    "3. Evolución de Tasas": "3. Evolución temporal de resultados biométricos",
    "4. Hardware": "4. Resultados por punto de acceso y dispositivo",
    "Analítica Avanzada e Inteligencia": "Hallazgos estadísticos del período",
    "Análisis Vehicular LPR": "Registros vehiculares identificados mediante LPR",
    "Flujo Vehicular": "Actividad vehicular por carril",
    "Períodos de mayor flujo": "Horarios acumulados con mayor actividad LPR",
    "Flujo por acceso": "Actividad LPR por punto de acceso",
    "Placas con mayor frecuencia": "Matrículas con más eventos LPR registrados",
}


DESCRIPCIONES_SECCIONES = {
    "Flujo por Punto de Acceso": "Muestra cuántos eventos se registraron en cada punto de acceso durante el período aplicado.",
    "Flujo por Hora del Día": "Compara la cantidad acumulada de eventos para cada hora del día dentro del período aplicado.",
    "Flujo por Punto de Acceso y Hora": "Permite identificar en qué horas se concentra la actividad de cada punto de acceso.",
    "Flujo Diario": "Presenta la evolución de eventos y usuarios identificados en cada fecha con datos.",
    "Flujo por Día de la Semana": "Resume los eventos registrados por día de la semana en el contexto seleccionado.",
    "Detalle Diario": "Complementa el gráfico con los conteos diarios de eventos y usuarios identificados.",
    "Entradas vs Salidas": "Compara los eventos clasificados como entrada, salida u otro movimiento.",
    "Entradas vs Salidas por Hora": "Muestra cómo se distribuyen las entradas y salidas a lo largo del día.",
    "Entradas vs Salidas por Ingreso": "Desglosa los movimientos registrados para cada categoría de ingreso.",
    "Entradas/Salidas por Punto de Acceso": "Detalla entradas, salidas y usuarios identificados en cada punto físico.",
    "Flujo por Tipo de Usuario": "Compara los eventos asociados a cada tipo de usuario informado por el sistema.",
    "Tipo de Usuario por Ingreso": "Relaciona los tipos de usuario con las categorías de ingreso utilizadas.",
    "Tipo de Usuario por Punto de Acceso": "Muestra qué tipos de usuario fueron registrados en cada punto de acceso.",
    "Flujo por Ingreso": "Compara el volumen de eventos de las categorías institucionales de acceso.",
    "Comparación de Flujo Horario por Ingreso": "Compara las horas de mayor actividad entre categorías de ingreso.",
    "Mapa de Calor: Día de la Semana × Hora": "La intensidad del color representa la cantidad de eventos para cada combinación de día y hora.",
    "Mapa de Calor: Punto de Acceso × Hora": "La intensidad del color representa la actividad registrada por punto de acceso y hora.",
    "Frecuencia de Utilización del Sistema": "Agrupa a los usuarios según la cantidad de eventos asociados durante el período.",
    "Frecuencia": "Agrupa a los usuarios según cuántos eventos tienen registrados en el contexto aplicado.",
    "Conclusiones y Hallazgos Automáticos": "Sintetiza patrones calculados a partir de los registros seleccionados, sin atribuir causas no demostradas.",
    "Días Pico Detallados": "Identifica las fechas con mayor y menor cantidad de eventos dentro del período.",
    "Validación y Calidad de Datos": "Informa la integridad del archivo y los registros que no pudieron utilizarse completamente.",
    "Valores Nulos por Columna": "Indica cuántos registros carecen de información en cada campo de origen.",
    "Puntos de Acceso Encontrados": "Lista los puntos detectados, su clasificación y el volumen de eventos asociado.",
    "1. Comportamiento Temporal": "Muestra cómo evolucionaron los eventos anormales por fecha y hora.",
    "2. Análisis Geográfico": "Compara los eventos anormales entre ingresos y puntos de acceso.",
    "3. Conclusiones Principales": "Resume los hallazgos calculados para los eventos anormales seleccionados.",
    "Resumen General de Movilidad": "Resume los registros biométricos peatonales, biométricos vehiculares y LPR incluidos por los filtros aplicados.",
    "Estadísticas vehiculares consolidadas": "Compara eventos de identificación biométrica VEH y LPR; la suma no representa vehículos físicos únicos.",
    "Flujo General Consolidado": "Compara los registros por tipo de movilidad y mecanismo incluidos en el contexto aplicado.",
    "Distribución Detallada por Categoría de Acceso": "Muestra la participación de cada una de las categorías institucionales de acceso.",
    "Flujo por Punto de Acceso Físico": "Ordena los puntos de acceso según la cantidad de eventos registrados.",
    "Comportamiento Horario Consolidado": "Compara la actividad peatonal y vehicular para cada hora del día.",
    "Comportamiento Diario": "Muestra la cantidad de registros por fecha dentro del período aplicado.",
    "Comportamiento Detallado por Hora": "Presenta la distribución horaria general y por categoría de ingreso.",
    "Mapa de Calor: Puntos de Acceso vs Hora": "Relaciona puntos de acceso y horas; los colores más intensos indican más eventos.",
    "Usuarios por Tipo y Punto de Acceso": "Compara los registros de usuarios por clasificación y lugar de acceso.",
    "Análisis de Tasas de Fallo y Éxito": "Distingue autenticaciones exitosas, fallos de reconocimiento, accesos denegados y otros resultados.",
    "1. Distribución de Resultados": "Muestra el número y porcentaje de eventos para cada resultado biométrico.",
    "2. Comportamiento por Ingreso": "Compara resultados biométricos entre las categorías de ingreso.",
    "3. Evolución de Tasas": "Muestra cómo variaron los resultados por fecha y hora del día.",
    "4. Hardware": "Compara los resultados por punto de acceso y por dispositivo registrado en HikCentral.",
    "Analítica Avanzada e Inteligencia": "Presenta comparaciones, concentraciones y casos que requieren revisión institucional.",
    "Calidad de Datos": "Resume la integridad del archivo biométrico utilizado en el análisis.",
    "Análisis Vehicular LPR": "Resume eventos LPR depurados, matrículas identificadas, sentidos y ubicaciones.",
    "Flujo Vehicular": "Muestra la actividad LPR por carril, minuto real y hora calendario dentro del período aplicado.",
    "Períodos de mayor flujo": "Ordena las franjas horarias por eventos LPR acumulados en todos los días analizados.",
    "Entradas vehiculares registradas por día": "Muestra los eventos LPR de entrada para cada fecha con datos.",
    "Actividad vehicular total en el tiempo": "Presenta la evolución diaria y la concentración por día de la semana y hora.",
    "Flujo por acceso": "Resume la franja acumulada de mayor actividad para cada punto de acceso LPR.",
    "Entradas y salidas LPR por ubicación": "Compara los eventos LPR de entrada y salida en 25 de Junio y Ferroviaria.",
    "Placas con mayor frecuencia": "Muestra las matrículas con más eventos LPR; cada evento es un registro, no un vehículo físico nuevo.",
    "Conclusiones Principales (Registros Biométricos)": "Resume los hallazgos calculados a partir de los eventos biométricos incluidos en los filtros aplicados.",
}


def mostrar_seccion(titulo: str, icono: str = "analytics"):
    """Renderiza un encabezado de sección."""
    titulo_visible = TITULOS_SECCIONES.get(titulo, titulo)
    st.markdown(
        f'<div class="section-header"><span class="material-symbols-rounded section-icon">{icono}</span>{titulo_visible}</div>',
        unsafe_allow_html=True,
    )
    descripcion = DESCRIPCIONES_SECCIONES.get(titulo)
    if descripcion:
        st.caption(descripcion)


def mostrar_contexto_resultados(df_biometrico=None, df_lpr=None, mecanismos=None):
    """Muestra una sola vez el contexto que realmente participa en los resultados."""
    partes = [df for df in [df_biometrico, df_lpr] if df is not None and not df.empty]
    fechas = []
    ubicaciones = set()
    for parte in partes:
        if "Fecha" in parte.columns:
            fechas.extend(pd.to_datetime(parte["Fecha"], errors="coerce").dropna().tolist())
        if "Ubicacion_Ingreso" in parte.columns:
            ubicaciones.update(
                parte["Ubicacion_Ingreso"].dropna().astype(str).loc[
                    lambda s: s.isin(["25 de Junio", "Ferroviaria"])
                ]
            )
    periodo = "Sin fechas disponibles"
    if fechas:
        periodo = f"{min(fechas):%d/%m/%Y} al {max(fechas):%d/%m/%Y}"
    ubicacion = ", ".join(sorted(ubicaciones)) if ubicaciones else "Todas las disponibles"
    mecanismo = ", ".join(mecanismos) if mecanismos else "Registros biométricos"
    st.info(
        f"Contexto aplicado: período {periodo} | Ubicación: {ubicacion} | "
        f"Mecanismo: {mecanismo}. Los valores corresponden a los filtros ya aplicados.",
        icon=":material/filter_alt:",
    )


def _calcular_analitica_integral(df_f, df_todos, df_consolidado_total, filtros_aplicados):
    """Calcula una vez las agregaciones que comparten las pestañas integrales."""
    tasas = ats.calcular_tasas_generales(df_f)
    top_usuarios_fallos = ats.calcular_top_usuarios_fallos(df_f)
    anomalias_avanzadas = ats.detectar_anomalias_avanzadas(df_f)

    comparacion_periodos = {}
    rango_fechas = filtros_aplicados.get("rango_fechas") or ()
    if len(rango_fechas) == 2 and (rango_fechas[1] - rango_fechas[0]).days > 0:
        dias_diferencia = (rango_fechas[1] - rango_fechas[0]).days + 1
        fecha_fin_anterior = rango_fechas[0] - pd.Timedelta(days=1)
        fecha_inicio_anterior = fecha_fin_anterior - pd.Timedelta(days=dias_diferencia - 1)
        filtros_anteriores = dict(filtros_aplicados)
        filtros_anteriores["rango_fechas"] = (fecha_inicio_anterior, fecha_fin_anterior)
        df_anterior, _ = aplicar_filtros_integrales(df_todos, None, filtros_anteriores)
        if not df_anterior.empty:
            comparacion_periodos = ats.comparar_periodos(df_f, df_anterior)

    stats_nuevas = {
        "resultados": ats.stats_resultados(df_f),
        "cruce_ingreso": ats.stats_cruce_ingreso_resultado(df_f),
        "cruce_hora": ats.stats_cruce_hora_resultado(df_f),
        "evolucion_diaria": ats.stats_evolucion_resultado(df_f),
        "dia_semana": ats.stats_dia_semana_resultado(df_f),
        "cruce_usuario": ats.stats_tipo_usuario_resultado(df_f),
        "cruce_punto": ats.stats_punto_acceso_resultado(df_f),
        "cruce_device": ats.stats_device_resultado(df_f),
        "heatmap": ats.stats_heatmap_dia_hora(df_f),
        "anomalias": ats.stats_comportamiento_anormal(df_f),
        "top_fallos": top_usuarios_fallos,
        "anomalias_avanzadas": anomalias_avanzadas,
        "comparacion_periodos": comparacion_periodos,
    }
    conclusiones = ats.generar_conclusiones_todos(df_f, tasas, stats_nuevas)
    stats_base = {
        "flujo_punto_acceso": flujo_por_punto_acceso(df_consolidado_total),
        "flujo_hora": flujo_por_hora(df_consolidado_total),
        "heatmap_punto_hora": flujo_punto_hora(df_consolidado_total),
        "heatmap_consolidado_hora": flujo_consolidado_hora(df_consolidado_total),
        "entradas_salidas": entradas_vs_salidas_general(df_consolidado_total),
        "entradas_salidas_hora": entradas_vs_salidas_por_hora(df_consolidado_total),
        "entradas_salidas_ingreso": entradas_vs_salidas_por_ingreso(df_consolidado_total),
        "flujo_ingreso": flujo_por_ingreso(df_consolidado_total),
        "flujo_consolidado": flujo_consolidado(df_consolidado_total),
        "tipo_usuario": flujo_por_tipo_usuario(df_consolidado_total),
        "tipo_usuario_ingreso": tipo_usuario_ingreso(df_consolidado_total),
        "flujo_diario": flujo_diario(df_consolidado_total),
        "flujo_diario_ingreso": flujo_diario_por_ingreso(df_consolidado_total),
        "dia_semana": flujo_dia_semana(df_consolidado_total),
        "heatmap_dia_hora": heatmap_dia_hora(df_consolidado_total),
        "ingreso_hora": ingreso_hora(df_consolidado_total),
        "punto_tipo_usuario": punto_tipo_usuario(df_consolidado_total),
        "frecuencia": frecuencia_utilizacion(df_consolidado_total)[0],
    }
    return tasas, stats_nuevas, conclusiones, stats_base


def _clave_filtros(filtros: dict) -> tuple:
    """Convierte el estado aplicado en una clave estable y comparable."""
    return tuple(
        (nombre, tuple(valor) if isinstance(valor, (list, tuple)) else valor)
        for nombre, valor in sorted(filtros.items())
    )


# ═════════════════════════════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL
# APLICACIÓN PRINCIPAL - MODO NORMALES
# ═════════════════════════════════════════════════════════════════════════════

def ejecutar_modo_exitoso():
    # Compatibilidad histórica: carga diferida para que deprecated no forme
    # parte del arranque ni de la sección operativa "Todos los Eventos".
    from deprecated.eventos_normales.data_loader import cargar_excel, validar_columnas, generar_reporte_calidad
    from deprecated.eventos_normales.data_processing import procesar_datos
    from deprecated.eventos_normales.export import exportar_dataset_filtrado, exportar_reporte_completo

    st.title(":material/check_circle: Análisis de eventos normales")
    st.markdown("Cargue un archivo Excel que contenga los registros de eventos normales para su análisis independiente.")

    archivo_subido = st.file_uploader(":material/upload_file: Cargar Excel de eventos normales", type=["xlsx"])

    if not archivo_subido:
        st.info("Esperando archivo. Por favor, suba un archivo Excel (.xlsx) para continuar.")
        st.stop()

    # ─── Cargar datos ────────────────────────────────────────────────────
    df_crudo = cargar_excel(archivo_subido)

    # ─── Validar columnas ────────────────────────────────────────────────
    validacion = validar_columnas(df_crudo)
    if not validacion["valido"]:
        st.error(f" Faltan columnas requeridas: {', '.join(validacion['faltantes'])}")
        st.stop()

    # ─── Reporte de calidad ──────────────────────────────────────────────
    calidad = generar_reporte_calidad(df_crudo)

    # ─── Procesar datos ──────────────────────────────────────────────────
    df, metricas = procesar_datos(df_crudo)
    
    # Excluir la categoría '25 DE JUNIO' del tipo de usuario / departamento
    df = df[df["Tipo_Usuario"] != "25 DE JUNIO"]
    
    # (Eliminado el filtro duro de Tipo_Usuario para incluir SIN CLASIFICAR)

    fecha_min = df["Fecha"].min()
    fecha_max = df["Fecha"].max()

    # ─── SIDEBAR: Filtros ────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## :material/filter_list: Filtros")

        st.button(
            " Restablecer filtros",
            icon=":material/restart_alt:",
            use_container_width=True,
            on_click=restablecer_widgets,
            args=({
                "filtro_fecha_inicio": fecha_min,
                "filtro_fecha_fin": fecha_max,
                "filtro_ingreso": [],
                "filtro_tipo_usuario": [],
                "filtro_movimiento": [],
                "filtro_punto_acceso": [],
                "filtro_hora": (0, 23),
            },),
        )

        st.markdown("---")

        # Rango de fechas
        fecha_inicio = st.date_input(
            " Fecha inicio",
            value=fecha_min,
            min_value=fecha_min,
            max_value=fecha_max,
            key="filtro_fecha_inicio",
        )
        fecha_fin = st.date_input(
            " Fecha fin",
            value=fecha_max,
            min_value=fecha_min,
            max_value=fecha_max,
            key="filtro_fecha_fin",
        )

        st.markdown("---")

        # Ingreso
        ingreso_opciones = sorted(df["Ingreso"].unique().tolist())
        ingreso_sel = st.multiselect(
            "Ingreso",
            options=ingreso_opciones,
            default=[],
            key="filtro_ingreso",
            placeholder="Todos"
        )

        # Tipo de usuario
        tipo_opciones = sorted(df["Tipo_Usuario"].unique().tolist())
        tipo_sel = st.multiselect(
            " Tipo de Usuario",
            options=tipo_opciones,
            default=[],
            key="filtro_tipo_usuario",
            placeholder="Todos"
        )

        # Movimiento
        mov_opciones = sorted(df["Movimiento"].unique().tolist())
        mov_sel = st.multiselect(
            " Movimiento",
            options=mov_opciones,
            default=[],
            key="filtro_movimiento",
            placeholder="Todos"
        )

        # Punto de acceso
        punto_opciones = sorted(df["Punto de acceso"].unique().tolist())
        punto_sel = st.multiselect(
            " Punto de Acceso",
            options=punto_opciones,
            default=[],
            format_func=obtener_nombre_amigable,
            key="filtro_punto_acceso",
            placeholder="Todos"
        )

        # Hora
        hora_rango = st.slider(
            " Rango de Hora",
            min_value=0,
            max_value=23,
            value=(0, 23),
            key="filtro_hora",
        )

        st.markdown("---")

        # ─── Exportación ─────────────────────────────────────────────────
        st.markdown("##  Exportar")

    # ─── Aplicar filtros ─────────────────────────────────────────────────
    df_filtrado = df.copy()
    
    if fecha_inicio and fecha_fin:
        df_filtrado = df_filtrado[(df_filtrado["Fecha"] >= fecha_inicio) & (df_filtrado["Fecha"] <= fecha_fin)]
        
    if ingreso_sel:
        df_filtrado = df_filtrado[df_filtrado["Ingreso"].isin(ingreso_sel)]
        
    if tipo_sel:
        df_filtrado = df_filtrado[df_filtrado["Tipo_Usuario"].isin(tipo_sel)]
        
    if mov_sel:
        df_filtrado = df_filtrado[df_filtrado["Movimiento"].isin(mov_sel)]
        
    if punto_sel:
        df_filtrado = df_filtrado[df_filtrado["Punto de acceso"].isin(punto_sel)]
        
    df_filtrado = df_filtrado[
        (df_filtrado["Hora_Dia"] >= hora_rango[0]) & (df_filtrado["Hora_Dia"] <= hora_rango[1])
    ]

    filtros_activos = (
        fecha_inicio != fecha_min
        or fecha_fin != fecha_max
        or len(ingreso_sel) > 0
        or len(tipo_sel) > 0
        or len(mov_sel) > 0
        or len(punto_sel) > 0
        or hora_rango != (0, 23)
    )

    # ─── Recalcular métricas si hay filtros ──────────────────────────────
    if filtros_activos:
        total_filtrado = len(df_filtrado)
        usuarios_filtrado = df_filtrado.loc[df_filtrado["Persona"] != "", "Persona"].nunique()
        entradas_f = int((df_filtrado["Movimiento"] == "ENTRADA").sum())
        salidas_f = int((df_filtrado["Movimiento"] == "SALIDA").sum())
        otros_f = int((df_filtrado["Movimiento"] == "OTRO").sum())
        dias_f = df_filtrado["Fecha"].nunique()
        promedio_f = round(total_filtrado / dias_f, 2) if dias_f > 0 else 0
    else:
        total_filtrado = metricas["total_eventos"]
        usuarios_filtrado = metricas["usuarios_unicos"]
        entradas_f = metricas["entradas"]
        salidas_f = metricas["salidas"]
        otros_f = metricas["otros"]
        dias_f = metricas["dias_unicos"]
        promedio_f = metricas["promedio_diario"]

# ─── Exportar botones (en sidebar) ───────────────────────────────────
    with st.sidebar:
        # ================================================================
        # PDF
        # ================================================================

        if "pdf_bytes" not in st.session_state:
            st.session_state.pdf_bytes = None

        def generar_pdf():
            stats_pdf = {
                "flujo_punto_acceso": flujo_por_punto_acceso(df_filtrado),
                "flujo_hora": flujo_por_hora(df_filtrado),
                "heatmap_punto_hora": flujo_punto_hora(df_filtrado),

                "entradas_salidas": entradas_vs_salidas_general(df_filtrado),
                "entradas_salidas_hora": entradas_vs_salidas_por_hora(df_filtrado),
                "entradas_salidas_ingreso": entradas_vs_salidas_por_ingreso(df_filtrado),

                "flujo_ingreso": flujo_por_ingreso(df_filtrado),

                "tipo_usuario": flujo_por_tipo_usuario(df_filtrado),
                "tipo_usuario_ingreso": tipo_usuario_ingreso(df_filtrado),

                "flujo_diario": flujo_diario(df_filtrado),
                "flujo_diario_ingreso": flujo_diario_por_ingreso(df_filtrado),

                "dia_semana": flujo_dia_semana(df_filtrado),
                "heatmap_dia_hora": heatmap_dia_hora(df_filtrado),

                "ingreso_hora": ingreso_hora(df_filtrado),

                "punto_tipo_usuario": punto_tipo_usuario(df_filtrado),

                "frecuencia": frecuencia_utilizacion(df_filtrado)[0],
            }

            graficos_pdf = construir_graficos_reporte(
                df_filtrado,
                stats_pdf,
            )

            conclusiones_pdf = generar_conclusiones(
                df_filtrado,
                metricas,
            )

            st.session_state.pdf_bytes = exportar_reporte_pdf(
                df=df_filtrado,
                metricas={
                    **metricas,
                    "total_eventos": total_filtrado,
                    "usuarios_unicos": usuarios_filtrado,
                    "entradas": entradas_f,
                    "salidas": salidas_f,
                    "otros": otros_f,
                    "dias_unicos": dias_f,
                    "promedio_diario": promedio_f,
                },
                calidad=calidad,
                conclusiones=conclusiones_pdf,
                graficos=graficos_pdf,
                stats=stats_pdf,
            )


        st.button(
            "Generar reporte ejecutivo PDF",
            icon=":material/picture_as_pdf:",
            on_click=generar_pdf,
            use_container_width=True,
        )

        if st.session_state.pdf_bytes is not None:
            st.download_button(
                "Descargar reporte ejecutivo PDF",
                icon=":material/download:",
                data=st.session_state.pdf_bytes,
                file_name=(
                    f"reporte_flujo_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                ),
                mime="application/pdf",
                use_container_width=True,
            )


        # ================================================================
        # REPORTE COMPLETO EXCEL
        # ================================================================

        if "reporte_excel_bytes" not in st.session_state:
            st.session_state.reporte_excel_bytes = None

        def generar_reporte_excel():
            st.session_state.reporte_excel_bytes = exportar_reporte_completo(
                df_filtrado,
                {
                    **metricas,
                    "total_eventos": total_filtrado,
                    "usuarios_unicos": usuarios_filtrado,
                    "entradas": entradas_f,
                    "salidas": salidas_f,
                    "otros": otros_f,
                    "dias_unicos": dias_f,
                    "promedio_diario": promedio_f,
                },
                calidad,
            )


        st.button(
            "Generar reporte completo Excel",
            icon=":material/table_view:",
            on_click=generar_reporte_excel,
            use_container_width=True,
        )

        if st.session_state.reporte_excel_bytes is not None:
            st.download_button(
                "Descargar reporte completo",
                icon=":material/download:",
                data=st.session_state.reporte_excel_bytes,
                file_name=(
                    f"reporte_flujo_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet"
                ),
                use_container_width=True,
            )


        # ================================================================
        # DATASET FILTRADO
        # ================================================================

        if "dataset_filtrado_bytes" not in st.session_state:
            st.session_state.dataset_filtrado_bytes = None

        def generar_dataset_filtrado():
            st.session_state.dataset_filtrado_bytes = (
                exportar_dataset_filtrado(df_filtrado)
            )


        st.button(
            "Preparar dataset filtrado",
            icon=":material/database:",
            on_click=generar_dataset_filtrado,
            use_container_width=True,
        )

        if st.session_state.dataset_filtrado_bytes is not None:
            st.download_button(
                "Descargar dataset filtrado",
                icon=":material/download:",
                data=st.session_state.dataset_filtrado_bytes,
                file_name=(
                    f"datos_filtrados_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet"
                ),
                use_container_width=True,
            )


        # ================================================================
        # INFORMACIÓN
        # ================================================================

        st.markdown("---")

        st.markdown(
            f"""
            <small style='color:#7F8C8D'>
            Archivo: {archivo_subido.name}
            </small>
            """,
            unsafe_allow_html=True,
    )

    # ═════════════════════════════════════════════════════════════════════
    # CONTENIDO PRINCIPAL
    # ═════════════════════════════════════════════════════════════════════

    # ─── Header ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="main-header">
        <h1> Sistema de Reportes — Flujo de Ingresos Peatonales</h1>
        <p>Período: {metricas['fecha_inicial'].strftime('%d/%m/%Y')} — {metricas['fecha_final'].strftime('%d/%m/%Y')} &nbsp;|&nbsp;
        Archivo: {archivo_subido.name}</p>
    </div>
    """, unsafe_allow_html=True)

    # Banner de filtros activos
    if filtros_activos:
        st.markdown(
            f"<div class='warning-box'><span class='material-symbols-rounded'>filter_list</span> <strong>Filtros activos</strong> — Mostrando <strong>{total_filtrado:,}</strong> de <strong>{metricas['total_eventos']:,}</strong> eventos ({total_filtrado/metricas['total_eventos']*100:.1f}%)</div>",
            unsafe_allow_html=True
        )

    if total_filtrado == 0:
        st.warning("No hay datos para los filtros seleccionados. Ajuste los filtros.")
        st.stop()

    mostrar_contexto_resultados(
        df_biometrico=df_filtrado,
        mecanismos=["Biométrico"],
    )

    # ─── 1. Métricas principales ─────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        mostrar_metrica("Eventos biométricos registrados", total_filtrado, "")
    with col2:
        mostrar_metrica("Usuarios identificados", usuarios_filtrado, "")
    with col3:
        mostrar_metrica("Eventos de entrada", entradas_f, "")
    with col4:
        mostrar_metrica("Eventos de salida", salidas_f, "")
    with col5:
        mostrar_metrica("Promedio diario de eventos", promedio_f, "")

    st.markdown("")

    col6, col7, col8, col9 = st.columns(4)
    with col6:
        mostrar_metrica("Puntos de acceso identificados", df_filtrado["Punto de acceso"].nunique(), "")
    with col7:
        mostrar_metrica("Categorías de ingreso", df_filtrado["Ingreso"].nunique(), "")
    with col8:
        mostrar_metrica("Días con registros", dias_f, "")
    with col9:
        mostrar_metrica("Eventos sin sentido de circulación", otros_f, "")

    # ═════════════════════════════════════════════════════════════════════
    # PESTAÑAS PRINCIPALES
    # ═════════════════════════════════════════════════════════════════════

    tab_acceso, tab_horario, tab_diario, tab_io, tab_usuario, tab_ingreso, tab_heatmaps, tab_frecuencia, tab_conclusiones, tab_calidad = st.tabs([
        ":material/door_front: Flujo por acceso",
        ":material/schedule: Flujo horario",
        ":material/calendar_month: Flujo diario",
        ":material/swap_horiz: Entradas vs. salidas",
        ":material/person: Tipo de usuario",
        ":material/login: Ingreso",
        ":material/grid_on: Mapas de calor",
        ":material/query_stats: Frecuencia",
        ":material/summarize: Conclusiones",
        ":material/fact_check: Calidad de datos",
    ])

    # ─── TAB 1: Flujo por punto de acceso ────────────────────────────────
    with tab_acceso:
        mostrar_seccion("Flujo por Punto de Acceso")

        df_flujo_acceso = flujo_por_punto_acceso(df_filtrado)

        # Gráfico
        fig_acceso = grafico_flujo_punto_acceso(df_flujo_acceso)
        st.plotly_chart(
            fig_acceso, use_container_width=True,
            key="grafico_flujo_punto_acceso",
        )

        # Tabla
        st.dataframe(
            df_flujo_acceso.style.format({
                "Eventos": "{:,}",
                "Porcentaje": "{:.2f}%",
                "Usuarios_Unicos": "{:,}",
            }),
            use_container_width=True,
            height=min(len(df_flujo_acceso) * 38 + 40, 800),
        )

        # Ranking
        st.markdown("**Cinco puntos de acceso con más eventos registrados**")
        for posicion, (_, row) in enumerate(df_flujo_acceso.head(5).iterrows(), start=1):
            st.markdown(
                f"**{posicion}.º** {row['Punto de acceso']} — "
                f"{row['Eventos']:,} eventos ({row['Porcentaje']}%) — "
                f"Ingreso: {row['Ingreso']} — {row['Movimiento']}"
            )

    # ─── TAB 2: Flujo horario ────────────────────────────────────────────
    with tab_horario:
        mostrar_seccion("Flujo por Hora del Día")

        df_flujo_hora = flujo_por_hora(df_filtrado)
        picos = horas_pico(df_filtrado)

        # Métricas de hora pico
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            hp_gen = picos["general"]
            horas_str = ", ".join([f"{h:02d}:00" for h in hp_gen["horas"]])
            empate_str = " (empate)" if hp_gen["empate"] else ""
            st.metric("Horario con más eventos acumulados", f"{horas_str}{empate_str}", f"{hp_gen['eventos']:,} eventos")
        with col_h2:
            if "entrada" in picos:
                hp_ent = picos["entrada"]
                horas_str = ", ".join([f"{h:02d}:00" for h in hp_ent["horas"]])
                empate_str = " (empate)" if hp_ent["empate"] else ""
                st.metric("Horario con más entradas acumuladas", f"{horas_str}{empate_str}", f"{hp_ent['eventos']:,} eventos")
        with col_h3:
            if "salida" in picos:
                hp_sal = picos["salida"]
                horas_str = ", ".join([f"{h:02d}:00" for h in hp_sal["horas"]])
                empate_str = " (empate)" if hp_sal["empate"] else ""
                st.metric("Horario con más salidas acumuladas", f"{horas_str}{empate_str}", f"{hp_sal['eventos']:,} eventos")

        # Hora pico por ingreso
        if picos.get("por_ingreso"):
            st.markdown("**Hora pico por ingreso:**")
            cols_ingreso = st.columns(len(picos["por_ingreso"]))
            for i, (ingreso, datos) in enumerate(picos["por_ingreso"].items()):
                with cols_ingreso[i]:
                    horas_str = ", ".join([f"{h:02d}:00" for h in datos["horas"]])
                    empate_str = " (empate)" if datos["empate"] else ""
                    st.metric(f":material/location_on: {ingreso}", f"{horas_str}{empate_str}", f"{datos['eventos']:,} eventos")

        # Gráfico
        fig_hora = grafico_flujo_hora(df_flujo_hora)
        st.plotly_chart(
            fig_hora, use_container_width=True,
            key="grafico_flujo_hora",
        )

        # Tabla
        st.dataframe(
            df_flujo_hora.style.format({"Eventos": "{:,}", "Usuarios_Unicos": "{:,}"}), use_container_width=True)

        # ─── Heatmap punto × hora ───────────────────────────────────────
        mostrar_seccion("Flujo por Punto de Acceso y Hora")

        pivot_ph = flujo_punto_hora(df_filtrado)
        fig_heatmap_ph = grafico_heatmap_punto_hora(pivot_ph)
        st.plotly_chart(
            fig_heatmap_ph, use_container_width=True,
            key="grafico_heatmap_punto_hora_tab_horario",
        )

        # Hora pico por punto de acceso
        if picos.get("por_punto"):
            st.markdown("**Hora pico por punto de acceso:**")
            pico_punto_data = []
            for punto, datos in picos["por_punto"].items():
                horas_str = ", ".join([f"{h:02d}:00" for h in datos["horas"]])
                empate_str = " (empate)" if datos["empate"] else ""
                pico_punto_data.append({
                    "Punto de Acceso": punto,
                    "Hora Pico": f"{horas_str}{empate_str}",
                    "Eventos en Hora Pico": datos["eventos"],
                })
            st.dataframe(
                pd.DataFrame(pico_punto_data).style.format({"Eventos en Hora Pico": "{:,}"}), use_container_width=True)

    # ─── TAB 3: Flujo diario ────────────────────────────────────────────
    with tab_diario:
        mostrar_seccion("Flujo Diario")

        df_diario = flujo_diario(df_filtrado)
        dp = dias_pico(df_filtrado)

        # Métricas de días pico
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            dias_str = ", ".join([str(d) for d in dp["mayor_flujo"]["dias"]])
            st.metric("Fecha con más eventos", dias_str, f"{dp['mayor_flujo']['eventos']:,} eventos")
        with col_d2:
            dias_str = ", ".join([str(d) for d in dp["menor_flujo"]["dias"]])
            st.metric("Fecha con menos eventos", dias_str, f"{dp['menor_flujo']['eventos']:,} eventos")
        with col_d3:
            st.metric("Promedio diario de eventos", formato_numero(promedio_f), f"{dias_f} días con registros")

        # Gráfico
        fig_diario = grafico_flujo_diario(df_diario)
        st.plotly_chart(
            fig_diario, use_container_width=True,
            key="grafico_flujo_diario",
        )

        # Día de la semana
        mostrar_seccion("Flujo por Día de la Semana")
        df_dia_semana = flujo_dia_semana(df_filtrado)

        fig_dsemana = grafico_dia_semana(df_dia_semana)
        st.plotly_chart(
            fig_dsemana, use_container_width=True,
            key="grafico_dia_semana",
        )

        st.dataframe(
            df_dia_semana.style.format({
                "Eventos": "{:,}",
                "Promedio": "{:,.1f}",
            }), use_container_width=True)

        # Tabla de flujo diario
        mostrar_seccion("Detalle Diario")
        st.dataframe(
            df_diario.style.format({
                "Eventos": "{:,}",
                "Usuarios_Unicos": "{:,}",
            }),
            use_container_width=True,
        )

    # ─── TAB 4: Entradas vs Salidas ─────────────────────────────────────
    with tab_io:
        mostrar_seccion("Entradas vs Salidas")

        # General
        df_ev_gen = entradas_vs_salidas_general(df_filtrado)
        st.dataframe(
            df_ev_gen.style.format({
                "Eventos": "{:,}",
                "Porcentaje": "{:.2f}%",
            }),
            use_container_width=True,
        )
        st.markdown("<br><br>", unsafe_allow_html=True)
        fig_ev = grafico_entradas_salidas(df_ev_gen)
        st.plotly_chart(
            fig_ev, use_container_width=True,
            key="grafico_entradas_salidas_general",
        )

        # Por hora
        mostrar_seccion("Entradas vs Salidas por Hora")
        df_ev_hora = entradas_vs_salidas_por_hora(df_filtrado)
        fig_ev_hora = grafico_entradas_salidas_hora(df_ev_hora)
        st.plotly_chart(
            fig_ev_hora, use_container_width=True,
            key="grafico_entradas_salidas_hora",
        )

        # Por ingreso
        mostrar_seccion("Entradas vs Salidas por Ingreso")
        df_ev_ingreso = entradas_vs_salidas_por_ingreso(df_filtrado)
        st.dataframe(
            df_ev_ingreso.style.format({
                "Eventos": "{:,}",
                "Porcentaje": "{:.2f}%",
                "Total_Ingreso": "{:,}",
            }), use_container_width=True)

        # Por punto de acceso (9.14)
        mostrar_seccion("Entradas/Salidas por Punto de Acceso")
        df_ev_punto = entradas_vs_salidas_por_punto(df_filtrado)
        st.dataframe(
            df_ev_punto.style.format({
                "Eventos": "{:,}",
                "Usuarios_Unicos": "{:,}",
            }),
            use_container_width=True,
        )

    # ─── TAB 5: Tipo de usuario ─────────────────────────────────────────
    with tab_usuario:
        mostrar_seccion("Flujo por Tipo de Usuario")

        df_tipo = flujo_por_tipo_usuario(df_filtrado)
        fig_tipo = grafico_tipo_usuario(df_tipo)
        st.plotly_chart(
            fig_tipo, use_container_width=True,
            key="grafico_tipo_usuario",
        )

        st.dataframe(
            df_tipo.style.format({
                "Eventos": "{:,}",
                "Porcentaje": "{:.2f}%",
                "Usuarios_Unicos": "{:,}",
            }), use_container_width=True)

        # Tipo de usuario × ingreso (9.8)
        mostrar_seccion("Tipo de Usuario por Ingreso")
        df_tu_ingreso = tipo_usuario_ingreso(df_filtrado)
        fig_tu_ingreso = grafico_tipo_usuario_ingreso(df_tu_ingreso)
        st.plotly_chart(
            fig_tu_ingreso, use_container_width=True,
            key="grafico_tipo_usuario_ingreso",
        )

        st.dataframe(
            df_tu_ingreso.style.format({
                "Eventos": "{:,}",
                "Porcentaje": "{:.2f}%",
            }), use_container_width=True)

        # Punto × tipo de usuario (9.13)
        mostrar_seccion("Tipo de Usuario por Punto de Acceso")
        df_pu_tipo = punto_tipo_usuario(df_filtrado)
        fig_pu_tipo = grafico_punto_tipo_usuario(df_pu_tipo)
        st.plotly_chart(
            fig_pu_tipo, use_container_width=True,
            key="grafico_punto_tipo_usuario",
        )

    # ─── TAB 6: Ingreso ──────────────────────────────────────────────────
    with tab_ingreso:
        mostrar_seccion("Flujo por Ingreso")

        df_ingreso_stats = flujo_por_ingreso(df_filtrado)
        fig_ingreso = grafico_ingreso(df_ingreso_stats)
        st.plotly_chart(
            fig_ingreso, use_container_width=True,
            key="grafico_flujo_por_ingreso",
        )

        st.dataframe(
            df_ingreso_stats.style.format({
                "Eventos": "{:,}",
                "Porcentaje": "{:.2f}%",
                "Usuarios_Unicos": "{:,}",
            }), use_container_width=True)

        # Ingreso + hora (9.12)
        mostrar_seccion("Comparación de Flujo Horario por Ingreso")
        df_ch = ingreso_hora(df_filtrado)
        fig_ch = grafico_ingreso_hora(df_ch)
        st.plotly_chart(
            fig_ch, use_container_width=True,
            key="grafico_ingreso_hora",
        )

        # Accesos no clasificados
        if metricas.get("accesos_no_clasificados"):
            st.markdown("---")
            st.markdown("""
            <div class="warning-box">
                    <span class="material-symbols-rounded">warning</span> <strong>Accesos no clasificados:</strong> Los siguientes puntos de acceso
                no pudieron ser asignados a un ingreso conocido.
            </div>
            """, unsafe_allow_html=True)
            for acceso in metricas["accesos_no_clasificados"]:
                st.markdown(f"- `{acceso}`")

    # ─── TAB 7: Heatmaps ────────────────────────────────────────────────
    with tab_heatmaps:
        mostrar_seccion("Mapa de Calor: Día de la Semana × Hora")
        st.markdown("Identificación visual de los períodos de mayor actividad.")

        pivot_dh = heatmap_dia_hora(df_filtrado)
        fig_dh = grafico_heatmap_dia_hora(pivot_dh)
        st.plotly_chart(
            fig_dh, use_container_width=True,
            key="grafico_heatmap_dia_hora",
        )

        mostrar_seccion("Mapa de Calor: Punto de Acceso × Hora")
        pivot_ph2 = flujo_punto_hora(df_filtrado)
        fig_ph2 = grafico_heatmap_punto_hora(pivot_ph2)
        st.plotly_chart(
            fig_ph2, use_container_width=True,
            key="grafico_heatmap_punto_hora_tab_heatmaps",
        )

    # ─── TAB 8: Frecuencia de utilización ────────────────────────────────
    with tab_frecuencia:
        mostrar_seccion("Frecuencia de Utilización del Sistema")

        rangos_df, stats_df = frecuencia_utilizacion(df_filtrado)

        # Estadísticas
        st.markdown("#### Resumen de frecuencia por usuario")
        st.caption("Resume el promedio, la mediana y los extremos de eventos asociados a cada usuario identificado.")
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        # Gráfico
        fig_freq = grafico_frecuencia(rangos_df)
        st.plotly_chart(
            fig_freq, use_container_width=True,
            key="grafico_frecuencia_utilizacion",
        )

        # Tabla de rangos
        st.markdown("#### Usuarios agrupados por cantidad de eventos")
        st.caption("Cada rango indica cuántos usuarios registraron una cantidad similar de eventos.")
        st.dataframe(
            rangos_df.style.format({"Usuarios": "{:,}"}),
            use_container_width=True,
            hide_index=True,
        )

    # ─── TAB 9: Conclusiones ────────────────────────────────────────────
    with tab_conclusiones:
        mostrar_seccion("Conclusiones y Hallazgos Automáticos")
        st.markdown("""
        <div class="info-box">
            <span class="material-symbols-rounded">info</span> Las siguientes conclusiones son <strong>observaciones basadas en los datos</strong>.
            No representan afirmaciones de causalidad. Los patrones observados deben ser
            interpretados en conjunto con el conocimiento institucional.
        </div>
        """, unsafe_allow_html=True)

        conclusiones = generar_conclusiones(df_filtrado, metricas)
        import re
        for i, conclusion in enumerate(conclusiones, 1):
            conclusion_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', conclusion)
            st.markdown(
                f'<div class="conclusion-item"><strong>{i}.</strong> {conclusion_html}</div>',
                unsafe_allow_html=True,
            )

        # Días pico detallados
        st.markdown("---")
        dp_full = dias_pico(df_filtrado)
        mostrar_seccion("Días Pico Detallados")

        col_dp1, col_dp2 = st.columns(2)
        with col_dp1:
            st.markdown("**Días de mayor flujo:**")
            for d in dp_full["mayor_flujo"]["dias"]:
                st.markdown(f"- {d}: **{dp_full['mayor_flujo']['eventos']:,}** eventos")
            if dp_full.get("mayor_entrada"):
                st.markdown("**Mayor día de entradas:**")
                for d in dp_full["mayor_entrada"]["dias"]:
                    st.markdown(f"- {d}: **{dp_full['mayor_entrada']['eventos']:,}** eventos")
        with col_dp2:
            st.markdown("**Días de menor flujo:**")
            for d in dp_full["menor_flujo"]["dias"]:
                st.markdown(f"- {d}: **{dp_full['menor_flujo']['eventos']:,}** eventos")
            if dp_full.get("mayor_salida"):
                st.markdown("**Mayor día de salidas:**")
                for d in dp_full["mayor_salida"]["dias"]:
                    st.markdown(f"- {d}: **{dp_full['mayor_salida']['eventos']:,}** eventos")

    # ─── TAB 10: Calidad de datos ────────────────────────────────────────
    with tab_calidad:
        mostrar_seccion("Validación y Calidad de Datos")
        st.caption("Esta sección utiliza el archivo original y no cambia cuando se aplican filtros al análisis.")

        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            mostrar_metrica("Registros originales", calidad["total_registros"], "")
        with col_q2:
            mostrar_metrica("Registros con fecha válida", calidad["registros_validos"], "")
        with col_q3:
            mostrar_metrica("Fechas inválidas", calidad["fechas_invalidas"], "event_busy")

        col_q4, col_q5, col_q6 = st.columns(3)
        with col_q4:
            mostrar_metrica("Registros sin punto de acceso", calidad["acceso_vacio"], "")
        with col_q5:
            mostrar_metrica("Registros sin departamento", calidad["departamento_vacio"], "")
        with col_q6:
            mostrar_metrica("Registros sin nombre o apellido", calidad["registros_sin_nombre"], "")

        st.markdown("---")

        col_u1, col_u2, col_u3 = st.columns(3)
        with col_u1:
            mostrar_metrica("Puntos de acceso diferentes", calidad["unicos_punto_acceso"], "")
        with col_u2:
            mostrar_metrica("Dispositivos diferentes", calidad["unicos_device_name"], "")
        # Nulos detallados
        mostrar_seccion("Valores Nulos por Columna")
        nulos_df = pd.DataFrame(
            list(calidad["nulos_por_columna"].items()),
            columns=["Columna", "Valores Nulos"],
        )
        st.dataframe(nulos_df, use_container_width=True, hide_index=True)

        # Valores únicos de punto de acceso
        mostrar_seccion("Puntos de Acceso Encontrados")
        puntos_df = df.groupby("Punto de acceso").agg(
            Eventos=("Hora", "count"),
            Ingreso=("Ingreso", "first"),
            Movimiento=("Movimiento", "first"),
        ).reset_index().sort_values("Eventos", ascending=False)
        puntos_df["Punto de acceso"] = puntos_df["Punto de acceso"].apply(obtener_nombre_amigable)
        st.dataframe(
            puntos_df.style.format({"Eventos": "{:,}"}), use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL - MODO EVENTOS ANORMALES
# ═════════════════════════════════════════════════════════════════════════════

def ejecutar_modo_fallidos():
    # Compatibilidad histórica, deliberadamente fuera de la navegación activa.
    from deprecated.eventos_fallidos.failed_data_loader import cargar_excel_fallidos, detectar_columnas_fallidos, reporte_calidad_fallidos
    from deprecated.eventos_fallidos.failed_data_processing import procesar_datos_fallidos
    from deprecated.eventos_fallidos import failed_statistics_calc as fs
    from deprecated.eventos_fallidos import failed_visualizations as fv
    from deprecated.eventos_fallidos.failed_pdf_report import exportar_reporte_fallidos_pdf

    st.title(":material/warning: Análisis de eventos anormales")
    st.markdown("Cargue un archivo Excel que contenga los registros de eventos anormales para su análisis independiente.")
    
    archivo_subido = st.file_uploader(":material/upload_file: Cargar Excel de eventos anormales", type=["xlsx"])
    
    if not archivo_subido:
        st.info("Esperando archivo. Por favor, suba un archivo Excel (.xlsx) para continuar.")
        st.stop()
        
    df_crudo = cargar_excel_fallidos(archivo_subido)
    mapeo = detectar_columnas_fallidos(df_crudo)
    calidad = reporte_calidad_fallidos(df_crudo, mapeo)
    
    if calidad["columnas_faltantes"]:
        st.warning(f"Las siguientes columnas clave no fueron detectadas: {', '.join(calidad['columnas_faltantes'])}. Algunas funcionalidades podrían no estar disponibles.", icon=":material/warning:")
        
    df, metricas = procesar_datos_fallidos(df_crudo, mapeo)
    
    # Excluir la categoría '25 DE JUNIO' del tipo de usuario / departamento
    df = df[df["Tipo_Usuario"] != "25 DE JUNIO"]
    
    fecha_min = pd.to_datetime(df["Fecha"].dropna()).min() if not df["Fecha"].dropna().empty else None
    fecha_max = pd.to_datetime(df["Fecha"].dropna()).max() if not df["Fecha"].dropna().empty else None
    ingresos = sorted([str(x) for x in df["Ingreso"].unique()])

    # ─── SIDEBAR: Filtros para Eventos Anormales ───
    with st.sidebar:
        st.markdown("## :material/filter_list: Filtros de eventos anormales")
        st.button(
            " Restablecer filtros anormales",
            icon=":material/restart_alt:",
            key="reset_fallidos",
            use_container_width=True,
            on_click=restablecer_widgets,
            args=({"ff_inicio": fecha_min, "ff_fin": fecha_max, "ff_ingreso": ingresos},),
        )
            
        st.markdown("---")
        
        if pd.notnull(fecha_min) and pd.notnull(fecha_max):
            fecha_inicio = st.date_input(" Fecha inicio", value=fecha_min, min_value=fecha_min, max_value=fecha_max, key="ff_inicio")
            fecha_fin = st.date_input(" Fecha fin", value=fecha_max, min_value=fecha_min, max_value=fecha_max, key="ff_fin")
        else:
            fecha_inicio, fecha_fin = None, None
            
        ingreso_sel = st.multiselect("Ingreso", options=ingresos, default=ingresos, key="ff_ingreso")
        
    # ─── Aplicar Filtros ───
    df_f = df.copy()
    if fecha_inicio and fecha_fin:
        df_f = df_f[(pd.to_datetime(df_f["Fecha"]) >= pd.to_datetime(fecha_inicio)) & (pd.to_datetime(df_f["Fecha"]) <= pd.to_datetime(fecha_fin))]
    if ingreso_sel:
        df_f = df_f[df_f["Ingreso"].isin(ingreso_sel)]
        
    if df_f.empty:
        st.warning("No hay datos que coincidan con los filtros seleccionados.")
        st.stop()

    mostrar_contexto_resultados(
        df_biometrico=df_f,
        mecanismos=["Eventos biométricos anormales"],
    )
        
    # ─── Cálculos ───
    stats = {
        "por_ingreso": fs.stats_fallos_por_ingreso(df_f),
        "por_hora": fs.stats_fallos_por_hora(df_f),
        "evolucion_diaria": fs.stats_fallos_evolucion_diaria(df_f),
        "por_punto": fs.stats_fallos_por_punto(df_f),
        "dia_semana": fs.stats_fallos_dia_semana(df_f)
    }
    
    conclusiones = fs.generar_conclusiones_fallidos(df_f, stats)
    
    # ─── Renderizado ───
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1: mostrar_metrica("Total Eventos Anormales", len(df_f), "")
    with col2: 
        if not stats["por_ingreso"].empty:
            mostrar_metrica("Ingreso más afectado", stats["por_ingreso"].iloc[0]["Ingreso"], "warning")
        else:
            mostrar_metrica("Ingreso", "N/A", "warning")
    with col3: mostrar_metrica("Días Analizados", df_f["Fecha"].nunique() if not df_f["Fecha"].dropna().empty else 0, "")
    
    mostrar_seccion("1. Comportamiento Temporal")
    if not stats["evolucion_diaria"].empty and not stats["por_hora"].empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fv.grafico_fallos_evolucion_diaria(stats["evolucion_diaria"]), use_container_width=True, key='grafico_fallos_evolucion_diaria_1068')
        with c2:
            st.plotly_chart(fv.grafico_fallos_por_hora(stats["por_hora"]), use_container_width=True, key='grafico_fallos_por_hora_1070')
            
    mostrar_seccion("2. Análisis Geográfico")
    if not stats["por_ingreso"].empty and not stats["por_punto"].empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fv.grafico_fallos_por_ingreso(stats["por_ingreso"]), use_container_width=True, key='grafico_fallos_por_ingreso_1076')
        with c2:
            st.plotly_chart(fv.grafico_fallos_por_punto(stats["por_punto"]), use_container_width=True, key='grafico_fallos_por_punto_1078')
            
    mostrar_seccion("3. Conclusiones Principales")
    for c in conclusiones:
        st.info(c)
        
    with st.sidebar:
        st.markdown("## :material/download: Exportar reporte")
        if st.button("Generar reporte PDF (anormales)", icon=":material/picture_as_pdf:", use_container_width=True, type="primary"):
            with st.spinner("Generando PDF..."):
                try:
                    pdf_buffer = exportar_reporte_fallidos_pdf(df_f, stats, conclusiones)
                    st.download_button(
                        label="Descargar PDF",
                        icon=":material/download:",
                        data=pdf_buffer,
                        file_name=f"Reporte_Eventos_Anormales_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                    st.success(" PDF listo.")
                except Exception as e:
                    st.error(f"Error al generar PDF: {str(e)}")

# ═════════════════════════════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL - MODO TODOS LOS EVENTOS
# ═════════════════════════════════════════════════════════════════════════════

def ejecutar_modo_todos():
    st.title(":material/dashboard: Sistema de Accesos UTMACH")
    st.markdown("Cargue los archivos correspondientes a eventos biométricos y vehiculares. El análisis biométrico es obligatorio.")
    
    col_bio, col_lpr = st.columns(2)
    with col_bio:
        archivo_subido = st.file_uploader(":material/upload_file: Eventos biométricos (obligatorio)", type=["xlsx"], key="uploader_todos")
    with col_lpr:
        archivo_lpr = st.file_uploader(":material/directions_car: Eventos vehiculares LPR (opcional)", type=["xlsx"], key="uploader_lpr")
    
    if not archivo_subido:
        st.info("Esperando archivo. Por favor, suba el archivo Excel de Eventos Biométricos (.xlsx) para continuar.")
        st.stop()

    archivo_biometrico_id = _archivo_id(archivo_subido)
    archivo_lpr_id = _archivo_id(archivo_lpr) if archivo_lpr is not None else None
    cache_biometrico = st.session_state.get("_biometrico_preparado")
    cache_lpr = st.session_state.get("_lpr_preparado")
    biometrico_en_sesion = bool(
        cache_biometrico and cache_biometrico["archivo_id"] == archivo_biometrico_id
    )
    lpr_en_sesion = archivo_lpr is None or bool(
        cache_lpr and cache_lpr["archivo_id"] == archivo_lpr_id
    )

    progreso_carga = None
    if not (biometrico_en_sesion and lpr_en_sesion):
        estado_carga = st.status(
            "Preparando archivos de acceso",
            state="running",
            expanded=True,
        )
        barra_carga = estado_carga.progress(
            0,
            text="**0%** · Validando archivos seleccionados",
        )
        cronometro_carga = LiveElapsedTimer(estado_carga)
        progreso_carga = LoadProgress(
            estado_carga,
            barra_carga,
            live_timer=cronometro_carga,
        )
        progreso_carga.start_stage("Validación de archivos")
        progreso_carga.finish_stage(12, "Validación de archivos completada")

    # Preparar una sola vez el archivo biométrico durante esta sesión.
    try:
        datos_biometricos = _preparar_biometrico_sesion(
            archivo_subido,
            archivo_id=archivo_biometrico_id,
            progreso=progreso_carga,
        )
    except Exception as exc:
        if progreso_carga:
            progreso_carga.fail("Error durante la lectura del Excel biométrico")
        st.error(f"No fue posible procesar el Excel biométrico: {exc}")
        st.stop()
    if datos_biometricos["columnas_faltantes"]:
        if progreso_carga:
            progreso_carga.fail("El Excel biométrico no contiene todas las columnas requeridas")
        st.error(
            "No se pudieron detectar las siguientes columnas requeridas: "
            f"{', '.join(datos_biometricos['columnas_faltantes'])}"
        )
        st.stop()
    df_todos = datos_biometricos["df"]
    metricas = datos_biometricos["metricas"]
    calidad = datos_biometricos["calidad"]
    
    if df_todos.empty:
        if progreso_carga:
            progreso_carga.fail("No se encontraron registros biométricos válidos")
        st.warning("No se encontraron registros biométricos válidos tras el procesamiento.", icon=":material/warning:")
        st.stop()
        
    # Procesar LPR si existe
    df_lpr_valido = None
    df_lpr_duplicados = None
    df_lpr_crudo = None
    metricas_lpr = {}
    if archivo_lpr is not None:
        try:
            datos_lpr = _preparar_lpr_sesion(
                archivo_lpr,
                archivo_id=archivo_lpr_id,
                progreso=progreso_carga,
            )
            if not datos_lpr["columnas_faltantes"]:
                df_lpr_crudo = datos_lpr["df_crudo"]
                df_lpr_valido = datos_lpr["df_valido"]
                df_lpr_duplicados = datos_lpr["df_duplicados"]
                metricas_lpr = datos_lpr["metricas"]
            else:
                if progreso_carga:
                    progreso_carga.fail("El Excel LPR no contiene todas las columnas requeridas")
                st.sidebar.error(
                    "Error LPR: Faltan columnas "
                    f"{', '.join(datos_lpr['columnas_faltantes'])}"
                )
        except Exception as e:
            if progreso_carga:
                progreso_carga.fail("Error durante la lectura o depuración del Excel LPR")
            st.sidebar.error(f"Error procesando LPR: {str(e)}")
    elif progreso_carga:
        progreso_carga.start_stage("Archivo LPR opcional no proporcionado")
        progreso_carga.finish_stage(62, "Lectura LPR omitida")
        progreso_carga.finish_stage(75, "Normalización y deduplicación LPR omitidas")
        
    fechas_bio = set(pd.to_datetime(df_todos["Fecha"].dropna()).dt.date.unique())
    fechas_lpr = (
        set(pd.to_datetime(df_lpr_valido["Fecha"].dropna()).dt.date.unique())
        if df_lpr_valido is not None and not df_lpr_valido.empty else set()
    )
    fechas = sorted(fechas_bio | fechas_lpr)
    min_date = min(fechas) if len(fechas) > 0 else None
    max_date = max(fechas) if len(fechas) > 0 else None

    ubicaciones_disponibles = sorted(
        set(df_todos["Ubicacion_Ingreso"].dropna().astype(str))
        | (
            set(df_lpr_valido["Ubicacion_Ingreso"].dropna().astype(str))
            if df_lpr_valido is not None and not df_lpr_valido.empty
            else set()
        )
    )
    ubicaciones_disponibles = [
        ubicacion
        for ubicacion in ubicaciones_disponibles
        if ubicacion in {"25 de Junio", "Ferroviaria"}
    ]
    puntos_disponibles = sorted(
        set(df_todos["Punto de acceso"].dropna().astype(str))
        | (
            set(df_lpr_valido["Camara"].dropna().astype(str))
            if df_lpr_valido is not None and not df_lpr_valido.empty and "Camara" in df_lpr_valido.columns
            else set()
        )
    )
    movimientos_disponibles = sorted(
        set(df_todos["Movimiento"].dropna().astype(str).str.upper())
        | (
            set(df_lpr_valido["Direccion"].dropna().astype(str).str.upper())
            if df_lpr_valido is not None and not df_lpr_valido.empty else set()
        )
    )
    rango_predeterminado = (min_date, max_date) if min_date is not None else ()
    filtros_predeterminados = {
        "rango_fechas": rango_predeterminado,
        "resultados": [],
        "ingresos": [],
        "tipos_usuario": [],
        "ubicaciones": [],
        "mecanismos": [],
        "puntos_acceso": [],
        "movimientos": [],
    }
    widgets_predeterminados = {
        "filt_fechas_todos": rango_predeterminado,
        "filt_res": [],
        "filt_ingreso_todos": [],
        "filt_tipo_usu_todos": [],
        "filt_ubicacion_todos": [],
        "filt_mecanismo_todos": [],
        "filt_punto_todos": [],
        "filt_movimiento_todos": [],
    }
    conjunto_id = (
        datos_biometricos["archivo_id"],
        datos_lpr["archivo_id"] if archivo_lpr is not None and "datos_lpr" in locals() else None,
    )
    if st.session_state.get("_conjunto_filtros_todos") != conjunto_id:
        restablecer_widgets(widgets_predeterminados)
        st.session_state["filtros_aplicados_todos"] = filtros_predeterminados.copy()
        st.session_state["_conjunto_filtros_todos"] = conjunto_id

    # SIDEBAR: los widgets son un borrador; solo el submit modifica resultados.
    with st.sidebar:
        st.markdown("## :material/filter_list: Filtros")

        st.button(
            "Restablecer filtros",
            icon=":material/restart_alt:",
            key="reset_todos",
            use_container_width=True,
            on_click=_restablecer_filtros_todos,
            args=(widgets_predeterminados, filtros_predeterminados),
        )

        with st.form("form_filtros_todos", border=False, enter_to_submit=False):
            if len(fechas) > 0:
                st.date_input(
                    "Rango de fechas",
                    min_value=min_date,
                    max_value=max_date,
                    key="filt_fechas_todos",
                )
            st.multiselect(
                "Ubicación",
                options=ubicaciones_disponibles,
                key="filt_ubicacion_todos",
                placeholder="Todas",
            )
            st.multiselect(
                "Punto de acceso / cámara",
                options=puntos_disponibles,
                key="filt_punto_todos",
                placeholder="Todos",
            )
            st.multiselect(
                "Movimiento",
                options=movimientos_disponibles,
                key="filt_movimiento_todos",
                placeholder="Todos",
            )
            st.multiselect(
                "Mecanismo en vistas consolidadas",
                options=list(MECANISMOS_CONSOLIDADOS),
                key="filt_mecanismo_todos",
                placeholder="Todos",
                help="Controla qué fuentes participan en los indicadores y gráficos consolidados. Los análisis propios de cada fuente permanecen disponibles.",
            )
            st.multiselect(
                "Resultado biométrico",
                options=sorted(df_todos["Resultado"].dropna().unique()),
                key="filt_res",
                placeholder="Todos",
            )
            st.multiselect(
                "Ingreso biométrico",
                options=sorted(df_todos["Ingreso"].dropna().unique()),
                key="filt_ingreso_todos",
                placeholder="Todos",
            )
            st.multiselect(
                "Tipo de usuario",
                options=sorted(df_todos["Tipo_Usuario"].dropna().unique()),
                key="filt_tipo_usu_todos",
                placeholder="Todos",
            )
            st.form_submit_button(
                "Aplicar filtros",
                icon=":material/filter_alt:",
                type="primary",
                width="stretch",
                on_click=_aplicar_filtros_todos_desde_widgets,
            )

        st.caption("Los resultados solo cambian al aplicar o restablecer los filtros.")

    filtros_aplicados = st.session_state["filtros_aplicados_todos"]
    rango_fechas = filtros_aplicados["rango_fechas"]
    sel_resultados = filtros_aplicados["resultados"]
    sel_ingreso = filtros_aplicados["ingresos"]
    sel_tipo_usu = filtros_aplicados["tipos_usuario"]

    df_f, df_lpr_f = aplicar_filtros_integrales(
        df_todos,
        df_lpr_valido,
        filtros_aplicados,
    )
        
    if df_f.empty and df_lpr_f.empty:
        st.warning("No hay registros biométricos ni LPR que coincidan con los filtros seleccionados.")
        st.stop()
    if df_f.empty:
        st.info("No hay datos biométricos para este contexto; se muestran los resultados LPR disponibles.")
        
    # Construcción de df_consolidado_total para métricas globales
    incluir_biometrico = mecanismo_incluido(filtros_aplicados, MECANISMO_BIOMETRICO)
    incluir_lpr = mecanismo_incluido(filtros_aplicados, MECANISMO_LPR)
    df_consolidado_total = df_f.copy() if incluir_biometrico else df_f.iloc[0:0].copy()
    
    if incluir_lpr and not df_lpr_f.empty:
        df_lpr_mapped = df_lpr_f.copy()
        
        # Mapear columnas LPR al estándar base
        df_lpr_mapped["Punto de acceso"] = df_lpr_mapped["Camara"]
        
        def map_movimiento(d):
            if pd.isna(d): return "OTRO"
            d = str(d).upper()
            if "ENTRADA" in d: return "ENTRADA"
            if "SALIDA" in d: return "SALIDA"
            return "OTRO"
            
        df_lpr_mapped["Movimiento"] = df_lpr_mapped["Direccion"].apply(map_movimiento)
        df_lpr_mapped["Tipo_Usuario"] = df_lpr_mapped["Lista_Vehiculos"] if "Lista_Vehiculos" in df_lpr_mapped.columns else "Vehículo"
        df_lpr_mapped["Persona"] = df_lpr_mapped["Matricula"]
        df_lpr_mapped["Persona_Analitica"] = "PLACA::" + df_lpr_mapped["Matricula"].astype(str)
        df_lpr_mapped["Resultado"] = "Exitoso"  # LPR valid reads are implicitly successful
        
        # Concatenar asegurando que coincidan las dimensiones requeridas
        df_consolidado_total = pd.concat([df_f, df_lpr_mapped], ignore_index=True)

        
    # Reutilizar agregaciones mientras no cambien el archivo ni los filtros aplicados.
    clave_analitica = (conjunto_id, _clave_filtros(filtros_aplicados))
    cache_analitica = st.session_state.get("_analitica_integral")
    if progreso_carga and not progreso_carga.failed:
        progreso_carga.start_stage("Preparación de estadísticas iniciales")
    if cache_analitica and cache_analitica["clave"] == clave_analitica:
        tasas = cache_analitica["tasas"]
        stats_nuevas = cache_analitica["stats_nuevas"]
        conclusiones = cache_analitica["conclusiones"]
        stats_base = cache_analitica["stats_base"]
    else:
        tasas, stats_nuevas, conclusiones, stats_base = _calcular_analitica_integral(
            df_f,
            df_todos,
            df_consolidado_total,
            filtros_aplicados,
        )
        st.session_state["_analitica_integral"] = {
            "clave": clave_analitica,
            "tasas": tasas,
            "stats_nuevas": stats_nuevas,
            "conclusiones": conclusiones,
            "stats_base": stats_base,
        }

    if progreso_carga and not progreso_carga.failed:
        progreso_carga.finish_stage(88, "Preparación de estadísticas completada")
        progreso_carga.start_stage("Finalización de carga")
        progreso_carga.complete("Carga y preparación finalizadas")

    mecanismos_contexto = []
    if incluir_biometrico:
        mecanismos_contexto.append("Biométrico")
    if incluir_lpr:
        mecanismos_contexto.append("Reconocimiento LPR")
    mostrar_contexto_resultados(
        df_biometrico=df_f if incluir_biometrico else None,
        df_lpr=df_lpr_f if incluir_lpr else None,
        mecanismos=mecanismos_contexto,
    )
    
    # Render Dashboard
    
    tab_resumen, tab_flujo_gen, tab_dist_det, tab_comp_hor, tab_comp_det, tab_resultados, tab_frecuencia, tab_analitica, tab_calidad, tab_lpr = st.tabs([
        ":material/dashboard: Resumen de movilidad",
        ":material/bar_chart: Flujo general",
        ":material/table_chart: Distribución detallada",
        ":material/schedule: Comportamiento horario",
        ":material/analytics: Comportamiento detallado",
        ":material/fact_check: Resultados",
        ":material/query_stats: Frecuencia",
        ":material/monitoring: Analítica avanzada",
        ":material/verified: Calidad de datos",
        ":material/directions_car: Análisis vehicular LPR"
    ])
    
    with tab_resumen:
        mostrar_seccion("Resumen General de Movilidad")
        
        # Huella de Movilidad
        huella = lprs.generar_huella_movilidad(
            df_f if incluir_biometrico else df_f.iloc[0:0],
            df_lpr_f if incluir_lpr else df_lpr_f.iloc[0:0],
        )
        stats_vehicular_consolidado = lprs.calcular_estadisticas_vehiculares_consolidadas(
            huella["eventos_vehiculares"]
        )
        
        st.markdown("""
<div class="mobility-heading">
<div class="mobility-heading__title">HUELLA DE MOVILIDAD</div>
<div class="mobility-heading__value">{tot_registros:,} <span class="mobility-heading__label">REGISTROS ANALIZADOS</span></div>
</div>
""".format(tot_registros=huella['tot_registros']), unsafe_allow_html=True)

        c_h1, c_h2, c_h3 = st.columns(3)
        with c_h1:
            st.markdown(f"""
<div class="mobility-card mobility-card--blue">
<div class="mobility-card__title">PEATONAL / BIOMÉTRICO</div>
<div class="mobility-card__value">{huella['tot_peatones_puros']:,}</div>
<div class="mobility-card__percentage">{huella['pct_peatones_puros']}%</div>
<div class="mobility-card__description">Registros biométricos clasificados como peatonales</div>
</div>
""", unsafe_allow_html=True)

        with c_h2:
            st.markdown(f"""
<div class="mobility-card mobility-card--orange">
<div class="mobility-card__title">TERMINALES VEH</div>
<div class="mobility-card__value">{huella['tot_terminales_veh']:,}</div>
<div class="mobility-card__percentage">{huella['pct_terminales_veh']}%</div>
<div class="mobility-card__description">Registros biométricos en terminales vehiculares</div>
</div>
""", unsafe_allow_html=True)

        with c_h3:
            st.markdown(f"""
<div class="mobility-card mobility-card--green">
<div class="mobility-card__title">RECONOCIMIENTO LPR</div>
<div class="mobility-card__value">{huella['tot_lpr']:,}</div>
<div class="mobility-card__percentage">{huella['pct_lpr']}%</div>
<div class="mobility-card__details">
<div><div class="mobility-card__detail-label">RECONOCIDAS</div><div class="mobility-card__detail-value">{huella['placas_reconocidas']:,}</div></div>
<div><div class="mobility-card__detail-label">ÚNICAS</div><div class="mobility-card__detail-value">{huella['placas_unicas']:,}</div></div>
</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if huella["tot_biometricos_sin_clasificar"]:
            st.warning(
                f"{huella['tot_biometricos_sin_clasificar']:,} registros biométricos "
                f"({huella['pct_biometricos_sin_clasificar']}%) no pudieron clasificarse como peatonales o "
                "vehiculares y se informan fuera de las tres tarjetas.",
                icon=":material/warning:",
            )
        
        c_b1, c_b2, c_b3 = st.columns(3)
        with c_b1:
            st.markdown(f"""
<div class="peak-card peak-card--blue">
<div class="peak-card__label">DÍA PICO</div>
<div class="peak-card__value">{huella['dia_pico_str']}</div>
</div>
""", unsafe_allow_html=True)
        with c_b2:
            st.markdown(f"""
<div class="peak-card peak-card--orange">
<div class="peak-card__label">HORA PICO</div>
<div class="peak-card__value">{huella['hora_pico_str']}</div>
</div>
""", unsafe_allow_html=True)
        with c_b3:
            st.markdown(f"""
<div class="peak-card peak-card--green">
<div class="peak-card__label">ACCESO PICO</div>
<div class="peak-card__value">{huella['acceso_pico_str']}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        st.info(
            "Las categorías representan registros generados por diferentes mecanismos del sistema de control de accesos. "
            "Un mismo acceso físico puede generar más de un registro cuando intervienen simultáneamente un terminal "
            "biométrico y el reconocimiento LPR. Por esta razón, las categorías no deben sumarse automáticamente como "
            "accesos físicos independientes.",
            icon=":material/info:",
        )

        mostrar_seccion("Estadísticas vehiculares consolidadas")
        st.caption(
            "Vista comparativa de eventos de identificación. La suma consolidada no representa vehículos físicos únicos."
        )

        entradas_veh = stats_vehicular_consolidado["entradas"]
        salidas_veh = stats_vehicular_consolidado["salidas"]
        promedios_veh = stats_vehicular_consolidado["promedios"]
        dias_veh = stats_vehicular_consolidado["dias"]

        c_ent_bio, c_ent_lpr, c_ent_total = st.columns(3)
        with c_ent_bio:
            mostrar_metrica("Entradas biométrico VEH", entradas_veh["Biométrico VEH"], "person_check")
        with c_ent_lpr:
            mostrar_metrica("Entradas LPR", entradas_veh["LPR"], "directions_car")
        with c_ent_total:
            mostrar_metrica("Total de eventos de entrada", entradas_veh["Consolidado"], "login")

        c_sal_bio, c_sal_lpr, c_sal_total = st.columns(3)
        with c_sal_bio:
            mostrar_metrica("Salidas biométrico VEH", salidas_veh["Biométrico VEH"], "person_check")
        with c_sal_lpr:
            mostrar_metrica("Salidas LPR", salidas_veh["LPR"], "directions_car")
        with c_sal_total:
            mostrar_metrica("Total de eventos de salida", salidas_veh["Consolidado"], "logout")

        c_prom_bio, c_prom_lpr, c_prom_total = st.columns(3)
        with c_prom_bio:
            mostrar_metrica("Promedio diario biométrico VEH", round(promedios_veh["Biométrico VEH"], 2), "calendar_month")
        with c_prom_lpr:
            mostrar_metrica("Promedio diario LPR", round(promedios_veh["LPR"], 2), "calendar_month")
        with c_prom_total:
            mostrar_metrica("Promedio diario consolidado", round(promedios_veh["Consolidado"], 2), "calendar_month")
        st.caption(
            "Promedios: entradas de cada mecanismo divididas para sus días con datos; consolidado dividido para la unión "
            f"de fechas con datos. Días considerados — biométrico VEH: {dias_veh['Biométrico VEH']}, "
            f"LPR: {dias_veh['LPR']}, consolidado: {dias_veh['Consolidado']}."
        )

        diario_veh = stats_vehicular_consolidado["diario"]
        if not diario_veh.empty:
            st.plotly_chart(
                lprv.grafico_entradas_vehiculares_consolidadas(
                    diario_veh,
                    theme="light" if obtener_tema_actual() == "Claro" else "dark",
                ),
                width="stretch",
                key="grafico_entradas_vehiculares_consolidadas",
            )
            st.dataframe(
                diario_veh.rename(columns={"Dia_Semana": "Día de la semana"}),
                width="stretch",
                hide_index=True,
            )

        ubicacion_veh = stats_vehicular_consolidado["por_ubicacion"]
        if not ubicacion_veh.empty:
            st.plotly_chart(
                lprv.grafico_movimientos_vehiculares_consolidados(
                    ubicacion_veh,
                    theme="light" if obtener_tema_actual() == "Claro" else "dark",
                ),
                width="stretch",
                key="grafico_movimientos_vehiculares_consolidados",
            )
            st.dataframe(
                ubicacion_veh.rename(columns={"Ubicacion": "Ubicación"}),
                width="stretch",
                hide_index=True,
            )

        periodos_veh = stats_vehicular_consolidado["periodos_pico"]
        if not periodos_veh.empty:
            st.markdown("#### Horarios con mayor actividad vehicular")
            st.caption(
                "Muestra las horas del día que acumularon más eventos de identificación vehicular "
                "durante el período seleccionado."
            )
            nombres_mecanismo = {
                "Consolidado": "Todos los mecanismos",
                "Biométrico VEH": "Biométrico VEH",
                "LPR": "Reconocimiento LPR",
            }
            columnas_ranking = st.columns(3)
            for columna, mecanismo in zip(
                columnas_ranking, ["Consolidado", "Biométrico VEH", "LPR"]
            ):
                with columna:
                    st.markdown(f"**{nombres_mecanismo[mecanismo]}**")
                    ranking = periodos_veh.loc[
                        periodos_veh["Mecanismo"] == mecanismo,
                        ["Rango", "Franja", "Registros"],
                    ].copy()
                    ranking["Rango"] = ranking["Rango"].apply(lambda valor: f"{int(valor)}.º")
                    ranking = ranking.rename(columns={
                        "Rango": "Posición",
                        "Franja": "Horario",
                        "Registros": "Eventos registrados",
                    })
                    st.dataframe(ranking, width="stretch", hide_index=True)
            st.caption(
                "Los registros corresponden a la suma de todos los días analizados. No representan la "
                "circulación de una sola hora o fecha. Todos los mecanismos es una suma de eventos, no de "
                "vehículos únicos."
            )

        flujo_carril = stats_vehicular_consolidado["flujo_por_carril"]
        if not flujo_carril.empty:
            st.markdown("#### Actividad vehicular registrada por carril")
            st.caption(
                "Muestra la cantidad de eventos de identificación en cada carril y los intervalos reales "
                "de mayor actividad durante el período seleccionado."
            )
            st.dataframe(
                flujo_carril[[
                    "Mecanismo", "Ubicacion", "Carril", "Sentido", "Eventos",
                    "Fecha_mayor_actividad", "Hora_pico", "Eventos_hora_pico",
                    "Promedio_hora_pico_min", "Minuto_maximo",
                    "Maximo_observado_minuto", "Promedio_diario_sentido",
                ]].rename(columns={
                    "Ubicacion": "Ubicación",
                    "Fecha_mayor_actividad": "Fecha de mayor actividad",
                    "Hora_pico": "Hora pico real",
                    "Eventos_hora_pico": "Eventos en hora pico",
                    "Promedio_hora_pico_min": "Eventos/min en hora pico",
                    "Minuto_maximo": "Minuto de máxima actividad",
                    "Maximo_observado_minuto": "Máximo eventos/min",
                    "Promedio_diario_sentido": "Promedio diario",
                }).style.format({
                    "Eventos/min en hora pico": "{:.2f}",
                    "Promedio diario": "{:.2f}",
                }),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Cada hora pico corresponde a una fecha y una hora concretas. El promedio se calcula como "
                "eventos de ese carril en esa hora / 60 minutos. Biométrico VEH y LPR permanecen separados."
            )

        caudal_acceso = stats_vehicular_consolidado["caudal_por_acceso"]
        if not caudal_acceso.empty:
            st.markdown("#### Actividad simultánea de los carriles por acceso físico")
            st.caption(
                "El caudal indica cuántos eventos coincidieron en los carriles del mismo acceso durante "
                "un minuto real."
            )
            st.dataframe(
                caudal_acceso[[
                    "Mecanismo", "Ubicacion", "Sentido", "Carriles", "Minuto_maximo",
                    "Caudal_maximo_eventos_min", "Promedio_por_carril_en_minuto_maximo",
                    "Hora_pico", "Promedio_conjunto_hora_pico_min",
                    "Promedio_por_carril_hora_pico_min",
                ]].rename(columns={
                    "Ubicacion": "Ubicación",
                    "Minuto_maximo": "Minuto simultáneo máximo",
                    "Caudal_maximo_eventos_min": "Caudal máximo (eventos/min)",
                    "Promedio_por_carril_en_minuto_maximo": "Promedio/carril en ese minuto",
                    "Hora_pico": "Hora pico real",
                    "Promedio_conjunto_hora_pico_min": "Caudal medio hora pico",
                    "Promedio_por_carril_hora_pico_min": "Promedio/carril hora pico",
                }).style.format({
                    "Promedio/carril en ese minuto": "{:.2f}",
                    "Caudal medio hora pico": "{:.2f}",
                    "Promedio/carril hora pico": "{:.2f}",
                }),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "El caudal se obtiene alineando E1/E2 o S1/S2 por el mismo minuto real. No se suman "
                "máximos ocurridos en instantes distintos. Las unidades son eventos registrados, no vehículos únicos."
            )
        if stats_vehicular_consolidado["direccion_no_valida"]:
            st.warning(
                f"{stats_vehicular_consolidado['direccion_no_valida']:,} registros vehiculares no tienen un sentido "
                "de circulación válido y no se incluyen en entradas o salidas.",
                icon=":material/warning:",
            )
        if stats_vehicular_consolidado["ubicacion_no_valida"]:
            st.warning(
                f"{stats_vehicular_consolidado['ubicacion_no_valida']:,} registros vehiculares no tienen una ubicación "
                "válida y no se incluyen en el desglose por campus.",
                icon=":material/warning:",
            )
        
        st.markdown("---")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: mostrar_metrica("Total Biométricos", tasas["total"])
        with c2: mostrar_metrica("Tasa de Éxito", f"{tasas['tasa_exito']}%")
        with c3: mostrar_metrica("Tasa de Fallo", f"{tasas['tasa_fallo_general']}%")
        with c4: mostrar_metrica("Otros / no clasificados", tasas["otros"])
        with c5: mostrar_metrica("Días Analizados", df_f["Fecha"].nunique())
        
        st.markdown("<br>", unsafe_allow_html=True)
        mostrar_seccion("Conclusiones Principales (Registros Biométricos)")
        for c in conclusiones:
            st.info(c)

    with tab_flujo_gen:
        mostrar_seccion("Flujo General Consolidado")
        st.plotly_chart(grafico_flujo_consolidado(stats_base["flujo_consolidado"]), use_container_width=True, key='grafico_flujo_consolidado_1402')
        
        mostrar_seccion("Entradas vs Salidas")
        st.plotly_chart(grafico_entradas_salidas(stats_base["entradas_salidas"]), use_container_width=True, key='grafico_entradas_salidas_1405')
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.plotly_chart(grafico_entradas_salidas_hora(stats_base["entradas_salidas_hora"]), use_container_width=True, key='grafico_entradas_salidas_hora_1407')

    with tab_dist_det:
        mostrar_seccion("Distribución Detallada por Categoría de Acceso")
        st.plotly_chart(grafico_ingreso(stats_base["flujo_ingreso"]), use_container_width=True, key='grafico_ingreso_1411')
        
        mostrar_seccion("Flujo por Punto de Acceso Físico")
        st.plotly_chart(grafico_flujo_punto_acceso(stats_base["flujo_punto_acceso"]), use_container_width=True, key='grafico_flujo_punto_acceso_1414')
        
    with tab_comp_hor:
        mostrar_seccion("Comportamiento Horario Consolidado")
        if "heatmap_consolidado_hora" in stats_base and not stats_base["heatmap_consolidado_hora"].empty:
            st.plotly_chart(grafico_heatmap_consolidado_hora(stats_base["heatmap_consolidado_hora"]), use_container_width=True, key='grafico_heatmap_consolidado_hora_1419')
        
        mostrar_seccion("Comportamiento Diario")
        st.plotly_chart(grafico_flujo_diario(stats_base["flujo_diario"]), use_container_width=True, key='grafico_flujo_diario_1422')

    with tab_comp_det:
        mostrar_seccion("Comportamiento Detallado por Hora")
        st.plotly_chart(grafico_flujo_hora(stats_base["flujo_hora"]), use_container_width=True, key='grafico_flujo_hora_1426')
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.plotly_chart(grafico_ingreso_hora(stats_base["ingreso_hora"]), use_container_width=True, key='grafico_ingreso_hora_1428')
        
        mostrar_seccion("Mapa de Calor: Puntos de Acceso vs Hora")
        st.plotly_chart(grafico_heatmap_punto_hora(stats_base["heatmap_punto_hora"]), use_container_width=True, key='grafico_heatmap_punto_hora_1431')
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.plotly_chart(grafico_heatmap_dia_hora(stats_base["heatmap_dia_hora"]), use_container_width=True, key='grafico_heatmap_dia_hora_1433')
        
        mostrar_seccion("Usuarios por Tipo y Punto de Acceso")
        st.plotly_chart(grafico_tipo_usuario(stats_base["tipo_usuario"]), use_container_width=True, key='grafico_tipo_usuario_1436')
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.plotly_chart(grafico_tipo_usuario_ingreso(stats_base["tipo_usuario_ingreso"]), use_container_width=True, key='grafico_tipo_usuario_ingreso_1438')
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.plotly_chart(grafico_punto_tipo_usuario(stats_base["punto_tipo_usuario"]), use_container_width=True, key='grafico_punto_tipo_usuario_1440')

    with tab_resultados:
        mostrar_seccion("Análisis de Tasas de Fallo y Éxito")
        mostrar_seccion("1. Distribución de Resultados")
        if not stats_nuevas["resultados"].empty:
            st.dataframe(stats_nuevas["resultados"].style.format({"Eventos": "{:,}", "Porcentaje": "{:.2f}%"}), hide_index=True)
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.plotly_chart(atv.grafico_resultados_generales(stats_nuevas["resultados"]), use_container_width=True, key='grafico_resultados_generales_1448')
                
        mostrar_seccion("2. Comportamiento por Ingreso")
        if not stats_nuevas["cruce_ingreso"].empty:
            st.plotly_chart(atv.grafico_cruce_ingreso_resultado(stats_nuevas["cruce_ingreso"]), use_container_width=True, key='grafico_cruce_ingreso_resultado_1452')
            
        mostrar_seccion("3. Evolución de Tasas")
        if not stats_nuevas["cruce_hora"].empty and not stats_nuevas["evolucion_diaria"].empty:
            st.plotly_chart(atv.grafico_evolucion_resultado(stats_nuevas["evolucion_diaria"]), use_container_width=True, key='grafico_evolucion_resultado_1456')
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.plotly_chart(atv.grafico_cruce_hora_resultado(stats_nuevas["cruce_hora"]), use_container_width=True, key='grafico_cruce_hora_resultado_1458')
                
        mostrar_seccion("4. Hardware")
        if not stats_nuevas["cruce_punto"].empty:
            st.plotly_chart(atv.grafico_punto_acceso_resultado(stats_nuevas["cruce_punto"]), use_container_width=True, key='grafico_punto_acceso_resultado_1462')
            st.markdown("<br><br>", unsafe_allow_html=True)
        if not stats_nuevas["cruce_device"].empty:
            st.plotly_chart(atv.grafico_device_resultado(stats_nuevas["cruce_device"]), use_container_width=True, key='grafico_device_resultado_1465')

    with tab_frecuencia:
        mostrar_seccion("Frecuencia")
        st.plotly_chart(grafico_frecuencia(stats_base["frecuencia"]), use_container_width=True, key='grafico_frecuencia_1469')

    with tab_analitica:
        mostrar_seccion("Analítica Avanzada e Inteligencia")
        
        # 1. Comparación
        if stats_nuevas["comparacion_periodos"]:
            st.subheader("Comparación con el período anterior equivalente")
            st.caption(
                "Compara el valor actual con un período anterior de igual duración cuando existen datos disponibles."
            )
            etiquetas_comparacion = {
                "total": "Intentos biométricos",
                "exitosos": "Autenticaciones exitosas",
                "denegados": "Accesos denegados",
                "fallos_rec": "Fallos de reconocimiento",
            }
            cols_comp = st.columns(4)
            for i, (k, v) in enumerate(stats_nuevas["comparacion_periodos"].items()):
                with cols_comp[i % 4]:
                    st.metric(
                        label=etiquetas_comparacion.get(k, k.replace("_", " ").title()),
                        value=f"{v['actual']:,}", 
                        delta=(f"{v['variacion_pct']}%" if v["variacion_pct"] is not None else "N/D"),
                        delta_color="inverse" if k in ["denegados", "fallos_rec"] else "normal"
                    )
            st.markdown("---")
            
        # 2. Anomalías
        st.subheader("Situaciones estadísticas que requieren revisión")
        st.caption(
            "Señala concentraciones o eventos fuera de los criterios habituales definidos; no determina por sí "
            "solo la causa de la situación."
        )
        if stats_nuevas["anomalias_avanzadas"]:
            for anomalia in stats_nuevas["anomalias_avanzadas"]:
                if anomalia["severidad"] == "CRITICAL":
                    st.error(f"**{anomalia['tipo']}**: {anomalia['descripcion']} (Punto: {anomalia['punto_acceso']}) - {anomalia['magnitud']}", icon=":material/error:")
                else:
                    st.warning(f"**{anomalia['tipo']}**: {anomalia['descripcion']} (Punto: {anomalia['punto_acceso']}) - {anomalia['magnitud']}", icon=":material/warning:")
                
                # Check if raw data is provided
                if "data" in anomalia and not anomalia["data"].empty:
                    with st.expander(f"Ver lista de {anomalia['tipo']}", icon=":material/visibility:"):
                        columnas_mostrar = ["Fecha", "Hora_Dia", "Persona", "Departamento", "Punto de acceso", "Resultado"]
                        # Filtran solo las columnas que existan para no romper en caso de faltantes
                        columnas = [c for c in columnas_mostrar if c in anomalia["data"].columns]
                        df_mostrar = anomalia["data"][columnas].copy()
                        
                        if "Hora_Dia" in df_mostrar.columns:
                            df_mostrar["Hora_Dia"] = df_mostrar["Hora_Dia"].apply(lambda x: f"{int(x):02d}:00" if pd.notnull(x) and x != -1 else "N/A")
                            df_mostrar = df_mostrar.rename(columns={"Hora_Dia": "Hora"})
                            
                        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            st.success("No se detectaron anomalías severas en el periodo.", icon=":material/check_circle:")
            
        st.markdown("---")
            
        # 3. Top Fallos
        st.subheader("Usuarios con mayor cantidad de fallos de reconocimiento")
        st.caption(
            "Ordena hasta diez usuarios por fallos biométricos registrados e informa su participación dentro "
            "del total de fallos del período."
        )
        if not stats_nuevas["top_fallos"].empty:
            df_top = stats_nuevas["top_fallos"]
            st.dataframe(
                df_top[["Persona", "Departamento", "Cantidad_Fallos", "Porcentaje_Total", "Puntos_Acceso"]].style.format({"Porcentaje_Total": "{:.2f}%"}), 
                use_container_width=True, hide_index=True
            )
            if df_top["Alerta"].any():
                st.warning("Se recomienda revisar el registro biométrico o considerar un nuevo enrolamiento para los usuarios marcados que superan el umbral de fallos.", icon=":material/warning:")
        else:
            st.info("No hay usuarios con fallos recurrentes en este periodo.")
            
        st.markdown("---")
        
        # 4. Buscador de Personas
        st.subheader("Consulta del historial de una persona")
        st.caption(
            "Permite revisar los eventos biométricos asociados a una persona dentro de los filtros aplicados."
        )
        lista_personas = df_f[~df_f["Persona"].str.contains("Desconocido", case=False, na=False)]["Persona"].unique()
        lista_personas = sorted([str(p) for p in lista_personas if p])
        
        persona_seleccionada = st.selectbox(
            "Seleccione o escriba el nombre de una persona para ver su historial:", 
            options=[""] + lista_personas, 
            index=0, 
            format_func=lambda x: "--- Escriba para buscar ---" if x == "" else x
        )
        
        if persona_seleccionada:
            df_persona = df_f[df_f["Persona"] == persona_seleccionada]
            
            c_p1, c_p2, c_p3, c_p4 = st.columns(4)
            with c_p1:
                st.metric("Eventos biométricos registrados", len(df_persona))
            with c_p2:
                exitosos = len(df_persona[df_persona["Resultado"] == "Exitoso"])
                st.metric("Autenticaciones exitosas", exitosos)
            with c_p3:
                fallos = len(df_persona[df_persona["Resultado"] == "Fallo de reconocimiento"])
                st.metric("Fallos de reconocimiento", fallos)
            with c_p4:
                denegados = len(df_persona[df_persona["Resultado"] == "Denegado"])
                st.metric("Accesos denegados", denegados)
                
            st.markdown(f"**Departamento:** {', '.join(df_persona['Departamento'].unique())}")
            
            if "Ubicacion_Ingreso" in df_persona.columns:
                conteo_ingreso = df_persona["Ubicacion_Ingreso"].value_counts()
            else:
                conteo_ingreso = df_persona["Ingreso"].apply(lambda x: "Ferroviaria" if "Ferroviaria" in str(x) else ("25 de Junio" if "25 de Junio" in str(x) else "Otra")).value_counts()
                
            ferroviaria = conteo_ingreso.get("Ferroviaria", 0)
            junio25 = conteo_ingreso.get("25 de Junio", 0)
            st.markdown(f"**Entradas utilizadas:** Ferroviaria ({ferroviaria}), 25 de Junio ({junio25})")

    with tab_calidad:
        mostrar_seccion("Calidad de Datos")
        st.caption("Estos indicadores describen la integridad del archivo biométrico original, antes de aplicar filtros.")
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            mostrar_metrica("Registros originales", calidad["total_registros"])
        with col_q2:
            mostrar_metrica("Registros con fecha válida", calidad["registros_validos"])
        with col_q3:
            mostrar_metrica("Fechas Inválidas", calidad["fechas_invalidas"])

        col_q4, col_q5, col_q6 = st.columns(3)
        with col_q4:
            mostrar_metrica("Registros sin punto de acceso", calidad["acceso_vacio"])
        with col_q5:
            mostrar_metrica("Registros sin departamento", calidad["departamento_vacio"])
        with col_q6:
            mostrar_metrica("Registros sin nombre", calidad["registros_sin_nombre"])

        st.markdown("---")
        
        # Nulos detallados
        mostrar_seccion("Valores Nulos por Columna")
        nulos_df = pd.DataFrame(
            list(calidad["nulos_por_columna"].items()),
            columns=["Columna", "Valores Nulos"],
        )
        st.dataframe(nulos_df, use_container_width=True, hide_index=True)

    with tab_lpr:
        mostrar_seccion("Análisis Vehicular LPR")
        
        if df_lpr_valido is not None and not df_lpr_valido.empty:
            tema_lpr = "light" if obtener_tema_actual() == "Claro" else "dark"
            
            # Estadísticas LPR
            contexto_lpr_completo = len(df_lpr_f) == len(df_lpr_valido)
            stats_gen_lpr = lprs.calcular_estadisticas_generales_lpr(
                df_lpr_f,
                df_lpr_duplicados if contexto_lpr_completo else None,
                df_lpr_crudo if contexto_lpr_completo else None,
            )
            resumen_entradas_lpr = lprs.resumen_entradas_vehiculares(df_lpr_f)
            movimientos_lpr = lprs.stats_movimientos_lpr_por_ubicacion_camara(df_lpr_f)
            
            # 1. Resumen Ejecutivo Vehicular
            st.markdown("### Resumen de registros vehiculares LPR")
            st.caption(
                "Presenta los principales resultados del reconocimiento de matrículas dentro del contexto aplicado."
            )
            texto_resumen = lprs.generar_texto_resumen_ejecutivo(df_lpr_f, stats_gen_lpr)
            st.info(texto_resumen)

            fecha_pico_lpr = resumen_entradas_lpr["fecha_pico"]
            dia_pico_lpr = (
                f"{fecha_pico_lpr.strftime('%d/%m/%Y')} · {resumen_entradas_lpr['entradas_pico']:,}"
                if fecha_pico_lpr is not None else "Sin entradas"
            )
            c_v1, c_v2, c_v3, c_v4 = st.columns(4)
            with c_v1:
                mostrar_metrica("Entradas vehiculares registradas", resumen_entradas_lpr["total_entradas"])
            with c_v2:
                mostrar_metrica("Promedio diario de entradas", round(resumen_entradas_lpr["promedio_diario"], 2))
            with c_v3:
                mostrar_metrica("Salidas vehiculares registradas", movimientos_lpr["total_salidas"])
            with c_v4:
                mostrar_metrica("Día de mayor ingreso", dia_pico_lpr)
            st.caption(
                "El promedio diario corresponde a eventos LPR de entrada depurados divididos para "
                f"{resumen_entradas_lpr['dias_con_datos']:,} días con datos LPR dentro del período filtrado."
            )

            st.markdown("#### Cobertura de los registros LPR analizados")
            st.caption(
                "Resume el volumen de eventos depurados, matrículas identificadas, días con datos y "
                "categorías de acceso presentes en los filtros aplicados."
            )
            
            c_l1, c_l2, c_l3, c_l4 = st.columns(4)
            with c_l1:
                mostrar_metrica("Registros LPR", stats_gen_lpr["eventos_validos"], "directions_car")
            with c_l2:
                mostrar_metrica("Placas únicas", stats_gen_lpr["placas_unicas"], "pin")
            with c_l3:
                mostrar_metrica("Días analizados", df_lpr_f["Fecha"].nunique(), "calendar_month")
            with c_l4:
                mostrar_metrica("Categorías de acceso LPR", df_lpr_f["Punto_Acceso"].nunique(), "door_front")
                
            st.markdown("---")
            
            # 2. Flujo Vehicular
            mostrar_seccion("Flujo Vehicular")

            eventos_lpr_carril = lprs.consolidar_eventos_vehiculares(pd.DataFrame(), df_lpr_f)
            flujo_lpr_carril = lprs.calcular_flujo_real_por_carril(eventos_lpr_carril)
            caudal_lpr_acceso = lprs.calcular_caudal_conjunto_por_acceso(eventos_lpr_carril)
            if not flujo_lpr_carril.empty:
                carril_mayor = flujo_lpr_carril.loc[flujo_lpr_carril["Eventos"].idxmax()]
                minuto_mayor = flujo_lpr_carril.loc[
                    flujo_lpr_carril["Maximo_observado_minuto"].idxmax()
                ]
                hora_mayor = flujo_lpr_carril.loc[flujo_lpr_carril["Eventos_hora_pico"].idxmax()]
                c_f1, c_f2, c_f3 = st.columns(3)
                with c_f1:
                    mostrar_metrica(
                        "Carril con mayor circulación",
                        f"{carril_mayor['Ubicacion']} · {carril_mayor['Carril']}",
                    )
                with c_f2:
                    mostrar_metrica(
                        "Máximo observado en un minuto",
                        f"{int(minuto_mayor['Maximo_observado_minuto'])} eventos",
                    )
                with c_f3:
                    mostrar_metrica(
                        "Intensidad durante la hora pico",
                        f"{hora_mayor['Promedio_hora_pico_min']:.2f} eventos/min",
                    )
                st.caption(
                    f"Máximo real: {minuto_mayor['Minuto_maximo']} en "
                    f"{minuto_mayor['Ubicacion']} · {minuto_mayor['Carril']}. "
                    f"Hora pico real de mayor intensidad: {hora_mayor['Hora_pico']}."
                )
                st.markdown("#### Detalle de actividad por carril LPR")
                st.caption(
                    "Muestra los eventos registrados en cada carril, su hora calendario de mayor actividad "
                    "y el mayor número observado en un minuto real."
                )
                st.dataframe(
                    flujo_lpr_carril[[
                        "Ubicacion", "Carril", "Sentido", "Eventos", "Fecha_mayor_actividad",
                        "Hora_pico", "Eventos_hora_pico", "Promedio_hora_pico_min",
                        "Minuto_maximo", "Maximo_observado_minuto", "Promedio_diario_sentido",
                    ]].rename(columns={
                        "Ubicacion": "Ubicación",
                        "Fecha_mayor_actividad": "Fecha de mayor actividad",
                        "Hora_pico": "Hora pico real",
                        "Eventos_hora_pico": "Eventos hora pico",
                        "Promedio_hora_pico_min": "Eventos/min hora pico",
                        "Minuto_maximo": "Minuto máximo",
                        "Maximo_observado_minuto": "Máximo eventos/min",
                        "Promedio_diario_sentido": "Promedio diario",
                    }).style.format({
                        "Eventos/min hora pico": "{:.2f}", "Promedio diario": "{:.2f}",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
                if not caudal_lpr_acceso.empty:
                    st.markdown("#### Caudal simultáneo de eventos LPR por acceso")
                    st.caption(
                        "Suma los eventos de los carriles del mismo sentido que coincidieron en cada minuto real."
                    )
                    caudal_lpr_presentacion = caudal_lpr_acceso[[
                        "Ubicacion", "Sentido", "Carriles", "Minuto_maximo",
                        "Caudal_maximo_eventos_min", "Promedio_por_carril_en_minuto_maximo",
                        "Hora_pico", "Promedio_conjunto_hora_pico_min",
                        "Promedio_por_carril_hora_pico_min",
                    ]].rename(columns={
                        "Ubicacion": "Ubicación",
                        "Minuto_maximo": "Minuto de mayor caudal",
                        "Caudal_maximo_eventos_min": "Mayor caudal (eventos por minuto)",
                        "Promedio_por_carril_en_minuto_maximo": "Promedio por carril en ese minuto",
                        "Hora_pico": "Hora de mayor actividad",
                        "Promedio_conjunto_hora_pico_min": "Eventos por minuto del acceso en esa hora",
                        "Promedio_por_carril_hora_pico_min": "Eventos por minuto y carril en esa hora",
                    })
                    st.dataframe(
                        caudal_lpr_presentacion.style.format({
                            "Promedio por carril en ese minuto": "{:.2f}",
                            "Eventos por minuto del acceso en esa hora": "{:.2f}",
                            "Eventos por minuto y carril en esa hora": "{:.2f}",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.caption(
                        "E1/E2 o S1/S2 se alinean por minuto calendario antes de sumarse; no se combinan "
                        "picos de momentos diferentes."
                    )

            st.markdown("#### Eventos LPR acumulados por hora del día")
            st.caption(
                "Compara las horas del día sumando los eventos de todas las fechas analizadas. Es una vista "
                "acumulada y no describe la intensidad de una hora calendario concreta."
            )
            
            df_hora_flujo = lprs.stats_flujo_vehicular_por_hora(df_lpr_f)
            
            if not df_hora_flujo.empty and df_hora_flujo["Registros"].max() > 0:
                hora_max = df_hora_flujo.loc[df_hora_flujo["Registros"].idxmax()]
                
                c_f1, c_f2, c_f3 = st.columns(3)
                with c_f1:
                    st.markdown(f"""
<div class="peak-card peak-card--orange peak-card--large">
<div class="peak-card__label">HORARIO CON MÁS EVENTOS ACUMULADOS</div>
<div class="peak-card__value">{int(hora_max['Hora'])}:00–{(int(hora_max['Hora'])+1)%24}:00</div>
</div>
""", unsafe_allow_html=True)
                with c_f2:
                    st.markdown(f"""
<div class="peak-card peak-card--blue peak-card--large">
<div class="peak-card__label">EVENTOS LPR ACUMULADOS</div>
<div class="peak-card__value">{int(hora_max['Registros']):,}</div>
</div>
""", unsafe_allow_html=True)
                with c_f3:
                    st.markdown(f"""
<div class="peak-card peak-card--green peak-card--large">
<div class="peak-card__label">MÁXIMO REAL EN UN MINUTO</div>
<div class="peak-card__value">{int(hora_max['Maximo_real_por_minuto'])} eventos</div>
</div>
""", unsafe_allow_html=True)

                st.caption(
                    f"Cálculo: registros acumulados / ({int(hora_max['Dias_considerados'])} días con datos × 60 minutos). "
                    f"Promedio acumulado secundario: {hora_max['Promedio_registros_minuto']} eventos/minuto de franja; "
                    f"promedio diario de la franja: {hora_max['Promedio_por_dia']}. Los días completamente ausentes "
                    "del archivo no se infieren."
                )
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.plotly_chart(lprv.grafico_flujo_vehicular_por_hora(df_hora_flujo, theme=tema_lpr), use_container_width=True, key='grafico_flujo_vehicular_por_hora_1651')
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # Ranking de Horas
                df_top_horas = lprs.stats_flujo_vehicular_top_periodos(df_lpr_f)
                mostrar_seccion("Períodos de mayor flujo")
                df_top_horas_presentacion = df_top_horas[[
                    "Franja", "Registros", "Dias_considerados", "Promedio_por_dia",
                    "Promedio_registros_minuto", "Maximo_real_por_minuto",
                ]].copy()
                df_top_horas_presentacion.insert(
                    0, "Posición", [f"{posición}.º" for posición in range(1, len(df_top_horas_presentacion) + 1)]
                )
                st.dataframe(
                    df_top_horas_presentacion.rename(columns={
                        "Franja": "Horario",
                        "Registros": "Eventos registrados",
                        "Dias_considerados": "Días con datos",
                        "Promedio_por_dia": "Promedio/día de la franja",
                        "Promedio_registros_minuto": "Promedio acumulado/minuto",
                        "Maximo_real_por_minuto": "Máximo real en un minuto",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
                st.markdown("<br><br>", unsafe_allow_html=True)

            mostrar_seccion("Entradas vehiculares registradas por día")
            df_entradas_dia = resumen_entradas_lpr["diario"]
            st.plotly_chart(
                lprv.grafico_entradas_vehiculares_por_dia(df_entradas_dia, theme=tema_lpr),
                use_container_width=True,
                key="grafico_entradas_vehiculares_diarias_lpr",
            )
            st.dataframe(
                df_entradas_dia.rename(columns={"Dia_Semana": "Día de la semana"}),
                use_container_width=True,
                hide_index=True,
            )

            mostrar_seccion("Actividad vehicular total en el tiempo")
            df_dia = lprs.stats_eventos_por_dia(df_lpr_f)
            st.plotly_chart(lprv.grafico_lpr_por_dia(df_dia, theme=tema_lpr), use_container_width=True, key='grafico_lpr_por_dia_1662')
            st.markdown("<br><br>", unsafe_allow_html=True)
                
            df_heatmap = lprs.stats_heatmap_dia_hora(df_lpr_f)
            st.plotly_chart(lprv.grafico_heatmap_lpr(df_heatmap, theme=tema_lpr), use_container_width=True, key='grafico_heatmap_lpr_1666')
            
            st.markdown("---")
            
            # 3. Flujo por acceso
            mostrar_seccion("Flujo por acceso")
            df_flujo_acceso = lprs.stats_flujo_vehicular_por_acceso(df_lpr_f)
            if not df_flujo_acceso.empty:
                st.dataframe(df_flujo_acceso.rename(columns={
                    "Hora_Pico": "Hora Pico",
                    "Dias_considerados": "Días con datos",
                    "Promedio_registros_minuto": "Promedio/minuto de franja",
                    "Promedio_por_dia": "Promedio/día de la franja",
                    "Maximo_real_por_minuto": "Máximo real en un minuto",
                }), use_container_width=True, hide_index=True)
                st.markdown("<br><br>", unsafe_allow_html=True)
            
            mostrar_seccion("Entradas y salidas LPR por ubicación")
            df_mov_ubicacion = movimientos_lpr["por_ubicacion"]

            def conteo_movimiento(ubicacion, sentido):
                filas = df_mov_ubicacion[
                    (df_mov_ubicacion["Ubicacion"] == ubicacion)
                    & (df_mov_ubicacion["Sentido"] == sentido)
                ]
                return int(filas["Registros"].sum())

            c_u1, c_u2, c_u3, c_u4 = st.columns(4)
            with c_u1:
                mostrar_metrica("Entradas 25 de Junio", conteo_movimiento("25 de Junio", "Entrada"))
            with c_u2:
                mostrar_metrica("Salidas 25 de Junio", conteo_movimiento("25 de Junio", "Salida"))
            with c_u3:
                mostrar_metrica("Entradas Ferroviaria", conteo_movimiento("Ferroviaria", "Entrada"))
            with c_u4:
                mostrar_metrica("Salidas Ferroviaria", conteo_movimiento("Ferroviaria", "Salida"))

            st.plotly_chart(
                lprv.grafico_entradas_salidas_por_ubicacion(df_mov_ubicacion, theme=tema_lpr),
                use_container_width=True,
                key="grafico_movimientos_lpr_por_ubicacion",
            )

            st.markdown("#### Eventos LPR por cámara de acceso")
            st.caption(
                "Detalla la ubicación, el sentido de circulación y los eventos registrados por cada cámara."
            )
            st.dataframe(
                movimientos_lpr["por_camara"].rename(
                    columns={
                        "Ubicacion": "Ubicación",
                        "Camara": "Cámara de acceso",
                        "Registros": "Eventos registrados",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            suma_ent_ubic = int(df_mov_ubicacion.loc[df_mov_ubicacion["Sentido"] == "Entrada", "Registros"].sum())
            suma_sal_ubic = int(df_mov_ubicacion.loc[df_mov_ubicacion["Sentido"] == "Salida", "Registros"].sum())
            df_mov_camara = movimientos_lpr["por_camara"]
            suma_ent_camara = int(df_mov_camara.loc[df_mov_camara["Sentido"] == "Entrada", "Registros"].sum())
            suma_sal_camara = int(df_mov_camara.loc[df_mov_camara["Sentido"] == "Salida", "Registros"].sum())
            st.caption(
                "Conciliación: entradas "
                f"{movimientos_lpr['total_entradas']:,} total / {suma_ent_ubic:,} por ubicación / {suma_ent_camara:,} por cámara; "
                "salidas "
                f"{movimientos_lpr['total_salidas']:,} total / {suma_sal_ubic:,} por ubicación / {suma_sal_camara:,} por cámara."
            )
            diferencias_lpr = movimientos_lpr["diferencias"]
            if any(diferencias_lpr.values()):
                st.warning(
                    "Registros fuera del desglose válido: "
                    f"{diferencias_lpr['entradas_sin_ubicacion_valida']} entradas y "
                    f"{diferencias_lpr['salidas_sin_ubicacion_valida']} salidas sin ubicación válida; "
                    f"{diferencias_lpr['entradas_sin_camara_valida']} entradas y "
                    f"{diferencias_lpr['salidas_sin_camara_valida']} salidas sin cámara válida; "
                    f"{diferencias_lpr['direccion_no_valida']} registros sin dirección válida."
                )
            
            st.markdown("---")
            
            # 4. Placas con mayor frecuencia
            mostrar_seccion("Placas con mayor frecuencia")
            sel_top = st.selectbox("Cantidad de matrículas que se mostrarán", [5, 10, 20], index=1, key="lpr_top_sel")
            df_top = lprs.stats_lpr_top_placas(df_lpr_f, sel_top)
            
            st.dataframe(
                df_top.rename(columns={"Eventos": "Eventos LPR registrados"}),
                use_container_width=True,
                hide_index=True,
            )
            st.metric(
                "Promedio de eventos LPR por matrícula identificada",
                round(stats_gen_lpr["eventos_validos"] / max(1, stats_gen_lpr["placas_unicas"]), 1),
            )
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.plotly_chart(lprv.grafico_top_placas(df_top, theme=tema_lpr), use_container_width=True, key='grafico_top_placas_1690')
                

                
        else:
            if archivo_lpr is None:
                st.info("No se cargó un archivo Excel de eventos vehiculares (LPR). Suba uno para habilitar esta sección.")
            else:
                st.warning("No se encontraron registros vehiculares válidos en el archivo LPR tras el procesamiento.")
        
    # Generar PDF
    with st.sidebar:
        st.markdown("---")
        st.markdown("## :material/download: Exportar reporte")
        if st.button("Generar reporte PDF", icon=":material/picture_as_pdf:", key="btn_pdf_todos", use_container_width=True):
            with st.spinner("Generando reporte (puede tardar unos segundos)..."):
                try:
                    # Preparar variables LPR para PDF si existen
                    pdf_stats_gen_lpr = None
                    pdf_stats_int_lpr = None
                    pdf_df_lpr_f = pd.DataFrame()
                    pdf_conclusiones_lpr = []
                    
                    if df_lpr_valido is not None and not df_lpr_valido.empty:
                        contexto_lpr_completo = len(df_lpr_f) == len(df_lpr_valido)
                        pdf_stats_gen_lpr = lprs.calcular_estadisticas_generales_lpr(
                            df_lpr_f,
                            df_lpr_duplicados if contexto_lpr_completo else None,
                            df_lpr_crudo if contexto_lpr_completo else None,
                        )
                        pdf_df_lpr_f = df_lpr_f
                        pdf_conclusiones_lpr = lprs.generar_conclusiones_lpr(pdf_stats_gen_lpr, pdf_df_lpr_f)

                    pdf_buffer = exportar_reporte_integral_pdf(df_consolidado_total, tasas, stats_base, stats_nuevas, conclusiones, calidad, pdf_stats_gen_lpr, pdf_df_lpr_f, pdf_conclusiones_lpr, huella_dashboard=huella)
                    st.download_button(
                        label="Descargar PDF",
                        icon=":material/download:",
                        data=pdf_buffer,
                        file_name=f"Reporte_Integral_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="dl_pdf_todos"
                    )
                    st.success("PDF generado correctamente.")
                except Exception as e:
                    st.error(f"Error al generar PDF: {str(e)}")

# ═════════════════════════════════════════════════════════════════════════════
# ENRUTADOR PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

def main():
    st.sidebar.markdown("## :material/analytics: Análisis")
    modo = st.sidebar.radio(
        "Seleccione el tipo de análisis:",
        # options=["Eventos Normales", "Eventos Anormales", "Todos los Eventos"],
        options=["Todos los Eventos"],
        index=0,
        key="selector_modo_analisis"
    )
    st.sidebar.markdown("---")
    
    if modo == "Eventos Normales":
        ejecutar_modo_exitoso()
    elif modo == "Eventos Anormales":
        ejecutar_modo_fallidos()
    else:
        ejecutar_modo_todos()

def app_protegida():
    configurar_tema_interfaz()

    import streamlit_authenticator as stauth
    import yaml
    from yaml.loader import SafeLoader

    # Obtener credenciales desde los secretos de Streamlit
    # Convertimos a dict estándar para que streamlit-authenticator pueda modificarlo en memoria
    if hasattr(st.secrets, "to_dict"):
        config = st.secrets.to_dict()
    else:
        config = dict(st.secrets)
        
    if "credentials" not in config:
        st.error("No se encontraron credenciales de acceso configuradas.")
        st.stop()

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    # Render login widget
    authenticator.login()

    if st.session_state["authentication_status"]:
        with st.sidebar:
            st.markdown(f"Bienvenido/a **{st.session_state['name']}**")
            authenticator.logout('Cerrar sesión', 'main')
            st.markdown("---")
        
        # Determine role from secrets
        for username, user_info in config['credentials']['usernames'].items():
            if username == st.session_state["username"]:
                st.session_state["rol"] = user_info.get("role", "viewer")
                break
                
        # Run main app
        main()
    elif st.session_state["authentication_status"] is False:
        st.error('Usuario o contraseña incorrectos')
    elif st.session_state["authentication_status"] is None:
        st.warning('Por favor ingrese su usuario y contraseña')

if __name__ == "__main__":
    app_protegida()
