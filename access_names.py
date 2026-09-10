import pandas as pd

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


def clasificar_acceso_funcional(nombre, es_lpr=False):
    """
    Retorna SOLAMENTE la categoría detallada oficial (una de las 6 categorías).
    """
    res = obtener_clasificacion_completa(nombre, es_lpr)
    return res["Categoria_Ingreso"]

def obtener_clasificacion_completa(nombre, es_lpr=False):
    """
    Clasifica un punto de acceso y devuelve un diccionario con 4 dimensiones:
    - Categoria_Ingreso (las 6 categorías detalladas oficiales)
    - Tipo_Flujo_Consolidado (Peatonal o Vehicular)
    - Mecanismo_Registro (Biométrico o LPR)
    - Ubicacion_Ingreso (25 de Junio o Ferroviaria)
    """
    default_res = {
        "Categoria_Ingreso": "Error de clasificación",
        "Tipo_Flujo_Consolidado": "Error de clasificación",
        "Mecanismo_Registro": "Error de clasificación",
        "Ubicacion_Ingreso": "Error de clasificación",
    }
    
    if pd.isna(nombre) or nombre is None:
        return default_res
        
    nombre_str = str(nombre).upper().strip()
    
    # Exclusión de valores vacíos o nulos
    if not nombre_str or nombre_str == "NAN" or nombre_str == "NONE" or nombre_str == "DESCONOCIDO":
        print(f"[DIAGNÓSTICO] Valor ignorado o desconocido: '{nombre}'")
        return default_res
        
    # Identificar mecanismo y tipo
    es_lpr_str = es_lpr or "LPR" in nombre_str
    es_vehicular_bio = "VEH" in nombre_str and not es_lpr_str
    es_peatonal = "TOR" in nombre_str or "DISCAP" in nombre_str or "PEATONAL" in nombre_str
    
    # Identificar ubicación
    es_ferroviaria = "FER" in nombre_str or "FERROVIARIA" in nombre_str
    es_25_junio = "25 DE JUNIO" in nombre_str or "TOR 1" in nombre_str or "TOR 2" in nombre_str or "TOR 3" in nombre_str or ("DISCAP" in nombre_str and "FER" not in nombre_str) or ("VEH" in nombre_str and "FER" not in nombre_str)
    
    ubicacion = "Ferroviaria" if es_ferroviaria else ("25 de Junio" if es_25_junio else "Error de clasificación")
    
    if es_lpr_str:
        return {
            "Categoria_Ingreso": f"Vehicular por LPR {ubicacion}",
            "Tipo_Flujo_Consolidado": "Vehicular",
            "Mecanismo_Registro": "LPR",
            "Ubicacion_Ingreso": ubicacion,
        }
    elif es_vehicular_bio:
        return {
            "Categoria_Ingreso": f"Vehicular por biométrico {ubicacion}",
            "Tipo_Flujo_Consolidado": "Vehicular",
            "Mecanismo_Registro": "Biométrico",
            "Ubicacion_Ingreso": ubicacion,
        }
    elif es_peatonal:
        return {
            "Categoria_Ingreso": f"Peatonal {ubicacion}",
            "Tipo_Flujo_Consolidado": "Peatonal",
            "Mecanismo_Registro": "Biométrico",
            "Ubicacion_Ingreso": ubicacion,
        }
            
    # Si llegó aquí es porque no coincide con los patrones exactos
    print(f"[DIAGNÓSTICO] No se pudo clasificar funcionalmente: '{nombre}'")
    return default_res

def obtener_nombre_corto_pdf(nombre):
    """
    Obtiene el nombre corto utilizado exclusivamente en los gráficos del PDF
    basado en las nuevas categorías funcionales.
    """
    if nombre is None:
        return nombre

    # Mapeo de categorías funcionales a nombres cortos
    mapeo_cortos = {
        "Peatonal 25 de Junio": "Peatonal 25 Jun",
        "Peatonal Ferroviaria": "Peatonal Ferro.",
        "Vehicular por biométrico 25 de Junio": "Veh. Bio 25 Jun",
        "Vehicular por biométrico Ferroviaria": "Veh. Bio Ferro.",
        "Vehicular por LPR 25 de Junio": "Veh. LPR 25 Jun",
        "Vehicular por LPR Ferroviaria": "Veh. LPR Ferro.",
        "Error de clasificación": "Error"
    }

    if nombre in mapeo_cortos:
        return mapeo_cortos[nombre]

    # Si por alguna razón recibe el nombre original, lo clasifica primero y luego lo acorta
    funcional = clasificar_acceso_funcional(nombre)
    return mapeo_cortos.get(funcional, nombre)

def obtener_nombre_amigable(nombre):
    """
    Retorna el nombre amigable de un punto de acceso.
    Si no existe en el diccionario, retorna el nombre original.
    """
    if not isinstance(nombre, str):
        return nombre
    
    # Retornar la clasificación funcional en lugar del mapeo antiguo o nombre original
    return clasificar_acceso_funcional(nombre)

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