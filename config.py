"""
Configuración central del proyecto.
Contiene constantes, mapeos y parámetros configurables.
"""

# ─── Columnas esperadas del Excel ────────────────────────────────────────────
COLUMNAS_ESPERADAS = [
    "Nombre",
    "Apellido",
    "Departamento",
    "Hora",
    "Device Name",
    "Punto de acceso"
]

# ─── Clasificación de ingreso ────────────────────────────────────────────────
# Cualquier punto de acceso que contenga "FER" (case-insensitive) → Ferroviaria
# Los puntos restantes conocidos → 25 de Junio
# Puntos no reconocidos → se muestran como "No clasificado"
INGRESO_FERROVIARIA_KEYWORD = "FER"
INGRESO_FERROVIARIA = "Ferroviaria"
INGRESO_25_JUNIO = "25 de Junio"
INGRESO_NO_CLASIFICADO = "No clasificado"

# Puntos de acceso conocidos que NO contienen "FER" y pertenecen a "25 de Junio"
# Se usa un patrón: si contiene TOR 1, TOR 2, TOR 3 o DISCAP (sin FER) → 25 de Junio
PATRONES_25_JUNIO = ["TOR 1", "TOR 2", "TOR 3", "DISCAP"]

# ─── Clasificación de movimiento ─────────────────────────────────────────────
MOVIMIENTO_ENTRADA = "ENTRADA"
MOVIMIENTO_SALIDA = "SALIDA"
MOVIMIENTO_OTRO = "OTRO"

# ─── Tipo de usuario ─────────────────────────────────────────────────────────
TIPO_USUARIO_SIN_CLASIFICAR = "SIN CLASIFICAR"
SEPARADOR_DEPARTAMENTO = ">"

# ─── Intervalos horarios ─────────────────────────────────────────────────────
# Intervalos de 1 hora: 00:00-00:59, 01:00-01:59, ..., 23:00-23:59
FORMATO_INTERVALO = "{:02d}:00–{:02d}:59"

# ─── Rangos de frecuencia de utilización ─────────────────────────────────────
RANGOS_FRECUENCIA = [
    (1, 5, "1–5 eventos"),
    (6, 10, "6–10 eventos"),
    (11, 20, "11–20 eventos"),
    (21, 50, "21–50 eventos"),
    (51, 100, "51–100 eventos"),
    (101, float("inf"), "Más de 100 eventos"),
]

# ─── Orden de días de la semana ──────────────────────────────────────────────
DIAS_SEMANA_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_SEMANA_MAP = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

# ─── Colores para gráficos ──────────────────────────────────────────────────
COLORES_INGRESO = {
    "Ferroviaria": "#1f77b4",
    "25 de Junio": "#ff7f0e",
    "No clasificado": "#7f7f7f",
}

COLORES_MOVIMIENTO = {
    "ENTRADA": "#2ca02c",
    "SALIDA": "#d62728",
    "OTRO": "#9467bd",
}

# ─── Formato de números ─────────────────────────────────────────────────────
DECIMALES_PORCENTAJE = 2

# ─── Configuración de la app ────────────────────────────────────────────────
APP_TITULO = "Sistema de Reportes — Flujo de Ingresos Peatonales"
APP_ICON = "📊"
APP_LAYOUT = "wide"

# ─── Clasificación de Resultado (Modo Todos los Eventos) ─────────────────────
RESULTADO_EXITOSO = "Exitoso"
RESULTADO_DENEGADO = "Denegado"
RESULTADO_FALLO_RECONOCIMIENTO = "Fallo de reconocimiento"
RESULTADO_OTRO = "Otro"

KW_EXITOSO = ["CONCEDIDO", "ÉXITO", "EXITOSO", "PERMITIDO", "AUTHORIZED", "GRANTED"]
KW_DENEGADO = ["DENEGADO", "RECHAZADO", "NO PERMITIDO", "DENIED", "REJECTED", "FORBIDDEN", "INVALID"]
KW_FALLO = ["FALLO", "NO DETECTADO", "ERROR", "TIMEOUT", "DESCONOCIDO", "UNRECOGNIZED"]

COLORES_RESULTADO = {
    RESULTADO_EXITOSO: "#2ca02c", # Verde (Éxito)
    RESULTADO_DENEGADO: "#d62728", # Rojo (Denegado)
    RESULTADO_FALLO_RECONOCIMIENTO: "#ff7f0e", # Naranja (Fallo)
    RESULTADO_OTRO: "#7f7f7f", # Gris
}
