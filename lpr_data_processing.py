"""
Procesamiento, limpieza y deduplicación de datos vehiculares (LPR).
"""
import pandas as pd
import numpy as np
from config import (
    INGRESO_FERROVIARIA_KEYWORD, INGRESO_FERROVIARIA,
    INGRESO_25_JUNIO, PATRONES_25_JUNIO, INGRESO_NO_CLASIFICADO,
    LPR_KEYWORDS_CAMARA, LPR_DIRECCION_ENTRADA, LPR_DIRECCION_SALIDA, LPR_DIRECCION_OTRA,
    DIAS_SEMANA_MAP, FORMATO_INTERVALO
)

def procesar_datos_lpr(df_crudo: pd.DataFrame, mapeo: dict) -> tuple[pd.DataFrame, dict]:
    """Limpia y estandariza las columnas LPR."""
    df = df_crudo.copy()
    renames = {}
    if mapeo["matricula"]: renames[mapeo["matricula"]] = "Matricula_Original"
    if mapeo["hora"]: renames[mapeo["hora"]] = "Hora_Original"
    if mapeo["camara"]: renames[mapeo["camara"]] = "Camara_Original"
    if mapeo["lista_vehiculos"]: renames[mapeo["lista_vehiculos"]] = "Lista_Vehiculos"
    if mapeo["propietario"]: renames[mapeo["propietario"]] = "Propietario_Original"
    df.rename(columns=renames, inplace=True)
    
    for col in ["Matricula_Original", "Hora_Original", "Camara_Original"]:
        if col not in df.columns: df[col] = "Desconocido"
            
    if "Propietario_Original" not in df.columns: df["Propietario_Original"] = "Sin propietario"
    if "Lista_Vehiculos" not in df.columns: df["Lista_Vehiculos"] = "AUTORIZADOS"
        
    df["Matricula"] = df["Matricula_Original"].astype(str).str.strip().str.upper()
    df["Propietario"] = df["Propietario_Original"].fillna("Sin propietario").astype(str).str.strip()
    df["Propietario"] = df["Propietario"].replace(["NAN", "NONE", ""], "Sin propietario")
    df["Camara"] = df["Camara_Original"].fillna("Desconocida").astype(str).str.strip().str.upper()
    df["Camara"] = df["Camara"].replace(r'\s+', ' ', regex=True)
    
    df["Hora"] = pd.to_datetime(df["Hora_Original"], errors="coerce")
    df = df.dropna(subset=["Hora"])
    df = df[df["Matricula"] != "DESCONOCIDO"]
    df = df[df["Matricula"] != ""]
    
    df["Fecha"] = df["Hora"].dt.date
    df["Hora_Dia"] = df["Hora"].dt.hour
    df["Hora_Dia"] = df["Hora_Dia"].fillna(-1).astype(int)
    
    df["Dia_Semana_Num"] = df["Hora"].dt.dayofweek
    df["Dia_Semana"] = df["Dia_Semana_Num"].map(DIAS_SEMANA_MAP)
    df["Mes"] = df["Hora"].dt.month
    df["Anio"] = df["Hora"].dt.year
    df["Intervalo_Horario"] = df["Hora_Dia"].apply(
        lambda h: FORMATO_INTERVALO.format(int(h), int(h)) if h >= 0 else "Desconocido"
    )
    
    def clasificar_sitio(camara: str) -> str:
        if INGRESO_FERROVIARIA_KEYWORD in camara: return INGRESO_FERROVIARIA
        if any(pat in camara for pat in PATRONES_25_JUNIO): return INGRESO_25_JUNIO
        if "25" in camara or "JUNIO" in camara: return INGRESO_25_JUNIO
        return INGRESO_NO_CLASIFICADO

    df["Sitio"] = df["Camara"].apply(clasificar_sitio)
    
    def clasificar_direccion(camara: str) -> str:
        if "ING" in camara or "ENTRADA" in camara: return LPR_DIRECCION_ENTRADA
        if "SAL" in camara or "SALIDA" in camara: return LPR_DIRECCION_SALIDA
        return LPR_DIRECCION_OTRA

    df["Direccion"] = df["Camara"].apply(clasificar_direccion)
    df["Punto_Acceso"] = df["Sitio"] + " - " + df["Direccion"]
    
    metricas = {"total_lecturas_originales": len(df_crudo), "total_procesados_inicial": len(df)}
    return df, metricas

def deduplicar_eventos_vehiculares(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty: return df, pd.DataFrame()
    df = df.sort_values(by=["Matricula", "Hora"]).copy()
    
    df["Prev_Matricula"] = df["Matricula"].shift(1)
    df["Prev_Direccion"] = df["Direccion"].shift(1)
    df["Prev_Hora"] = df["Hora"].shift(1)
    df["Delta_Tiempo_Previo"] = (df["Hora"] - df["Prev_Hora"]).dt.total_seconds()
    
    cond_nueva_mat = df["Matricula"] != df["Prev_Matricula"]
    cond_cambio_dir = (df["Matricula"] == df["Prev_Matricula"]) & (df["Direccion"] != df["Prev_Direccion"])
    cond_tiempo = (df["Matricula"] == df["Prev_Matricula"]) & (df["Delta_Tiempo_Previo"] > 14400)
    
    es_valido = cond_nueva_mat | cond_cambio_dir | cond_tiempo
    df_valido = df[es_valido].copy()
    df_duplicados = df[~es_valido].copy()
    
    df_valido.drop(columns=["Prev_Matricula", "Prev_Direccion", "Prev_Hora", "Delta_Tiempo_Previo"], inplace=True)
    df_duplicados.drop(columns=["Prev_Matricula", "Prev_Direccion", "Prev_Hora", "Delta_Tiempo_Previo"], inplace=True)
    df_valido = df_valido.sort_values(by="Hora").reset_index(drop=True)
    
    return df_valido, df_duplicados

