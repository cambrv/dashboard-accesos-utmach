"""
Procesamiento y limpieza de datos integrales ("Todos los Eventos").
"""
import pandas as pd
from config import (
    INGRESO_FERROVIARIA_KEYWORD, INGRESO_FERROVIARIA, 
    INGRESO_25_JUNIO, PATRONES_25_JUNIO, INGRESO_NO_CLASIFICADO,
    RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO,
    KW_EXITOSO, KW_DENEGADO, KW_FALLO,
    TIPO_USUARIO_SIN_CLASIFICAR, SEPARADOR_DEPARTAMENTO,
    DIAS_SEMANA_MAP, FORMATO_INTERVALO,
    MOVIMIENTO_ENTRADA, MOVIMIENTO_SALIDA, MOVIMIENTO_OTRO
)

def clasificar_tipo_evento(texto_evento: str) -> str:
    """
    Clasifica un evento a partir de su texto original utilizando las palabras clave
    definidas en config.py
    """
    if pd.isna(texto_evento):
        return RESULTADO_OTRO
        
    t = str(texto_evento).upper()
    
    for kw in KW_EXITOSO:
        if kw in t:
            return RESULTADO_EXITOSO
            
    for kw in KW_DENEGADO:
        if kw in t:
            return RESULTADO_DENEGADO
            
    for kw in KW_FALLO:
        if kw in t:
            return RESULTADO_FALLO_RECONOCIMIENTO
            
    return RESULTADO_OTRO


def procesar_datos_todos(df_crudo: pd.DataFrame, mapeo: dict) -> tuple[pd.DataFrame, dict]:
    """
    Limpia y estandariza las columnas basándose en el mapeo detectado heurísticamente.
    """
    df = df_crudo.copy()
    
    # 1. Renombrar a columnas estándar
    renames = {}
    if mapeo["tiempo"]: renames[mapeo["tiempo"]] = "Tiempo_Original"
    if mapeo["punto_acceso"]: renames[mapeo["punto_acceso"]] = "Punto de acceso"
    if mapeo["device_name"]: renames[mapeo["device_name"]] = "Device Name"
    if mapeo["tipo_evento"]: renames[mapeo["tipo_evento"]] = "Tipo_Evento_Original"
    if mapeo["nombre"]: renames[mapeo["nombre"]] = "Nombre"
    if mapeo["apellido"]: renames[mapeo["apellido"]] = "Apellido"
    if mapeo["departamento"]: renames[mapeo["departamento"]] = "Departamento"
    
    df.rename(columns=renames, inplace=True)
    
    # Asegurar que las columnas existan
    for col in ["Tiempo_Original", "Punto de acceso", "Device Name", "Tipo_Evento_Original", "Nombre", "Apellido", "Departamento"]:
        if col not in df.columns:
            df[col] = "Desconocido"
            
    # 2. Limpieza de texto básica
    for col in ["Punto de acceso", "Device Name", "Tipo_Evento_Original", "Nombre", "Apellido", "Departamento"]:
        df[col] = df[col].fillna("Desconocido").astype(str).str.strip()
        
    # 3. Extraer Fecha y Hora
    if mapeo["tiempo"]:
        df["Hora"] = pd.to_datetime(df["Tiempo_Original"], errors="coerce")
        df["Fecha"] = df["Hora"].dt.date
        df["Hora_Dia"] = df["Hora"].dt.hour
        df["Hora_Dia"] = df["Hora_Dia"].fillna(-1).astype(int)
    else:
        df["Hora"] = pd.NaT
        df["Fecha"] = pd.NaT
        df["Hora_Dia"] = -1
        
    df["Dia_Semana_Num"] = df["Hora"].dt.dayofweek
    df["Dia_Semana"] = df["Dia_Semana_Num"].map(DIAS_SEMANA_MAP)
    df["Mes"] = df["Hora"].dt.month
    df["Anio"] = df["Hora"].dt.year
    df["Intervalo_Horario"] = df["Hora_Dia"].apply(
        lambda h: FORMATO_INTERVALO.format(int(h), int(h)) if h >= 0 else "Desconocido"
    )
        
    # 4. Clasificación de Ingreso
    def clasificar_ingreso(punto: str) -> str:
        p = punto.upper()
        if p == "DESCONOCIDO" or not p:
            return INGRESO_NO_CLASIFICADO
        if INGRESO_FERROVIARIA_KEYWORD in p:
            return INGRESO_FERROVIARIA
        if any(pat in p for pat in PATRONES_25_JUNIO):
            return INGRESO_25_JUNIO
        return INGRESO_NO_CLASIFICADO

    df["Ingreso"] = df["Punto de acceso"].apply(clasificar_ingreso)
    
    # 4.5 Clasificación de Movimiento
    def clasificar_movimiento(punto: str) -> str:
        if pd.isna(punto):
            return MOVIMIENTO_OTRO
        p = str(punto).upper()
        if MOVIMIENTO_ENTRADA in p:
            return MOVIMIENTO_ENTRADA
        if MOVIMIENTO_SALIDA in p:
            return MOVIMIENTO_SALIDA
        return MOVIMIENTO_ENTRADA # Por defecto entrada en caso de torniquetes mixtos que no lo especifican

    df["Movimiento"] = df["Punto de acceso"].apply(clasificar_movimiento)
    
    # 5. Clasificación de Tipo de Evento
    df["Resultado"] = df["Tipo_Evento_Original"].apply(clasificar_tipo_evento)
    
    # 6. Tipo de Usuario
    def extraer_tipo_usuario(depto: str) -> str:
        if depto == "Desconocido" or not depto:
            return TIPO_USUARIO_SIN_CLASIFICAR
        partes = depto.split(SEPARADOR_DEPARTAMENTO)
        tipo = partes[-1].strip().upper()
        return tipo if tipo else TIPO_USUARIO_SIN_CLASIFICAR
        
    df["Tipo_Usuario"] = df["Departamento"].apply(extraer_tipo_usuario)
    
    # 7. Persona
    df["Persona"] = (df["Nombre"].replace("Desconocido", "") + " " + df["Apellido"].replace("Desconocido", "")).str.strip()
    
    metricas = {
        "total_procesados": len(df),
        "con_ingreso_clasificado": int((df["Ingreso"] != INGRESO_NO_CLASIFICADO).sum()),
        "exitosos": int((df["Resultado"] == RESULTADO_EXITOSO).sum()),
        "fallidos": int((df["Resultado"] != RESULTADO_EXITOSO).sum()),
    }
    
    return df, metricas
