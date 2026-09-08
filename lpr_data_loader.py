"""
Módulo de carga de datos para eventos vehiculares (LPR).
"""
import pandas as pd
import streamlit as st

@st.cache_data(max_entries=1, ttl=1800, show_spinner="Cargando archivo de eventos vehiculares...")
def cargar_excel_lpr(archivo) -> pd.DataFrame:
    """Carga el archivo subido en memoria."""
    return pd.read_excel(archivo, engine="openpyxl")

def detectar_columnas_lpr(df: pd.DataFrame) -> dict:
    """
    Busca heurísticamente las columnas clave en el dataset LPR.
    """
    cols = df.columns.tolist()
    cols_upper = [c.upper() for c in cols]
    
    mapeo = {
        "matricula": None,
        "hora": None,
        "camara": None,
        "lista_vehiculos": None,
        "propietario": None
    }
    
    for i, c in enumerate(cols_upper):
        if any(kw in c for kw in ["MATRÍCULA", "MATRICULA", "PLACA"]):
            mapeo["matricula"] = cols[i]
        elif "HORA" in c or "TIME" in c or "FECHA" in c:
            if not mapeo["hora"]:
                mapeo["hora"] = cols[i]
        elif "CÁMARA" in c or "CAMARA" in c or "DISPOSITIVO" in c:
            mapeo["camara"] = cols[i]
        elif "LISTA" in c:
            mapeo["lista_vehiculos"] = cols[i]
        elif "PROPIETARIO" in c:
            mapeo["propietario"] = cols[i]
            
    return mapeo

def reporte_calidad_lpr(df: pd.DataFrame, mapeo: dict) -> dict:
    """Calcula indicadores de calidad para LPR."""
    calidad = {
        "total_registros": len(df),
        "columnas_faltantes": []
    }
    
    for clave, col in mapeo.items():
        if col is None and clave != "propietario":
            calidad["columnas_faltantes"].append(clave)
            
    if mapeo["propietario"] is None:
        calidad["nulos_propietario"] = len(df)
    else:
        calidad["nulos_propietario"] = df[mapeo["propietario"]].isnull().sum()
        
    return calidad
