"""
Exportación de reporte ejecutivo a PDF.

Genera un PDF visual y profesional utilizando:
- Estadísticas calculadas en statistics_calc.py
- Gráficos de visualizations.py
- ReportLab para la generación del PDF
- Kaleido para convertir gráficos Plotly a imágenes PNG

IMPORTANTE:
Este módulo NO utiliza fotografías de HikCentral.
Las "imágenes" del PDF son exclusivamente los gráficos estadísticos.
"""

import io
import os
import re
import tempfile
from datetime import datetime

import pandas as pd
import plotly.io as pio

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from access_names import obtener_nombre_corto_pdf

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN VISUAL
# ─────────────────────────────────────────────────────────────────────────────

COLOR_PRINCIPAL = "#1B4F72"
COLOR_SECUNDARIO = "#2E86C1"
COLOR_CLARO = "#D4E6F1"
COLOR_TEXTO = "#2C3E50"
COLOR_GRIS = "#6B7280"
COLOR_FONDO = "#F5F7FA"
COLOR_BLANCO = "#FFFFFF"
COLOR_VERDE = "#27AE60"
COLOR_ROJO = "#C0392B"

PAGE_WIDTH, PAGE_HEIGHT = A4


# ─────────────────────────────────────────────────────────────────────────────
# FUENTES
# ─────────────────────────────────────────────────────────────────────────────

def _nombres_cortos_pdf_dataframe(df):
    """
    Convierte temporalmente los nombres de puntos de acceso
    a nombres cortos para los gráficos del PDF.

    NO modifica el DataFrame original.
    """

    if df is None or df.empty:
        return df

    df = df.copy()

    # Columnas que pueden contener nombres de puntos de acceso
    columnas_punto = [
        "Punto de acceso",
        "Punto de Acceso",
        "punto_acceso",
        "Punto",
        "Punto Acceso",
        "Nombre",
    ]

    for columna in columnas_punto:
        if columna in df.columns:
            df[columna] = df[columna].map(
                obtener_nombre_corto_pdf
            )

    # Si los puntos están en el índice
    if df.index.name in columnas_punto:
        df.index = df.index.map(
            obtener_nombre_corto_pdf
        )

    # Por si el índice no tiene nombre pero contiene
    # nombres de terminales
    elif df.index.dtype == "object":
        try:
            df.index = df.index.map(
                obtener_nombre_corto_pdf
            )
        except Exception:
            pass

    return df

def _obtener_abreviaturas_utilizadas(df):
    """
    Obtiene las abreviaturas de terminales realmente utilizadas
    en el DataFrame.

    Retorna:
        lista de tuplas:
        [(abreviatura, nombre_completo), ...]
    """

    if df is None or df.empty:
        return []

    nombres = set()

    columnas_punto = [
        "Punto de acceso",
        "Punto de Acceso",
        "punto_acceso",
        "Punto",
        "Punto Acceso",
        "Nombre",
    ]

    # Buscar nombres en columnas
    for columna in columnas_punto:
        if columna in df.columns:
            valores = df[columna].dropna().unique()

            for valor in valores:
                valor = str(valor).strip()

                if valor:
                    nombres.add(valor)

    # Buscar nombres en índice
    if df.index.dtype == "object":
        for valor in df.index.dropna().unique():
            valor = str(valor).strip()

            if valor:
                nombres.add(valor)

    resultado = []

    for nombre in sorted(nombres):
        try:
            corto = obtener_nombre_corto_pdf(nombre)

            if corto and corto != nombre:
                resultado.append(
                    (corto, nombre)
                )

        except Exception:
            continue

    return resultado


def _crear_nota_abreviaturas(df):
    """
    Genera una nota visual para el PDF explicando las abreviaturas
    utilizadas en un gráfico.
    """

    abreviaturas = _obtener_abreviaturas_utilizadas(df)

    if not abreviaturas:
        return None

    partes = []

    for corto, completo in abreviaturas:
        partes.append(
            f"<b>{corto}</b> = {completo}"
        )

    texto = (
        "<b>Nota:</b> Abreviaturas utilizadas en el gráfico: "
        + "; ".join(partes)
        + "."
    )

    return Paragraph(
        texto,
        ParagraphStyle(
            "NotaAbreviaturas",
            parent=ESTILO_NORMAL,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor(COLOR_GRIS),
            spaceBefore=2,
            spaceAfter=8,
        ),
    )

def registrar_fuentes():
    """
    Intenta registrar Segoe UI.
    Si no está disponible, ReportLab utilizará Helvetica.
    """

    posibles = [
        (
            "SegoeUI",
            r"C:\Windows\Fonts\segoeui.ttf",
        ),
        (
            "SegoeUI-Bold",
            r"C:\Windows\Fonts\segoeuib.ttf",
        ),
        (
            "Arial",
            r"C:\Windows\Fonts\arial.ttf",
        ),
        (
            "Arial-Bold",
            r"C:\Windows\Fonts\arialbd.ttf",
        ),
    ]

    registradas = {}

    for nombre, ruta in posibles:
        if os.path.exists(ruta):
            try:
                pdfmetrics.registerFont(TTFont(nombre, ruta))
                registradas[nombre] = True
            except Exception:
                pass

    return registradas


FUENTES = registrar_fuentes()

FONT_NORMAL = "SegoeUI" if "SegoeUI" in FUENTES else "Helvetica"
FONT_BOLD = "SegoeUI-Bold" if "SegoeUI-Bold" in FUENTES else "Helvetica-Bold"


# ─────────────────────────────────────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────────────────────────────────────

styles = getSampleStyleSheet()

ESTILO_TITULO = ParagraphStyle(
    "TituloReporte",
    parent=styles["Title"],
    fontName=FONT_BOLD,
    fontSize=24,
    leading=29,
    textColor=colors.HexColor(COLOR_PRINCIPAL),
    alignment=TA_CENTER,
    spaceAfter=12,
)

ESTILO_SUBTITULO = ParagraphStyle(
    "SubtituloReporte",
    parent=styles["Normal"],
    fontName=FONT_NORMAL,
    fontSize=13,
    leading=18,
    textColor=colors.HexColor(COLOR_GRIS),
    alignment=TA_CENTER,
)

ESTILO_SECCION = ParagraphStyle(
    "Seccion",
    parent=styles["Heading1"],
    fontName=FONT_BOLD,
    fontSize=17,
    leading=21,
    textColor=colors.HexColor(COLOR_PRINCIPAL),
    spaceBefore=5,
    spaceAfter=12,
)

ESTILO_SUBSECCION = ParagraphStyle(
    "Subseccion",
    parent=styles["Heading2"],
    fontName=FONT_BOLD,
    fontSize=12,
    leading=16,
    textColor=colors.HexColor(COLOR_TEXTO),
    spaceBefore=6,
    spaceAfter=7,
)

ESTILO_NORMAL = ParagraphStyle(
    "NormalReporte",
    parent=styles["Normal"],
    fontName=FONT_NORMAL,
    fontSize=9.5,
    leading=14,
    textColor=colors.HexColor(COLOR_TEXTO),
)

ESTILO_CONCLUSION = ParagraphStyle(
    "Conclusion",
    parent=ESTILO_NORMAL,
    fontSize=10,
    leading=15,
    leftIndent=8,
    rightIndent=8,
    spaceAfter=7,
)

ESTILO_FOOTER = ParagraphStyle(
    "Footer",
    parent=styles["Normal"],
    fontName=FONT_NORMAL,
    fontSize=7.5,
    textColor=colors.HexColor(COLOR_GRIS),
    alignment=TA_CENTER,
)


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

def _limpiar_markdown(texto: str) -> str:
    """
    Convierte Markdown básico a etiquetas compatibles con ReportLab.
    Escapa caracteres HTML para evitar errores de parsing.
    """

    if texto is None:
        return ""

    texto = str(texto)

    # Escapar caracteres especiales de XML/HTML
    texto = (
        texto.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
    )

    # Convertir pares de **texto** a <b>texto</b>
    texto = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        texto,
    )

    return texto


def _formatear_numero(valor):
    """Formatea números para presentación."""
    if pd.isna(valor):
        return "-"

    if isinstance(valor, float):
        if valor.is_integer():
            return f"{int(valor):,}"
        return f"{valor:,.2f}"

    if isinstance(valor, int):
        return f"{valor:,}"

    return str(valor)


def _configurar_layout_para_pdf(fig, ancho_cm=None, alto_cm=None):
    """
    Reconfigura de forma inteligente el layout de una figura Plotly
    específicamente para su renderizado óptimo en PDF.
    """
    base_width = 1000
    
    # 1. Determinar altura base
    if fig.layout.height:
        base_height = fig.layout.height
    else:
        if alto_cm and ancho_cm:
            # Respetamos la altura explícita solicitada usando regla de 3
            base_height = int(base_width * (alto_cm / ancho_cm))
        else:
            base_height = 600
            
    # 2. Detección y ajuste de Leyendas
    has_legend = False
    for trace in fig.data:
        if getattr(trace, 'showlegend', True):
            has_legend = True
            break
            
    if has_legend:
        # Forzar leyenda horizontal inferior
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.25, 
                xanchor="center",
                x=0.5,
                title_text="" # Remover título para ahorrar espacio
            )
        )
        
        # Calcular margen inferior dinámico
        num_traces = len(fig.data)
        extra_margin = 80
        if num_traces > 4:
            extra_margin += 40 * ((num_traces - 1) // 4)
            
        current_b = fig.layout.margin.b if fig.layout.margin and fig.layout.margin.b else 40
        fig.update_layout(margin=dict(b=current_b + extra_margin))
        
        # Expandir la altura base para que el gráfico no se aplaste
        base_height += extra_margin

    # 3. Evitar corte de etiquetas en ejes
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)

    fig.update_layout(
        width=base_width,
        height=base_height
    )
    
    return base_width, base_height


def _crear_grafico_png(fig, ancho_cm=None, alto_cm=None, scale=2):
    """
    Convierte una figura Plotly a PNG en memoria.
    """
    if fig is None:
        return None, "Figura nula"

    try:
        # Ajustamos el layout exclusivamente para el PDF antes de generar imagen
        width, height = _configurar_layout_para_pdf(fig, ancho_cm, alto_cm)

        imagen = pio.to_image(
            fig,
            format="png",
            width=width,
            height=height,
            scale=scale,
            engine="kaleido"
        )

        return (io.BytesIO(imagen), width, height), None

    except Exception as e:
        error_msg = f"Error Kaleido/Plotly: {str(e)}"
        print(f"[PDF] {error_msg}")
        return None, error_msg


def _agregar_grafico(
    story,
    fig,
    ancho=15.0 * cm,
    alto=None,
    df_referencia=None,
    mostrar_abreviaturas=False,
):
    """
    Agrega una figura Plotly al documento.

    Si mostrar_abreviaturas=True, agrega debajo del gráfico
    una nota explicando los nombres cortos utilizados.
    """

    if fig is None:
        return

    ancho_cm_val = ancho / cm
    alto_cm_val = (alto / cm) if alto else None

    resultado, error_msg = _crear_grafico_png(fig, ancho_cm_val, alto_cm_val)

    if resultado is None:
        estilos = getSampleStyleSheet()
        estilo_error = ParagraphStyle(
            "EstiloError",
            parent=estilos["Normal"],
            textColor=colors.red,
            alignment=TA_CENTER,
            fontSize=10,
        )
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>[No se pudo renderizar el gráfico en PDF]</b><br/>{error_msg}", estilo_error))
        story.append(Spacer(1, 10))
        return
        
    imagen, png_width, png_height = resultado

    # Forzamos la proporción matemática exacta del PNG
    alto_real = ancho * (png_height / png_width)

    story.append(
        Image(
            imagen,
            width=ancho,
            height=alto_real,  # Corregido: usar alto_real para mantener proporción
            hAlign="CENTER",
        )
    )

    # Nota de abreviaturas
    if mostrar_abreviaturas and df_referencia is not None:
        nota = _crear_nota_abreviaturas(
            df_referencia
        )

        if nota is not None:
            story.append(nota)

    story.append(
        Spacer(1, 0.25 * cm)
    )

# ─────────────────────────────────────────────────────────────────────────────
# ENCABEZADO / PIE DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────

def _dibujar_pagina(canvas, doc):
    """
    Encabezado y pie de página.
    """

    canvas.saveState()

    # Línea superior
    canvas.setStrokeColor(colors.HexColor(COLOR_PRINCIPAL))
    canvas.setLineWidth(2)
    canvas.line(
        1.5 * cm,
        PAGE_HEIGHT - 1.0 * cm,
        PAGE_WIDTH - 1.5 * cm,
        PAGE_HEIGHT - 1.0 * cm,
    )

    # Encabezado
    canvas.setFont(FONT_BOLD, 7.5)
    canvas.setFillColor(colors.HexColor(COLOR_PRINCIPAL))
    canvas.drawString(
        1.5 * cm,
        PAGE_HEIGHT - 0.75 * cm,
        "UTMACH · REPORTE DE FLUJO DE INGRESOS PEATONALES",
    )

    # Pie
    canvas.setStrokeColor(colors.HexColor("#D5D8DC"))
    canvas.setLineWidth(0.5)
    canvas.line(
        1.5 * cm,
        1.15 * cm,
        PAGE_WIDTH - 1.5 * cm,
        1.15 * cm,
    )

    canvas.setFont(FONT_NORMAL, 7)
    canvas.setFillColor(colors.HexColor(COLOR_GRIS))

    canvas.drawString(
        1.5 * cm,
        0.75 * cm,
        "Unidad de Obras e Infraestructura Universitaria",
    )

    canvas.drawRightString(
        PAGE_WIDTH - 1.5 * cm,
        0.75 * cm,
        f"Página {doc.page}",
    )

    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# TARJETAS DE MÉTRICAS
# ─────────────────────────────────────────────────────────────────────────────

def _crear_tarjeta(titulo, valor, descripcion=""):
    """
    Crea una tarjeta visual para una métrica.
    """

    contenido = [
        [
            Paragraph(
                str(titulo),
                ParagraphStyle(
                    "TarjetaTitulo",
                    fontName=FONT_BOLD,
                    fontSize=8,
                    textColor=colors.HexColor(COLOR_GRIS),
                    alignment=TA_CENTER,
                ),
            )
        ],
        [
            Paragraph(
                str(valor),
                ParagraphStyle(
                    "TarjetaValor",
                    fontName=FONT_BOLD,
                    fontSize=18,
                    textColor=colors.HexColor(COLOR_PRINCIPAL),
                    alignment=TA_CENTER,
                ),
            )
        ],
    ]

    if descripcion:
        contenido.append(
            [
                Paragraph(
                    str(descripcion),
                    ParagraphStyle(
                        "TarjetaDescripcion",
                        fontName=FONT_NORMAL,
                        fontSize=7,
                        textColor=colors.HexColor(COLOR_GRIS),
                        alignment=TA_CENTER,
                    ),
                )
            ]
        )

    tabla = Table(
        contenido,
        colWidths=[3.55 * cm],
        rowHeights=None,
    )

    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D5D8DC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return tabla


def _agregar_metricas(story, metricas):
    """
    Agrega las principales métricas en tarjetas.
    """

    tarjetas = [
        _crear_tarjeta(
            "TOTAL DE EVENTOS",
            _formatear_numero(metricas.get("total_eventos", 0)),
        ),
        _crear_tarjeta(
            "USUARIOS ÚNICOS",
            _formatear_numero(metricas.get("usuarios_unicos", 0)),
        ),
        _crear_tarjeta(
            "PROMEDIO DIARIO",
            _formatear_numero(metricas.get("promedio_diario", 0)),
        ),
        _crear_tarjeta(
            "DÍAS REGISTRADOS",
            _formatear_numero(metricas.get("dias_unicos", 0)),
        ),
    ]

    tabla = Table(
        [tarjetas],
        colWidths=[4.2 * cm] * 4,
    )

    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    story.append(tabla)
    story.append(Spacer(1, 0.45 * cm))


# ─────────────────────────────────────────────────────────────────────────────
# TABLAS
# ─────────────────────────────────────────────────────────────────────────────

def _tabla_dataframe(df, max_filas=15):
    """
    Convierte un DataFrame a una tabla visual para PDF.
    """

    if df is None or df.empty:
        return Paragraph(
            "No existen datos disponibles para esta sección.",
            ESTILO_NORMAL,
        )

    df_temp = df.copy()

    if isinstance(df_temp.index, pd.RangeIndex) is False:
        if df_temp.index.name is not None:
            df_temp = df_temp.reset_index()

    df_temp = df_temp.head(max_filas)

    encabezados = [str(c) for c in df_temp.columns]

    datos = [encabezados]

    for _, fila in df_temp.iterrows():
        datos.append(
            [
                _formatear_numero(v)
                for v in fila.tolist()
            ]
        )

    ancho_total = 17.5 * cm
    numero_columnas = len(encabezados)

    if numero_columnas == 0:
        return None

    ancho_columna = ancho_total / numero_columnas

    tabla = Table(
        datos,
        colWidths=[ancho_columna] * numero_columnas,
        repeatRows=1,
    )

    tabla.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(COLOR_PRINCIPAL),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    FONT_BOLD,
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    FONT_NORMAL,
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#D5D8DC"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F7F9FA"),
                    ],
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return tabla


# ─────────────────────────────────────────────────────────────────────────────
# PORTADA
# ─────────────────────────────────────────────────────────────────────────────

def _agregar_portada(story, metricas):
    """
    Genera la portada del reporte.
    """

    story.append(Spacer(1, 2.0 * cm))

    story.append(
        Paragraph(
            "UNIVERSIDAD TÉCNICA DE MACHALA",
            ParagraphStyle(
                "Institucion",
                fontName=FONT_BOLD,
                fontSize=14,
                textColor=colors.HexColor(COLOR_PRINCIPAL),
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
                fontName=FONT_NORMAL,
                fontSize=10,
                textColor=colors.HexColor(COLOR_GRIS),
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
                    "REPORTE DE FLUJO DEL<br/>SISTEMA DE INGRESOS PEATONALES",
                    ParagraphStyle(
                        "Banda",
                        fontName=FONT_BOLD,
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
    )

    banda.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(COLOR_PRINCIPAL),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    story.append(banda)
    story.append(Spacer(1, 1.2 * cm))

    fecha_inicial = metricas.get("fecha_inicial", "")
    fecha_final = metricas.get("fecha_final", "")

    if hasattr(fecha_inicial, "strftime"):
        fecha_inicial = fecha_inicial.strftime("%d/%m/%Y")

    if hasattr(fecha_final, "strftime"):
        fecha_final = fecha_final.strftime("%d/%m/%Y")

    periodo = (
        f"Período analizado: <b>{fecha_inicial}</b> al "
        f"<b>{fecha_final}</b>"
    )

    story.append(
        Paragraph(
            periodo,
            ParagraphStyle(
                "Periodo",
                fontName=FONT_NORMAL,
                fontSize=12,
                textColor=colors.HexColor(COLOR_TEXTO),
                alignment=TA_CENTER,
            ),
        )
    )

    story.append(Spacer(1, 1.0 * cm))

    story.append(
        Paragraph(
            "Documento de análisis estadístico del flujo de eventos "
            "registrados por el sistema de control de ingresos peatonales.",
            ParagraphStyle(
                "DescripcionPortada",
                fontName=FONT_NORMAL,
                fontSize=10,
                leading=15,
                textColor=colors.HexColor(COLOR_GRIS),
                alignment=TA_CENTER,
                leftIndent=2 * cm,
                rightIndent=2 * cm,
            ),
        )
    )

    story.append(Spacer(1, 2.0 * cm))

    story.append(
        Paragraph(
            f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            ESTILO_FOOTER,
        )
    )

    story.append(PageBreak())


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN EJECUTIVO
# ─────────────────────────────────────────────────────────────────────────────

def _agregar_resumen(story, df, metricas, conclusiones):
    story.append(Paragraph("1. Resumen Ejecutivo", ESTILO_SECCION))

    _agregar_metricas(story, metricas)

    story.append(
        Paragraph(
            "Principales hallazgos",
            ESTILO_SUBSECCION,
        )
    )

    for conclusion in conclusiones:
        texto = _limpiar_markdown(conclusion)

        bloque = Table(
            [
                [
                    Paragraph(
                        "●",
                        ParagraphStyle(
                            "Bullet",
                            fontName=FONT_BOLD,
                            fontSize=11,
                            textColor=colors.HexColor(COLOR_SECUNDARIO),
                            alignment=TA_CENTER,
                        ),
                    ),
                    Paragraph(texto, ESTILO_CONCLUSION),
                ]
            ],
            colWidths=[0.6 * cm, 16.8 * cm],
        )

        bloque.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#F7F9FA"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor("#E5E7E9"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                ]
            )
        )

        story.append(bloque)
        story.append(Spacer(1, 0.15 * cm))

    story.append(PageBreak())


# ─────────────────────────────────────────────────────────────────────────────
# CREACIÓN DEL PDF
# ─────────────────────────────────────────────────────────────────────────────

def exportar_reporte_pdf(
    df: pd.DataFrame,
    metricas: dict,
    calidad: dict,
    conclusiones: list[str],
    graficos: dict,
    stats: dict | None = None,
) -> bytes:
    """
    Genera el PDF completo.

    Parámetros
    ----------
    df:
        Dataset limpio y filtrado.

    metricas:
        Diccionario de métricas generales.

    calidad:
        Diccionario de calidad de datos.

    conclusiones:
        Lista generada por generar_conclusiones().

    graficos:
        Diccionario con figuras Plotly.

    Retorna
    -------
    bytes
        Contenido completo del PDF.
    """
    if stats is None:
        stats = {}
        
    output = io.BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.5 * cm,
        title="Reporte de Flujo del Sistema de Ingresos Peatonales",
        author="Universidad Técnica de Machala",
        subject="Reporte estadístico de ingresos peatonales",
    )

    story = []

    # ─────────────────────────────────────────────────────────────────────
    # PORTADA
    # ─────────────────────────────────────────────────────────────────────

    _agregar_portada(story, metricas)

    # ─────────────────────────────────────────────────────────────────────
    # RESUMEN
    # ─────────────────────────────────────────────────────────────────────

    _agregar_resumen(
        story,
        df,
        metricas,
        conclusiones,
    )

    # ─────────────────────────────────────────────────────────────────────
    # FLUJO POR INGRESO
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "2. Flujo por Ingreso",
            ESTILO_SECCION,
        )
    )

    story.append(
        Paragraph(
            "Distribución de eventos registrados en cada uno de los "
            "ingresos peatonales analizados.",
            ESTILO_NORMAL,
        )
    )

    story.append(Spacer(1, 0.25 * cm))

    _agregar_grafico(
        story,
        graficos.get("ingreso"),
        alto=8.5 * cm,
    )

    _agregar_grafico(
        story,
        graficos.get("contraste_ingresos"),
        alto=8.0 * cm,
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # ENTRADAS VS SALIDAS
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "3. Entradas y Salidas",
            ESTILO_SECCION,
        )
    )

    _agregar_grafico(
        story,
        graficos.get("entradas_salidas"),
        alto=8.0 * cm,
    )

    _agregar_grafico(
        story,
        graficos.get("entradas_salidas_hora"),
        alto=8.0 * cm,
    )

    _agregar_grafico(
        story,
        graficos.get("entradas_salidas_ingreso"),
        alto=7.5 * cm,
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # ANÁLISIS HORARIO
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "4. Análisis Horario",
            ESTILO_SECCION,
        )
    )

    _agregar_grafico(
        story,
        graficos.get("flujo_hora"),
        alto=8.2 * cm,
    )

    _agregar_grafico(
        story,
        graficos.get("ingreso_hora"),
        alto=8.2 * cm,
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # HEATMAPS
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "5. Mapas de Calor",
            ESTILO_SECCION,
        )
    )

    story.append(
        Paragraph(
            "Los mapas de calor permiten identificar visualmente "
            "los períodos de mayor concentración de eventos.",
            ESTILO_NORMAL,
        )
    )

    story.append(Spacer(1, 0.25 * cm))

    _agregar_grafico(
        story,
        graficos.get("heatmap_punto_hora"),
        alto=8.0 * cm,
        df_referencia=stats.get("heatmap_punto_hora"),
        mostrar_abreviaturas=True,
    )

    _agregar_grafico(
        story,
        graficos.get("heatmap_dia_hora"),
        alto=7.0 * cm,
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # FLUJO DIARIO
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "6. Evolución Diaria",
            ESTILO_SECCION,
        )
    )

    _agregar_grafico(
        story,
        graficos.get("flujo_diario"),
        alto=8.5 * cm,
    )

    _agregar_grafico(
        story,
        graficos.get("flujo_diario_ingreso"),
        alto=8.0 * cm,
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # DÍAS DE SEMANA
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "7. Distribución por Día de la Semana",
            ESTILO_SECCION,
        )
    )

    _agregar_grafico(
        story,
        graficos.get("dia_semana"),
        alto=8.0 * cm,
    )

    _agregar_grafico(
        story,
        graficos.get("heatmap_dia_hora"),
        alto=7.5 * cm,
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # TIPO DE USUARIO
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "8. Tipo de Usuario",
            ESTILO_SECCION,
        )
    )

    _agregar_grafico(
        story,
        graficos.get("tipo_usuario"),
        alto=7.5 * cm,
    )

    _agregar_grafico(
        story,
        graficos.get("tipo_usuario_ingreso"),
        alto=7.5 * cm,
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # PUNTOS DE ACCESO
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "9. Análisis de Puntos de Acceso",
            ESTILO_SECCION,
        )
    )

    _agregar_grafico(
        story,
        graficos.get("flujo_punto_acceso"),
        alto=7.5 * cm,
        df_referencia=stats.get("flujo_punto_acceso"),
        mostrar_abreviaturas=False,
    )

    _agregar_grafico(
        story,
        graficos.get("punto_tipo_usuario"),
        alto=7.5 * cm,
        df_referencia=stats.get("punto_tipo_usuario"),
        mostrar_abreviaturas=False,
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # FRECUENCIA DE UTILIZACIÓN
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "10. Frecuencia de Utilización",
            ESTILO_SECCION,
        )
    )

    _agregar_grafico(
        story,
        graficos.get("frecuencia"),
        alto=8.0 * cm,
    )

    story.append(
        Paragraph(
            "La distribución muestra la frecuencia con la que los "
            "usuarios identificados aparecen en los registros durante "
            "el período analizado.",
            ESTILO_NORMAL,
        )
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # CALIDAD DE DATOS
    # ─────────────────────────────────────────────────────────────────────

    story.append(
        Paragraph(
            "11. Calidad de los Datos",
            ESTILO_SECCION,
        )
    )

    calidad_data = {
        "Métrica": [
            "Total de registros",
            "Registros válidos",
            "Registros con fecha inválida",
            "Registros con punto de acceso vacío",
            "Registros con departamento vacío",
            "Registros sin nombre/apellido",
            "Valores únicos - Punto de acceso",
            "Valores únicos - Device Name",
        ],
        "Valor": [
            calidad.get("total_registros", 0),
            calidad.get("registros_validos", 0),
            calidad.get("fechas_invalidas", 0),
            calidad.get("acceso_vacio", 0),
            calidad.get("departamento_vacio", 0),
            calidad.get("registros_sin_nombre", 0),
            calidad.get("unicos_punto_acceso", 0),
            calidad.get("unicos_device_name", 0),
        ],
    }

    df_calidad = pd.DataFrame(calidad_data)

    tabla = _tabla_dataframe(
        df_calidad,
        max_filas=20,
    )

    if tabla:
        story.append(tabla)

    story.append(Spacer(1, 0.6 * cm))

    story.append(
        Paragraph(
            "<b>Nota metodológica:</b> El análisis se realiza sobre "
            "los registros previamente depurados y normalizados. "
            "Las estadísticas representan eventos registrados por "
            "el sistema y no constituyen una identificación individual "
            "de personas.",
            ESTILO_NORMAL,
        )
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # CIERRE
    # ─────────────────────────────────────────────────────────────────────

    story.append(Spacer(1, 3 * cm))

    story.append(
        Paragraph(
            "Conclusión del Reporte",
            ESTILO_TITULO,
        )
    )

    story.append(Spacer(1, 0.8 * cm))

    story.append(
        Paragraph(
            "El presente documento consolida los principales indicadores "
            "estadísticos obtenidos a partir de los registros del sistema "
            "de ingresos peatonales durante el período analizado.",
            ParagraphStyle(
                "Cierre",
                parent=ESTILO_NORMAL,
                fontSize=11,
                leading=18,
                alignment=TA_CENTER,
                leftIndent=2 * cm,
                rightIndent=2 * cm,
            ),
        )
    )

    story.append(Spacer(1, 2 * cm))

    story.append(
        Paragraph(
            "Universidad Técnica de Machala",
            ParagraphStyle(
                "Firma",
                fontName=FONT_BOLD,
                fontSize=11,
                textColor=colors.HexColor(COLOR_PRINCIPAL),
                alignment=TA_CENTER,
            ),
        )
    )

    # ─────────────────────────────────────────────────────────────────────
    # CONSTRUIR PDF
    # ─────────────────────────────────────────────────────────────────────

    doc.build(
        story,
        onFirstPage=_dibujar_pagina,
        onLaterPages=_dibujar_pagina,
    )

    return output.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN AUXILIAR PARA CONSTRUIR TODOS LOS GRÁFICOS
# ─────────────────────────────────────────────────────────────────────────────

def construir_graficos_reporte(df, stats):
    """
    Construye todas las figuras necesarias para el PDF.

    Los DataFrames utilizados exclusivamente para gráficos que
    contienen puntos de acceso son transformados temporalmente
    a nombres cortos.

    El DataFrame original NO se modifica.
    """

    from visualizations import (
        grafico_flujo_punto_acceso,
        grafico_flujo_hora,
        grafico_heatmap_punto_hora,
        grafico_entradas_salidas,
        grafico_entradas_salidas_hora,
        grafico_entradas_salidas_por_ingreso,
        grafico_ingreso,
        grafico_tipo_usuario,
        grafico_tipo_usuario_ingreso,
        grafico_flujo_diario,
        grafico_flujo_diario_por_ingreso,
        grafico_dia_semana,
        grafico_heatmap_dia_hora,
        grafico_ingreso_hora,
        grafico_punto_tipo_usuario,
        grafico_frecuencia,
        grafico_contraste_ingresos,
    )

    graficos = {}

    # ================================================================
    # DATAFRAMES PARA PDF
    # ================================================================

    # Copia general para evitar modificar el dataset original
    df_pdf = df.copy()

    # ================================================================
    # FLUJO POR PUNTO DE ACCESO
    # ================================================================

    if "flujo_punto_acceso" in stats:

        stats_punto = _nombres_cortos_pdf_dataframe(
            stats["flujo_punto_acceso"]
        )

        graficos["flujo_punto_acceso"] = (
            grafico_flujo_punto_acceso(
                stats_punto
            )
        )

    # ================================================================
    # FLUJO POR HORA
    # ================================================================

    if "flujo_hora" in stats:

        graficos["flujo_hora"] = (
            grafico_flujo_hora(
                stats["flujo_hora"]
            )
        )

    # ================================================================
    # HEATMAP PUNTO × HORA
    # ================================================================

    if "heatmap_punto_hora" in stats:

        stats_heatmap = _nombres_cortos_pdf_dataframe(
            stats["heatmap_punto_hora"]
        )

        graficos["heatmap_punto_hora"] = (
            grafico_heatmap_punto_hora(
                stats_heatmap
            )
        )

    # ================================================================
    # ENTRADAS VS SALIDAS
    # ================================================================

    if "entradas_salidas" in stats:

        graficos["entradas_salidas"] = (
            grafico_entradas_salidas(
                stats["entradas_salidas"]
            )
        )

    # ================================================================
    # ENTRADAS VS SALIDAS POR HORA
    # ================================================================

    if "entradas_salidas_hora" in stats:

        graficos["entradas_salidas_hora"] = (
            grafico_entradas_salidas_hora(
                stats["entradas_salidas_hora"]
            )
        )

    # ================================================================
    # ENTRADAS VS SALIDAS POR INGRESO
    # ================================================================

    if "entradas_salidas_ingreso" in stats:

        graficos["entradas_salidas_ingreso"] = (
            grafico_entradas_salidas_por_ingreso(
                stats["entradas_salidas_ingreso"]
            )
        )

    # ================================================================
    # FLUJO POR INGRESO
    # ================================================================

    if "flujo_ingreso" in stats:

        graficos["ingreso"] = (
            grafico_ingreso(
                stats["flujo_ingreso"]
            )
        )

    # ================================================================
    # TIPO DE USUARIO
    # ================================================================

    if "tipo_usuario" in stats:

        graficos["tipo_usuario"] = (
            grafico_tipo_usuario(
                stats["tipo_usuario"]
            )
        )

    # ================================================================
    # TIPO DE USUARIO × INGRESO
    # ================================================================

    if "tipo_usuario_ingreso" in stats:

        graficos["tipo_usuario_ingreso"] = (
            grafico_tipo_usuario_ingreso(
                stats["tipo_usuario_ingreso"]
            )
        )

    # ================================================================
    # FLUJO DIARIO
    # ================================================================

    if "flujo_diario" in stats:

        graficos["flujo_diario"] = (
            grafico_flujo_diario(
                stats["flujo_diario"]
            )
        )

    # ================================================================
    # FLUJO DIARIO POR INGRESO
    # ================================================================

    if "flujo_diario_ingreso" in stats:

        graficos["flujo_diario_ingreso"] = (
            grafico_flujo_diario_por_ingreso(
                stats["flujo_diario_ingreso"]
            )
        )

    # ================================================================
    # DÍA DE SEMANA
    # ================================================================

    if "dia_semana" in stats:

        graficos["dia_semana"] = (
            grafico_dia_semana(
                stats["dia_semana"]
            )
        )

    # ================================================================
    # HEATMAP DÍA × HORA
    # ================================================================

    if "heatmap_dia_hora" in stats:

        graficos["heatmap_dia_hora"] = (
            grafico_heatmap_dia_hora(
                stats["heatmap_dia_hora"]
            )
        )

    # ================================================================
    # INGRESO × HORA
    # ================================================================

    if "ingreso_hora" in stats:

        graficos["ingreso_hora"] = (
            grafico_ingreso_hora(
                stats["ingreso_hora"]
            )
        )

    # ================================================================
    # PUNTO × TIPO DE USUARIO
    # ================================================================

    if "punto_tipo_usuario" in stats:

        stats_punto_tipo = _nombres_cortos_pdf_dataframe(
            stats["punto_tipo_usuario"]
        )

        graficos["punto_tipo_usuario"] = (
            grafico_punto_tipo_usuario(
                stats_punto_tipo
            )
        )

    # ================================================================
    # FRECUENCIA
    # ================================================================

    if "frecuencia" in stats:

        graficos["frecuencia"] = (
            grafico_frecuencia(
                stats["frecuencia"]
            )
        )

    # ================================================================
    # CONTRASTE ENTRE INGRESOS
    # ================================================================

    graficos["contraste_ingresos"] = (
        grafico_contraste_ingresos(
            df_pdf
        )
    )

    return graficos