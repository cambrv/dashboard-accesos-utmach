"""
Cálculo de estadísticas integrales (Todos los Eventos).
"""
import pandas as pd
from config import DIAS_SEMANA_MAP, RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO

def calcular_tasas_generales(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {}
    
    conteo = df["Resultado"].value_counts()
    exitosos = conteo.get(RESULTADO_EXITOSO, 0)
    denegados = conteo.get(RESULTADO_DENEGADO, 0)
    fallos_rec = conteo.get(RESULTADO_FALLO_RECONOCIMIENTO, 0)
    otros = conteo.get(RESULTADO_OTRO, 0)
    
    fallidos_totales = denegados + fallos_rec + otros
    
    return {
        "total": total,
        "exitosos": exitosos,
        "fallidos": fallidos_totales,
        "denegados": denegados,
        "fallos_rec": fallos_rec,
        "otros": otros,
        "tasa_exito": round((exitosos / total) * 100, 2),
        "tasa_fallo_general": round((fallidos_totales / total) * 100, 2),
        "tasa_denegacion": round((denegados / total) * 100, 2),
        "tasa_fallo_rec": round((fallos_rec / total) * 100, 2)
    }

def stats_resultados(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    conteo = df["Resultado"].value_counts().reset_index()
    conteo.columns = ["Resultado", "Eventos"]
    total = conteo["Eventos"].sum()
    conteo["Porcentaje"] = (conteo["Eventos"] / total * 100).round(2)
    return conteo

def stats_cruce_ingreso_resultado(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cruce = pd.crosstab(df["Ingreso"], df["Resultado"]).reset_index()
    cruce["Total"] = cruce.drop(columns="Ingreso").sum(axis=1)
    # Asegurar columnas
    for col in [RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO]:
        if col not in cruce.columns:
            cruce[col] = 0
            
    cruce["Tasa_Fallo"] = ((cruce["Total"] - cruce[RESULTADO_EXITOSO]) / cruce["Total"] * 100).round(2)
    return cruce.sort_values("Total", ascending=False)

def stats_cruce_hora_resultado(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df[df["Hora_Dia"] >= 0]
    if df_valid.empty:
        return pd.DataFrame()
    cruce = pd.crosstab(df_valid["Hora_Dia"], df_valid["Resultado"]).reset_index()
    cruce["Total"] = cruce.drop(columns="Hora_Dia").sum(axis=1)
    
    for col in [RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO]:
        if col not in cruce.columns:
            cruce[col] = 0
            
    cruce["Tasa_Fallo"] = ((cruce["Total"] - cruce[RESULTADO_EXITOSO]) / cruce["Total"] * 100).round(2)
    return cruce

def stats_evolucion_resultado(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df.dropna(subset=["Fecha"])
    if df_valid.empty:
        return pd.DataFrame()
    cruce = pd.crosstab(df_valid["Fecha"], df_valid["Resultado"]).reset_index()
    cruce["Total"] = cruce.drop(columns="Fecha").sum(axis=1)
    
    for col in [RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO]:
        if col not in cruce.columns:
            cruce[col] = 0
            
    cruce["Fecha"] = pd.to_datetime(cruce["Fecha"])
    return cruce.sort_values("Fecha")

def stats_dia_semana_resultado(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df.dropna(subset=["Dia_Semana"])
    if df_valid.empty:
        return pd.DataFrame()
    cruce = pd.crosstab(df_valid["Dia_Semana"], df_valid["Resultado"]).reset_index()
    cruce["Total"] = cruce.drop(columns="Dia_Semana").sum(axis=1)
    
    for col in [RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO]:
        if col not in cruce.columns:
            cruce[col] = 0
            
    cruce["Dia"] = cruce["Dia_Semana"].map(DIAS_SEMANA_MAP)
    return cruce.sort_values("Dia_Semana")

def stats_tipo_usuario_resultado(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cruce = pd.crosstab(df["Tipo_Usuario"], df["Resultado"]).reset_index()
    cruce["Total"] = cruce.drop(columns="Tipo_Usuario").sum(axis=1)
    for col in [RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO]:
        if col not in cruce.columns:
            cruce[col] = 0
    cruce["Tasa_Fallo"] = ((cruce["Total"] - cruce[RESULTADO_EXITOSO]) / cruce["Total"] * 100).round(2)
    return cruce.sort_values("Total", ascending=False)

def stats_punto_acceso_resultado(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cruce = pd.crosstab(df["Punto de acceso"], df["Resultado"]).reset_index()
    cruce["Total"] = cruce.drop(columns="Punto de acceso").sum(axis=1)
    for col in [RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO]:
        if col not in cruce.columns:
            cruce[col] = 0
    cruce["Tasa_Fallo"] = ((cruce["Total"] - cruce[RESULTADO_EXITOSO]) / cruce["Total"] * 100).round(2)
    return cruce.sort_values("Total", ascending=False)

def stats_device_resultado(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cruce = pd.crosstab(df["Device Name"], df["Resultado"]).reset_index()
    cruce["Total"] = cruce.drop(columns="Device Name").sum(axis=1)
    for col in [RESULTADO_EXITOSO, RESULTADO_DENEGADO, RESULTADO_FALLO_RECONOCIMIENTO, RESULTADO_OTRO]:
        if col not in cruce.columns:
            cruce[col] = 0
    cruce["Tasa_Fallo"] = ((cruce["Total"] - cruce[RESULTADO_EXITOSO]) / cruce["Total"] * 100).round(2)
    return cruce.sort_values("Total", ascending=False)

def stats_heatmap_dia_hora(df: pd.DataFrame) -> pd.DataFrame:
    df_valid = df.dropna(subset=["Dia_Semana", "Hora_Dia"])
    df_valid = df_valid[df_valid["Hora_Dia"] >= 0]
    if df_valid.empty:
        return pd.DataFrame()
    
    pivot = pd.pivot_table(
        df_valid,
        index="Dia_Semana",
        columns="Hora_Dia",
        aggfunc="size",
        fill_value=0
    )
    # Ensure all days and hours are present
    pivot = pivot.reindex(index=range(7), columns=range(24), fill_value=0)
    pivot.index = pivot.index.map(DIAS_SEMANA_MAP)
    return pivot

def stats_comportamiento_anormal(df: pd.DataFrame) -> dict:
    """Busca entidades con las peores tasas de fallo que superen un umbral de volumen."""
    anomalias = {}
    
    def _peor_tasa(cruce_df, col_entidad, min_volumen=10):
        if cruce_df.empty: return None
        # Solo entidades con un mínimo de eventos para no sesgar con n=1
        valido = cruce_df[cruce_df["Total"] >= min_volumen]
        if valido.empty: return None
        peor = valido.loc[valido["Tasa_Fallo"].idxmax()]
        if peor["Tasa_Fallo"] > 0:
            return {"entidad": peor[col_entidad], "tasa": peor["Tasa_Fallo"], "total": peor["Total"]}
        return None

    # Reusamos las funciones de stats para generar los dataframes
    anomalias["peor_ingreso"] = _peor_tasa(stats_cruce_ingreso_resultado(df), "Ingreso", 50)
    anomalias["peor_hora"] = _peor_tasa(stats_cruce_hora_resultado(df), "Hora_Dia", 20)
    anomalias["peor_punto"] = _peor_tasa(stats_punto_acceso_resultado(df), "Punto de acceso", 20)
    anomalias["peor_device"] = _peor_tasa(stats_device_resultado(df), "Device Name", 20)
    
    return anomalias

def generar_conclusiones_todos(df: pd.DataFrame, tasas: dict, stats: dict) -> list:
    """Genera conclusiones específicas para eventos integrales."""
    conclusiones = []
    
    total = tasas.get("total", 0)
    if total == 0:
        return ["No se registraron eventos en el período seleccionado."]
        
    conclusiones.append(f"Se registraron {total:,} eventos en total, con una tasa de éxito general del {tasas.get('tasa_exito', 0)}% y una tasa de fallos del {tasas.get('tasa_fallo_general', 0)}%.")
    
    if "cruce_ingreso" in stats and isinstance(stats["cruce_ingreso"], pd.DataFrame) and not stats["cruce_ingreso"].empty:
        if "Ingreso" in stats["cruce_ingreso"].columns and "Total" in stats["cruce_ingreso"].columns:
            top_ingreso = stats["cruce_ingreso"].iloc[0]
            conclusiones.append(f"El ingreso '{top_ingreso['Ingreso']}' concentró la mayor cantidad de flujo ({int(top_ingreso['Total']):,} eventos).")
            
            # Buscar ingreso con mayor tasa de fallo (mínimo 50 eventos para significancia)
            if "Tasa_Fallo" in stats["cruce_ingreso"].columns:
                df_ingreso = stats["cruce_ingreso"]
                df_significativo = df_ingreso[df_ingreso["Total"] >= 50]
                if not df_significativo.empty:
                    peor_ingreso = df_significativo.loc[df_significativo["Tasa_Fallo"].idxmax()]
                    if peor_ingreso["Tasa_Fallo"] > 0:
                        conclusiones.append(f"Entre los ingresos con volumen significativo, '{peor_ingreso['Ingreso']}' presentó la mayor proporción de eventos fallidos ({peor_ingreso['Tasa_Fallo']}%).")
                
    if "cruce_hora" in stats and isinstance(stats["cruce_hora"], pd.DataFrame) and not stats["cruce_hora"].empty:
        if "Hora_Dia" in stats["cruce_hora"].columns and "Total" in stats["cruce_hora"].columns:
            top_hora = stats["cruce_hora"].loc[stats["cruce_hora"]["Total"].idxmax()]
            conclusiones.append(f"La franja horaria de las {int(top_hora.get('Hora_Dia', 0)):02d}:00 experimentó el mayor volumen de tráfico.")
        else:
            conclusiones.append("No se dispone de información suficiente para determinar la franja horaria de mayor flujo.")
    else:
        conclusiones.append("No se dispone de información suficiente para determinar la franja horaria de mayor flujo.")
        
    return conclusiones
