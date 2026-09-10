"""
Módulo de cálculo de estadísticas para eventos vehiculares LPR.
"""
import pandas as pd
import numpy as np

def calcular_estadisticas_generales_lpr(df_valido: pd.DataFrame, df_duplicados: pd.DataFrame, df_crudo: pd.DataFrame) -> dict:
    total_lecturas = len(df_crudo) if df_crudo is not None else 0
    total_validos = len(df_valido)
    total_duplicados = len(df_duplicados) if df_duplicados is not None else 0
    entradas = len(df_valido[df_valido["Direccion"] == "ENTRADA"])
    salidas = len(df_valido[df_valido["Direccion"] == "SALIDA"])
    placas_unicas = df_valido["Matricula"].nunique() if not df_valido.empty else 0
    propietarios_identificados = df_valido[df_valido["Propietario"] != "Sin propietario"]["Propietario"].nunique() if not df_valido.empty else 0
    return {
        "total_lecturas": total_lecturas,
        "eventos_validos": total_validos,
        "duplicados_descartados": total_duplicados,
        "entradas": entradas,
        "salidas": salidas,
        "placas_unicas": placas_unicas,
        "propietarios_identificados": propietarios_identificados
    }

def stats_flujo_vehicular_por_hora(df_valido: pd.DataFrame) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    agrupado = df_valido.groupby("Hora_Dia").size().reset_index(name="Registros")
    agrupado.rename(columns={"Hora_Dia": "Hora"}, inplace=True)
    agrupado["Registros_por_minuto"] = (agrupado["Registros"] / 60).round(1)
    
    todas_horas = pd.DataFrame({"Hora": range(24)})
    resultado = todas_horas.merge(agrupado, on="Hora", how="left").fillna(0)
    resultado["Registros"] = resultado["Registros"].astype(int)
    return resultado

def stats_flujo_vehicular_top_periodos(df_valido: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    agrupado = df_valido.groupby("Hora_Dia").size().reset_index(name="Registros")
    agrupado.rename(columns={"Hora_Dia": "Hora"}, inplace=True)
    agrupado["Registros_por_minuto"] = (agrupado["Registros"] / 60).round(1)
    agrupado["Franja"] = agrupado["Hora"].apply(lambda h: f"{int(h)}:00–{(int(h)+1)%24}:00")
    agrupado = agrupado.sort_values(by="Registros", ascending=False).head(n)
    return agrupado

def stats_flujo_vehicular_por_acceso(df_valido: pd.DataFrame) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    # Buscar hora pico por cada acceso
    agrupado = df_valido.groupby(["Punto_Acceso", "Hora_Dia"]).size().reset_index(name="Registros")
    
    idx_max = agrupado.groupby("Punto_Acceso")["Registros"].idxmax()
    top_por_acceso = agrupado.loc[idx_max].copy()
    
    top_por_acceso["Registros_por_minuto"] = (top_por_acceso["Registros"] / 60).round(1)
    top_por_acceso["Hora_Pico"] = top_por_acceso["Hora_Dia"].apply(lambda h: f"{int(h)}:00–{(int(h)+1)%24}:00")
    
    top_por_acceso = top_por_acceso.sort_values(by="Registros", ascending=False)
    return top_por_acceso[["Punto_Acceso", "Hora_Pico", "Registros", "Registros_por_minuto"]]

def stats_lpr_por_sitio(df_valido: pd.DataFrame) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    agrupado = df_valido.groupby(["Sitio", "Direccion"]).size().reset_index(name="Eventos")
    agrupado["Punto_Acceso"] = agrupado["Sitio"] + " - " + agrupado["Direccion"]
    return agrupado.sort_values(by="Eventos", ascending=False)

def stats_lpr_por_camara(df_valido: pd.DataFrame) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    return df_valido["Camara"].value_counts().reset_index(name="Eventos").rename(columns={"index": "Camara"})

def stats_lpr_top_placas(df_valido: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    return df_valido["Matricula"].value_counts().head(n).reset_index(name="Eventos").rename(columns={"index": "Matricula"})

def stats_lpr_top_propietarios(df_valido: pd.DataFrame) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    df_prop = df_valido[df_valido["Propietario"] != "Sin propietario"]
    return df_prop["Propietario"].value_counts().head(10).reset_index(name="Eventos").rename(columns={"index": "Propietario"})

def generar_conclusiones_lpr(stats_gen: dict, df_valido: pd.DataFrame) -> list:
    conclusiones = []
    total = stats_gen.get("eventos_validos", 0)
    if total == 0: return ["No se registraron eventos vehiculares válidos en el período seleccionado."]
    conclusiones.append(f"Se analizaron {total:,} registros vehiculares, correspondientes a {stats_gen.get('placas_unicas', 0):,} placas únicas. Se descartaron {stats_gen.get('duplicados_descartados', 0):,} lecturas repetidas.")
    
    df_hora = stats_flujo_vehicular_por_hora(df_valido)
    if not df_hora.empty:
        hora_max = df_hora.loc[df_hora["Registros"].idxmax()]
        if hora_max["Registros"] > 0:
            concentracion = round((hora_max["Registros"] / total) * 100, 1)
            conclusiones.append(f"La hora de mayor flujo vehicular fue entre las {int(hora_max['Hora'])}:00 y {(int(hora_max['Hora'])+1)%24}:00, con {int(hora_max['Registros']):,} registros vehiculares. Esto representa un promedio de {hora_max['Registros_por_minuto']} registros vehiculares por minuto durante ese período.")
            conclusiones.append(f"El {concentracion}% del total de los registros vehiculares se concentraron exclusivamente durante esta hora pico.")
            
    return conclusiones

def generar_texto_resumen_ejecutivo(df_valido: pd.DataFrame, stats_gen: dict) -> str:
    if df_valido.empty:
        return "No hay suficientes datos vehiculares para generar un resumen ejecutivo."
        
    dias_analizados = df_valido["Fecha"].nunique()
    fecha_min = df_valido["Fecha"].min().strftime("%d/%m/%Y")
    fecha_max = df_valido["Fecha"].max().strftime("%d/%m/%Y")
    
    total_eventos = stats_gen.get("eventos_validos", 0)
    placas_unicas = stats_gen.get("placas_unicas", 0)
    
    # Obtener el día pico
    eventos_por_dia = df_valido.groupby("Fecha").size().reset_index(name="Eventos")
    dia_pico_row = eventos_por_dia.loc[eventos_por_dia["Eventos"].idxmax()]
    # Formatear el día
    import locale
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except:
        pass
    dia_pico_str = dia_pico_row["Fecha"].strftime("%A %d/%m").capitalize()
    
    # Hora pico
    eventos_por_hora = df_valido.groupby("Hora_Dia").size().reset_index(name="Eventos")
    hora_pico = eventos_por_hora.loc[eventos_por_hora["Eventos"].idxmax()]["Hora_Dia"]
    
    # Acceso pico
    eventos_por_acceso = df_valido.groupby("Punto_Acceso").size().reset_index(name="Eventos")
    acceso_pico = eventos_por_acceso.loc[eventos_por_acceso["Eventos"].idxmax()]["Punto_Acceso"]
    
    texto = (
        f"Se analizaron {dias_analizados} días de actividad vehicular, comprendidos entre el "
        f"{fecha_min} y el {fecha_max}.\n\n"
        f"Durante este período se analizaron {total_eventos:,} registros vehiculares, "
        f"correspondientes a {placas_unicas:,} placas únicas.\n\n"
    )
    
    df_hora = stats_flujo_vehicular_por_hora(df_valido)
    if not df_hora.empty and df_hora["Registros"].max() > 0:
        hora_max = df_hora.loc[df_hora["Registros"].idxmax()]
        texto += (
            f"La mayor concentración de registros vehiculares se presentó entre las **{int(hora_max['Hora'])}:00 y {(int(hora_max['Hora'])+1)%24}:00**, "
            f"con **{int(hora_max['Registros']):,} registros**, equivalente a aproximadamente **{hora_max['Registros_por_minuto']} registros vehiculares por minuto** durante este período.\n\n"
            f"Este comportamiento permite identificar la franja horaria de mayor demanda y facilita la evaluación de los momentos de mayor movimiento en los accesos.\n\n"
        )
    else:
        texto += (
            f"La mayor concentración de reconocimientos ocurrió el {dia_pico_str}, mientras que la franja horaria "
            f"con mayor actividad fue entre las {int(hora_pico):02d}:00 y {(int(hora_pico)+1)%24:02d}:00.\n\n"
        )

    texto += f"El acceso con mayor flujo fue {acceso_pico}.\n\n"
        
    return texto

def generar_huella_movilidad(df_peatones: pd.DataFrame, df_vehiculos: pd.DataFrame) -> dict:
    tot_registros = 0
    tot_peatones_puros = 0
    tot_terminales_veh = 0
    tot_lpr = 0
    placas_reconocidas = 0
    placas_unicas = 0
    
    df_combined = pd.DataFrame()
    
    # 1. Analizar Peatones / Terminales Biométricos
    if df_peatones is not None and not df_peatones.empty:
        col_acceso_p = None
        for col in ["Punto de acceso", "Punto_Acceso", "Punto Acceso", "Punto", "Acceso"]:
            if col in df_peatones.columns:
                col_acceso_p = col
                break
                
        tot_registros += len(df_peatones)
        
        if col_acceso_p:
            mask_veh = df_peatones[col_acceso_p].str.contains("VEH", case=False, na=False)
            tot_terminales_veh = mask_veh.sum()
            tot_peatones_puros = len(df_peatones) - tot_terminales_veh
            
            if "Fecha" in df_peatones.columns and "Hora" in df_peatones.columns:
                df_p = df_peatones[["Fecha", "Hora", col_acceso_p]].copy()
                df_p.rename(columns={col_acceso_p: "Punto_Acceso"}, inplace=True)
                df_combined = pd.concat([df_combined, df_p])
        else:
            tot_peatones_puros = len(df_peatones)
            
    # 2. Analizar LPR
    if df_vehiculos is not None and not df_vehiculos.empty:
        tot_lpr = len(df_vehiculos)
        tot_registros += tot_lpr
        
        # Placas reconocidas (asumiendo que DESCONOCIDO o vacíos son no reconocidas)
        if "Matricula" in df_vehiculos.columns:
            df_reconocidas = df_vehiculos[~df_vehiculos["Matricula"].isin(["DESCONOCIDO", "", "No Plate"])]
            placas_reconocidas = len(df_reconocidas)
            placas_unicas = df_reconocidas["Matricula"].nunique()
            
        col_acceso_v = None
        for col in ["Punto_Acceso", "Punto de acceso", "Punto Acceso", "Punto", "Acceso"]:
            if col in df_vehiculos.columns:
                col_acceso_v = col
                break
                
        if col_acceso_v and "Fecha" in df_vehiculos.columns and "Hora" in df_vehiculos.columns:
            df_v = df_vehiculos[["Fecha", "Hora", col_acceso_v]].copy()
            df_v.rename(columns={col_acceso_v: "Punto_Acceso"}, inplace=True)
            df_combined = pd.concat([df_combined, df_v])

    # 3. Picos Generales
    dia_pico_str = "N/A"
    hora_pico_str = "N/A"
    acceso_pico_str = "N/A"
    
    if not df_combined.empty:
        eventos_dia = df_combined.groupby("Fecha").size()
        d_pico = eventos_dia.idxmax()
        ev_d_pico = eventos_dia.max()
        try:
            import locale
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            pass
        dia_pico_str = f"{d_pico.strftime('%A %d/%m').capitalize()} — {ev_d_pico:,} registros"
        
        df_combined["Hora_Dia"] = df_combined["Hora"].dt.hour
        eventos_hora = df_combined.groupby("Hora_Dia").size()
        h_pico = eventos_hora.idxmax()
        ev_h_pico = eventos_hora.max()
        hora_pico_str = f"{int(h_pico)}:00–{(int(h_pico)+1)%24}:00 — {ev_h_pico:,} registros"
        
        eventos_acceso = df_combined.groupby("Punto_Acceso").size()
        a_pico = eventos_acceso.idxmax()
        ev_a_pico = eventos_acceso.max()
        acceso_pico_str = f"{a_pico} — {ev_a_pico:,} registros"

    # Cálculos de porcentajes
    pct_peatones_puros = round((tot_peatones_puros / tot_registros) * 100, 1) if tot_registros > 0 else 0
    pct_terminales_veh = round((tot_terminales_veh / tot_registros) * 100, 1) if tot_registros > 0 else 0
    pct_lpr = round((tot_lpr / tot_registros) * 100, 1) if tot_registros > 0 else 0

    return {
        "tot_registros": tot_registros,
        "tot_peatones_puros": tot_peatones_puros,
        "tot_terminales_veh": tot_terminales_veh,
        "tot_lpr": tot_lpr,
        "pct_peatones_puros": pct_peatones_puros,
        "pct_terminales_veh": pct_terminales_veh,
        "pct_lpr": pct_lpr,
        "placas_reconocidas": placas_reconocidas,
        "placas_unicas": placas_unicas,
        "dia_pico_str": dia_pico_str,
        "hora_pico_str": hora_pico_str,
        "acceso_pico_str": acceso_pico_str
    }

def stats_eventos_por_dia(df_valido: pd.DataFrame) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    agrupado = df_valido.groupby("Fecha").size().reset_index(name="Eventos")
    return agrupado

def stats_heatmap_dia_hora(df_valido: pd.DataFrame) -> pd.DataFrame:
    if df_valido.empty: return pd.DataFrame()
    heatmap_data = df_valido.groupby(["Dia_Semana", "Hora_Dia"]).size().reset_index(name="Eventos")
    heatmap_pivot = heatmap_data.pivot(index="Dia_Semana", columns="Hora_Dia", values="Eventos").fillna(0)
    # Reordenar dias
    from config import DIAS_SEMANA_ORDEN
    dias_presentes = [d for d in DIAS_SEMANA_ORDEN if d in heatmap_pivot.index]
    if not dias_presentes:
        return heatmap_pivot
    heatmap_pivot = heatmap_pivot.reindex(dias_presentes)
    # Completar horas
    for h in range(24):
        if h not in heatmap_pivot.columns:
            heatmap_pivot[h] = 0
    heatmap_pivot = heatmap_pivot[range(24)]
    return heatmap_pivot
