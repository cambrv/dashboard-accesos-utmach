"""
Exportación a PDF del Reporte Integral ("Todos los Eventos").
Este reporte compila el 100% de las gráficas de Eventos Exitosos + las nuevas gráficas de Tasas de Fallo.
"""
import io
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle

# Imports de base
from pdf_report import (
    ESTILO_TITULO, ESTILO_SUBTITULO, ESTILO_NORMAL, ESTILO_SECCION, ESTILO_CONCLUSION,
    _agregar_grafico, _tabla_dataframe
)
import visualizations as v
from all_events_visualizations import (
    grafico_resultados_generales, grafico_cruce_ingreso_resultado,
    grafico_cruce_hora_resultado, grafico_evolucion_resultado,
    grafico_dia_semana_resultado, grafico_tipo_usuario_resultado,
    grafico_punto_acceso_resultado, grafico_heatmap_todos,
    grafico_device_resultado
)
import re

def formatear_texto_pdf(texto):
    if not isinstance(texto, str):
        return texto
        
    try:
        texto_corregido = texto.encode('cp1252').decode('utf-8')
        texto = texto_corregido
    except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
        pass
        
    try:
        texto_corregido = texto.encode('latin1').decode('utf-8')
        texto = texto_corregido
    except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
        pass
        
    texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
    return texto


def _ahora_local():
    return datetime.now(ZoneInfo("America/Guayaquil"))


def _anonimizar_matricula(valor):
    texto = re.sub(r"[^A-Z0-9]", "", str(valor).upper())
    if len(texto) <= 2:
        return "***"
    return f"{texto[:1]}{'*' * max(3, len(texto) - 2)}{texto[-1:]}"


def _dibujar_pie_integral(canvas, doc, periodo):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D5D8DC"))
    canvas.line(2 * cm, 1.35 * cm, A4[0] - 2 * cm, 1.35 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#5D6D7E"))
    canvas.drawString(2 * cm, 0.95 * cm, "Reporte Integral de Movilidad UTMACH")
    canvas.drawCentredString(A4[0] / 2, 0.95 * cm, f"Período: {periodo}")
    canvas.drawRightString(A4[0] - 2 * cm, 0.95 * cm, f"Página {doc.page}")
    canvas.restoreState()

def _agregar_portada_integral(story, fecha_min: str, fecha_max: str, titulo: str):
    """Genera la portada del reporte integral."""
    story.append(Spacer(1, 2.0 * cm))
    
    story.append(Paragraph("UNIVERSIDAD TÉCNICA DE MACHALA",
        ParagraphStyle("Institucion", fontName="Helvetica-Bold", fontSize=14, textColor=colors.HexColor("#1B4F72"), alignment=TA_CENTER, spaceAfter=8)))
    
    story.append(Paragraph("UNIDAD DE OBRAS E INFRAESTRUCTURA UNIVERSITARIA",
        ParagraphStyle("Unidad", fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#5D6D7E"), alignment=TA_CENTER, spaceAfter=35)))
    
    banda = Table(
        [[Paragraph(titulo.replace(" / ", "<br/>"),
            ParagraphStyle("Banda", fontName="Helvetica-Bold", fontSize=19, leading=25, textColor=colors.white, alignment=TA_CENTER))]],
        colWidths=[17 * cm], rowHeights=[3.0 * cm],
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1B4F72")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ],
    )
    story.append(banda)
    story.append(Spacer(1, 1.5 * cm))
    
    story.append(Paragraph("Reporte Integral Estadístico",
        ParagraphStyle("Subtitulo", fontName="Helvetica-Bold", fontSize=14, textColor=colors.HexColor("#2C3E50"), alignment=TA_CENTER, spaceAfter=20)))
    
    datos_fechas = [
        ["Fecha de inicio:", fecha_min],
        ["Fecha de fin:", fecha_max],
        ["Fecha de generación:", _ahora_local().strftime("%d/%m/%Y %H:%M")],
        ["Fuentes:", "HikCentral: biometría y reconocimiento LPR"],
        ["Alcance:", "Análisis estadístico de eventos registrados; no identifica trayectos ni vehículos únicos"],
    ]
    tabla_fechas = Table(datos_fechas, colWidths=[6 * cm, 6 * cm], style=[
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONT", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2C3E50")),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
    ])
    story.append(tabla_fechas)

def exportar_reporte_integral_pdf(df: pd.DataFrame, tasas: dict, stats_base: dict, stats_nuevas: dict, conclusiones: list, calidad: dict, stats_gen_lpr: dict = None, df_lpr_f: pd.DataFrame = None, conclusiones_lpr: list = None, huella_dashboard: dict = None) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    
    # 1. Portada
    fecha_min = df["Fecha"].min().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].min()) else "N/A"
    fecha_max = df["Fecha"].max().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].max()) else "N/A"
    _agregar_portada_integral(story, fecha_min, fecha_max, "REPORTE INTEGRAL DE MOVILIDAD")
    story.append(PageBreak())

    story.append(Paragraph("Índice de secciones", ESTILO_TITULO))
    indice = [
        "1. Resumen ejecutivo y huella de movilidad",
        "2. Análisis vehicular consolidado por mecanismo y carril",
        "3. Registros biométricos",
        "4. Distribución general y comportamiento temporal",
        "5. Resultados y fallos biométricos",
        "6. Análisis específico LPR",
        "7. Metodología, limitaciones, conclusiones y recomendaciones",
    ]
    for item in indice:
        story.append(Paragraph(item, ESTILO_NORMAL))
        story.append(Spacer(1, 0.12 * cm))
    story.append(PageBreak())
    
    # 2. Resumen General de Movilidad
    import lpr_statistics_calc as lprs
    huella = huella_dashboard if huella_dashboard is not None else lprs.generar_huella_movilidad(df, df_lpr_f)
    
    story.append(Paragraph("1. Resumen ejecutivo y huella de movilidad", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    texto_huella = (
        f"Durante el período analizado se procesaron {huella['tot_registros']:,} registros en total. "
        f"El {huella['pct_peatones_puros']}% ({huella['tot_peatones_puros']:,}) correspondió a registros de ingreso peatonal/biométrico, "
        f"el {huella['pct_terminales_veh']}% ({huella['tot_terminales_veh']:,}) a registros biométricos en terminales vehiculares, "
        f"y el {huella['pct_lpr']}% ({huella['tot_lpr']:,}) a eventos de reconocimiento de placas (LPR)."
    )
    if huella.get("tot_biometricos_sin_clasificar", 0):
        texto_huella += (
            f" Además, {huella['tot_biometricos_sin_clasificar']:,} registros biométricos "
            f"({huella.get('pct_biometricos_sin_clasificar', 0)}%) no pudieron clasificarse como peatonales o vehiculares."
        )
    story.append(Paragraph(formatear_texto_pdf(texto_huella), ESTILO_NORMAL))
    story.append(Spacer(1, 0.5 * cm))
    
    nota_metodologica = "Nota: Las categorías representan registros generados por diferentes mecanismos. Un mismo acceso físico puede generar más de un registro. Por esta razón, las categorías no deben sumarse automáticamente como accesos físicos independientes."
    story.append(Paragraph(formatear_texto_pdf(f"<font size=8 color='#5D6D7E'><i>{nota_metodologica}</i></font>"), ESTILO_NORMAL))
    story.append(Spacer(1, 0.5 * cm))
    
    datos_huella = [
        ["Registros Analizados", "Peatonales", "Terminales VEH", "Eventos LPR", "Día Pico", "Hora Pico", "Acceso Pico"],
        [
            f"{huella['tot_registros']:,}", 
            f"{huella['tot_peatones_puros']:,}", 
            f"{huella['tot_terminales_veh']:,}", 
            f"{huella['tot_lpr']:,}",
            formatear_texto_pdf(huella['dia_pico_str'].split(' — ')[0] if ' — ' in huella['dia_pico_str'] else huella['dia_pico_str']),
            formatear_texto_pdf(huella['hora_pico_str'].split(' — ')[0] if ' — ' in huella['hora_pico_str'] else huella['hora_pico_str']),
            formatear_texto_pdf(huella['acceso_pico_str'].split(' — ')[0] if ' — ' in huella['acceso_pico_str'] else huella['acceso_pico_str'])
        ]
    ]
    tabla_huella = Table(datos_huella, style=[
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3B82B8")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, 1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F8F9F9")),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#D5D8DC")),
    ])
    story.append(tabla_huella)
    story.append(Spacer(1, 1 * cm))

    hallazgos_resumen = []
    if tasas.get("total", 0):
        hallazgos_resumen.append(
            f"En biometría se registraron {tasas.get('fallos_rec', 0):,} fallos de reconocimiento y "
            f"{tasas.get('denegados', 0):,} accesos denegados; son resultados distintos y se analizan por separado."
        )
    if huella.get("tot_terminales_veh", 0) or huella.get("tot_lpr", 0):
        hallazgos_resumen.append(
            "Los registros biométricos VEH y LPR describen mecanismos de identificación; su suma no equivale "
            "a vehículos físicos únicos."
        )
    for hallazgo in hallazgos_resumen:
        story.append(Paragraph(formatear_texto_pdf(hallazgo), ESTILO_CONCLUSION))

    # 2. Análisis vehicular consolidado con intervalos calendario reales.
    eventos_vehiculares = huella.get("eventos_vehiculares", pd.DataFrame())
    stats_veh = lprs.calcular_estadisticas_vehiculares_consolidadas(eventos_vehiculares)
    story.append(PageBreak())
    story.append(Paragraph("2. Análisis vehicular consolidado", ESTILO_TITULO))
    story.append(Paragraph(
        "Se comparan eventos biométricos registrados en terminales VEH y eventos LPR depurados. "
        "Los mecanismos permanecen separados y se emplea la unidad eventos registrados.",
        ESTILO_NORMAL,
    ))
    resumen_veh = [["Mecanismo", "Entradas", "Salidas", "Días con datos", "Promedio diario de entradas"]]
    for mecanismo in ["Biométrico VEH", "LPR", "Consolidado"]:
        resumen_veh.append([
            mecanismo,
            f"{stats_veh['entradas'][mecanismo]:,}",
            f"{stats_veh['salidas'][mecanismo]:,}",
            f"{stats_veh['dias'][mecanismo]:,}",
            f"{stats_veh['promedios'][mecanismo]:.2f}",
        ])
    story.append(Table(resumen_veh, repeatRows=1, colWidths=[3.8*cm, 2.6*cm, 2.6*cm, 2.5*cm, 4.5*cm], style=[
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F8F9F9")),
    ]))
    story.append(Spacer(1, 0.5 * cm))

    flujo_carril = stats_veh["flujo_por_carril"]
    if not flujo_carril.empty:
        story.append(Paragraph("Intensidad real por carril", ESTILO_SUBTITULO))
        tabla_carril = [[
            "Mecanismo", "Ubicación", "Carril", "Sentido", "Eventos",
            "Hora pico real", "Ev./min hora pico", "Máximo real/min", "Minuto máximo",
        ]]
        for fila in flujo_carril.itertuples():
            tabla_carril.append([
                fila.Mecanismo, fila.Ubicacion, fila.Carril, fila.Sentido, f"{fila.Eventos:,}",
                fila.Hora_pico, f"{fila.Promedio_hora_pico_min:.2f}",
                f"{fila.Maximo_observado_minuto:,}", fila.Minuto_maximo,
            ])
        story.append(Table(tabla_carril, repeatRows=1, colWidths=[2.2*cm, 2.1*cm, 1*cm, 1.3*cm, 1.2*cm, 3.2*cm, 1.8*cm, 1.6*cm, 2.6*cm], style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3B82B8")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6.2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#BDC3C7")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F7")]),
        ]))
        story.append(Paragraph(
            "Hora pico real = fecha y hora concretas con más eventos del carril. Ev./min hora pico = eventos "
            "de esa hora / 60; no es el promedio mensual de una franja.", ESTILO_NORMAL,
        ))

    caudal = stats_veh["caudal_por_acceso"]
    if not caudal.empty:
        story.append(Paragraph("Caudal simultáneo por acceso físico", ESTILO_SUBTITULO))
        tabla_caudal = [[
            "Mecanismo", "Ubicación", "Sentido", "Carriles", "Minuto máximo",
            "Caudal eventos/min", "Promedio/carril", "Media hora pico",
        ]]
        for fila in caudal.itertuples():
            tabla_caudal.append([
                fila.Mecanismo, fila.Ubicacion, fila.Sentido, fila.Carriles, fila.Minuto_maximo,
                f"{fila.Caudal_maximo_eventos_min:,}",
                f"{fila.Promedio_por_carril_en_minuto_maximo:.2f}",
                f"{fila.Promedio_conjunto_hora_pico_min:.2f}",
            ])
        story.append(Table(tabla_caudal, repeatRows=1, colWidths=[2.3*cm, 2.2*cm, 1.5*cm, 1.5*cm, 3.4*cm, 2.2*cm, 2*cm, 1.9*cm], style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6.5),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#BDC3C7")),
        ]))
        story.append(Paragraph(
            "Los carriles se alinean por el mismo minuto calendario antes de sumarse. No se suman máximos "
            "ocurridos en momentos distintos.", ESTILO_NORMAL,
        ))
    
    # 3. Resumen de Registros Biométricos
    story.append(PageBreak())
    story.append(Paragraph("3. Resumen de registros biométricos", ESTILO_TITULO))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Se analizan los registros generados mediante los terminales biométricos del sistema, diferenciando los asociados a ingresos peatonales y a ingresos vehiculares.", ESTILO_NORMAL))
    story.append(Spacer(1, 0.5 * cm))
    
    for conclusion in conclusiones:
        story.append(Paragraph(formatear_texto_pdf(f"• {conclusion}"), ESTILO_CONCLUSION))
    story.append(Spacer(1, 0.5 * cm))
    
    datos_indicadores = [
        ["Métrica", "Valor"],
        ["Total de Registros Biométricos", f"{tasas.get('total', 0):,}"],
        ["Accesos biométricos exitosos", f"{tasas.get('exitosos', 0):,}"],
        ["Denegados", f"{tasas.get('denegados', 0):,}"],
        ["Fallos de reconocimiento", f"{tasas.get('fallos_rec', 0):,}"],
        ["Otros / no clasificados", f"{tasas.get('otros', 0):,}"],
        ["Tasa de Éxito", f"{tasas.get('tasa_exito', 0):.2f}%"],
        ["Tasa de Fallo General", f"{tasas.get('tasa_fallo_general', 0):.2f}%"]
    ]
    tabla_indicadores = Table(datos_indicadores, colWidths=[8*cm, 6*cm], style=[
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F2F4F4")),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
    ])
    story.append(tabla_indicadores)
    story.append(Spacer(1, 1 * cm))
    
    # 4. Flujo General Consolidado
    import all_events_visualizations as atv
    import lpr_visualizations as lprv
    import visualizations as v

    def safe_add_grafico(story, fig, alto=8 * cm):
        if fig is not None:
            try:
                _agregar_grafico(story, fig, alto=alto)
            except Exception as e:
                story.append(Paragraph(f"<font color='red'>Error al renderizar gráfico: {str(e)}</font>", ESTILO_NORMAL))

    story.append(Paragraph("3. Flujo General Consolidado", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    if "flujo_consolidado" in stats_base and not stats_base["flujo_consolidado"].empty:
        fig = v.grafico_flujo_consolidado(stats_base["flujo_consolidado"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "entradas_salidas" in stats_base and not stats_base["entradas_salidas"].empty:
        fig = v.grafico_entradas_salidas(stats_base["entradas_salidas"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))

    if "entradas_salidas_hora" in stats_base and not stats_base["entradas_salidas_hora"].empty:
        fig = v.grafico_entradas_salidas_hora(stats_base["entradas_salidas_hora"])
        safe_add_grafico(story, fig)

    story.append(PageBreak())

    # 5. Distribución Detallada por Categoría de Acceso
    story.append(Paragraph("4. Distribución general de registros por categoría de acceso", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    if "flujo_ingreso" in stats_base and not stats_base["flujo_ingreso"].empty:
        fig = v.grafico_ingreso(stats_base["flujo_ingreso"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))

    if "flujo_punto_acceso" in stats_base and not stats_base["flujo_punto_acceso"].empty:
        fig = v.grafico_flujo_punto_acceso(stats_base["flujo_punto_acceso"])
        safe_add_grafico(story, fig)

    story.append(PageBreak())
    
    # 6. Comportamiento Horario Consolidado y Detallado
    story.append(Paragraph("5. Comportamiento Horario y Diario", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    if "heatmap_consolidado_hora" in stats_base and not stats_base["heatmap_consolidado_hora"].empty:
        fig = v.grafico_heatmap_consolidado_hora(stats_base["heatmap_consolidado_hora"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "flujo_diario" in stats_base and not stats_base["flujo_diario"].empty:
        fig = v.grafico_flujo_diario(stats_base["flujo_diario"])
        safe_add_grafico(story, fig)
        story.append(PageBreak())
        
    if "flujo_hora" in stats_base and not stats_base["flujo_hora"].empty:
        fig = v.grafico_flujo_hora(stats_base["flujo_hora"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "ingreso_hora" in stats_base and not stats_base["ingreso_hora"].empty:
        fig = v.grafico_ingreso_hora(stats_base["ingreso_hora"])
        safe_add_grafico(story, fig)
        
    story.append(PageBreak())
    
    # 7. Mapas de Calor Adicionales
    story.append(Paragraph("6. Mapas de Calor: Puntos de Acceso y Días", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    if "heatmap_punto_hora" in stats_base and not stats_base["heatmap_punto_hora"].empty:
        fig = v.grafico_heatmap_punto_hora(stats_base["heatmap_punto_hora"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "heatmap_dia_hora" in stats_base and not stats_base["heatmap_dia_hora"].empty:
        fig = v.grafico_heatmap_dia_hora(stats_base["heatmap_dia_hora"])
        safe_add_grafico(story, fig)

    story.append(PageBreak())
    
    # 8. Usuarios por Tipo
    story.append(Paragraph("7. Usuarios por Tipo y Punto de Acceso", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    if "tipo_usuario" in stats_base and not stats_base["tipo_usuario"].empty:
        fig = v.grafico_tipo_usuario(stats_base["tipo_usuario"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "tipo_usuario_ingreso" in stats_base and not stats_base["tipo_usuario_ingreso"].empty:
        fig = v.grafico_tipo_usuario_ingreso(stats_base["tipo_usuario_ingreso"])
        safe_add_grafico(story, fig)
        story.append(PageBreak())
        
    if "punto_tipo_usuario" in stats_base and not stats_base["punto_tipo_usuario"].empty:
        fig = v.grafico_punto_tipo_usuario(stats_base["punto_tipo_usuario"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))

    # 9. Análisis de Tasas de Fallo y Éxito
    story.append(Paragraph("8. Análisis de Resultados y Tasas de Fallo", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    if "resultados" in stats_nuevas and not stats_nuevas["resultados"].empty:
        fig = atv.grafico_resultados_generales(stats_nuevas["resultados"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "cruce_ingreso" in stats_nuevas and not stats_nuevas["cruce_ingreso"].empty:
        fig = atv.grafico_cruce_ingreso_resultado(stats_nuevas["cruce_ingreso"])
        safe_add_grafico(story, fig)
        story.append(PageBreak())
        
    if "evolucion_diaria" in stats_nuevas and not stats_nuevas["evolucion_diaria"].empty:
        fig = atv.grafico_evolucion_resultado(stats_nuevas["evolucion_diaria"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "cruce_hora" in stats_nuevas and not stats_nuevas["cruce_hora"].empty:
        fig = atv.grafico_cruce_hora_resultado(stats_nuevas["cruce_hora"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
    
    if "cruce_punto" in stats_nuevas and not stats_nuevas["cruce_punto"].empty:
        fig = atv.grafico_punto_acceso_resultado(stats_nuevas["cruce_punto"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "cruce_device" in stats_nuevas and not stats_nuevas["cruce_device"].empty:
        dispositivos = stats_nuevas["cruce_device"].copy()
        for columna in ["Denegado", "Fallo de reconocimiento"]:
            if columna not in dispositivos.columns:
                dispositivos[columna] = 0
        dispositivos["Fallos_y_denegados"] = (
            dispositivos["Denegado"] + dispositivos["Fallo de reconocimiento"]
        )
        dispositivos = dispositivos.sort_values(
            ["Fallos_y_denegados", "Total"], ascending=False
        ).head(15)
        tabla_dispositivos = [[
            "Dispositivo", "Intentos", "Fallo reconocimiento", "Denegados", "Total adversos", "Tasa adversa",
        ]]
        for _, fila in dispositivos.iterrows():
            tabla_dispositivos.append([
                str(fila["Device Name"]), f"{int(fila['Total']):,}",
                f"{int(fila['Fallo de reconocimiento']):,}", f"{int(fila['Denegado']):,}",
                f"{int(fila['Fallos_y_denegados']):,}", f"{float(fila['Tasa_Fallo']):.2f}%",
            ])
        story.append(Paragraph("Dispositivos con mayor cantidad de resultados adversos", ESTILO_SUBTITULO))
        story.append(Table(tabla_dispositivos, repeatRows=1, colWidths=[5.8*cm, 2*cm, 3*cm, 2*cm, 2.2*cm, 2*cm], style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#BDC3C7")),
        ]))
        story.append(Paragraph(
            "El orden usa cantidades absolutas y luego volumen total, evitando priorizar porcentajes altos con "
            "muestras pequeñas. Una tasa elevada identifica un punto para verificación; no demuestra por sí sola "
            "una causa de red, iluminación, cámara o configuración.", ESTILO_NORMAL,
        ))
        anomalia_dispositivo = stats_nuevas.get("anomalias", {}).get("peor_device")
        if anomalia_dispositivo:
            story.append(Paragraph(
                formatear_texto_pdf(
                    f"Punto de atención con muestra suficiente: {anomalia_dispositivo['entidad']} registró "
                    f"una tasa adversa de {anomalia_dispositivo['tasa']:.2f}% sobre "
                    f"{int(anomalia_dispositivo['total']):,} intentos. El hallazgo justifica verificación, "
                    "pero no establece una causa técnica."
                ),
                ESTILO_CONCLUSION,
            ))
        try:
            fig = atv.grafico_device_resultado(stats_nuevas["cruce_device"])
            safe_add_grafico(story, fig)
        except Exception as e:
            story.append(Paragraph(f"<font color='red'>Error al renderizar gráfico devices: {str(e)}</font>", ESTILO_NORMAL))

    story.append(PageBreak())
    
    # 10. Frecuencia
    story.append(Paragraph("9. Frecuencia de Utilización", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    if "frecuencia" in stats_base and not stats_base["frecuencia"].empty:
        fig = v.grafico_frecuencia(stats_base["frecuencia"])
        safe_add_grafico(story, fig)

    story.append(PageBreak())

    # 11. Analítica Avanzada LPR
    if stats_gen_lpr is not None and df_lpr_f is not None and not df_lpr_f.empty:
        story.append(Paragraph("10. Flujo Vehicular LPR (Reconocimiento de Placas)", ESTILO_TITULO))
        story.append(Spacer(1, 0.5 * cm))
        
        import lpr_statistics_calc as lprs
        texto_resumen = lprs.generar_texto_resumen_ejecutivo(df_lpr_f, stats_gen_lpr)
        story.append(Paragraph(formatear_texto_pdf(texto_resumen).replace('\n', '<br/>'), ESTILO_NORMAL))
        story.append(Spacer(1, 0.5 * cm))
        
        datos_lpr = [
            ["Eventos Válidos", "Placas Únicas", "Entradas", "Salidas"],
            [
                f"{stats_gen_lpr.get('eventos_validos', 0):,}",
                f"{stats_gen_lpr.get('placas_unicas', 0):,}",
                f"{stats_gen_lpr.get('entradas', 0):,}",
                f"{stats_gen_lpr.get('salidas', 0):,}"
            ]
        ]
        tabla_lpr = Table(datos_lpr, colWidths=[4*cm, 4*cm, 4*cm, 4*cm], style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3B82B8")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F8F9F9")),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#D5D8DC")),
        ])
        story.append(tabla_lpr)
        story.append(Spacer(1, 0.5 * cm))

        resumen_entradas = lprs.resumen_entradas_vehiculares(df_lpr_f)
        pico = resumen_entradas.get("fecha_pico")
        datos_entradas = [
            ["Entradas registradas", "Días con datos", "Promedio diario", "Día de mayor ingreso"],
            [
                f"{resumen_entradas['total_entradas']:,}",
                f"{resumen_entradas['dias_con_datos']:,}",
                f"{resumen_entradas['promedio_diario']:.2f}",
                (f"{pico.strftime('%d/%m/%Y')} ({resumen_entradas['entradas_pico']:,})" if pico else "Sin entradas"),
            ],
        ]
        story.append(Table(datos_entradas, colWidths=[4*cm]*4, style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#DDEBF7")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#AAB7B8")),
        ]))
        story.append(Paragraph(
            formatear_texto_pdf("<font size=8>Promedio diario = entradas LPR depuradas / días con datos LPR del contexto filtrado.</font>"),
            ESTILO_NORMAL,
        ))
        story.append(Spacer(1, 0.7 * cm))
        
        # Gráficos LPR
        df_hora_flujo = lprs.stats_flujo_vehicular_por_hora(df_lpr_f)
        if not df_hora_flujo.empty and df_hora_flujo["Registros"].max() > 0:
            pico_hora = df_hora_flujo.loc[df_hora_flujo["Registros"].idxmax()]
            texto_temporal = (
                f"La franja pico acumuló {int(pico_hora['Registros']):,} registros. "
                f"Promedio acumulado secundario por minuto de franja: {pico_hora['Promedio_registros_minuto']}; "
                f"promedio diario de la franja: {pico_hora['Promedio_por_dia']}; "
                f"máximo real observado en un minuto: {int(pico_hora['Maximo_real_por_minuto'])}. "
                f"El denominador fue {int(pico_hora['Dias_considerados'])} días con datos × 60 minutos."
            )
            story.append(Paragraph(formatear_texto_pdf(texto_temporal), ESTILO_NORMAL))
            story.append(Spacer(1, 0.3 * cm))
        fig = lprv.grafico_flujo_vehicular_por_hora(df_hora_flujo, theme="light")
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
        df_dia = lprs.stats_eventos_por_dia(df_lpr_f)
        fig = lprv.grafico_lpr_por_dia(df_dia, theme="light")
        safe_add_grafico(story, fig)
        
        story.append(PageBreak())
        
        df_heatmap = lprs.stats_heatmap_dia_hora(df_lpr_f)
        fig = lprv.grafico_heatmap_lpr(df_heatmap, theme="light")
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
        df_lpr_sitio = lprs.stats_lpr_por_sitio(df_lpr_f)
        if not df_lpr_sitio.empty:
            fig = lprv.grafico_lpr_por_sitio(df_lpr_sitio, theme="light")
            safe_add_grafico(story, fig)

        movimientos = lprs.stats_movimientos_lpr_por_ubicacion_camara(df_lpr_f)
        if not movimientos["por_ubicacion"].empty:
            tabla_movimientos = [["Ubicación", "Sentido", "Registros"]] + [
                [fila.Ubicacion, fila.Sentido, f"{int(fila.Registros):,}"]
                for fila in movimientos["por_ubicacion"].itertuples()
            ]
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph("Entradas y salidas por ubicación", ESTILO_SUBTITULO))
            story.append(Table(tabla_movimientos, colWidths=[6*cm, 5*cm, 4*cm], style=[
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#DDEBF7")),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#AAB7B8")),
            ]))
            
        story.append(PageBreak())
            
        df_top = lprs.stats_lpr_top_placas(df_lpr_f, 10)
        if not df_top.empty:
            df_top = df_top.copy()
            df_top["Matricula"] = df_top["Matricula"].apply(_anonimizar_matricula)
            fig = lprv.grafico_top_placas(df_top, theme="light")
            safe_add_grafico(story, fig)

    story.append(PageBreak())
    story.append(Paragraph("11. Metodología y limitaciones", ESTILO_TITULO))
    metodologia = [
        "Fuentes: exportaciones de HikCentral Professional para eventos biométricos y reconocimiento LPR.",
        "Biométrico peatonal, biométrico VEH y LPR se clasifican como mecanismos distintos. Un evento facial en un terminal VEH no prueba por sí solo el paso de un vehículo.",
        "Los eventos LPR empleados conservan la regla de depuración vigente del proyecto. No se modifican los archivos Excel originales.",
        "Evento significa un registro del sistema; matrícula única y usuario único son identificadores distintos y no equivalen necesariamente a desplazamientos o vehículos físicos distintos.",
        "Los promedios diarios usan días con datos del mecanismo dentro del contexto filtrado. Un día ausente no se interpreta como circulación cero.",
        "El flujo por minuto agrupa fecha, hora y minuto completos, ubicación, carril, sentido y mecanismo. La hora pico es una hora calendario concreta y su promedio se divide para 60 minutos.",
        "El caudal conjunto alinea carriles del mismo acceso en el mismo minuto. No suma máximos producidos en instantes diferentes.",
        "Las matrículas mostradas en este informe se anonimizan; los datos internos no se alteran.",
    ]
    for texto in metodologia:
        story.append(Paragraph(formatear_texto_pdf(f"• {texto}"), ESTILO_NORMAL))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("12. Conclusiones técnicas y recomendaciones", ESTILO_TITULO))
    conclusiones_tecnicas = []
    if not eventos_vehiculares.empty and not stats_veh["flujo_por_carril"].empty:
        top_carril = stats_veh["flujo_por_carril"].loc[stats_veh["flujo_por_carril"]["Eventos"].idxmax()]
        conclusiones_tecnicas.append(
            f"El carril con más actividad registrada fue {top_carril['Ubicacion']} {top_carril['Carril']} "
            f"mediante {top_carril['Mecanismo']}, con {int(top_carril['Eventos']):,} eventos."
        )
        conclusiones_tecnicas.append(
            f"Su hora calendario de mayor actividad fue {top_carril['Hora_pico']}, con una intensidad media "
            f"de {top_carril['Promedio_hora_pico_min']:.2f} eventos por minuto."
        )
    if tasas.get("fallidos", 0):
        conclusiones_tecnicas.append(
            f"Se observaron {tasas.get('fallos_rec', 0):,} fallos de reconocimiento y "
            f"{tasas.get('denegados', 0):,} denegaciones, que deben interpretarse como resultados diferenciados."
        )
    if not conclusiones_tecnicas:
        conclusiones_tecnicas.append("El conjunto filtrado no aporta datos suficientes para conclusiones vehiculares específicas.")
    for texto in conclusiones_tecnicas:
        story.append(Paragraph(formatear_texto_pdf(f"• {texto}"), ESTILO_CONCLUSION))
    recomendaciones = [
        "Evaluar la operación de los accesos y carriles con mayor concentración durante sus horas pico reales.",
        "Verificar primero los dispositivos con mayor cantidad de fallos y una muestra suficiente, conservando evidencia antes de atribuir causas.",
        "Mantener seguimiento periódico por mecanismo, ubicación, sentido y carril para comparar períodos equivalentes.",
    ]
    for texto in recomendaciones:
        story.append(Paragraph(formatear_texto_pdf(f"Recomendación: {texto}"), ESTILO_NORMAL))

    periodo = f"{fecha_min} – {fecha_max}"
    pie = lambda canvas, documento: _dibujar_pie_integral(canvas, documento, periodo)
    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    buffer.seek(0)
    return buffer
