"""
Módulo de limpieza y transformación de datos.
Aplica las reglas definidas en REPORTES_ACCESOS_REGLAS.md.
No elimina registros salvo los de fecha inválida (que se contabilizan).
"""

import pandas as pd
import numpy as np
import streamlit as st
from config import (
    INGRESO_FERROVIARIA_KEYWORD,
    INGRESO_FERROVIARIA,
    INGRESO_25_JUNIO,
    INGRESO_NO_CLASIFICADO,
    MOVIMIENTO_ENTRADA,
    MOVIMIENTO_SALIDA,
    MOVIMIENTO_OTRO,
    TIPO_USUARIO_SIN_CLASIFICAR,
    SEPARADOR_DEPARTAMENTO,
    DIAS_SEMANA_MAP,
    FORMATO_INTERVALO,
    PATRONES_25_JUNIO,
)


@st.cache_data(show_spinner="Procesando datos...")
def procesar_datos(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Procesa el DataFrame crudo aplicando todas las transformaciones.
    Retorna:
        - DataFrame procesado
        - Diccionario con métricas de procesamiento
    """
    df = df.copy()
    metricas = {}

    # ─── 1. Convertir columna Hora a datetime ───────────────────────────
    df["Hora"] = pd.to_datetime(df["Hora"], errors="coerce")
    fechas_invalidas = int(df["Hora"].isna().sum())
    metricas["fechas_invalidas"] = fechas_invalidas

    # Separar registros con fecha inválida (se reportan, no se eliminan silenciosamente)
    if fechas_invalidas > 0:
        metricas["registros_fecha_invalida"] = fechas_invalidas
        df = df.dropna(subset=["Hora"]).copy()

    metricas["registros_procesados"] = len(df)

    # ─── 2. Generar columnas temporales ──────────────────────────────────
    df["Fecha"] = df["Hora"].dt.date
    df["Hora_Dia"] = df["Hora"].dt.hour
    df["Dia_Semana_Num"] = df["Hora"].dt.dayofweek
    df["Dia_Semana"] = df["Dia_Semana_Num"].map(DIAS_SEMANA_MAP)
    df["Mes"] = df["Hora"].dt.month
    df["Anio"] = df["Hora"].dt.year
    df["Intervalo_Horario"] = df["Hora_Dia"].apply(
        lambda h: FORMATO_INTERVALO.format(h, h)
    )

    # ─── 3. Extraer Tipo de Usuario de Departamento ─────────────────────
    df["Tipo_Usuario"] = df["Departamento"].apply(_extraer_tipo_usuario)

    # ─── 4. Determinar Ingreso desde Punto de acceso ────────────────────
    df["Ingreso"] = df["Punto de acceso"].apply(_clasificar_ingreso)

    # ─── 5. Determinar Movimiento (Entrada/Salida/Otro) ─────────────────
    df["Movimiento"] = df["Punto de acceso"].apply(_clasificar_movimiento)

    # ─── 6. Crear identificador de persona ──────────────────────────────
    df["Persona"] = (
        df["Nombre"].fillna("").str.strip() + " " + df["Apellido"].fillna("").str.strip()
    ).str.strip()
    # Personas sin nombre quedan como cadena vacía → se tratan pero no se eliminan

    # ─── 7. Métricas generales ──────────────────────────────────────────
    metricas["fecha_inicial"] = df["Hora"].min()
    metricas["fecha_final"] = df["Hora"].max()
    metricas["total_eventos"] = len(df)
    metricas["usuarios_unicos"] = df.loc[df["Persona"] != "", "Persona"].nunique()
    metricas["puntos_acceso"] = df["Punto de acceso"].nunique()
    metricas["ingreso_count"] = df["Ingreso"].nunique()
    metricas["entradas"] = int((df["Movimiento"] == MOVIMIENTO_ENTRADA).sum())
    metricas["salidas"] = int((df["Movimiento"] == MOVIMIENTO_SALIDA).sum())
    metricas["otros"] = int((df["Movimiento"] == MOVIMIENTO_OTRO).sum())

    # Promedio diario
    dias_unicos = df["Fecha"].nunique()
    metricas["dias_unicos"] = dias_unicos
    metricas["promedio_diario"] = round(len(df) / dias_unicos, 2) if dias_unicos > 0 else 0

    # Accesos no clasificados
    no_clasificados = df[df["Ingreso"] == INGRESO_NO_CLASIFICADO]["Punto de acceso"].unique().tolist()
    metricas["accesos_no_clasificados"] = no_clasificados

    return df, metricas


def _extraer_tipo_usuario(departamento) -> str:
    """
    Extrae el tipo de usuario de la columna Departamento.
    'All Departments > ESTUDIANTES' → 'ESTUDIANTES'
    Valores vacíos o inválidos → 'SIN CLASIFICAR'
    """
    if pd.isna(departamento) or str(departamento).strip() == "":
        return TIPO_USUARIO_SIN_CLASIFICAR
    partes = str(departamento).split(SEPARADOR_DEPARTAMENTO)
    tipo = partes[-1].strip().upper()
    return tipo if tipo else TIPO_USUARIO_SIN_CLASIFICAR


def _clasificar_ingreso(punto_acceso) -> str:
    """
    Clasifica el ingreso a partir del punto de acceso.
    Si contiene 'FER' → Ferroviaria
    Si contiene patrones conocidos de 25 de Junio → 25 de Junio
    Otros → No clasificado
    """
    if pd.isna(punto_acceso):
        return INGRESO_NO_CLASIFICADO
    acceso_upper = str(punto_acceso).upper()
    if INGRESO_FERROVIARIA_KEYWORD.upper() in acceso_upper:
        return INGRESO_FERROVIARIA
    # Verificar patrones de 25 de Junio
    for patron in PATRONES_25_JUNIO:
        if patron.upper() in acceso_upper:
            return INGRESO_25_JUNIO
    return INGRESO_NO_CLASIFICADO


def _clasificar_movimiento(punto_acceso) -> str:
    """
    Determina el tipo de movimiento del punto de acceso.
    """
    if pd.isna(punto_acceso):
        return MOVIMIENTO_OTRO
    acceso_upper = str(punto_acceso).upper()
    if MOVIMIENTO_ENTRADA in acceso_upper:
        return MOVIMIENTO_ENTRADA
    if MOVIMIENTO_SALIDA in acceso_upper:
        return MOVIMIENTO_SALIDA
    return MOVIMIENTO_OTRO
