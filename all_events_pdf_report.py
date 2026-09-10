"""
Exportación a PDF del Reporte Integral ("Todos los Eventos").
Este reporte compila el 100% de las gráficas de Eventos Exitosos + las nuevas gráficas de Tasas de Fallo.
"""
import io
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle

# Imports de base
from pdf_report import (
    ESTILO_TITULO, ESTILO_NORMAL, ESTILO_SECCION, ESTILO_CONCLUSION,
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
        ["Fecha de generación:", datetime.now().strftime("%d/%m/%Y %H:%M")],
    ]
    tabla_fechas = Table(datos_fechas, colWidths=[6 * cm, 6 * cm], style=[
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONT", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
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
    
    # 2. Resumen General de Movilidad
    import lpr_statistics_calc as lprs
    huella = huella_dashboard if huella_dashboard is not None else lprs.generar_huella_movilidad(df, df_lpr_f)
    
    story.append(Paragraph("1. Resumen General de Movilidad", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    texto_huella = (
        f"Durante el período analizado se procesaron {huella['tot_registros']:,} registros en total. "
        f"El {huella['pct_peatones_puros']}% ({huella['tot_peatones_puros']:,}) correspondió a registros de ingreso peatonal/biométrico, "
        f"el {huella['pct_terminales_veh']}% ({huella['tot_terminales_veh']:,}) a registros biométricos en terminales vehiculares, "
        f"y el {huella['pct_lpr']}% ({huella['tot_lpr']:,}) a eventos de reconocimiento de placas (LPR)."
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
    
    # 3. Resumen de Registros Biométricos
    story.append(Paragraph("2. Resumen de Registros Biométricos", ESTILO_TITULO))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Se analizan los registros generados mediante los terminales biométricos del sistema, diferenciando los asociados a ingresos peatonales y a ingresos vehiculares.", ESTILO_NORMAL))
    story.append(Spacer(1, 0.5 * cm))
    
    for conclusion in conclusiones:
        story.append(Paragraph(formatear_texto_pdf(f"• {conclusion}"), ESTILO_CONCLUSION))
    story.append(Spacer(1, 0.5 * cm))
    
    datos_indicadores = [
        ["Métrica", "Valor"],
        ["Total de Registros Biométricos", f"{tasas.get('total', 0):,}"],
        ["Registros Normales", f"{tasas.get('exitosos', 0):,}"],
        ["Registros Anormales", f"{tasas.get('fallidos', 0):,}"],
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
    story.append(Paragraph("4. Distribución por Categoría de Acceso (Biometría)", ESTILO_TITULO))
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
        story.append(Spacer(1, 1 * cm))
        
        # Gráficos LPR
        df_hora_flujo = lprs.stats_flujo_vehicular_por_hora(df_lpr_f)
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
            
        story.append(PageBreak())
            
        df_top = lprs.stats_lpr_top_placas(df_lpr_f, 10)
        if not df_top.empty:
            fig = lprv.grafico_top_placas(df_top, theme="light")
            safe_add_grafico(story, fig)

    doc.build(story)
    buffer.seek(0)
    return buffer
