NOMBRES_PUNTOS_ACCESO = {
    "TER ENTRADA 1 DISCAP_Door_1":
        "Terminal Entrada 1 Discapacitados",

    "TER ENTRADA 1 TOR 1_Door_1":
        "Terminal Entrada 1 Torniquete 1",

    "TER ENTRADA 1 TOR 2_Door_1":
        "Terminal Entrada 1 Torniquete 2",

    "TER ENTRADA 1 TOR 3_Door_1":
        "Terminal Entrada 1 Torniquete 3",

    "TER ENTRADA 1 TOR FER_Door_1":
        "Terminal Entrada 1 Torniquete Ferroviaria",

    "TER ENTRADA 2 TOR 1_Door_1":
        "Terminal Entrada 2 Torniquete 1",

    "TER ENTRADA 2 TOR 2_Door_1":
        "Terminal Entrada 2 Torniquete 2",

    "TER ENTRADA 2 TOR 3_Door_1":
        "Terminal Entrada 2 Torniquete 3",

    "TER ENTRADA 2 TOR FER_Door_1":
        "Terminal Entrada 2 Torniquete Ferroviaria",

    "TER ENTRADA DISCAP FER_Door_1":
        "Terminal Entrada Discapacitados Ferroviaria",

    "TER SALIDA 1 DISCAP_Door_1":
        "Terminal Salida 1 Discapacitados",

    "TER SALIDA 1 TOR 1_Door_1":
        "Terminal Salida 1 Torniquete 1",

    "TER SALIDA 1 TOR 2_Door_1":
        "Terminal Salida 1 Torniquete 2",

    "TER SALIDA 1 TOR 3_Door_1":
        "Terminal Salida 1 Torniquete 3",

    "TER SALIDA 1 TOR FER_Door_1":
        "Terminal Salida 1 Torniquete Ferroviaria",

    "TER SALIDA 2 TOR 1_Door_1":
        "Terminal Salida 2 Torniquete 1",

    "TER SALIDA 2 TOR 2_Door_1":
        "Terminal Salida 2 Torniquete 2",

    "TER SALIDA 2 TOR 3_Door_1":
        "Terminal Salida 2 Torniquete 3",

    "TER SALIDA 2 TOR FER_Door_1":
        "Terminal Salida 2 Torniquete Ferroviaria",

    "TER SALIDA DISCAP FER_Door_1":
        "Terminal Salida Discapacitados Ferroviaria",
}

# ─────────────────────────────────────────────────────────────────────────────
# NOMBRES CORTOS PARA REPORTES PDF
# ─────────────────────────────────────────────────────────────────────────────

NOMBRES_CORTOS_PDF = {
    "TER ENTRADA 1 DISCAP_Door_1":
        "ED 25 de Junio",

    "TER ENTRADA 1 TOR 1_Door_1":
        "E1 · T1",

    "TER ENTRADA 1 TOR 2_Door_1":
        "E1 · T2",

    "TER ENTRADA 1 TOR 3_Door_1":
        "E1 · T3",

    "TER ENTRADA 1 TOR FER_Door_1":
        "E1 · FERRO",

    "TER ENTRADA 2 TOR 1_Door_1":
        "E2 · T1",

    "TER ENTRADA 2 TOR 2_Door_1":
        "E2 · T2",

    "TER ENTRADA 2 TOR 3_Door_1":
        "E2 · T3",

    "TER ENTRADA 2 TOR FER_Door_1":
        "E2 · FERRO",

    "TER ENTRADA DISCAP FER_Door_1":
        "ED FERRO",

    "TER SALIDA 1 DISCAP_Door_1":
        "SD 25 de Junio",

    "TER SALIDA 1 TOR 1_Door_1":
        "S1 · T1",

    "TER SALIDA 1 TOR 2_Door_1":
        "S1 · T2",

    "TER SALIDA 1 TOR 3_Door_1":
        "S1 · T3",

    "TER SALIDA 1 TOR FER_Door_1":
        "S1 · FERRO",

    "TER SALIDA 2 TOR 1_Door_1":
        "S2 · T1",

    "TER SALIDA 2 TOR 2_Door_1":
        "S2 · T2",

    "TER SALIDA 2 TOR 3_Door_1":
        "S2 · T3",

    "TER SALIDA 2 TOR FER_Door_1":
        "S2 · FERRO",

    "TER SALIDA DISCAP FER_Door_1":
        "SD FERRO",
}


def obtener_nombre_corto_pdf(nombre):
    """
    Obtiene el nombre corto utilizado exclusivamente
    en los gráficos del PDF. Puede recibir el nombre
    original o el nombre amigable.
    """
    if nombre is None:
        return nombre

    # Si es el nombre original y está en el diccionario de cortos
    if nombre in NOMBRES_CORTOS_PDF:
        return NOMBRES_CORTOS_PDF[nombre]

    # Si es un nombre amigable, buscar su original y luego su corto
    for original, amigable in NOMBRES_PUNTOS_ACCESO.items():
        if amigable == nombre:
            if original in NOMBRES_CORTOS_PDF:
                return NOMBRES_CORTOS_PDF[original]
            break

    return nombre

def obtener_nombre_amigable(nombre):
    """
    Retorna el nombre amigable de un punto de acceso.
    Si no existe en el diccionario, retorna el nombre original.
    """
    if not isinstance(nombre, str):
        return nombre
    return NOMBRES_PUNTOS_ACCESO.get(nombre, nombre)

def aplicar_nombres_amigables_df(df, columna="Punto de acceso"):
    """
    Retorna una copia del DataFrame con la columna especificada mapeada
    a los nombres amigables.
    """
    df_mapped = df.copy()
    if columna in df_mapped.columns:
        df_mapped[columna] = df_mapped[columna].apply(obtener_nombre_amigable)
    return df_mapped

# Por retrocompatibilidad, mantenemos este alias si se usaba antes
def nombre_punto_acceso(nombre):
    return obtener_nombre_amigable(nombre)