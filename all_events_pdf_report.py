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

def exportar_reporte_integral_pdf(df: pd.DataFrame, tasas: dict, stats_base: dict, stats_nuevas: dict, conclusiones: list, calidad: dict, stats_gen_lpr: dict = None, df_lpr_f: pd.DataFrame = None, conclusiones_lpr: list = None) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    
    # 1. Portada
    fecha_min = df["Fecha"].min().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].min()) else "N/A"
    fecha_max = df["Fecha"].max().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].max()) else "N/A"
    _agregar_portada_integral(story, fecha_min, fecha_max, "REPORTE INTEGRAL DE EVENTOS PEATONALES")
    story.append(PageBreak())
    
    # 2. Huella de Movilidad
    import lpr_statistics_calc as lprs
    huella = lprs.generar_huella_movilidad(df, df_lpr_f)
    
    story.append(Paragraph("Resumen General de Flujo", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    # Texto descriptivo de la Huella
    texto_huella = (
        f"Durante el período analizado se procesaron {huella['tot_registros']:,} registros en total. "
        f"El {huella['pct_peatones_puros']}% ({huella['tot_peatones_puros']:,}) correspondió a registros peatonales puros, "
        f"el {huella['pct_terminales_veh']}% ({huella['tot_terminales_veh']:,}) a registros biométricos en terminales VEH, "
        f"y el {huella['pct_lpr']}% ({huella['tot_lpr']:,}) a eventos de reconocimiento de placas (LPR)."
    )
    story.append(Paragraph(texto_huella, ESTILO_NORMAL))
    story.append(Spacer(1, 0.5 * cm))
    
    nota_metodologica = "Nota: Las categorías representan registros generados por diferentes mecanismos. Un mismo acceso físico puede generar más de un registro. Por esta razón, las categorías no deben sumarse automáticamente como accesos físicos independientes."
    story.append(Paragraph(f"<i>{nota_metodologica}</i>", ESTILO_NORMAL))
    story.append(Spacer(1, 0.5 * cm))
    
    datos_huella = [
        ["Registros Analizados", "Peatonales", "Terminales VEH", "Eventos LPR", "Día Pico", "Hora Pico", "Acceso Pico"],
        [
            f"{huella['tot_registros']:,}", 
            f"{huella['tot_peatones_puros']:,}", 
            f"{huella['tot_terminales_veh']:,}", 
            f"{huella['tot_lpr']:,}",
            huella['dia_pico_str'].split(' — ')[0] if ' — ' in huella['dia_pico_str'] else huella['dia_pico_str'],
            huella['hora_pico_str'].split(' — ')[0] if ' — ' in huella['hora_pico_str'] else huella['hora_pico_str'],
            huella['acceso_pico_str'].split(' — ')[0] if ' — ' in huella['acceso_pico_str'] else huella['acceso_pico_str']
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

    # 3. Resumen Peatonal
    story.append(Paragraph("Resumen Ejecutivo Peatonal", ESTILO_TITULO))
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
        _agregar_grafico(story, fig, alto=9 * cm)
    story.append(PageBreak())
    
    # =========================================================================
    # BLOQUE DE ESTADÍSTICAS BASE (Heredado de Eventos Exitosos)
    # =========================================================================
    
    # 5. Flujo por Ingreso
    story.append(Paragraph("2. Flujo por Ingreso", ESTILO_SECCION))
    if not stats_base["flujo_ingreso"].empty:
        fig = v.grafico_ingreso(stats_base["flujo_ingreso"])
        _agregar_grafico(story, fig, alto=9 * cm)
    story.append(PageBreak())
        
    # 6. Entradas vs Salidas
    story.append(Paragraph("3. Entradas vs Salidas", ESTILO_SECCION))
    if not stats_base["entradas_salidas"].empty:
        fig = v.grafico_entradas_salidas(stats_base["entradas_salidas"])
        _agregar_grafico(story, fig, alto=9 * cm)
    if not stats_base["entradas_salidas_hora"].empty:
        fig2 = v.grafico_entradas_salidas_hora(stats_base["entradas_salidas_hora"])
        _agregar_grafico(story, fig2, alto=9 * cm)
    story.append(PageBreak())

    # 7. Análisis Horario
    story.append(Paragraph("4. Análisis Horario", ESTILO_SECCION))
    if not stats_base["flujo_hora"].empty:
        fig = v.grafico_flujo_hora(stats_base["flujo_hora"])
        _agregar_grafico(story, fig, alto=9 * cm)
    if not stats_base["ingreso_hora"].empty:
        fig2 = v.grafico_ingreso_hora(stats_base["ingreso_hora"])
        _agregar_grafico(story, fig2, alto=9 * cm)
    story.append(PageBreak())

    # 8. Heatmaps (Punto x Hora, Día x Hora)
    story.append(Paragraph("5. Mapas de Calor", ESTILO_SECCION))
    if not stats_base["heatmap_punto_hora"].empty:
        fig = v.grafico_heatmap_punto_hora(stats_base["heatmap_punto_hora"])
        _agregar_grafico(story, fig, alto=9 * cm)
    if not stats_base["heatmap_dia_hora"].empty:
        fig2 = v.grafico_heatmap_dia_hora(stats_base["heatmap_dia_hora"])
        _agregar_grafico(story, fig2, alto=9 * cm)
    story.append(PageBreak())
    
    # 9. Evolución Diaria y Día de Semana
    story.append(Paragraph("6. Comportamiento Diario", ESTILO_SECCION))
    if not stats_base["flujo_diario"].empty:
        fig = v.grafico_flujo_diario(stats_base["flujo_diario"])
        _agregar_grafico(story, fig, alto=9 * cm)
    if not stats_base["dia_semana"].empty:
        fig2 = v.grafico_dia_semana(stats_base["dia_semana"])
        _agregar_grafico(story, fig2, alto=9 * cm)
    story.append(PageBreak())

    # 10. Tipo de Usuario y Puntos de Acceso
    story.append(Paragraph("7. Tipo de Usuario y Puntos de Acceso", ESTILO_SECCION))
    if not stats_base["tipo_usuario"].empty:
        fig = v.grafico_tipo_usuario(stats_base["tipo_usuario"])
        _agregar_grafico(story, fig, alto=9 * cm)
    if not stats_base["tipo_usuario_ingreso"].empty:
        fig2 = v.grafico_tipo_usuario_ingreso(stats_base["tipo_usuario_ingreso"])
        _agregar_grafico(story, fig2, alto=9 * cm)
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
        _agregar_grafico(story, fig, alto=9 * cm)
        story.append(PageBreak())

    # =========================================================================
    # BLOQUE DE ESTADÍSTICAS NUEVAS (Tasas de Fallo y Cruces)
    # =========================================================================
    
    story.append(Paragraph("11. Análisis de Tasas de Éxito y Fallo", ESTILO_SECCION))
    
    # Ingreso x Resultado
    if "cruce_ingreso" in stats_nuevas and not stats_nuevas["cruce_ingreso"].empty:
        fig = grafico_cruce_ingreso_resultado(stats_nuevas["cruce_ingreso"])
        _agregar_grafico(story, fig, alto=9 * cm)
        df_t = stats_nuevas["cruce_ingreso"].copy()
        df_t["Tasa_Fallo"] = df_t["Tasa_Fallo"].astype(str) + "%"
        story.append(_tabla_dataframe(df_t))
        story.append(Spacer(1, 1 * cm))
        
    # Hora x Resultado
    if "cruce_hora" in stats_nuevas and not stats_nuevas["cruce_hora"].empty:
        fig = grafico_cruce_hora_resultado(stats_nuevas["cruce_hora"])
        _agregar_grafico(story, fig, alto=9 * cm)
        story.append(PageBreak())
        
    # Punto de Acceso x Resultado
    story.append(Paragraph("12. Tasas por Punto de Acceso y Dispositivo", ESTILO_SECCION))
    if "cruce_punto" in stats_nuevas and not stats_nuevas["cruce_punto"].empty:
        fig = grafico_punto_acceso_resultado(stats_nuevas["cruce_punto"])
        _agregar_grafico(story, fig, alto=9 * cm)
        
    # Device Name x Resultado
    if "cruce_device" in stats_nuevas and not stats_nuevas["cruce_device"].empty:
        fig = grafico_device_resultado(stats_nuevas["cruce_device"])
        _agregar_grafico(story, fig, alto=9 * cm)
        story.append(PageBreak())
        
    # Tipo Usuario x Resultado
    if "cruce_usuario" in stats_nuevas and not stats_nuevas["cruce_usuario"].empty:
        story.append(Paragraph("13. Tasas por Tipo de Usuario", ESTILO_SECCION))
        fig = grafico_tipo_usuario_resultado(stats_nuevas["cruce_usuario"])
        _agregar_grafico(story, fig, alto=9 * cm)
        story.append(PageBreak())
        
    # Evolución x Resultado
    story.append(Paragraph("14. Evolución Temporal de Tasas", ESTILO_SECCION))
    if "evolucion_diaria" in stats_nuevas and not stats_nuevas["evolucion_diaria"].empty:
        fig = grafico_evolucion_resultado(stats_nuevas["evolucion_diaria"])
        _agregar_grafico(story, fig, alto=9 * cm)
    if "dia_semana" in stats_nuevas and not stats_nuevas["dia_semana"].empty:
        fig = grafico_dia_semana_resultado(stats_nuevas["dia_semana"])
        _agregar_grafico(story, fig, alto=9 * cm)
        
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

    # Removido doc.build() prematuro
    if stats_gen_lpr is not None and df_lpr_f is not None and not df_lpr_f.empty:
        story.append(PageBreak())
        story.append(Paragraph("13. Análisis Vehicular LPR", ESTILO_SECCION))
        story.append(Spacer(1, 0.5 * cm))
        
        import lpr_visualizations as lprv
        import lpr_statistics_calc as lprs
        
        # Resumen de texto
        texto_resumen = lprs.generar_texto_resumen_ejecutivo(df_lpr_f, stats_gen_lpr)
        story.append(Paragraph(texto_resumen.replace('\n', '<br/>'), ESTILO_NORMAL))
        story.append(Spacer(1, 0.5 * cm))
        
        # Tabla de métricas LPR
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
        try:
            df_dia = lprs.stats_eventos_por_dia(df_lpr_f)
            fig_dia = lprv.grafico_lpr_por_dia(df_dia, theme="light")
            _agregar_grafico(story, fig_dia, alto=9 * cm)
            
            df_hora_flujo = lprs.stats_flujo_vehicular_por_hora(df_lpr_f)
            fig_hora = lprv.grafico_flujo_vehicular_por_hora(df_hora_flujo, theme="light")
            _agregar_grafico(story, fig_hora, alto=9 * cm)
            
            df_lpr_sitio = lprs.stats_lpr_por_sitio(df_lpr_f)
            if not df_lpr_sitio.empty:
                fig_sitio = lprv.grafico_lpr_por_sitio(df_lpr_sitio, theme="light")
                _agregar_grafico(story, fig_sitio, alto=9 * cm)
                
            df_top = lprs.stats_lpr_top_placas(df_lpr_f, 10)
            if not df_top.empty:
                fig_top = lprv.grafico_top_placas(df_top, theme="light")
                _agregar_grafico(story, fig_top, alto=9 * cm)
            
        except Exception as e:
            story.append(Paragraph(f"Error al generar gráficos LPR: {str(e)}", ESTILO_NORMAL))

    doc.build(story)
    buffer.seek(0)
    return buffer
