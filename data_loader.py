"""
Módulo de carga de datos.
Responsable de leer el archivo Excel y realizar la validación inicial.
"""

import pandas as pd
import streamlit as st
from config import COLUMNAS_ESPERADAS


@st.cache_data(max_entries=1, ttl=1800, show_spinner="Cargando archivo Excel...")
def cargar_excel(ruta_archivo: str) -> pd.DataFrame:
    """
    Carga el archivo Excel y devuelve un DataFrame crudo.
    Utiliza cache para evitar recargas innecesarias.
    """
    df = pd.read_excel(ruta_archivo, engine="openpyxl")
    return df


def validar_columnas(df: pd.DataFrame) -> dict:
    """
    Valida que el DataFrame contenga las columnas esperadas.
    Retorna un diccionario con el resultado de la validación.
    """
    columnas_presentes = set(df.columns.tolist())
    columnas_esperadas = set(COLUMNAS_ESPERADAS)

    faltantes = columnas_esperadas - columnas_presentes
    extras = columnas_presentes - columnas_esperadas

    return {
        "valido": len(faltantes) == 0,
        "faltantes": list(faltantes),
        "extras": list(extras),
        "columnas_encontradas": df.columns.tolist(),
    }


def generar_reporte_calidad(df: pd.DataFrame) -> dict:
    """
    Genera un reporte de calidad de los datos crudos.
    No modifica ni elimina registros.
    """
    total = len(df)

    # Fechas inválidas
    hora_dt = pd.to_datetime(df["Hora"], errors="coerce")
    fechas_invalidas = int(hora_dt.isna().sum())

    # Nulos por columna
    nulos = df.isnull().sum().to_dict()

    # Registros con punto de acceso vacío
    acceso_vacio = int(df["Punto de acceso"].isna().sum() + (df["Punto de acceso"] == "").sum())

    # Registros con departamento vacío
    depto_vacio = int(df["Departamento"].isna().sum() + (df["Departamento"] == "").sum())

    # Registros con nombre o apellido vacío
    nombre_vacio = int(
        df["Nombre"].isna().sum()
        + df["Apellido"].isna().sum()
        + (df["Nombre"].fillna("") == "").sum()
        + (df["Apellido"].fillna("") == "").sum()
    )
    # Evitar doble conteo: contar registros donde ALGUNO sea nulo
    mask_nombre_vacio = df["Nombre"].isna() | (df["Nombre"] == "")
    mask_apellido_vacio = df["Apellido"].isna() | (df["Apellido"] == "")
    registros_sin_nombre = int((mask_nombre_vacio | mask_apellido_vacio).sum())

    # Valores únicos
    unicos_acceso = int(df["Punto de acceso"].nunique())
    unicos_device = int(df["Device Name"].nunique())

    return {
        "total_registros": total,
        "registros_validos": total - fechas_invalidas,
        "fechas_invalidas": fechas_invalidas,
        "acceso_vacio": acceso_vacio,
        "departamento_vacio": depto_vacio,
        "registros_sin_nombre": registros_sin_nombre,
        "nulos_por_columna": nulos,
        "unicos_punto_acceso": unicos_acceso,
        "unicos_device_name": unicos_device,
    }
