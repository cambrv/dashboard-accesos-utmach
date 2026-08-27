"""
Módulo de carga de datos para eventos fallidos.
"""
import pandas as pd
import streamlit as st

@st.cache_data(max_entries=1, ttl=1800, show_spinner="Cargando archivo de eventos fallidos...")
def cargar_excel_fallidos(archivo) -> pd.DataFrame:
    """Carga el archivo subido en memoria."""
    return pd.read_excel(archivo, engine="openpyxl")

def detectar_columnas_fallidos(df: pd.DataFrame) -> dict:
    """
    Busca heurísticamente las columnas clave en un dataset de fallidos.
    Retorna un diccionario con el mapeo lógico de la columna original.
    """
    cols = df.columns.tolist()
    cols_upper = [c.upper() for c in cols]
    
    mapeo = {
        "tiempo": None,
        "punto_acceso": None,
        "tipo_fallo": None,
        "persona": None
    }
    
    # Heurística para Tiempo (Hora, Fecha, Time, Date)
    for i, c in enumerate(cols_upper):
        if any(kw in c for kw in ["HORA", "TIME", "FECHA", "DATE", "TIMESTAMP"]):
            mapeo["tiempo"] = cols[i]
            break
            
    # Heurística para Punto de acceso
    for i, c in enumerate(cols_upper):
        if any(kw in c for kw in ["PUNTO", "DEVICE", "DISPOSITIVO", "TERMINAL", "PUERTA"]):
            mapeo["punto_acceso"] = cols[i]
            break
            
    # Heurística para Tipo de Fallo
    for i, c in enumerate(cols_upper):
        if any(kw in c for kw in ["FALLO", "DENEGADO","MOTIVO", "RESULTADO", "EVENTO", "TYPE", "STATUS", "RAZON", "ERROR", "DESCRIPCI"]):
            mapeo["tipo_fallo"] = cols[i]
            break
            
    # Heurística para Persona
    for i, c in enumerate(cols_upper):
        if any(kw in c for kw in ["NOMBRE", "APELLIDO", "PERSONA", "USUARIO"]):
            mapeo["persona"] = cols[i]
            break
            
    return mapeo

def reporte_calidad_fallidos(df: pd.DataFrame, mapeo: dict) -> dict:
    """Calcula indicadores de calidad en base a las columnas detectadas."""
    calidad = {
        "total_registros": len(df),
        "columnas_faltantes": []
    }
    
    for clave, col in mapeo.items():
        if col is None:
            calidad["columnas_faltantes"].append(clave)
        else:
            # Reemplazar espacios o nulos para contar vacíos reales
            nulos = df[col].replace(r'^\s*$', pd.NA, regex=True).isnull().sum()
            calidad[f"nulos_{clave}"] = int(nulos)
            
    return calidad
