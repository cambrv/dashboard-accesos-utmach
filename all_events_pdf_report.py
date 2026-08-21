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

def exportar_reporte_integral_pdf(df: pd.DataFrame, tasas: dict, stats_base: dict, stats_nuevas: dict, conclusiones: list, calidad: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    
    # 1. Portada
    fecha_min = df["Fecha"].min().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].min()) else "N/A"
    fecha_max = df["Fecha"].max().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].max()) else "N/A"
    _agregar_portada_integral(story, fecha_min, fecha_max, "REPORTE INTEGRAL DE EVENTOS PEATONALES")
    story.append(PageBreak())
    
    # 2. Resumen Ejecutivo
    story.append(Paragraph("Resumen Ejecutivo", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    for conclusion in conclusiones:
        story.append(Paragraph(f"• {conclusion}", ESTILO_CONCLUSION))
        story.append(Spacer(1, 0.3 * cm))
    story.append(Spacer(1, 1 * cm))
    
    # 3. Indicadores Generales
    story.append(Paragraph("1. Indicadores Generales", ESTILO_SECCION))
    datos_indicadores = [
        ["Métrica", "Valor"],
        ["Total de Eventos", f"{tasas.get('total', 0):,}"],
        ["Eventos Normales", f"{tasas.get('exitosos', 0):,}"],
        ["Eventos Anormales", f"{tasas.get('fallidos', 0):,}"],
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
    
    # 4. Resultados Generales
    if "resultados" in stats_nuevas and not stats_nuevas["resultados"].empty:
        fig = grafico_resultados_generales(stats_nuevas["resultados"])
        _agregar_grafico(story, fig, alto=7 * cm)
    story.append(PageBreak())
    
    # =========================================================================
    # BLOQUE DE ESTADÍSTICAS BASE (Heredado de Eventos Exitosos)
    # =========================================================================
    
    # 5. Flujo por Ingreso
    story.append(Paragraph("2. Flujo por Ingreso", ESTILO_SECCION))
    if not stats_base["flujo_ingreso"].empty:
        fig = v.grafico_ingreso(stats_base["flujo_ingreso"])
        _agregar_grafico(story, fig, alto=8 * cm)
    story.append(PageBreak())
        
    # 6. Entradas vs Salidas
    story.append(Paragraph("3. Entradas vs Salidas", ESTILO_SECCION))
    if not stats_base["entradas_salidas"].empty:
        fig = v.grafico_entradas_salidas(stats_base["entradas_salidas"])
        _agregar_grafico(story, fig, alto=7 * cm)
    if not stats_base["entradas_salidas_hora"].empty:
        fig2 = v.grafico_entradas_salidas_hora(stats_base["entradas_salidas_hora"])
        _agregar_grafico(story, fig2, alto=7 * cm)
    story.append(PageBreak())

    # 7. Análisis Horario
    story.append(Paragraph("4. Análisis Horario", ESTILO_SECCION))
    if not stats_base["flujo_hora"].empty:
        fig = v.grafico_flujo_hora(stats_base["flujo_hora"])
        _agregar_grafico(story, fig, alto=7 * cm)
    if not stats_base["ingreso_hora"].empty:
        fig2 = v.grafico_ingreso_hora(stats_base["ingreso_hora"])
        _agregar_grafico(story, fig2, alto=7 * cm)
    story.append(PageBreak())

    # 8. Heatmaps (Punto x Hora, Día x Hora)
    story.append(Paragraph("5. Mapas de Calor", ESTILO_SECCION))
    if not stats_base["heatmap_punto_hora"].empty:
        fig = v.grafico_heatmap_punto_hora(stats_base["heatmap_punto_hora"])
        _agregar_grafico(story, fig, alto=7 * cm)
    if not stats_base["heatmap_dia_hora"].empty:
        fig2 = v.grafico_heatmap_dia_hora(stats_base["heatmap_dia_hora"])
        _agregar_grafico(story, fig2, alto=7 * cm)
    story.append(PageBreak())
    
    # 9. Evolución Diaria y Día de Semana
    story.append(Paragraph("6. Comportamiento Diario", ESTILO_SECCION))
    if not stats_base["flujo_diario"].empty:
        fig = v.grafico_flujo_diario(stats_base["flujo_diario"])
        _agregar_grafico(story, fig, alto=7 * cm)
    if not stats_base["dia_semana"].empty:
        fig2 = v.grafico_dia_semana(stats_base["dia_semana"])
        _agregar_grafico(story, fig2, alto=7 * cm)
    story.append(PageBreak())

    # 10. Tipo de Usuario y Puntos de Acceso
    story.append(Paragraph("7. Tipo de Usuario y Puntos de Acceso", ESTILO_SECCION))
    if not stats_base["tipo_usuario"].empty:
        fig = v.grafico_tipo_usuario(stats_base["tipo_usuario"])
        _agregar_grafico(story, fig, alto=7 * cm)
    if not stats_base["tipo_usuario_ingreso"].empty:
        fig2 = v.grafico_tipo_usuario_ingreso(stats_base["tipo_usuario_ingreso"])
        _agregar_grafico(story, fig2, alto=7 * cm)
    story.append(PageBreak())
    
    if not stats_base["flujo_punto_acceso"].empty:
        story.append(Paragraph("8. Flujo por Punto de Acceso", ESTILO_SECCION))
        fig = v.grafico_flujo_punto_acceso(stats_base["flujo_punto_acceso"])
        _agregar_grafico(story, fig, alto=9 * cm)
        story.append(PageBreak())
        
    if not stats_base["punto_tipo_usuario"].empty:
        story.append(Paragraph("9. Puntos de Acceso x Tipo Usuario", ESTILO_SECCION))
        fig = v.grafico_punto_tipo_usuario(stats_base["punto_tipo_usuario"])
        _agregar_grafico(story, fig, alto=9 * cm)
        story.append(PageBreak())
        
    if not stats_base["frecuencia"].empty:
        story.append(Paragraph("10. Frecuencia de Utilización", ESTILO_SECCION))
        fig = v.grafico_frecuencia(stats_base["frecuencia"])
        _agregar_grafico(story, fig, alto=7 * cm)
        story.append(PageBreak())

    # =========================================================================
    # BLOQUE DE ESTADÍSTICAS NUEVAS (Tasas de Fallo y Cruces)
    # =========================================================================
    
    story.append(Paragraph("11. Análisis de Tasas de Éxito y Fallo", ESTILO_SECCION))
    
    # Ingreso x Resultado
    if "cruce_ingreso" in stats_nuevas and not stats_nuevas["cruce_ingreso"].empty:
        fig = grafico_cruce_ingreso_resultado(stats_nuevas["cruce_ingreso"])
        _agregar_grafico(story, fig, alto=7 * cm)
        df_t = stats_nuevas["cruce_ingreso"].copy()
        df_t["Tasa_Fallo"] = df_t["Tasa_Fallo"].astype(str) + "%"
        story.append(_tabla_dataframe(df_t))
        story.append(Spacer(1, 1 * cm))
        
    # Hora x Resultado
    if "cruce_hora" in stats_nuevas and not stats_nuevas["cruce_hora"].empty:
        fig = grafico_cruce_hora_resultado(stats_nuevas["cruce_hora"])
        _agregar_grafico(story, fig, alto=7 * cm)
        story.append(PageBreak())
        
    # Punto de Acceso x Resultado
    story.append(Paragraph("12. Tasas por Punto de Acceso y Dispositivo", ESTILO_SECCION))
    if "cruce_punto" in stats_nuevas and not stats_nuevas["cruce_punto"].empty:
        fig = grafico_punto_acceso_resultado(stats_nuevas["cruce_punto"])
        _agregar_grafico(story, fig, alto=8 * cm)
        
    # Device Name x Resultado
    if "cruce_device" in stats_nuevas and not stats_nuevas["cruce_device"].empty:
        fig = grafico_device_resultado(stats_nuevas["cruce_device"])
        _agregar_grafico(story, fig, alto=8 * cm)
        story.append(PageBreak())
        
    # Tipo Usuario x Resultado
    if "cruce_usuario" in stats_nuevas and not stats_nuevas["cruce_usuario"].empty:
        story.append(Paragraph("13. Tasas por Tipo de Usuario", ESTILO_SECCION))
        fig = grafico_tipo_usuario_resultado(stats_nuevas["cruce_usuario"])
        _agregar_grafico(story, fig, alto=8 * cm)
        story.append(PageBreak())
        
    # Evolución x Resultado
    story.append(Paragraph("14. Evolución Temporal de Tasas", ESTILO_SECCION))
    if "evolucion_diaria" in stats_nuevas and not stats_nuevas["evolucion_diaria"].empty:
        fig = grafico_evolucion_resultado(stats_nuevas["evolucion_diaria"])
        _agregar_grafico(story, fig, alto=7 * cm)
    if "dia_semana" in stats_nuevas and not stats_nuevas["dia_semana"].empty:
        fig = grafico_dia_semana_resultado(stats_nuevas["dia_semana"])
        _agregar_grafico(story, fig, alto=7 * cm)
        
    story.append(PageBreak())
    
    # 15. Comportamientos Anormales
    story.append(Paragraph("15. Indicadores de Comportamiento Anormal", ESTILO_SECCION))
    story.append(Spacer(1, 0.5 * cm))
    anomalias = stats_nuevas.get("anomalias", {})
    if not anomalias:
        story.append(Paragraph("No se detectaron suficientes datos para analizar anomalías.", ESTILO_NORMAL))
    else:
        for k, anomalia_val in anomalias.items():
            if anomalia_val:
                texto = ""
                if k == "peor_ingreso": texto = f"El Ingreso con peor tasa de fallo es '{anomalia_val['entidad']}' ({anomalia_val['tasa']}% de fallos en {int(anomalia_val['total'])} eventos)."
                elif k == "peor_hora": texto = f"La Hora con peor tasa de fallo es las {int(anomalia_val['entidad']):02d}:00 ({anomalia_val['tasa']}% de fallos en {int(anomalia_val['total'])} eventos)."
                elif k == "peor_punto": texto = f"El Punto de Acceso con peor tasa de fallo es '{anomalia_val['entidad']}' ({anomalia_val['tasa']}% de fallos en {int(anomalia_val['total'])} eventos)."
                elif k == "peor_device": texto = f"El Dispositivo con peor tasa de fallo es '{anomalia_val['entidad']}' ({anomalia_val['tasa']}% de fallos en {int(anomalia_val['total'])} eventos)."
                
                if texto:
                    story.append(Paragraph(f"• {texto}", ESTILO_NORMAL))
                    story.append(Spacer(1, 0.2 * cm))

    doc.build(story)
    buffer.seek(0)
    return buffer
