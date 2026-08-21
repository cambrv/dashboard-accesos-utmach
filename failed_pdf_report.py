"""
Módulo de exportación PDF exclusivo para eventos fallidos.
"""
import io
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table
from reportlab.lib.units import cm

from pdf_report import (
    ESTILO_TITULO, ESTILO_SUBTITULO, ESTILO_NORMAL, ESTILO_SECCION, ESTILO_CONCLUSION,
    _agregar_grafico, _tabla_dataframe
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from failed_visualizations import (
    grafico_fallos_por_ingreso,
    grafico_fallos_por_hora, grafico_fallos_evolucion_diaria, grafico_fallos_por_punto
)

def _agregar_portada_fallidos(story, fecha_min: str, fecha_max: str, titulo: str):
    """
    Genera la portada del reporte de eventos fallidos.
    """
    story.append(Spacer(1, 2.0 * cm))
    
    story.append(
        Paragraph(
            "UNIVERSIDAD TÉCNICA DE MACHALA",
            ParagraphStyle(
                "Institucion",
                fontName="Helvetica-Bold",
                fontSize=14,
                textColor=colors.HexColor("#1B4F72"),
                alignment=TA_CENTER,
                spaceAfter=8,
            ),
        )
    )
    
    story.append(
        Paragraph(
            "UNIDAD DE OBRAS E INFRAESTRUCTURA UNIVERSITARIA",
            ParagraphStyle(
                "Unidad",
                fontName="Helvetica",
                fontSize=10,
                textColor=colors.HexColor("#5D6D7E"),
                alignment=TA_CENTER,
                spaceAfter=35,
            ),
        )
    )
    
    # Banda visual
    banda = Table(
        [
            [
                Paragraph(
                    titulo.replace(" / ", "<br/>"),
                    ParagraphStyle(
                        "Banda",
                        fontName="Helvetica-Bold",
                        fontSize=19,
                        leading=25,
                        textColor=colors.white,
                        alignment=TA_CENTER,
                    ),
                )
            ]
        ],
        colWidths=[17 * cm],
        rowHeights=[3.0 * cm],
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1B4F72")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
        ],
    )
    story.append(banda)
    story.append(Spacer(1, 1.5 * cm))
    
    story.append(
        Paragraph(
            "Reporte Estadístico",
            ParagraphStyle(
                "Subtitulo",
                fontName="Helvetica-Bold",
                fontSize=14,
                textColor=colors.HexColor("#2C3E50"),
                alignment=TA_CENTER,
                spaceAfter=20,
            ),
        )
    )
    
    # Tabla de métricas (fechas)
    datos_fechas = [
        ["Fecha de inicio:", fecha_min],
        ["Fecha de fin:", fecha_max],
        ["Fecha de generación:", datetime.now().strftime("%d/%m/%Y %H:%M")],
    ]
    
    tabla_fechas = Table(
        datos_fechas,
        colWidths=[6 * cm, 6 * cm],
        style=[
            ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONT", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2C3E50")),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ],
    )
    story.append(tabla_fechas)

def exportar_reporte_fallidos_pdf(df: pd.DataFrame, stats: dict, conclusiones: list) -> io.BytesIO:
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    
    story = []
    
    # 1. Portada
    fecha_min = df["Fecha"].min().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].min()) else "N/A"
    fecha_max = df["Fecha"].max().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].max()) else "N/A"
    
    _agregar_portada_fallidos(
        story,
        fecha_min,
        fecha_max,
        "REPORTE DE EVENTOS ANORMALES"
    )
    story.append(PageBreak())
    
    # 2. Resumen Ejecutivo
    story.append(Paragraph("Resumen Ejecutivo", ESTILO_TITULO))
    story.append(Spacer(1, 0.5 * cm))
    
    for conclusion in conclusiones:
        story.append(Paragraph(f"• {conclusion}", ESTILO_CONCLUSION))
        story.append(Spacer(1, 0.3 * cm))
        
    story.append(Spacer(1, 1 * cm))
    
    # 3. Distribución Temporal (Evolución y Horas)
    story.append(Paragraph("1. Comportamiento Temporal", ESTILO_SECCION))
    
    if "evolucion_diaria" in stats and not stats["evolucion_diaria"].empty:
        fig_dia = grafico_fallos_evolucion_diaria(stats["evolucion_diaria"])
        _agregar_grafico(story, fig_dia, alto=7 * cm)
        
    if "por_hora" in stats and not stats["por_hora"].empty:
        fig_hora = grafico_fallos_por_hora(stats["por_hora"])
        _agregar_grafico(story, fig_hora, alto=7 * cm)
        
    story.append(PageBreak())
        
    # 5. Distribución por Ingreso / Puntos
    story.append(Paragraph("3. Distribución Geográfica", ESTILO_SECCION))
    
    if "por_ingreso" in stats and not stats["por_ingreso"].empty:
        fig_ingreso = grafico_fallos_por_ingreso(stats["por_ingreso"])
        _agregar_grafico(story, fig_ingreso, alto=8 * cm)
        
    if "por_punto" in stats and not stats["por_punto"].empty:
        fig_punto = grafico_fallos_por_punto(stats["por_punto"])
        _agregar_grafico(story, fig_punto, alto=9 * cm)
        
    doc.build(story)
    buffer.seek(0)
    return buffer
