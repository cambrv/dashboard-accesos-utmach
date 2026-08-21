"""
Módulo de carga de datos para "Todos los Eventos".
"""
import pandas as pd
import streamlit as st

@st.cache_data(max_entries=1, ttl=1800, show_spinner="Cargando archivo de eventos integrales...")
def cargar_excel_todos(archivo) -> pd.DataFrame:
    """Carga el archivo subido en memoria."""
    return pd.read_excel(archivo, engine="openpyxl")

def detectar_columnas_todos(df: pd.DataFrame) -> dict:
    """
    Busca heurísticamente las columnas clave en el dataset integral.
    Retorna un diccionario con el mapeo lógico de la columna original.
    """
    cols = df.columns.tolist()
    cols_upper = [c.upper() for c in cols]
    
    mapeo = {
        "tiempo": None,
        "punto_acceso": None,
        "device_name": None,
        "tipo_evento": None,
        "nombre": None,
        "apellido": None,
        "departamento": None
    }
    
    # 1. Tiempo (Hora, Fecha, Time, Date)
    for i, c in enumerate(cols_upper):
        if any(kw in c for kw in ["HORA", "TIME", "FECHA", "DATE", "TIMESTAMP"]):
            mapeo["tiempo"] = cols[i]
            break
            
    # 2. Punto de acceso
    for i, c in enumerate(cols_upper):
        if any(kw in c for kw in ["PUNTO DE ACCESO", "PUNTO", "TERMINAL", "PUERTA"]) and "DEVICE" not in c:
            mapeo["punto_acceso"] = cols[i]
            break
            
    # 3. Device Name
    for i, c in enumerate(cols_upper):
        if "DEVICE" in c or "DISPOSITIVO" in c:
            mapeo["device_name"] = cols[i]
            break
            
    # 4. Tipo de Evento
    for i, c in enumerate(cols_upper):
        if any(kw in c for kw in ["TIPO DE EVENTO", "EVENTO", "TIPO", "RESULTADO", "FALLO", "MOTIVO"]):
            mapeo["tipo_evento"] = cols[i]
            break
            
    # 5. Nombre
    for i, c in enumerate(cols_upper):
        if "NOMBRE" in c:
            mapeo["nombre"] = cols[i]
            break
            
    # 6. Apellido
    for i, c in enumerate(cols_upper):
        if "APELLIDO" in c:
            mapeo["apellido"] = cols[i]
            break
            
    # 7. Departamento
    for i, c in enumerate(cols_upper):
        if "DEPARTAMENTO" in c or "AREA" in c or "ÁREA" in c:
            mapeo["departamento"] = cols[i]
            break
            
    return mapeo

def reporte_calidad_todos(df: pd.DataFrame, mapeo: dict) -> dict:
    """Calcula indicadores de calidad."""
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
            
    # Provide the keys expected by app.py for UI display
    calidad["registros_validos"] = len(df) # simplified for now
    
    # Calculate more specific nulls based on mapped columns
    col_tiempo = mapeo.get("tiempo")
    calidad["fechas_invalidas"] = int(df[col_tiempo].replace(r'^\s*$', pd.NA, regex=True).isnull().sum()) if col_tiempo else 0
    
    col_pa = mapeo.get("punto_acceso")
    calidad["acceso_vacio"] = int(df[col_pa].replace(r'^\s*$', pd.NA, regex=True).isnull().sum()) if col_pa else 0
    
    col_dep = mapeo.get("departamento")
    calidad["departamento_vacio"] = int(df[col_dep].replace(r'^\s*$', pd.NA, regex=True).isnull().sum()) if col_dep else 0
    
    col_nom = mapeo.get("nombre")
    calidad["registros_sin_nombre"] = int(df[col_nom].replace(r'^\s*$', pd.NA, regex=True).isnull().sum()) if col_nom else 0

    if mapeo["tipo_evento"]:
        calidad["unicos_tipo_evento"] = df[mapeo["tipo_evento"]].nunique()
    if mapeo["punto_acceso"]:
        calidad["unicos_punto_acceso"] = df[mapeo["punto_acceso"]].nunique()
    if mapeo["device_name"]:
        calidad["unicos_device_name"] = df[mapeo["device_name"]].nunique()
        
    nulos_dict = {clave: calidad.get(f"nulos_{clave}", 0) for clave in mapeo.keys()}
    calidad["nulos_por_columna"] = nulos_dict
        
    return calidad
