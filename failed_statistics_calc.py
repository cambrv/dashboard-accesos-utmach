"""
Cálculo de estadísticas para eventos fallidos.
"""
import pandas as pd
from config import DIAS_SEMANA_MAP

def stats_fallos_por_ingreso(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    conteo = df["Ingreso"].value_counts().reset_index()
    conteo.columns = ["Ingreso", "Eventos"]
    total = conteo["Eventos"].sum()
    conteo["Porcentaje"] = (conteo["Eventos"] / total * 100).round(2)
    return conteo

def stats_fallos_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df[df["Hora"] >= 0]
    if df_valid.empty:
        return pd.DataFrame()
    conteo = df_valid.groupby("Hora").size().reset_index(name="Eventos")
    return conteo

def stats_fallos_evolucion_diaria(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df.dropna(subset=["Fecha"])
    if df_valid.empty:
        return pd.DataFrame()
    conteo = df_valid.groupby("Fecha").size().reset_index(name="Eventos")
    conteo["Fecha"] = pd.to_datetime(conteo["Fecha"])
    return conteo.sort_values("Fecha")

def stats_fallos_por_punto(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    conteo = df["Punto_Acceso"].value_counts().reset_index()
    conteo.columns = ["Punto de acceso", "Eventos"]
    return conteo

def stats_fallos_dia_semana(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df.dropna(subset=["Dia_Semana_Num"])
    if df_valid.empty:
        return pd.DataFrame()
    conteo = df_valid.groupby("Dia_Semana_Num").size().reset_index(name="Eventos")
    conteo["Dia"] = conteo["Dia_Semana_Num"].map(DIAS_SEMANA_MAP)
    return conteo.sort_values("Dia_Semana_Num")

def generar_conclusiones_fallidos(df: pd.DataFrame, stats: dict) -> list:
    """Genera conclusiones específicas para eventos anormales (sin inferir causas)."""
    conclusiones = []
    
    total = len(df)
    if total == 0:
        return ["No se registraron eventos anormales en el período seleccionado."]
        
    conclusiones.append(f"Durante el período analizado se registraron {total:,} eventos anormales.")
    
    if "por_ingreso" in stats and not stats["por_ingreso"].empty:
        top_ingreso = stats["por_ingreso"].iloc[0]
        if top_ingreso["Ingreso"] != "Desconocido" and top_ingreso["Ingreso"] != "No clasificado":
            conclusiones.append(f"El ingreso '{top_ingreso['Ingreso']}' concentró la mayor cantidad de eventos anormales ({int(top_ingreso['Eventos']):,}).")
            
    if "por_hora" in stats and not stats["por_hora"].empty:
        top_hora = stats["por_hora"].loc[stats["por_hora"]["Eventos"].idxmax()]
        conclusiones.append(f"Los eventos anormales presentaron una mayor concentración durante la franja de las {int(top_hora['Hora']):02d}:00 horas.")
        
    return conclusiones
