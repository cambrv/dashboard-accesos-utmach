"""
Procesamiento y limpieza de datos de eventos fallidos.
"""
import pandas as pd
from config import INGRESO_FERROVIARIA_KEYWORD, INGRESO_FERROVIARIA, INGRESO_25_JUNIO, PATRONES_25_JUNIO, INGRESO_NO_CLASIFICADO

def procesar_datos_fallidos(df_crudo: pd.DataFrame, mapeo: dict) -> tuple[pd.DataFrame, dict]:
    """
    Limpia y estandariza las columnas basándose en el mapeo detectado heurísticamente.
    Retorna el DataFrame estandarizado y un diccionario de métricas.
    """
    df = df_crudo.copy()
    
    # 1. Renombrar a columnas estándar
    renames = {}
    if mapeo["tiempo"]: renames[mapeo["tiempo"]] = "Tiempo_Original"
    if mapeo["punto_acceso"]: renames[mapeo["punto_acceso"]] = "Punto_Acceso"
    if mapeo["tipo_fallo"]: renames[mapeo["tipo_fallo"]] = "Tipo_Fallo"
    if mapeo["persona"]: renames[mapeo["persona"]] = "Persona"
    
    df.rename(columns=renames, inplace=True)
    
    # Asegurar que las columnas existan aunque estén vacías
    for col in ["Tiempo_Original", "Punto_Acceso", "Tipo_Fallo", "Persona"]:
        if col not in df.columns:
            df[col] = "Desconocido"
            
    # 2. Limpieza de texto
    df["Punto_Acceso"] = df["Punto_Acceso"].fillna("Desconocido").astype(str).str.strip()
    df["Tipo_Fallo"] = df["Tipo_Fallo"].fillna("Desconocido").astype(str).str.strip()
    df["Persona"] = df["Persona"].fillna("Desconocido").astype(str).str.strip()
    
    # 3. Extraer Fecha y Hora
    if mapeo["tiempo"]:
        # Convertir a datetime, ignorando errores
        tiempo_dt = pd.to_datetime(df["Tiempo_Original"], errors="coerce")
        df["Fecha"] = tiempo_dt.dt.date
        df["Hora"] = tiempo_dt.dt.hour
        df["Hora"] = df["Hora"].fillna(-1).astype(int)
    else:
        df["Fecha"] = pd.NaT
        df["Hora"] = -1
        
    # Día de la semana (0=Lunes, 6=Domingo)
    df["Dia_Semana"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.dayofweek
        
    # 4. Clasificación de Ingreso (Reutilizamos la lógica del negocio)
    def clasificar_ingreso(punto: str) -> str:
        p = punto.upper()
        if p == "DESCONOCIDO" or not p:
            return INGRESO_NO_CLASIFICADO
        if INGRESO_FERROVIARIA_KEYWORD in p:
            return INGRESO_FERROVIARIA
        if any(pat in p for pat in PATRONES_25_JUNIO):
            return INGRESO_25_JUNIO
        return INGRESO_NO_CLASIFICADO

    df["Ingreso"] = df["Punto_Acceso"].apply(clasificar_ingreso)
    
    # Reemplazar valores vacíos
    df["Tipo_Fallo"] = df["Tipo_Fallo"].replace(["", "nan", "None"], "Desconocido")
    
    metricas = {
        "total_procesados": len(df),
        "con_ingreso_clasificado": int((df["Ingreso"] != INGRESO_NO_CLASIFICADO).sum())
    }
    
    return df, metricas
