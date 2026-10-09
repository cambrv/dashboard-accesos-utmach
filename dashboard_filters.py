"""Filtros puros del dashboard integral.

Este módulo no conoce Streamlit: recibe el estado confirmado del formulario y
devuelve DataFrames filtrados. Esto permite probar que editar widgets y aplicar
filtros sean responsabilidades separadas.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


MECANISMO_BIOMETRICO = "Biométrico"
MECANISMO_LPR = "LPR"
MECANISMOS_CONSOLIDADOS = (MECANISMO_BIOMETRICO, MECANISMO_LPR)


def aplicar_filtros_integrales(
    df_biometrico: pd.DataFrame,
    df_lpr: pd.DataFrame | None,
    filtros: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica exclusivamente los valores ya confirmados por el usuario.

    El filtro de mecanismo se usa después al construir las vistas consolidadas;
    los análisis propios de cada fuente conservan su DataFrame correspondiente.
    """
    bio = df_biometrico
    lpr = df_lpr if df_lpr is not None else pd.DataFrame()

    rango = filtros.get("rango_fechas") or ()
    if len(rango) == 2:
        inicio, fin = rango
        bio = bio[(bio["Fecha"] >= inicio) & (bio["Fecha"] <= fin)]
        if not lpr.empty:
            lpr = lpr[(lpr["Fecha"] >= inicio) & (lpr["Fecha"] <= fin)]

    resultados = filtros.get("resultados") or []
    if resultados:
        bio = bio[bio["Resultado"].isin(resultados)]

    ingresos = filtros.get("ingresos") or []
    if ingresos:
        bio = bio[bio["Ingreso"].isin(ingresos)]

    tipos_usuario = filtros.get("tipos_usuario") or []
    if tipos_usuario:
        bio = bio[bio["Tipo_Usuario"].isin(tipos_usuario)]

    ubicaciones = filtros.get("ubicaciones") or []
    if ubicaciones:
        if "Ubicacion_Ingreso" in bio.columns:
            bio = bio[bio["Ubicacion_Ingreso"].isin(ubicaciones)]
        if not lpr.empty and "Ubicacion_Ingreso" in lpr.columns:
            lpr = lpr[lpr["Ubicacion_Ingreso"].isin(ubicaciones)]

    puntos = filtros.get("puntos_acceso") or []
    if puntos:
        if "Punto de acceso" in bio.columns:
            bio = bio[bio["Punto de acceso"].isin(puntos)]
        if not lpr.empty:
            columna_lpr = "Camara" if "Camara" in lpr.columns else "Punto_Acceso"
            if columna_lpr in lpr.columns:
                lpr = lpr[lpr[columna_lpr].isin(puntos)]

    movimientos = [str(valor).upper() for valor in (filtros.get("movimientos") or [])]
    if movimientos:
        if "Movimiento" in bio.columns:
            bio = bio[bio["Movimiento"].astype(str).str.upper().isin(movimientos)]
        if not lpr.empty and "Direccion" in lpr.columns:
            lpr = lpr[lpr["Direccion"].astype(str).str.upper().isin(movimientos)]

    return bio.copy(), lpr.copy()


def mecanismo_incluido(filtros: dict[str, Any], mecanismo: str) -> bool:
    """Indica si una fuente participa en las vistas consolidadas."""
    seleccion = filtros.get("mecanismos") or []
    return not seleccion or mecanismo in seleccion
