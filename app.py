"""
Aplicación principal Streamlit — Sistema de Reportes de Flujo de Ingresos Peatonales.

Ejecutar con: streamlit run app.py

Arquitectura modular:
- config.py:          Configuración central
- data_loader.py:     Carga y validación de datos
- data_processing.py: Limpieza y transformación
- statistics_calc.py: Cálculo de estadísticas
- visualizations.py:  Gráficos interactivos con Plotly
- export.py:          Exportación de reportes
"""

import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

from config import APP_TITULO, APP_ICON, APP_LAYOUT
from data_loader import cargar_excel, validar_columnas, generar_reporte_calidad
from data_processing import procesar_datos
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
)
from export import exportar_dataset_filtrado, exportar_reporte_completo
from pdf_report import exportar_reporte_pdf, construir_graficos_reporte
from styles import aplicar_estilos

# ─── Monkey Patch para Plotly ───────────────────────────────────────────────
# Streamlit >= 1.16 sobrescribe por defecto el layout de Plotly con su propio tema.
# Para que los gráficos hereden "Plus Jakarta Sans" desde el layout de visualizations.py,
# forzamos globalmente que theme=None.
if not hasattr(st, "_original_plotly_chart"):
    st._original_plotly_chart = st.plotly_chart

def _patched_plotly_chart(*args, **kwargs):
    kwargs["theme"] = None
    return st._original_plotly_chart(*args, **kwargs)

st.plotly_chart = _patched_plotly_chart

# ─── Configuración de página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Reportes Flujo Peatonal",
    page_icon=APP_ICON,
    initial_sidebar_state="expanded",
    layout="wide"
)

# Importaciones para el módulo de eventos fallidos
from failed_data_loader import cargar_excel_fallidos, detectar_columnas_fallidos, reporte_calidad_fallidos
from failed_data_processing import procesar_datos_fallidos
import failed_statistics_calc as fs
import failed_visualizations as fv
from failed_pdf_report import exportar_reporte_fallidos_pdf

# Importaciones para el módulo de Todos los Eventos
from all_events_data_loader import cargar_excel_todos, detectar_columnas_todos, reporte_calidad_todos
from all_events_data_processing import procesar_datos_todos
import all_events_statistics_calc as ats
import all_events_visualizations as atv
from all_events_pdf_report import exportar_reporte_integral_pdf

aplicar_estilos()

def formato_numero(n) -> str:
    """Formatea un número con separador de miles."""
    if isinstance(n, float):
        return f"{n:,.2f}"
    return f"{int(n):,}"


def mostrar_metrica(label: str, value, icon: str = ""):
    """Renderiza una tarjeta de métrica."""
    display = formato_numero(value) if isinstance(value, (int, float)) else str(value)
    st.markdown(f"""
    <div class="metric-card">
        <div class="value">{icon} {display}</div>
        <div class="label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def mostrar_seccion(titulo: str):
    """Renderiza un encabezado de sección."""
    st.markdown(f'<div class="section-header">{titulo}</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL
# APLICACIÓN PRINCIPAL - MODO NORMALES
# ═════════════════════════════════════════════════════════════════════════════

def ejecutar_modo_exitoso():
    st.markdown("<h1><i class='bi bi-check-circle-fill' style='color:#55A878;'></i> Análisis de Eventos Normales</h1>", unsafe_allow_html=True)
    st.markdown("Cargue un archivo Excel que contenga los registros de eventos normales para su análisis independiente.")

    archivo_subido = st.file_uploader("Cargar Excel de Eventos Normales", type=["xlsx"])

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

    # ─── SIDEBAR: Filtros ────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## <i class='bi bi-funnel'></i> Filtros", unsafe_allow_html=True)

        # Botón restablecer
        if st.button(" Restablecer filtros", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key.startswith("filtro_"):
                    del st.session_state[key]
            st.rerun()

        st.markdown("---")

        # Rango de fechas
        fecha_min = df["Fecha"].min()
        fecha_max = df["Fecha"].max()
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
            "️ Ingreso",
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
            "️ Generar Reporte Ejecutivo PDF",
            on_click=generar_pdf,
            use_container_width=True,
        )

        if st.session_state.pdf_bytes is not None:
            st.download_button(
                " Descargar Reporte Ejecutivo PDF",
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
            "️ Generar Reporte Completo Excel",
            on_click=generar_reporte_excel,
            use_container_width=True,
        )

        if st.session_state.reporte_excel_bytes is not None:
            st.download_button(
                " Descargar Reporte Completo",
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
            "️ Preparar Dataset Filtrado",
            on_click=generar_dataset_filtrado,
            use_container_width=True,
        )

        if st.session_state.dataset_filtrado_bytes is not None:
            st.download_button(
                " Descargar Dataset Filtrado",
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
            f"<div class='warning-box'><i class='bi bi-funnel-fill' style='color:#3B82B8;'></i> <strong>Filtros activos</strong> — Mostrando <strong>{total_filtrado:,}</strong> de <strong>{metricas['total_eventos']:,}</strong> eventos ({total_filtrado/metricas['total_eventos']*100:.1f}%)</div>",
            unsafe_allow_html=True
        )

    if total_filtrado == 0:
        st.warning("No hay datos para los filtros seleccionados. Ajuste los filtros.")
        st.stop()

    # ─── 1. Métricas principales ─────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        mostrar_metrica("Total de Eventos", total_filtrado, "")
    with col2:
        mostrar_metrica("Usuarios Únicos", usuarios_filtrado, "")
    with col3:
        mostrar_metrica("Entradas", entradas_f, "")
    with col4:
        mostrar_metrica("Salidas", salidas_f, "")
    with col5:
        mostrar_metrica("Promedio Diario", promedio_f, "")

    st.markdown("")

    col6, col7, col8, col9 = st.columns(4)
    with col6:
        mostrar_metrica("Puntos de Acceso", df_filtrado["Punto de acceso"].nunique(), "")
    with col7:
        mostrar_metrica("Ingreso", df_filtrado["Ingreso"].nunique(), "")
    with col8:
        mostrar_metrica("Días Registrados", dias_f, "")
    with col9:
        mostrar_metrica("Otros Eventos", otros_f, "")

    # ═════════════════════════════════════════════════════════════════════
    # PESTAÑAS PRINCIPALES
    # ═════════════════════════════════════════════════════════════════════

    tabs = st.tabs([
        "Flujo por Acceso",
        "Flujo Horario",
        "Flujo Diario",
        "Entradas vs Salidas",
        "Tipo de Usuario",
        "Ingreso",
        "Heatmaps",
        "Frecuencia",
        "Conclusiones",
        "Calidad de Datos",
    ])

    # ─── TAB 1: Flujo por punto de acceso ────────────────────────────────
    with tabs[0]:
        mostrar_seccion("Flujo por Punto de Acceso")
        st.markdown("Cada punto de acceso con su volumen de eventos, porcentaje, ingreso y movimiento.")

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
        st.markdown("** Ranking Top 5:**")
        for i, row in df_flujo_acceso.head(5).iterrows():
            st.markdown(
                f"**{i}.** {row['Punto de acceso']} — "
                f"{row['Eventos']:,} eventos ({row['Porcentaje']}%) — "
                f"Ingreso: {row['Ingreso']} — {row['Movimiento']}"
            )

    # ─── TAB 2: Flujo horario ────────────────────────────────────────────
    with tabs[1]:
        mostrar_seccion("Flujo por Hora del Día")

        df_flujo_hora = flujo_por_hora(df_filtrado)
        picos = horas_pico(df_filtrado)

        # Métricas de hora pico
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            hp_gen = picos["general"]
            horas_str = ", ".join([f"{h:02d}:00" for h in hp_gen["horas"]])
            empate_str = " (empate)" if hp_gen["empate"] else ""
            st.metric("Hora Pico General", f"{horas_str}{empate_str}", f"{hp_gen['eventos']:,} eventos")
        with col_h2:
            if "entrada" in picos:
                hp_ent = picos["entrada"]
                horas_str = ", ".join([f"{h:02d}:00" for h in hp_ent["horas"]])
                empate_str = " (empate)" if hp_ent["empate"] else ""
                st.metric("Hora Pico Entrada", f"{horas_str}{empate_str}", f"{hp_ent['eventos']:,} eventos")
        with col_h3:
            if "salida" in picos:
                hp_sal = picos["salida"]
                horas_str = ", ".join([f"{h:02d}:00" for h in hp_sal["horas"]])
                empate_str = " (empate)" if hp_sal["empate"] else ""
                st.metric("Hora Pico Salida", f"{horas_str}{empate_str}", f"{hp_sal['eventos']:,} eventos")

        # Hora pico por ingreso
        if picos.get("por_ingreso"):
            st.markdown("**Hora pico por ingreso:**")
            cols_ingreso = st.columns(len(picos["por_ingreso"]))
            for i, (ingreso, datos) in enumerate(picos["por_ingreso"].items()):
                with cols_ingreso[i]:
                    horas_str = ", ".join([f"{h:02d}:00" for h in datos["horas"]])
                    empate_str = " (empate)" if datos["empate"] else ""
                    st.metric(f"️ {ingreso}", f"{horas_str}{empate_str}", f"{datos['eventos']:,} eventos")

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
        st.markdown("¿A qué hora se utiliza más cada ingreso?")

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
                empate_str = " ️" if datos["empate"] else ""
                pico_punto_data.append({
                    "Punto de Acceso": punto,
                    "Hora Pico": f"{horas_str}{empate_str}",
                    "Eventos en Hora Pico": datos["eventos"],
                })
            st.dataframe(
                pd.DataFrame(pico_punto_data).style.format({"Eventos en Hora Pico": "{:,}"}), use_container_width=True)

    # ─── TAB 3: Flujo diario ────────────────────────────────────────────
    with tabs[2]:
        mostrar_seccion("Flujo Diario")

        df_diario = flujo_diario(df_filtrado)
        dp = dias_pico(df_filtrado)

        # Métricas de días pico
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            dias_str = ", ".join([str(d) for d in dp["mayor_flujo"]["dias"]])
            st.metric(" Día Mayor Flujo", dias_str, f"{dp['mayor_flujo']['eventos']:,} eventos")
        with col_d2:
            dias_str = ", ".join([str(d) for d in dp["menor_flujo"]["dias"]])
            st.metric(" Día Menor Flujo", dias_str, f"{dp['menor_flujo']['eventos']:,} eventos")
        with col_d3:
            st.metric(" Promedio Diario", formato_numero(promedio_f), f"{dias_f} días")

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
    with tabs[3]:
        mostrar_seccion("Entradas vs Salidas")

        # General
        df_ev_gen = entradas_vs_salidas_general(df_filtrado)
        col_ev1, col_ev2 = st.columns([1, 2])
        with col_ev1:
            st.dataframe(
                df_ev_gen.style.format({
                    "Eventos": "{:,}",
                    "Porcentaje": "{:.2f}%",
                }),
                use_container_width=True,
            )
        with col_ev2:
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
    with tabs[4]:
        mostrar_seccion("Flujo por Tipo de Usuario")
        st.markdown("Categorías reales encontradas en los datos (sin asumir categorías predefinidas).")

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
    with tabs[5]:
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
                ️ <strong>Accesos no clasificados:</strong> Los siguientes puntos de acceso
                no pudieron ser asignados a un ingreso conocido.
            </div>
            """, unsafe_allow_html=True)
            for acceso in metricas["accesos_no_clasificados"]:
                st.markdown(f"- `{acceso}`")

    # ─── TAB 7: Heatmaps ────────────────────────────────────────────────
    with tabs[6]:
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
    with tabs[7]:
        mostrar_seccion("Frecuencia de Utilización del Sistema")
        st.markdown("Distribución de cuántos eventos registra cada usuario.")

        rangos_df, stats_df = frecuencia_utilizacion(df_filtrado)

        # Estadísticas
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        # Gráfico
        fig_freq = grafico_frecuencia(rangos_df)
        st.plotly_chart(
            fig_freq, use_container_width=True,
            key="grafico_frecuencia_utilizacion",
        )

        # Tabla de rangos
        st.dataframe(
            rangos_df.style.format({"Usuarios": "{:,}"}),
            use_container_width=True,
            hide_index=True,
        )

    # ─── TAB 9: Conclusiones ────────────────────────────────────────────
    with tabs[8]:
        mostrar_seccion("Conclusiones y Hallazgos Automáticos")
        st.markdown("""
        <div class="info-box">
            ℹ️ Las siguientes conclusiones son <strong>observaciones basadas en los datos</strong>.
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
    with tabs[9]:
        mostrar_seccion("Validación y Calidad de Datos")
        st.markdown("Reporte de validación inicial del archivo cargado (datos originales, sin filtros).")

        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            mostrar_metrica("Total de Registros", calidad["total_registros"], "")
        with col_q2:
            mostrar_metrica("Registros Válidos", calidad["registros_validos"], "")
        with col_q3:
            mostrar_metrica("Fechas Inválidas", calidad["fechas_invalidas"], "️")

        col_q4, col_q5, col_q6 = st.columns(3)
        with col_q4:
            mostrar_metrica("Acceso Vacío", calidad["acceso_vacio"], "")
        with col_q5:
            mostrar_metrica("Depto. Vacío", calidad["departamento_vacio"], "")
        with col_q6:
            mostrar_metrica("Sin Nombre/Apellido", calidad["registros_sin_nombre"], "")

        st.markdown("---")

        col_u1, col_u2, col_u3 = st.columns(3)
        with col_u1:
            mostrar_metrica("Puntos de Acceso Únicos", calidad["unicos_punto_acceso"], "")
        with col_u2:
            mostrar_metrica("Device Name Únicos", calidad["unicos_device_name"], "")
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
    st.markdown("<h1><i class='bi bi-exclamation-triangle-fill' style='color:#D66A6A;'></i> Análisis de Eventos Anormales</h1>", unsafe_allow_html=True)
    st.markdown("Cargue un archivo Excel que contenga los registros de eventos anormales para su análisis independiente.")
    
    archivo_subido = st.file_uploader("Cargar Excel de Eventos Anormales", type=["xlsx"])
    
    if not archivo_subido:
        st.info("Esperando archivo. Por favor, suba un archivo Excel (.xlsx) para continuar.")
        st.stop()
        
    df_crudo = cargar_excel_fallidos(archivo_subido)
    mapeo = detectar_columnas_fallidos(df_crudo)
    calidad = reporte_calidad_fallidos(df_crudo, mapeo)
    
    if calidad["columnas_faltantes"]:
        st.warning(f"️ Las siguientes columnas clave no fueron detectadas: {', '.join(calidad['columnas_faltantes'])}. Algunas funcionalidades podrían no estar disponibles.")
        
    df, metricas = procesar_datos_fallidos(df_crudo, mapeo)
    
    # Excluir la categoría '25 DE JUNIO' del tipo de usuario / departamento
    df = df[df["Tipo_Usuario"] != "25 DE JUNIO"]
    
    # ─── SIDEBAR: Filtros para Eventos Anormales ───
    with st.sidebar:
        st.markdown("## <i class='bi bi-funnel'></i> Filtros Eventos Anormales", unsafe_allow_html=True)
        if st.button(" Restablecer filtros anormales", key="reset_fallidos", use_container_width=True):
            # Eliminar todo el state de este modo
            for key in list(st.session_state.keys()):
                if key.startswith("ff_"):
                    del st.session_state[key]
            st.rerun()
            
        st.markdown("---")
        
        fecha_min = pd.to_datetime(df["Fecha"].dropna()).min() if not df["Fecha"].dropna().empty else None
        fecha_max = pd.to_datetime(df["Fecha"].dropna()).max() if not df["Fecha"].dropna().empty else None
        if pd.notnull(fecha_min) and pd.notnull(fecha_max):
            fecha_inicio = st.date_input(" Fecha inicio", value=fecha_min, min_value=fecha_min, max_value=fecha_max, key="ff_inicio")
            fecha_fin = st.date_input(" Fecha fin", value=fecha_max, min_value=fecha_min, max_value=fecha_max, key="ff_fin")
        else:
            fecha_inicio, fecha_fin = None, None
            
        ingresos = sorted([str(x) for x in df["Ingreso"].unique()])
        ingreso_sel = st.multiselect("️ Ingreso", options=ingresos, default=ingresos, key="ff_ingreso")
        
    # ─── Aplicar Filtros ───
    df_f = df.copy()
    if fecha_inicio and fecha_fin:
        df_f = df_f[(pd.to_datetime(df_f["Fecha"]) >= pd.to_datetime(fecha_inicio)) & (pd.to_datetime(df_f["Fecha"]) <= pd.to_datetime(fecha_fin))]
    if ingreso_sel:
        df_f = df_f[df_f["Ingreso"].isin(ingreso_sel)]
        
    if df_f.empty:
        st.warning("No hay datos que coincidan con los filtros seleccionados.")
        st.stop()
        
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
            mostrar_metrica("Ingreso más afectado", stats["por_ingreso"].iloc[0]["Ingreso"], "️")
        else:
            mostrar_metrica("Ingreso", "N/A", "️")
    with col3: mostrar_metrica("Días Analizados", df_f["Fecha"].nunique() if not df_f["Fecha"].dropna().empty else 0, "")
    
    mostrar_seccion("1. Comportamiento Temporal")
    if not stats["evolucion_diaria"].empty and not stats["por_hora"].empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fv.grafico_fallos_evolucion_diaria(stats["evolucion_diaria"]), use_container_width=True)
        with c2:
            st.plotly_chart(fv.grafico_fallos_por_hora(stats["por_hora"]), use_container_width=True)
            
    mostrar_seccion("2. Análisis Geográfico")
    if not stats["por_ingreso"].empty and not stats["por_punto"].empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fv.grafico_fallos_por_ingreso(stats["por_ingreso"]), use_container_width=True)
        with c2:
            st.plotly_chart(fv.grafico_fallos_por_punto(stats["por_punto"]), use_container_width=True)
            
    mostrar_seccion("3. Conclusiones Principales")
    for c in conclusiones:
        st.info(c)
        
    with st.sidebar:
        st.markdown("## <i class='bi bi-download'></i> Exportar Reporte", unsafe_allow_html=True)
        if st.button(" Generar Reporte PDF (Anormales)", use_container_width=True, type="primary"):
            with st.spinner("Generando PDF..."):
                try:
                    pdf_buffer = exportar_reporte_fallidos_pdf(df_f, stats, conclusiones)
                    st.download_button(
                        label="⬇️ Descargar PDF",
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
    st.markdown("<h1><i class='bi bi-layers-fill' style='color:#3B82B8;'></i> Análisis Integral: Todos los Eventos</h1>", unsafe_allow_html=True)
    st.markdown("Cargue un archivo Excel que contenga los registros de eventos integrales (exitosos y anormales).")
    
    archivo_subido = st.file_uploader("Cargar Excel Integral", type=["xlsx"], key="uploader_todos")
    
    if not archivo_subido:
        st.info("Esperando archivo. Por favor, suba un archivo Excel (.xlsx) para continuar.")
        st.stop()
        
    # Cargar datos
    df_crudo = cargar_excel_todos(archivo_subido)
    
    # Detectar columnas
    mapeo = detectar_columnas_todos(df_crudo)
    
    # Validar
    calidad = reporte_calidad_todos(df_crudo, mapeo)
    if calidad["columnas_faltantes"]:
        st.error(f" No se pudieron detectar las siguientes columnas requeridas: {', '.join(calidad['columnas_faltantes'])}")
        st.stop()
        
    # Procesar
    df_todos, metricas = procesar_datos_todos(df_crudo, mapeo)
    
    # Excluir la categoría '25 DE JUNIO' del tipo de usuario / departamento
    df_todos = df_todos[df_todos["Tipo_Usuario"] != "25 DE JUNIO"]
    
    # (Filtro duro de Tipo_Usuario eliminado para permitir SIN CLASIFICAR)
    if df_todos.empty:
        st.warning("️ No se encontraron registros válidos tras el procesamiento.")
        st.stop()
        
    # SIDEBAR Filtros
    with st.sidebar:
        st.markdown("## <i class='bi bi-funnel'></i> Filtros (Integral)", unsafe_allow_html=True)
        
        if st.button(" Restablecer filtros", key="reset_todos", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key.startswith("filt_"):
                    del st.session_state[key]
            st.rerun()
            
        st.markdown("---")
        
        fechas = pd.to_datetime(df_todos["Fecha"].dropna()).dt.date.unique()
        if len(fechas) > 0:
            min_date = min(fechas)
            max_date = max(fechas)
            rango_fechas = st.date_input(
                "Rango de Fechas", 
                value=(min_date, max_date), 
                min_value=min_date, 
                max_value=max_date,
                key="filt_fechas_todos"
            )
        else:
            rango_fechas = ()
            
        sel_resultados = st.multiselect("Resultado", options=df_todos["Resultado"].unique(), default=[], key="filt_res", placeholder="Todos")
        sel_ingreso = st.multiselect("Ingreso", options=df_todos["Ingreso"].unique(), default=[], key="filt_ingreso_todos", placeholder="Todos")
        sel_tipo_usu = st.multiselect("Tipo Usuario", options=df_todos["Tipo_Usuario"].unique(), default=[], key="filt_tipo_usu_todos", placeholder="Todos")
        
    # Aplicar filtros
    df_f = df_todos.copy()
    if len(rango_fechas) == 2:
        df_f = df_f[(df_f["Fecha"] >= rango_fechas[0]) & (df_f["Fecha"] <= rango_fechas[1])]
    if sel_resultados:
        df_f = df_f[df_f["Resultado"].isin(sel_resultados)]
    if sel_ingreso:
        df_f = df_f[df_f["Ingreso"].isin(sel_ingreso)]
    if sel_tipo_usu:
        df_f = df_f[df_f["Tipo_Usuario"].isin(sel_tipo_usu)]
        
    if df_f.empty:
        st.warning("No hay datos que coincidan con los filtros seleccionados.")
        st.stop()
        
    # Calcular estadísticas nuevas
    tasas = ats.calcular_tasas_generales(df_f)
    # --- Cálculos de Analítica Avanzada ---
    top_usuarios_fallos = ats.calcular_top_usuarios_fallos(df_f)
    anomalias_avanzadas = ats.detectar_anomalias_avanzadas(df_f)
    
    # Intentar calcular periodo anterior
    comparacion_periodos = {}
    if len(rango_fechas) == 2 and (rango_fechas[1] - rango_fechas[0]).days > 0:
        dias_diferencia = (rango_fechas[1] - rango_fechas[0]).days + 1
        fecha_fin_anterior = rango_fechas[0] - pd.Timedelta(days=1)
        fecha_inicio_anterior = fecha_fin_anterior - pd.Timedelta(days=dias_diferencia - 1)
        
        df_anterior = df_todos.copy()
        df_anterior = df_anterior[(df_anterior["Fecha"] >= fecha_inicio_anterior) & (df_anterior["Fecha"] <= fecha_fin_anterior)]
        if not df_anterior.empty:
            comparacion_periodos = ats.comparar_periodos(df_f, df_anterior)
    # --------------------------------------

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
        "comparacion_periodos": comparacion_periodos
    }
    conclusiones = ats.generar_conclusiones_todos(df_f, tasas, stats_nuevas)
    
    # Calcular estadísticas base heredadas
    stats_base = {
        "flujo_punto_acceso": flujo_por_punto_acceso(df_f),
        "flujo_hora": flujo_por_hora(df_f),
        "heatmap_punto_hora": flujo_punto_hora(df_f),
        "entradas_salidas": entradas_vs_salidas_general(df_f),
        "entradas_salidas_hora": entradas_vs_salidas_por_hora(df_f),
        "entradas_salidas_ingreso": entradas_vs_salidas_por_ingreso(df_f),
        "flujo_ingreso": flujo_por_ingreso(df_f),
        "tipo_usuario": flujo_por_tipo_usuario(df_f),
        "tipo_usuario_ingreso": tipo_usuario_ingreso(df_f),
        "flujo_diario": flujo_diario(df_f),
        "flujo_diario_ingreso": flujo_diario_por_ingreso(df_f),
        "dia_semana": flujo_dia_semana(df_f),
        "heatmap_dia_hora": heatmap_dia_hora(df_f),
        "ingreso_hora": ingreso_hora(df_f),
        "punto_tipo_usuario": punto_tipo_usuario(df_f),
        "frecuencia": frecuencia_utilizacion(df_f)[0],
    }
    
    # Render Dashboard
    
    tabs = st.tabs([
        "Resumen Ejecutivo",
        "Flujo General",
        "Análisis Temporal",
        "Mapas de Calor",
        "Usuarios",
        "Puntos de Acceso",
        "Resultados",
        "Frecuencia",
        "Analítica Avanzada",
        "Calidad de Datos"
    ])
    
    with tabs[0]:
        mostrar_seccion("Resumen Ejecutivo")
        c1, c2, c3, c4 = st.columns(4)
        with c1: mostrar_metrica("Total Eventos", tasas["total"])
        with c2: mostrar_metrica("Tasa de Éxito", f"{tasas['tasa_exito']}%")
        with c3: mostrar_metrica("Tasa de Fallo", f"{tasas['tasa_fallo_general']}%")
        with c4: mostrar_metrica("Días Analizados", df_f["Fecha"].nunique())
        
        st.markdown("<br>", unsafe_allow_html=True)
        mostrar_seccion("Conclusiones Principales")
        for c in conclusiones:
            st.info(c)

    with tabs[1]:
        mostrar_seccion("Flujo General")
        st.plotly_chart(grafico_ingreso(stats_base["flujo_ingreso"]), use_container_width=True)
        
        mostrar_seccion("Entradas vs Salidas")
        c_es1, c_es2 = st.columns(2)
        with c_es1: st.plotly_chart(grafico_entradas_salidas(stats_base["entradas_salidas"]), use_container_width=True)
        with c_es2: st.plotly_chart(grafico_entradas_salidas_hora(stats_base["entradas_salidas_hora"]), use_container_width=True)

    with tabs[2]:
        mostrar_seccion("Análisis Temporal")
        c_temp1, c_temp2 = st.columns(2)
        with c_temp1: st.plotly_chart(grafico_flujo_hora(stats_base["flujo_hora"]), use_container_width=True)
        with c_temp2: st.plotly_chart(grafico_ingreso_hora(stats_base["ingreso_hora"]), use_container_width=True)
        
        mostrar_seccion("Comportamiento Diario")
        st.plotly_chart(grafico_flujo_diario(stats_base["flujo_diario"]), use_container_width=True)
        
    with tabs[3]:
        mostrar_seccion("Mapas de Calor")
        st.plotly_chart(grafico_heatmap_punto_hora(stats_base["heatmap_punto_hora"]), use_container_width=True)
        st.plotly_chart(grafico_heatmap_dia_hora(stats_base["heatmap_dia_hora"]), use_container_width=True)

    with tabs[4]:
        mostrar_seccion("Usuarios")
        c_usu1, c_usu2 = st.columns(2)
        with c_usu1: st.plotly_chart(grafico_tipo_usuario(stats_base["tipo_usuario"]), use_container_width=True)
        with c_usu2: st.plotly_chart(grafico_tipo_usuario_ingreso(stats_base["tipo_usuario_ingreso"]), use_container_width=True)
        
        mostrar_seccion("Usuarios por Punto de Acceso")
        st.plotly_chart(grafico_punto_tipo_usuario(stats_base["punto_tipo_usuario"]), use_container_width=True)
        
    with tabs[5]:
        mostrar_seccion("Puntos de Acceso")
        st.plotly_chart(grafico_flujo_punto_acceso(stats_base["flujo_punto_acceso"]), use_container_width=True)

    with tabs[6]:
        mostrar_seccion("Análisis de Tasas de Fallo y Éxito")
        mostrar_seccion("1. Distribución de Resultados")
        if not stats_nuevas["resultados"].empty:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.plotly_chart(atv.grafico_resultados_generales(stats_nuevas["resultados"]), use_container_width=True)
            with col2:
                st.dataframe(stats_nuevas["resultados"].style.format({"Eventos": "{:,}", "Porcentaje": "{:.2f}%"}), hide_index=True)
                
        mostrar_seccion("2. Comportamiento por Ingreso")
        if not stats_nuevas["cruce_ingreso"].empty:
            st.plotly_chart(atv.grafico_cruce_ingreso_resultado(stats_nuevas["cruce_ingreso"]), use_container_width=True)
            
        mostrar_seccion("3. Evolución de Tasas")
        if not stats_nuevas["cruce_hora"].empty and not stats_nuevas["evolucion_diaria"].empty:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(atv.grafico_evolucion_resultado(stats_nuevas["evolucion_diaria"]), use_container_width=True)
            with col2:
                st.plotly_chart(atv.grafico_cruce_hora_resultado(stats_nuevas["cruce_hora"]), use_container_width=True)
                
        mostrar_seccion("4. Hardware")
        if not stats_nuevas["cruce_punto"].empty:
            st.plotly_chart(atv.grafico_punto_acceso_resultado(stats_nuevas["cruce_punto"]), use_container_width=True)
        if not stats_nuevas["cruce_device"].empty:
            st.plotly_chart(atv.grafico_device_resultado(stats_nuevas["cruce_device"]), use_container_width=True)

    with tabs[7]:
        mostrar_seccion("Frecuencia")
        st.plotly_chart(grafico_frecuencia(stats_base["frecuencia"]), use_container_width=True)

    with tabs[8]:
        mostrar_seccion("Analítica Avanzada e Inteligencia")
        
        # 1. Comparación
        if stats_nuevas["comparacion_periodos"]:
            st.subheader("Comparativa vs Periodo Anterior Equivalente")
            cols_comp = st.columns(4)
            for i, (k, v) in enumerate(stats_nuevas["comparacion_periodos"].items()):
                with cols_comp[i % 4]:
                    st.metric(
                        label=k.capitalize().replace("_", " "), 
                        value=f"{v['actual']:,}", 
                        delta=f"{v['variacion_pct']}%", 
                        delta_color="inverse" if k in ["denegados", "fallos_rec"] else "normal"
                    )
            st.markdown("---")
            
        # 2. Anomalías
        st.subheader("Detección de Anomalías")
        if stats_nuevas["anomalias_avanzadas"]:
            for anomalia in stats_nuevas["anomalias_avanzadas"]:
                if anomalia["severidad"] == "CRITICAL":
                    st.error(f"🚨 **{anomalia['tipo']}**: {anomalia['descripcion']} (Punto: {anomalia['punto_acceso']}) - {anomalia['magnitud']}")
                else:
                    st.warning(f"⚠️ **{anomalia['tipo']}**: {anomalia['descripcion']} (Punto: {anomalia['punto_acceso']}) - {anomalia['magnitud']}")
                
                # Check if raw data is provided
                if "data" in anomalia and not anomalia["data"].empty:
                    with st.expander(f"Ver lista de {anomalia['tipo']}"):
                        columnas_mostrar = ["Fecha", "Hora_Dia", "Persona", "Departamento", "Punto de acceso", "Resultado"]
                        # Filtran solo las columnas que existan para no romper en caso de faltantes
                        columnas = [c for c in columnas_mostrar if c in anomalia["data"].columns]
                        df_mostrar = anomalia["data"][columnas].copy()
                        
                        if "Hora_Dia" in df_mostrar.columns:
                            df_mostrar["Hora_Dia"] = df_mostrar["Hora_Dia"].apply(lambda x: f"{int(x):02d}:00" if pd.notnull(x) and x != -1 else "N/A")
                            df_mostrar = df_mostrar.rename(columns={"Hora_Dia": "Hora"})
                            
                        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No se detectaron anomalías severas en el periodo.")
            
        st.markdown("---")
            
        # 3. Top Fallos
        st.subheader("Top 10 Usuarios Recurrentes con Fallos")
        if not stats_nuevas["top_fallos"].empty:
            df_top = stats_nuevas["top_fallos"]
            st.dataframe(
                df_top[["Persona", "Departamento", "Cantidad_Fallos", "Porcentaje_Total", "Puntos_Acceso"]].style.format({"Porcentaje_Total": "{:.2f}%"}), 
                use_container_width=True, hide_index=True
            )
            if df_top["Alerta"].any():
                st.warning("⚠️ Se recomienda revisar el registro biométrico o considerar un nuevo enrolamiento para los usuarios marcados que superan el umbral de fallos.")
        else:
            st.info("No hay usuarios con fallos recurrentes en este periodo.")
            
        st.markdown("---")
        
        # 4. Buscador de Personas
        st.subheader("Buscador de Personas")
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
                st.metric("Total Registros", len(df_persona))
            with c_p2:
                exitosos = len(df_persona[df_persona["Resultado"] == "Exitoso"])
                st.metric("Accesos Exitosos", exitosos)
            with c_p3:
                fallos = len(df_persona[df_persona["Resultado"] == "Fallo de reconocimiento"])
                st.metric("Fallos Biométricos", fallos)
            with c_p4:
                denegados = len(df_persona[df_persona["Resultado"] == "Denegado"])
                st.metric("Accesos Denegados", denegados)
                
            st.markdown(f"**Departamento:** {', '.join(df_persona['Departamento'].unique())}")
            
            conteo_ingreso = df_persona["Ingreso"].value_counts()
            ferroviaria = conteo_ingreso.get("Ferroviaria", 0)
            junio25 = conteo_ingreso.get("25 de Junio", 0)
            st.markdown(f"**Entradas utilizadas:** Ferroviaria ({ferroviaria}), 25 de Junio ({junio25})")

    with tabs[9]:
        mostrar_seccion("Calidad de Datos")
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            mostrar_metrica("Total Registros Originales", calidad["total_registros"])
        with col_q2:
            mostrar_metrica("Registros Válidos", calidad["registros_validos"])
        with col_q3:
            mostrar_metrica("Fechas Inválidas", calidad["fechas_invalidas"])

        col_q4, col_q5, col_q6 = st.columns(3)
        with col_q4:
            mostrar_metrica("Puntos de Acceso Vacíos", calidad["acceso_vacio"])
        with col_q5:
            mostrar_metrica("Departamentos Vacíos", calidad["departamento_vacio"])
        with col_q6:
            mostrar_metrica("Registros sin Nombre", calidad["registros_sin_nombre"])

        st.markdown("---")
        
        # Nulos detallados
        mostrar_seccion("Valores Nulos por Columna")
        nulos_df = pd.DataFrame(
            list(calidad["nulos_por_columna"].items()),
            columns=["Columna", "Valores Nulos"],
        )
        st.dataframe(nulos_df, use_container_width=True, hide_index=True)

        
    # Generar PDF
    with st.sidebar:
        st.markdown("---")
        st.markdown("## <i class='bi bi-download'></i> Exportar Reporte", unsafe_allow_html=True)
        if st.button("Generar Mega Reporte PDF", key="btn_pdf_todos", use_container_width=True):
            with st.spinner("Generando mega reporte (puede tardar unos segundos)..."):
                try:
                    pdf_buffer = exportar_reporte_integral_pdf(df_f, tasas, stats_base, stats_nuevas, conclusiones, calidad)
                    st.download_button(
                        label="Descargar PDF",
                        data=pdf_buffer,
                        file_name=f"Mega_Reporte_Integral_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
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
    st.sidebar.markdown("## <i class='bi bi-bar-chart'></i> Análisis", unsafe_allow_html=True)
    modo = st.sidebar.radio(
        "Seleccione el tipo de análisis:",
        options=["Eventos Normales", "Eventos Anormales", "Todos los Eventos"],
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
    import streamlit_authenticator as stauth
    import yaml
    from yaml.loader import SafeLoader

    import toml
    with open('.streamlit/secrets.toml', 'r', encoding='utf-8') as f:
        config = toml.load(f)

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