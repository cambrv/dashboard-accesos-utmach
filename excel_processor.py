import pandas as pd
import re

# Conjunto de columnas esperadas (combinado del proyecto para heurística)
KEYWORDS_ESPERADOS = set([
    "nombre", "apellido", "departamento", "hora", "device", "punto", "acceso",
    "tiempo", "fecha", "date", "time", "timestamp", "terminal", "puerta", "dispositivo",
    "tipo", "evento", "resultado", "fallo", "motivo", "area", "área", "persona",
    "usuario", "matricula", "matrícula", "placa", "camara", "cámara", "lista",
    "propietario", "dirección", "direccion", "grupo"
])

def _clean_col_name_for_match(col_name):
    if pd.isna(col_name):
        return ""
    return re.sub(r'\s+', ' ', str(col_name).strip().lower())

def leer_excel_centralizado(archivo, es_lpr=False) -> pd.DataFrame:
    """
    Lee un archivo Excel ubicando dinámicamente la fila de encabezados.
    Se basa en coincidencias múltiples con las columnas esperadas del proyecto.
    Luego, filtra los registros cuyo dispositivo contenga 'ACC' (si no es LPR)
    y conserva solo las columnas esenciales (si es LPR).
    """
    if hasattr(archivo, 'seek'):
        archivo.seek(0)
        
    # 1. Leer las primeras 30 filas para buscar el encabezado
    df_temp = pd.read_excel(archivo, engine="openpyxl", nrows=30, header=None)
    
    best_row_idx = 0
    max_matches = 0
    
    if es_lpr:
        keywords_busqueda = {"matricula", "matrícula", "placa", "hora", "camara", "cámara", "lista", "propietario"}
        umbral = 4  # Más estricto para LPR
    else:
        keywords_busqueda = KEYWORDS_ESPERADOS
        umbral = 3
    
    for idx, row in df_temp.iterrows():
        matches = 0
        for cell in row:
            c_clean = _clean_col_name_for_match(cell)
            if not c_clean:
                continue
                
            # Coincidencia flexible
            if any(kw in c_clean for kw in keywords_busqueda):
                matches += 1
                
        if matches > max_matches:
            max_matches = matches
            best_row_idx = idx
            
        # Si encuentra un buen número de coincidencias, se asume que es el encabezado
        if matches >= umbral:
            break
            
    if hasattr(archivo, 'seek'):
        archivo.seek(0)
        
    # 2. Crear el DataFrame con la fila detectada como encabezado
    df = pd.read_excel(archivo, engine="openpyxl", header=best_row_idx)
    
    # 3. Limpiar/normalizar nombres de columnas (quitar saltos de línea y espacios extra)
    df.columns = [
        re.sub(r'\s+', ' ', str(c).strip()) if pd.notna(c) else f"Unnamed_{i}" 
        for i, c in enumerate(df.columns)
    ]
    
    # 4. Procesamiento específico según el tipo de Excel
    if es_lpr:
        # Conservar únicamente las 5 columnas necesarias para LPR
        # "Número de matrícula", "Hora", "Cámara", "Lista de vehículos", "Propietario del vehículo"
        columnas_a_conservar = []
        for col in df.columns:
            c_upper = str(col).upper()
            es_necesaria = False
            
            if any(kw in c_upper for kw in ["MATRÍCULA", "MATRICULA", "PLACA"]):
                es_necesaria = True
            elif "HORA" in c_upper or "TIME" in c_upper or "FECHA" in c_upper:
                es_necesaria = True
            elif "CÁMARA" in c_upper or "CAMARA" in c_upper or "DISPOSITIVO" in c_upper:
                es_necesaria = True
            elif "LISTA" in c_upper:
                es_necesaria = True
            elif "PROPIETARIO" in c_upper:
                es_necesaria = True
                
            if es_necesaria:
                columnas_a_conservar.append(col)
                
        if columnas_a_conservar:
            df = df[columnas_a_conservar]
    else:
        # Filtrar los registros cuyo 'Nombre del dispositivo' contenga 'ACC'
        device_col = None
        for col in df.columns:
            c_clean = str(col).lower()
            if "device" in c_clean or "dispositivo" in c_clean or "cámara" in c_clean or "camara" in c_clean:
                device_col = col
                break
                
        if device_col:
            mask = df[device_col].astype(str).str.contains("ACC", case=False, na=False)
            df = df[~mask]
        
    return df
