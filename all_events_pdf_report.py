"""
Exportación a PDF del Reporte Integral ("Todos los Eventos").
Este reporte compila el 100% de las gráficas de Eventos Exitosos + las nuevas gráficas de Tasas de Fallo.
"""
import io
import copy
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    CondPageBreak,
)
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle

# Imports de base
from pdf_report import (
    FONT_NORMAL, FONT_BOLD, _agregar_grafico,
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


# Sistema editorial único del reporte integral. El área útil de A4 es 17 cm.
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 2 * cm
MARGIN_TOP = 2 * cm
MARGIN_BOTTOM = 2 * cm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN_X)

NAVY = colors.HexColor("#173B57")
BLUE = colors.HexColor("#2F6F9F")
TEXT = colors.HexColor("#263746")
MUTED = colors.HexColor("#667783")
LINE = colors.HexColor("#D5DEE5")
PALE = colors.HexColor("#F3F6F8")
ACCENT = colors.HexColor("#C56A2D")
WHITE = colors.white

ESTILO_TITULO = ParagraphStyle(
    "IntegralSeccion", fontName=FONT_BOLD, fontSize=14.5, leading=18,
    textColor=NAVY, spaceBefore=7, spaceAfter=9, keepWithNext=True,
)
ESTILO_SUBTITULO = ParagraphStyle(
    "IntegralSubseccion", fontName=FONT_BOLD, fontSize=11.5, leading=14,
    textColor=BLUE, spaceBefore=7, spaceAfter=5, keepWithNext=True,
)
ESTILO_NORMAL = ParagraphStyle(
    "IntegralNormal", fontName=FONT_NORMAL, fontSize=9.5, leading=13.2,
    textColor=TEXT, spaceAfter=5,
)
ESTILO_CONCLUSION = ParagraphStyle(
    "IntegralHallazgo", parent=ESTILO_NORMAL, leftIndent=8, rightIndent=8,
    borderColor=ACCENT, borderWidth=0, borderLeftWidth=2,
    borderPadding=(3, 5, 3, 8), backColor=colors.HexColor("#FFF8F1"),
    spaceBefore=3, spaceAfter=6,
)
ESTILO_CELDA = ParagraphStyle(
    "IntegralCelda", fontName=FONT_NORMAL, fontSize=8.5, leading=10.5,
    textColor=TEXT,
)
ESTILO_CELDA_NUM = ParagraphStyle(
    "IntegralCeldaNumero", parent=ESTILO_CELDA, alignment=TA_RIGHT,
)
ESTILO_CABECERA = ParagraphStyle(
    "IntegralCabeceraTabla", parent=ESTILO_CELDA, fontName=FONT_BOLD,
    fontSize=8.7, leading=10.5, textColor=WHITE, alignment=TA_CENTER,
)
ESTILO_NOTA = ParagraphStyle(
    "IntegralNota", parent=ESTILO_NORMAL, fontSize=8, leading=10.5,
    textColor=MUTED, spaceBefore=3, spaceAfter=6,
)

_DIAS_ES = {
    "Monday": "lunes", "Tuesday": "martes", "Wednesday": "miércoles",
    "Thursday": "jueves", "Friday": "viernes", "Saturday": "sábado",
    "Sunday": "domingo",
}
_MESES_ES = {
    "January": "enero", "February": "febrero", "March": "marzo",
    "April": "abril", "May": "mayo", "June": "junio", "July": "julio",
    "August": "agosto", "September": "septiembre", "October": "octubre",
    "November": "noviembre", "December": "diciembre",
}


def _texto_espanol(texto):
    """Traduce nombres de días/meses sin depender del locale del servidor."""
    resultado = str(texto)
    for origen, destino in {**_DIAS_ES, **_MESES_ES}.items():
        resultado = re.sub(rf"\b{origen}\b", destino, resultado, flags=re.IGNORECASE)
    return resultado


def _p(valor, estilo=ESTILO_CELDA):
    texto = formatear_texto_pdf(_texto_espanol(valor if valor is not None else "—"))
    return Paragraph(escape(str(texto)), estilo)


def _tabla_estadistica(filas, proporciones, columnas_numericas=(), cabecera=BLUE):
    """Construye una tabla legible cuyo ancho nunca excede el área imprimible."""
    total = float(sum(proporciones))
    anchos = [CONTENT_WIDTH * (valor / total) for valor in proporciones]
    contenido = []
    for numero_fila, fila in enumerate(filas):
        contenido.append([
            _p(valor, ESTILO_CABECERA if numero_fila == 0 else (
                ESTILO_CELDA_NUM if columna in columnas_numericas else ESTILO_CELDA
            ))
            for columna, valor in enumerate(fila)
        ])
    tabla = Table(contenido, colWidths=anchos, repeatRows=1, hAlign="CENTER")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), cabecera),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
    ]))
    return tabla


def _tabla_indicadores(indicadores, columnas=4):
    """Presenta indicadores como tarjetas; cada valor puede ajustar varias líneas."""
    filas = []
    for inicio in range(0, len(indicadores), columnas):
        bloque = indicadores[inicio:inicio + columnas]
        bloque += [("", "")] * (columnas - len(bloque))
        filas.append([
            Paragraph(
                f"<font color='#667783' size='8'>{escape(formatear_texto_pdf(_texto_espanol(etiqueta)))}</font>"
                f"<br/><font color='#173B57' size='12'><b>{escape(formatear_texto_pdf(_texto_espanol(valor)))}</b></font>",
                ParagraphStyle(
                    f"Indicador{inicio}{pos}", parent=ESTILO_CELDA,
                    alignment=TA_CENTER, leading=15,
                ),
            )
            for pos, (etiqueta, valor) in enumerate(bloque)
        ])
    tabla = Table(filas, colWidths=[CONTENT_WIDTH / columnas] * columnas, hAlign="CENTER")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, WHITE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return tabla

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
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN_X, 1.35 * cm, PAGE_WIDTH - MARGIN_X, 1.35 * cm)
    canvas.setFont(FONT_NORMAL, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_X, 0.95 * cm, "Reporte Integral de Movilidad UTMACH")
    canvas.drawCentredString(PAGE_WIDTH / 2, 0.95 * cm, f"Período: {periodo}")
    canvas.drawRightString(PAGE_WIDTH - MARGIN_X, 0.95 * cm, f"Página {doc.page}")
    canvas.restoreState()

def _agregar_portada_integral(story, fecha_min: str, fecha_max: str, titulo: str):
    """Genera la portada del reporte integral."""
    story.append(Spacer(1, 2.3 * cm))
    
    story.append(Paragraph("UNIVERSIDAD TÉCNICA DE MACHALA",
        ParagraphStyle("Institucion", fontName=FONT_BOLD, fontSize=14, leading=18, textColor=NAVY, alignment=TA_CENTER, spaceAfter=8)))
    
    story.append(Paragraph("UNIDAD DE OBRAS E INFRAESTRUCTURA UNIVERSITARIA",
        ParagraphStyle("Unidad", fontName=FONT_NORMAL, fontSize=10, leading=14, textColor=MUTED, alignment=TA_CENTER, spaceAfter=30)))
    
    banda = Table(
        [[Paragraph(titulo.replace(" / ", "<br/>"),
            ParagraphStyle("Banda", fontName=FONT_BOLD, fontSize=20, leading=25, textColor=WHITE, alignment=TA_CENTER))]],
        colWidths=[CONTENT_WIDTH], rowHeights=[3.0 * cm], hAlign="CENTER",
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ],
    )
    story.append(banda)
    story.append(Spacer(1, 1.25 * cm))
    
    datos_fechas = [
        [_p("Período analizado"), _p(f"{fecha_min} – {fecha_max}")],
        [_p("Fecha de generación"), _p(_ahora_local().strftime("%d/%m/%Y %H:%M"))],
        [_p("Fuentes de información"), _p("HikCentral: biometría y reconocimiento LPR")],
        [_p("Alcance del reporte"), _p("Análisis estadístico de eventos registrados; no identifica trayectos ni vehículos únicos.")],
    ]
    tabla_fechas = Table(datos_fechas, colWidths=[4.3 * cm, 10.5 * cm], hAlign="CENTER", style=[
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ])
    story.append(tabla_fechas)

def exportar_reporte_integral_pdf(df: pd.DataFrame, tasas: dict, stats_base: dict, stats_nuevas: dict, conclusiones: list, calidad: dict, stats_gen_lpr: dict = None, df_lpr_f: pd.DataFrame = None, conclusiones_lpr: list = None, huella_dashboard: dict = None) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=MARGIN_X, leftMargin=MARGIN_X,
        topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
        title="Reporte Integral de Movilidad UTMACH",
        author="Universidad Técnica de Machala",
    )
    story = []
    
    # 1. Portada
    fecha_min = df["Fecha"].min().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].min()) else "N/A"
    fecha_max = df["Fecha"].max().strftime("%d/%m/%Y") if not df.empty and not pd.isna(df["Fecha"].max()) else "N/A"

    def hay_datos(diccionario, claves):
        for clave in claves:
            valor = diccionario.get(clave)
            if valor is not None and (not hasattr(valor, "empty") or not valor.empty):
                return True
        return False

    grupos_disponibles = {
        "resumen": True,
        "vehicular": True,
        "biometrico": True,
        "flujo": hay_datos(stats_base, ["flujo_consolidado", "entradas_salidas", "entradas_salidas_hora"]),
        "distribucion": hay_datos(stats_base, ["flujo_ingreso", "flujo_punto_acceso"]),
        "temporal": hay_datos(stats_base, ["heatmap_consolidado_hora", "flujo_diario", "flujo_hora", "ingreso_hora"]),
        "mapas": hay_datos(stats_base, ["heatmap_punto_hora", "heatmap_dia_hora"]),
        "usuarios": hay_datos(stats_base, ["tipo_usuario", "tipo_usuario_ingreso", "punto_tipo_usuario"]),
        "resultados": hay_datos(stats_nuevas, ["resultados", "cruce_ingreso", "evolucion_diaria", "cruce_hora", "cruce_punto", "cruce_device"]),
        "frecuencia": hay_datos(stats_base, ["frecuencia"]),
        "lpr": stats_gen_lpr is not None and df_lpr_f is not None and not df_lpr_f.empty,
        "metodologia": True,
        "conclusiones": True,
    }
    titulos_seccion = {
        "resumen": "Resumen ejecutivo y huella de movilidad",
        "vehicular": "Análisis vehicular consolidado",
        "biometrico": "Registros biométricos",
        "flujo": "Flujo general consolidado",
        "distribucion": "Distribución por categoría de acceso",
        "temporal": "Comportamiento horario y diario",
        "mapas": "Mapas de calor: puntos de acceso y días",
        "usuarios": "Usuarios por tipo y punto de acceso",
        "resultados": "Análisis de resultados y tasas de fallo",
        "frecuencia": "Frecuencia de utilización",
        "lpr": "Flujo vehicular LPR (reconocimiento de matrículas)",
        "metodologia": "Metodología y limitaciones",
        "conclusiones": "Conclusiones técnicas y recomendaciones",
    }
    claves_seccion = [clave for clave, disponible in grupos_disponibles.items() if disponible]
    numeros_seccion = {clave: posicion for posicion, clave in enumerate(claves_seccion, start=1)}

    _agregar_portada_integral(story, fecha_min, fecha_max, "REPORTE INTEGRAL DE MOVILIDAD")
    story.append(PageBreak())

    story.append(Paragraph("Índice de secciones", ESTILO_TITULO))
    indice = [f"{numeros_seccion[clave]}. {titulos_seccion[clave]}" for clave in claves_seccion]
    for item in indice:
        story.append(Paragraph(item, ESTILO_NORMAL))
        story.append(Spacer(1, 0.12 * cm))
    story.append(PageBreak())
    
    # 2. Resumen General de Movilidad
    import lpr_statistics_calc as lprs
    huella = huella_dashboard if huella_dashboard is not None else lprs.generar_huella_movilidad(df, df_lpr_f)
    
    story.append(Paragraph(f"{numeros_seccion['resumen']}. {titulos_seccion['resumen']}", ESTILO_TITULO))
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
    
    extraer_resumen = lambda valor: str(valor).split(" — ")[0]
    story.append(_tabla_indicadores([
        ("Registros analizados", f"{huella['tot_registros']:,}"),
        ("Peatonales", f"{huella['tot_peatones_puros']:,}"),
        ("Terminales VEH", f"{huella['tot_terminales_veh']:,}"),
        ("Eventos LPR", f"{huella['tot_lpr']:,}"),
        ("Día pico", _texto_espanol(extraer_resumen(huella['dia_pico_str']))),
        ("Hora pico", extraer_resumen(huella['hora_pico_str'])),
        ("Acceso pico", extraer_resumen(huella['acceso_pico_str'])),
    ], columnas=4))
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
    story.append(Paragraph(f"{numeros_seccion['vehicular']}. {titulos_seccion['vehicular']}", ESTILO_TITULO))
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
    story.append(_tabla_estadistica(resumen_veh, [3.7, 2.3, 2.3, 2.4, 4.3], (1, 2, 3, 4), NAVY))
    story.append(Spacer(1, 0.5 * cm))

    flujo_carril = stats_veh["flujo_por_carril"]
    if not flujo_carril.empty:
        story.append(CondPageBreak(7 * cm))
        story.append(Paragraph("Actividad registrada por carril", ESTILO_SUBTITULO))
        actividad_carril = [["Ubicación", "Carril", "Sentido", "Mecanismo", "Eventos registrados"]]
        intensidad_carril = [[
            "Ubicación y carril", "Hora pico real", "Promedio durante la hora pico",
            "Máximo en un minuto", "Minuto del máximo",
        ]]
        for fila in flujo_carril.itertuples():
            actividad_carril.append([
                fila.Ubicacion, fila.Carril, fila.Sentido, fila.Mecanismo, f"{fila.Eventos:,}",
            ])
            intensidad_carril.append([
                f"{fila.Ubicacion} · {fila.Carril}", fila.Hora_pico,
                f"{fila.Promedio_hora_pico_min:.2f} eventos/min",
                f"{fila.Maximo_observado_minuto:,}", fila.Minuto_maximo,
            ])
        story.append(_tabla_estadistica(actividad_carril, [3.6, 1.8, 2.2, 3.4, 2.4], (4,)))
        story.append(CondPageBreak(7 * cm))
        story.append(Paragraph("Intensidad y máximos por carril", ESTILO_SUBTITULO))
        story.append(_tabla_estadistica(intensidad_carril, [4.0, 3.3, 3.0, 2.1, 3.1], (2, 3)))
        story.append(Paragraph(
            "Hora pico real = fecha y hora concretas con más eventos del carril. El promedio durante esa "
            "hora se calcula con sus eventos divididos para 60; no representa el promedio mensual de una franja.",
            ESTILO_NOTA,
        ))

    caudal = stats_veh["caudal_por_acceso"]
    if not caudal.empty:
        story.append(CondPageBreak(7 * cm))
        story.append(Paragraph("Caudal simultáneo por acceso físico", ESTILO_SUBTITULO))
        tabla_caudal = [[
            "Ubicación", "Sentido", "Mecanismo", "Carriles", "Minuto de mayor actividad conjunta",
            "Eventos en ese minuto", "Promedio por carril",
        ]]
        for fila in caudal.itertuples():
            tabla_caudal.append([
                fila.Ubicacion, fila.Sentido, fila.Mecanismo, fila.Carriles, fila.Minuto_maximo,
                f"{fila.Caudal_maximo_eventos_min:,}",
                f"{fila.Promedio_por_carril_en_minuto_maximo:.2f}",
            ])
        story.append(_tabla_estadistica(tabla_caudal, [2.7, 1.7, 2.5, 1.4, 3.6, 2.1, 2.2], (3, 5, 6), NAVY))
        secundarios_caudal = [[
            "Ubicación y sentido", "Mecanismo", "Hora pico real",
            "Promedio conjunto en la hora pico", "Promedio por carril en la hora pico",
        ]]
        for fila in caudal.itertuples():
            secundarios_caudal.append([
                f"{fila.Ubicacion} · {fila.Sentido}", fila.Mecanismo, fila.Hora_pico,
                f"{fila.Promedio_conjunto_hora_pico_min:.2f}",
                f"{fila.Promedio_por_carril_hora_pico_min:.2f}",
            ])
        story.append(CondPageBreak(6 * cm))
        story.append(Paragraph("Estadísticas de la hora pico conjunta", ESTILO_SUBTITULO))
        story.append(_tabla_estadistica(secundarios_caudal, [3.5, 2.5, 3.0, 3.2, 3.2], (3, 4)))
        story.append(Paragraph(
            "Los carriles se alinean por el mismo minuto calendario antes de sumarse. No se suman máximos "
            "ocurridos en momentos distintos. El promedio por carril corresponde exclusivamente al minuto "
            "de mayor actividad conjunta.", ESTILO_NOTA,
        ))
    
    # 3. Resumen de Registros Biométricos
    story.append(CondPageBreak(8 * cm))
    story.append(Paragraph(f"{numeros_seccion['biometrico']}. {titulos_seccion['biometrico']}", ESTILO_TITULO))
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
    story.append(_tabla_estadistica(datos_indicadores, [9, 5], (1,), NAVY))
    story.append(Spacer(1, 1 * cm))
    
    # 4. Flujo General Consolidado
    import all_events_visualizations as atv
    import lpr_visualizations as lprv
    import visualizations as v

    def safe_add_grafico(story, fig, alto=8 * cm):
        if fig is not None:
            try:
                figura_pdf = copy.deepcopy(fig)
                figura_pdf.update_layout(
                    font=dict(family="Segoe UI, Helvetica, Arial, sans-serif", size=12, color="#263746"),
                    paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(l=70, r=35, t=70, b=70),
                    legend=dict(font=dict(size=11)),
                )
                figura_pdf.update_xaxes(automargin=True, title_font=dict(size=12), tickfont=dict(size=10))
                figura_pdf.update_yaxes(automargin=True, title_font=dict(size=12), tickfont=dict(size=10))
                _agregar_grafico(story, figura_pdf, ancho=CONTENT_WIDTH, alto=alto)
            except Exception as e:
                story.append(Paragraph(f"<font color='red'>Error al renderizar gráfico: {str(e)}</font>", ESTILO_NORMAL))

    if grupos_disponibles["flujo"]:
        story.append(CondPageBreak(9 * cm))
        story.append(Paragraph(f"{numeros_seccion['flujo']}. {titulos_seccion['flujo']}", ESTILO_TITULO))
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

    if grupos_disponibles["distribucion"]:
        story.append(CondPageBreak(9 * cm))
        story.append(Paragraph(f"{numeros_seccion['distribucion']}. {titulos_seccion['distribucion']}", ESTILO_TITULO))
        story.append(Spacer(1, 0.5 * cm))
    
    if "flujo_ingreso" in stats_base and not stats_base["flujo_ingreso"].empty:
        fig = v.grafico_ingreso(stats_base["flujo_ingreso"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))

    if "flujo_punto_acceso" in stats_base and not stats_base["flujo_punto_acceso"].empty:
        fig = v.grafico_flujo_punto_acceso(stats_base["flujo_punto_acceso"])
        safe_add_grafico(story, fig)

    if grupos_disponibles["temporal"]:
        story.append(CondPageBreak(9 * cm))
        story.append(Paragraph(f"{numeros_seccion['temporal']}. {titulos_seccion['temporal']}", ESTILO_TITULO))
        story.append(Spacer(1, 0.5 * cm))
    
    if "heatmap_consolidado_hora" in stats_base and not stats_base["heatmap_consolidado_hora"].empty:
        fig = v.grafico_heatmap_consolidado_hora(stats_base["heatmap_consolidado_hora"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "flujo_diario" in stats_base and not stats_base["flujo_diario"].empty:
        fig = v.grafico_flujo_diario(stats_base["flujo_diario"])
        safe_add_grafico(story, fig)
        story.append(CondPageBreak(9 * cm))
        
    if "flujo_hora" in stats_base and not stats_base["flujo_hora"].empty:
        fig = v.grafico_flujo_hora(stats_base["flujo_hora"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "ingreso_hora" in stats_base and not stats_base["ingreso_hora"].empty:
        fig = v.grafico_ingreso_hora(stats_base["ingreso_hora"])
        safe_add_grafico(story, fig)
        
    if grupos_disponibles["mapas"]:
        story.append(CondPageBreak(9 * cm))
        story.append(Paragraph(f"{numeros_seccion['mapas']}. {titulos_seccion['mapas']}", ESTILO_TITULO))
        story.append(Spacer(1, 0.5 * cm))
    
    if "heatmap_punto_hora" in stats_base and not stats_base["heatmap_punto_hora"].empty:
        fig = v.grafico_heatmap_punto_hora(stats_base["heatmap_punto_hora"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "heatmap_dia_hora" in stats_base and not stats_base["heatmap_dia_hora"].empty:
        fig = v.grafico_heatmap_dia_hora(stats_base["heatmap_dia_hora"])
        safe_add_grafico(story, fig)

    if grupos_disponibles["usuarios"]:
        story.append(CondPageBreak(9 * cm))
        story.append(Paragraph(f"{numeros_seccion['usuarios']}. {titulos_seccion['usuarios']}", ESTILO_TITULO))
        story.append(Spacer(1, 0.5 * cm))
    
    if "tipo_usuario" in stats_base and not stats_base["tipo_usuario"].empty:
        fig = v.grafico_tipo_usuario(stats_base["tipo_usuario"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "tipo_usuario_ingreso" in stats_base and not stats_base["tipo_usuario_ingreso"].empty:
        fig = v.grafico_tipo_usuario_ingreso(stats_base["tipo_usuario_ingreso"])
        safe_add_grafico(story, fig)
        story.append(CondPageBreak(9 * cm))
        
    if "punto_tipo_usuario" in stats_base and not stats_base["punto_tipo_usuario"].empty:
        fig = v.grafico_punto_tipo_usuario(stats_base["punto_tipo_usuario"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))

    # 9. Análisis de Tasas de Fallo y Éxito
    if grupos_disponibles["resultados"]:
        story.append(CondPageBreak(9 * cm))
        story.append(Paragraph(f"{numeros_seccion['resultados']}. {titulos_seccion['resultados']}", ESTILO_TITULO))
        story.append(Spacer(1, 0.5 * cm))
    
    if "resultados" in stats_nuevas and not stats_nuevas["resultados"].empty:
        fig = atv.grafico_resultados_generales(stats_nuevas["resultados"])
        safe_add_grafico(story, fig)
        story.append(Spacer(1, 0.5 * cm))
        
    if "cruce_ingreso" in stats_nuevas and not stats_nuevas["cruce_ingreso"].empty:
        fig = atv.grafico_cruce_ingreso_resultado(stats_nuevas["cruce_ingreso"])
        safe_add_grafico(story, fig)
        story.append(CondPageBreak(9 * cm))
        
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
        story.append(CondPageBreak(7 * cm))
        story.append(Paragraph("Dispositivos con mayor cantidad de resultados adversos", ESTILO_SUBTITULO))
        story.append(_tabla_estadistica(tabla_dispositivos, [5.3, 1.8, 2.8, 1.8, 2.1, 2.0], (1, 2, 3, 4, 5), NAVY))
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

    if grupos_disponibles["frecuencia"]:
        story.append(CondPageBreak(9 * cm))
        story.append(Paragraph(f"{numeros_seccion['frecuencia']}. {titulos_seccion['frecuencia']}", ESTILO_TITULO))
        story.append(Spacer(1, 0.5 * cm))
    
    if "frecuencia" in stats_base and not stats_base["frecuencia"].empty:
        fig = v.grafico_frecuencia(stats_base["frecuencia"])
        safe_add_grafico(story, fig)

    if grupos_disponibles["lpr"]:
        story.append(CondPageBreak(9 * cm))

    # 11. Analítica Avanzada LPR
    if stats_gen_lpr is not None and df_lpr_f is not None and not df_lpr_f.empty:
        story.append(Paragraph(f"{numeros_seccion['lpr']}. {titulos_seccion['lpr']}", ESTILO_TITULO))
        story.append(Spacer(1, 0.5 * cm))
        
        import lpr_statistics_calc as lprs
        texto_resumen = _texto_espanol(lprs.generar_texto_resumen_ejecutivo(df_lpr_f, stats_gen_lpr))
        story.append(Paragraph(formatear_texto_pdf(texto_resumen).replace('\n', '<br/>'), ESTILO_NORMAL))
        story.append(Spacer(1, 0.5 * cm))

        story.append(Paragraph("Resumen general LPR", ESTILO_SUBTITULO))
        datos_lpr = [
            ["Eventos válidos", "Matrículas únicas", "Entradas", "Salidas"],
            [
                f"{stats_gen_lpr.get('eventos_validos', 0):,}",
                f"{stats_gen_lpr.get('placas_unicas', 0):,}",
                f"{stats_gen_lpr.get('entradas', 0):,}",
                f"{stats_gen_lpr.get('salidas', 0):,}"
            ]
        ]
        story.append(_tabla_estadistica(datos_lpr, [1, 1, 1, 1], (0, 1, 2, 3)))
        story.append(Spacer(1, 0.5 * cm))

        resumen_entradas = lprs.resumen_entradas_vehiculares(df_lpr_f)
        pico = resumen_entradas.get("fecha_pico")
        story.append(Paragraph("Actividad diaria LPR", ESTILO_SUBTITULO))
        datos_entradas = [
            ["Días con registros", "Promedio diario de entradas", "Fecha de mayor ingreso", "Entradas en ese día"],
            [
                f"{resumen_entradas['dias_con_datos']:,}",
                f"{resumen_entradas['promedio_diario']:.2f}",
                (pico.strftime('%d/%m/%Y') if pico else "Sin entradas"),
                (f"{resumen_entradas['entradas_pico']:,}" if pico else "—"),
            ],
        ]
        story.append(_tabla_estadistica(datos_entradas, [1, 1.3, 1.2, 1], (0, 1, 3), NAVY))
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
        
        story.append(CondPageBreak(9 * cm))
        
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
            story.append(_tabla_estadistica(tabla_movimientos, [6, 5, 4], (2,)))
            
        story.append(CondPageBreak(9 * cm))
            
        df_top = lprs.stats_lpr_top_placas(df_lpr_f, 10)
        if not df_top.empty:
            df_top = df_top.copy()
            df_top["Matricula"] = df_top["Matricula"].apply(_anonimizar_matricula)
            fig = lprv.grafico_top_placas(df_top, theme="light")
            safe_add_grafico(story, fig)

    story.append(CondPageBreak(9 * cm))
    story.append(Paragraph(f"{numeros_seccion['metodologia']}. {titulos_seccion['metodologia']}", ESTILO_TITULO))
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
    story.append(CondPageBreak(7 * cm))
    story.append(Paragraph(f"{numeros_seccion['conclusiones']}. {titulos_seccion['conclusiones']}", ESTILO_TITULO))
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
