"""
Módulo de cálculo de estadísticas para eventos vehiculares LPR.
"""
import pandas as pd
import numpy as np
from config import DIAS_SEMANA_MAP
from access_names import clasificar_carril_vehicular


UBICACIONES_LPR_VALIDAS = ("25 de Junio", "Ferroviaria")
DIRECCIONES_LPR_VALIDAS = ("ENTRADA", "SALIDA")
VALORES_CAMARA_INVALIDA = {"", "NAN", "NONE", "DESCONOCIDO", "DESCONOCIDA"}

def calcular_estadisticas_generales_lpr(df_valido: pd.DataFrame, df_duplicados: pd.DataFrame, df_crudo: pd.DataFrame) -> dict:
    total_lecturas = len(df_crudo) if df_crudo is not None else None
    total_validos = len(df_valido)
    total_duplicados = len(df_duplicados) if df_duplicados is not None else None
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


def stats_entradas_vehiculares_diarias(df_valido: pd.DataFrame) -> pd.DataFrame:
    """Cuenta eventos LPR de entrada por cada día que contiene datos LPR.

    Los días que solo contienen salidas se conservan con cero entradas. Esto
    hace que el promedio represente días con datos, no únicamente días con al
    menos una entrada.
    """
    columnas = ["Fecha", "Dia_Semana", "Entradas"]
    if df_valido is None or df_valido.empty or "Fecha" not in df_valido.columns:
        return pd.DataFrame(columns=columnas)

    base = df_valido.dropna(subset=["Fecha"]).copy()
    if base.empty:
        return pd.DataFrame(columns=columnas)

    fechas = pd.Index(sorted(base["Fecha"].unique()), name="Fecha")
    entradas = (
        base.loc[base["Direccion"] == "ENTRADA"]
        .groupby("Fecha")
        .size()
        .reindex(fechas, fill_value=0)
    )
    resultado = entradas.rename("Entradas").reset_index()
    fechas_dt = pd.to_datetime(resultado["Fecha"], errors="coerce")
    resultado["Dia_Semana"] = fechas_dt.dt.dayofweek.map(DIAS_SEMANA_MAP)
    resultado["Entradas"] = resultado["Entradas"].astype(int)
    return resultado[columnas]


def resumen_entradas_vehiculares(df_valido: pd.DataFrame) -> dict:
    """Resume entradas registradas, promedio por día con datos y día pico."""
    diario = stats_entradas_vehiculares_diarias(df_valido)
    total = int(diario["Entradas"].sum()) if not diario.empty else 0
    dias_con_datos = len(diario)
    promedio = total / dias_con_datos if dias_con_datos else 0.0
    if diario.empty or total == 0:
        fecha_pico, entradas_pico = None, 0
    else:
        fila_pico = diario.loc[diario["Entradas"].idxmax()]
        fecha_pico = fila_pico["Fecha"]
        entradas_pico = int(fila_pico["Entradas"])
    return {
        "total_entradas": total,
        "dias_con_datos": dias_con_datos,
        "promedio_diario": promedio,
        "fecha_pico": fecha_pico,
        "entradas_pico": entradas_pico,
        "diario": diario,
    }


def stats_movimientos_lpr_por_ubicacion_camara(df_valido: pd.DataFrame) -> dict:
    """Desglosa entradas/salidas LPR y expone diferencias de clasificación."""
    columnas_ubicacion = ["Ubicacion", "Sentido", "Registros"]
    columnas_camara = ["Ubicacion", "Sentido", "Camara", "Registros"]
    vacio = {
        "total_entradas": 0,
        "total_salidas": 0,
        "por_ubicacion": pd.DataFrame(columns=columnas_ubicacion),
        "por_camara": pd.DataFrame(columns=columnas_camara),
        "diferencias": {
            "entradas_sin_ubicacion_valida": 0,
            "salidas_sin_ubicacion_valida": 0,
            "entradas_sin_camara_valida": 0,
            "salidas_sin_camara_valida": 0,
            "direccion_no_valida": 0,
        },
    }
    if df_valido is None or df_valido.empty:
        return vacio

    df = df_valido.copy()
    direccion = df.get("Direccion", pd.Series(index=df.index, dtype="object")).astype(str).str.upper()
    ubicacion = df.get("Ubicacion_Ingreso", pd.Series(index=df.index, dtype="object")).astype(str).str.strip()
    camara = df.get("Camara", pd.Series(index=df.index, dtype="object")).astype(str).str.strip()
    mascara_direccion = direccion.isin(DIRECCIONES_LPR_VALIDAS)
    mascara_ubicacion = ubicacion.isin(UBICACIONES_LPR_VALIDAS)
    mascara_camara = ~camara.str.upper().isin(VALORES_CAMARA_INVALIDA)

    total_entradas = int((direccion == "ENTRADA").sum())
    total_salidas = int((direccion == "SALIDA").sum())

    detalle = pd.DataFrame(
        {"Ubicacion": ubicacion, "Sentido": direccion.str.title(), "Camara": camara},
        index=df.index,
    )
    por_ubicacion = (
        detalle.loc[mascara_direccion & mascara_ubicacion]
        .groupby(["Ubicacion", "Sentido"], as_index=False)
        .size()
        .rename(columns={"size": "Registros"})
    )

    detalle_camara = detalle.loc[mascara_direccion & mascara_camara].copy()
    detalle_camara.loc[~mascara_ubicacion, "Ubicacion"] = "Sin clasificar"
    por_camara = (
        detalle_camara.groupby(["Ubicacion", "Sentido", "Camara"], as_index=False)
        .size()
        .rename(columns={"size": "Registros"})
        .sort_values(["Ubicacion", "Sentido", "Camara"])
        .reset_index(drop=True)
    )

    diferencias = {
        "entradas_sin_ubicacion_valida": int(((direccion == "ENTRADA") & ~mascara_ubicacion).sum()),
        "salidas_sin_ubicacion_valida": int(((direccion == "SALIDA") & ~mascara_ubicacion).sum()),
        "entradas_sin_camara_valida": int(((direccion == "ENTRADA") & ~mascara_camara).sum()),
        "salidas_sin_camara_valida": int(((direccion == "SALIDA") & ~mascara_camara).sum()),
        "direccion_no_valida": int((~mascara_direccion).sum()),
    }
    return {
        "total_entradas": total_entradas,
        "total_salidas": total_salidas,
        "por_ubicacion": por_ubicacion[columnas_ubicacion],
        "por_camara": por_camara[columnas_camara],
        "diferencias": diferencias,
    }

def _metricas_temporales_por_hora(df_valido: pd.DataFrame) -> pd.DataFrame:
    """Métricas horarias sin confundir acumulados del período con una hora real.

    El denominador incluye todos los días con al menos un registro LPR válido
    dentro del contexto filtrado. Por tanto, una franja sin eventos en uno de
    esos días aporta 60 minutos con valor cero. No se infiere cobertura para
    días completamente ausentes del archivo.
    """
    columnas = [
        "Hora", "Registros", "Dias_considerados", "Minutos_considerados",
        "Promedio_registros_minuto", "Promedio_por_dia",
        "Maximo_real_por_minuto",
    ]
    if df_valido is None or df_valido.empty:
        return pd.DataFrame(columns=columnas)

    base = df_valido.copy()
    base["Fecha"] = pd.to_datetime(base.get("Fecha"), errors="coerce").dt.date
    base["Hora_Dia"] = pd.to_numeric(base.get("Hora_Dia"), errors="coerce")
    dias = int(base["Fecha"].dropna().nunique())
    validos_hora = base[base["Hora_Dia"].between(0, 23, inclusive="both")]
    conteo = validos_hora.groupby("Hora_Dia").size().rename("Registros")

    # El máximo real usa ventanas de minuto calendario observadas, no la suma
    # de esa misma hora a través de todos los días.
    hora_dt = pd.to_datetime(base.get("Hora"), errors="coerce")
    base["Minuto_observado"] = hora_dt.dt.floor("min")
    por_minuto = (
        base.dropna(subset=["Minuto_observado", "Hora_Dia"])
        .groupby(["Hora_Dia", "Minuto_observado"])
        .size()
    )
    maximos = por_minuto.groupby(level=0).max() if not por_minuto.empty else pd.Series(dtype="int64")

    resultado = pd.DataFrame({"Hora": range(24)})
    resultado["Registros"] = resultado["Hora"].map(conteo).fillna(0).astype(int)
    resultado["Dias_considerados"] = dias
    resultado["Minutos_considerados"] = dias * 60
    denominador_minutos = resultado["Minutos_considerados"].replace(0, np.nan)
    resultado["Promedio_registros_minuto"] = (
        resultado["Registros"] / denominador_minutos
    ).fillna(0).round(3)
    resultado["Promedio_por_dia"] = (
        resultado["Registros"] / (dias if dias else np.nan)
    ).fillna(0).round(2)
    resultado["Maximo_real_por_minuto"] = (
        resultado["Hora"].map(maximos).fillna(0).astype(int)
    )
    return resultado[columnas]


def stats_flujo_vehicular_por_hora(df_valido: pd.DataFrame) -> pd.DataFrame:
    return _metricas_temporales_por_hora(df_valido)

def stats_flujo_vehicular_top_periodos(df_valido: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    agrupado = _metricas_temporales_por_hora(df_valido)
    if agrupado.empty:
        return agrupado
    agrupado["Franja"] = agrupado["Hora"].apply(lambda h: f"{int(h)}:00–{(int(h)+1)%24}:00")
    agrupado = agrupado.sort_values(by="Registros", ascending=False).head(n)
    return agrupado

def stats_flujo_vehicular_por_acceso(df_valido: pd.DataFrame) -> pd.DataFrame:
    columnas = [
        "Punto_Acceso", "Hora_Pico", "Registros", "Dias_considerados",
        "Promedio_registros_minuto", "Promedio_por_dia", "Maximo_real_por_minuto",
    ]
    if df_valido is None or df_valido.empty:
        return pd.DataFrame(columns=columnas)
    dias = int(pd.to_datetime(df_valido["Fecha"], errors="coerce").dt.date.nunique())
    # Buscar hora pico por cada acceso
    agrupado = df_valido.groupby(["Punto_Acceso", "Hora_Dia"]).size().reset_index(name="Registros")
    
    idx_max = agrupado.groupby("Punto_Acceso")["Registros"].idxmax()
    top_por_acceso = agrupado.loc[idx_max].copy()
    
    top_por_acceso["Dias_considerados"] = dias
    top_por_acceso["Promedio_registros_minuto"] = (
        top_por_acceso["Registros"] / (dias * 60 if dias else np.nan)
    ).fillna(0).round(3)
    top_por_acceso["Promedio_por_dia"] = (
        top_por_acceso["Registros"] / (dias if dias else np.nan)
    ).fillna(0).round(2)

    minutos = df_valido.copy()
    minutos["Minuto_observado"] = pd.to_datetime(minutos["Hora"], errors="coerce").dt.floor("min")
    maximos = (
        minutos.dropna(subset=["Minuto_observado", "Hora_Dia"])
        .groupby(["Punto_Acceso", "Hora_Dia", "Minuto_observado"])
        .size()
        .groupby(level=[0, 1])
        .max()
    )
    top_por_acceso["Maximo_real_por_minuto"] = [
        int(maximos.get((fila.Punto_Acceso, fila.Hora_Dia), 0))
        for fila in top_por_acceso.itertuples()
    ]
    top_por_acceso["Hora_Pico"] = top_por_acceso["Hora_Dia"].apply(lambda h: f"{int(h)}:00–{(int(h)+1)%24}:00")
    
    top_por_acceso = top_por_acceso.sort_values(by="Registros", ascending=False)
    return top_por_acceso[columnas]

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
    conclusiones.append(
        f"Se analizaron {total:,} registros vehiculares, correspondientes a "
        f"{stats_gen.get('placas_unicas', 0):,} placas únicas."
    )
    duplicados = stats_gen.get("duplicados_descartados")
    if duplicados is not None:
        conclusiones.append(f"En el procesamiento completo se descartaron {duplicados:,} lecturas repetidas.")
    
    flujo_carril = calcular_flujo_real_por_carril(
        consolidar_eventos_vehiculares(pd.DataFrame(), df_valido)
    )
    if not flujo_carril.empty:
        hora_max = flujo_carril.loc[flujo_carril["Eventos_hora_pico"].idxmax()]
        minuto_max = flujo_carril.loc[flujo_carril["Maximo_observado_minuto"].idxmax()]
        conclusiones.append(
            f"La hora calendario de mayor actividad por carril fue {hora_max['Hora_pico']} en "
            f"{hora_max['Ubicacion']} {hora_max['Carril']}, con {int(hora_max['Eventos_hora_pico']):,} "
            f"eventos y un promedio de {hora_max['Promedio_hora_pico_min']:.2f} eventos por minuto."
        )
        conclusiones.append(
            f"El máximo observado en un minuto real fue de {int(minuto_max['Maximo_observado_minuto']):,} "
            f"eventos en {minuto_max['Ubicacion']} {minuto_max['Carril']} ({minuto_max['Minuto_maximo']})."
        )
            
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
    
    flujo_carril = calcular_flujo_real_por_carril(
        consolidar_eventos_vehiculares(pd.DataFrame(), df_valido)
    )
    if not flujo_carril.empty:
        hora_max = flujo_carril.loc[flujo_carril["Eventos_hora_pico"].idxmax()]
        minuto_max = flujo_carril.loc[flujo_carril["Maximo_observado_minuto"].idxmax()]
        texto += (
            f"La hora calendario de mayor actividad por carril fue **{hora_max['Hora_pico']}** en "
            f"**{hora_max['Ubicacion']} {hora_max['Carril']}**, con "
            f"**{int(hora_max['Eventos_hora_pico']):,} eventos** y una intensidad media de "
            f"**{hora_max['Promedio_hora_pico_min']:.2f} eventos por minuto**. El máximo real observado "
            f"fue **{int(minuto_max['Maximo_observado_minuto']):,} eventos en un minuto**, en "
            f"{minuto_max['Ubicacion']} {minuto_max['Carril']} ({minuto_max['Minuto_maximo']}).\n\n"
        )
    else:
        texto += (
            f"La mayor concentración de reconocimientos ocurrió el {dia_pico_str}, mientras que la franja horaria "
            f"con mayor actividad fue entre las {int(hora_pico):02d}:00 y {(int(hora_pico)+1)%24:02d}:00.\n\n"
        )

    texto += f"El acceso con mayor flujo fue {acceso_pico}.\n\n"
        
    return texto


def consolidar_eventos_vehiculares(
    df_biometricos: pd.DataFrame, df_lpr: pd.DataFrame
) -> pd.DataFrame:
    """Unifica eventos biométricos VEH y LPR sin deduplicar entre mecanismos.

    Reutiliza las dimensiones calculadas durante el procesamiento. El LPR
    recibido debe ser el conjunto depurado por ``deduplicar_eventos_vehiculares``.
    """
    columnas = [
        "Fecha", "Hora", "Hora_Dia", "Movimiento", "Ubicacion_Ingreso",
        "Mecanismo_Registro", "Categoria_Ingreso", "Punto_Acceso", "Carril",
        "Carril_ID", "Dispositivo",
    ]
    partes = []

    if df_biometricos is not None and not df_biometricos.empty:
        bio = df_biometricos.copy()
        if "Tipo_Flujo_Consolidado" in bio.columns:
            mascara_veh = bio["Tipo_Flujo_Consolidado"].eq("Vehicular")
        elif "Categoria_Ingreso" in bio.columns:
            mascara_veh = bio["Categoria_Ingreso"].astype(str).str.contains(
                "Vehicular por biométrico", case=False, na=False
            )
        else:
            acceso = bio.get("Punto de acceso", pd.Series(index=bio.index, dtype="object"))
            mascara_veh = acceso.astype(str).str.contains("VEH", case=False, na=False)
        bio = bio.loc[mascara_veh].copy()
        if not bio.empty:
            bio["Mecanismo_Registro"] = "Biométrico VEH"
            bio["Punto_Acceso"] = bio.get("Punto de acceso", bio.get("Categoria_Ingreso", ""))
            bio["Dispositivo"] = bio.get("Device Name", bio["Punto_Acceso"])
            if "Carril" not in bio.columns:
                carriles = bio.apply(
                    lambda fila: clasificar_carril_vehicular(
                        fila["Punto_Acceso"], fila.get("Ubicacion_Ingreso"), fila.get("Movimiento")
                    ), axis=1
                )
                bio["Carril"] = carriles.apply(lambda x: x["Carril"])
                bio["Carril_ID"] = carriles.apply(lambda x: x["Carril_ID"])
            for columna in columnas:
                if columna not in bio.columns:
                    bio[columna] = pd.NA
            partes.append(bio[columnas])

    if df_lpr is not None and not df_lpr.empty:
        lpr = df_lpr.copy()
        direccion = lpr.get("Direccion", pd.Series("OTRO", index=lpr.index))
        lpr["Movimiento"] = direccion.astype(str).str.upper()
        lpr["Mecanismo_Registro"] = "LPR"
        lpr["Punto_Acceso"] = lpr.get("Camara", lpr.get("Punto_Acceso", ""))
        lpr["Dispositivo"] = lpr["Punto_Acceso"]
        if "Carril" not in lpr.columns:
            carriles = lpr.apply(
                lambda fila: clasificar_carril_vehicular(
                    fila["Punto_Acceso"], fila.get("Ubicacion_Ingreso"), fila.get("Movimiento")
                ), axis=1
            )
            lpr["Carril"] = carriles.apply(lambda x: x["Carril"])
            lpr["Carril_ID"] = carriles.apply(lambda x: x["Carril_ID"])
        for columna in columnas:
            if columna not in lpr.columns:
                lpr[columna] = pd.NA
        partes.append(lpr[columnas])

    if not partes:
        return pd.DataFrame(columns=columnas)

    consolidado = pd.concat(partes, ignore_index=True)
    consolidado["Movimiento"] = consolidado["Movimiento"].astype(str).str.upper()
    consolidado["Fecha"] = pd.to_datetime(consolidado["Fecha"], errors="coerce").dt.date
    consolidado["Hora"] = pd.to_datetime(consolidado["Hora"], errors="coerce")
    consolidado["Hora_Dia"] = pd.to_numeric(consolidado["Hora_Dia"], errors="coerce")
    return consolidado


def calcular_flujo_real_por_carril(df_vehicular: pd.DataFrame) -> pd.DataFrame:
    """Calcula intensidad por carril usando minutos y horas calendario reales.

    La hora pico es una fecha y hora concretas. ``Promedio_hora_pico_min`` es
    el total de esa hora dividido para 60, incluidos sus minutos sin eventos.
    """
    columnas = [
        "Mecanismo", "Ubicacion", "Carril", "Sentido", "Eventos",
        "Fecha_mayor_actividad", "Eventos_fecha_pico", "Hora_pico_inicio",
        "Hora_pico", "Eventos_hora_pico", "Promedio_hora_pico_min",
        "Minuto_maximo_inicio", "Minuto_maximo", "Maximo_observado_minuto",
        "Dias_con_datos_mecanismo", "Promedio_diario_sentido",
    ]
    if df_vehicular is None or df_vehicular.empty:
        return pd.DataFrame(columns=columnas)

    df = df_vehicular.copy()
    df["Hora"] = pd.to_datetime(df.get("Hora"), errors="coerce")
    df = df.dropna(subset=["Hora"])
    if df.empty:
        return pd.DataFrame(columns=columnas)
    if "Carril" not in df.columns:
        df["Carril"] = "Sin clasificar"
    dias_mecanismo = (
        df[df["Mecanismo_Registro"].isin(["Biométrico VEH", "LPR"])]
        .assign(Fecha_calendario=lambda x: x["Hora"].dt.date)
        .groupby("Mecanismo_Registro")["Fecha_calendario"]
        .nunique()
    )
    validos = df[
        df["Mecanismo_Registro"].isin(["Biométrico VEH", "LPR"])
        & df["Ubicacion_Ingreso"].isin(UBICACIONES_LPR_VALIDAS)
        & df["Movimiento"].isin(DIRECCIONES_LPR_VALIDAS)
        & df["Carril"].isin(["E1", "E2", "S1", "S2"])
    ].copy()
    if validos.empty:
        return pd.DataFrame(columns=columnas)

    claves = ["Mecanismo_Registro", "Ubicacion_Ingreso", "Carril", "Movimiento"]
    validos["Minuto"] = validos["Hora"].dt.floor("min")
    validos["Hora_calendario"] = validos["Hora"].dt.floor("h")
    validos["Fecha_calendario"] = validos["Hora"].dt.date

    filas = []
    for clave, parte in validos.groupby(claves, sort=True):
        mecanismo, ubicacion, carril, sentido = clave
        por_minuto = parte.groupby("Minuto").size()
        minuto_pico = por_minuto.idxmax()
        por_hora = parte.groupby("Hora_calendario").size()
        hora_pico = por_hora.idxmax()
        por_fecha = parte.groupby("Fecha_calendario").size()
        fecha_pico = por_fecha.idxmax()
        dias = int(dias_mecanismo.get(mecanismo, 0))
        eventos = int(len(parte))
        filas.append({
            "Mecanismo": mecanismo,
            "Ubicacion": ubicacion,
            "Carril": carril,
            "Sentido": sentido.title(),
            "Eventos": eventos,
            "Fecha_mayor_actividad": fecha_pico,
            "Eventos_fecha_pico": int(por_fecha.max()),
            "Hora_pico_inicio": hora_pico,
            "Hora_pico": f"{hora_pico:%d/%m/%Y %H}:00–{(hora_pico + pd.Timedelta(hours=1)):%H}:00",
            "Eventos_hora_pico": int(por_hora.max()),
            "Promedio_hora_pico_min": float(por_hora.max() / 60),
            "Minuto_maximo_inicio": minuto_pico,
            "Minuto_maximo": f"{minuto_pico:%d/%m/%Y %H:%M}–{(minuto_pico + pd.Timedelta(minutes=1)):%H:%M}",
            "Maximo_observado_minuto": int(por_minuto.max()),
            "Dias_con_datos_mecanismo": dias,
            "Promedio_diario_sentido": float(eventos / dias) if dias else 0.0,
        })
    return pd.DataFrame(filas, columns=columnas).sort_values(
        ["Mecanismo", "Ubicacion", "Sentido", "Carril"]
    ).reset_index(drop=True)


def calcular_caudal_conjunto_por_acceso(df_vehicular: pd.DataFrame) -> pd.DataFrame:
    """Alinea carriles por minuto antes de calcular el caudal del acceso."""
    columnas = [
        "Mecanismo", "Ubicacion", "Sentido", "Carriles", "Eventos",
        "Minuto_maximo_inicio", "Minuto_maximo", "Caudal_maximo_eventos_min",
        "Promedio_por_carril_en_minuto_maximo", "Hora_pico_inicio", "Hora_pico",
        "Eventos_hora_pico", "Promedio_conjunto_hora_pico_min",
        "Promedio_por_carril_hora_pico_min",
    ]
    if df_vehicular is None or df_vehicular.empty:
        return pd.DataFrame(columns=columnas)
    df = df_vehicular.copy()
    df["Hora"] = pd.to_datetime(df.get("Hora"), errors="coerce")
    if "Carril" not in df.columns:
        df["Carril"] = "Sin clasificar"
    df = df[
        df["Hora"].notna()
        & df["Mecanismo_Registro"].isin(["Biométrico VEH", "LPR"])
        & df["Ubicacion_Ingreso"].isin(UBICACIONES_LPR_VALIDAS)
        & df["Movimiento"].isin(DIRECCIONES_LPR_VALIDAS)
        & df["Carril"].isin(["E1", "E2", "S1", "S2"])
    ].copy()
    if df.empty:
        return pd.DataFrame(columns=columnas)
    df["Minuto"] = df["Hora"].dt.floor("min")
    df["Hora_calendario"] = df["Hora"].dt.floor("h")
    filas = []
    for (mecanismo, ubicacion, movimiento), parte in df.groupby(
        ["Mecanismo_Registro", "Ubicacion_Ingreso", "Movimiento"], sort=True
    ):
        carriles = sorted(parte["Carril"].unique())
        alineado = parte.groupby(["Minuto", "Carril"]).size().unstack(fill_value=0)
        alineado = alineado.reindex(columns=carriles, fill_value=0)
        total_minuto = alineado.sum(axis=1)
        minuto_pico = total_minuto.idxmax()
        por_hora = parte.groupby("Hora_calendario").size()
        hora_pico = por_hora.idxmax()
        numero_carriles = len(carriles)
        filas.append({
            "Mecanismo": mecanismo,
            "Ubicacion": ubicacion,
            "Sentido": movimiento.title(),
            "Carriles": ", ".join(carriles),
            "Eventos": int(len(parte)),
            "Minuto_maximo_inicio": minuto_pico,
            "Minuto_maximo": f"{minuto_pico:%d/%m/%Y %H:%M}–{(minuto_pico + pd.Timedelta(minutes=1)):%H:%M}",
            "Caudal_maximo_eventos_min": int(total_minuto.max()),
            "Promedio_por_carril_en_minuto_maximo": float(total_minuto.max() / numero_carriles),
            "Hora_pico_inicio": hora_pico,
            "Hora_pico": f"{hora_pico:%d/%m/%Y %H}:00–{(hora_pico + pd.Timedelta(hours=1)):%H}:00",
            "Eventos_hora_pico": int(por_hora.max()),
            "Promedio_conjunto_hora_pico_min": float(por_hora.max() / 60),
            "Promedio_por_carril_hora_pico_min": float(por_hora.max() / (60 * numero_carriles)),
        })
    return pd.DataFrame(filas, columns=columnas)


def calcular_estadisticas_vehiculares_consolidadas(df_vehicular: pd.DataFrame) -> dict:
    """Calcula indicadores comparables manteniendo separados ambos mecanismos."""
    mecanismos = ["Biométrico VEH", "LPR"]
    columnas_diario = [
        "Fecha", "Dia_Semana", "Entradas biométrico VEH", "Entradas LPR",
        "Total registros de entrada",
    ]
    columnas_ubicacion = ["Ubicacion", "Movimiento", "Mecanismo", "Registros"]
    columnas_periodos = ["Mecanismo", "Rango", "Franja", "Registros"]
    vacio = {
        "entradas": {"Biométrico VEH": 0, "LPR": 0, "Consolidado": 0},
        "salidas": {"Biométrico VEH": 0, "LPR": 0, "Consolidado": 0},
        "dias": {"Biométrico VEH": 0, "LPR": 0, "Consolidado": 0},
        "promedios": {"Biométrico VEH": 0.0, "LPR": 0.0, "Consolidado": 0.0},
        "diario": pd.DataFrame(columns=columnas_diario),
        "por_ubicacion": pd.DataFrame(columns=columnas_ubicacion),
        "periodos_pico": pd.DataFrame(columns=columnas_periodos),
        "flujo_por_carril": calcular_flujo_real_por_carril(pd.DataFrame()),
        "caudal_por_acceso": calcular_caudal_conjunto_por_acceso(pd.DataFrame()),
        "direccion_no_valida": 0,
        "ubicacion_no_valida": 0,
    }
    if df_vehicular is None or df_vehicular.empty:
        return vacio

    df = df_vehicular[df_vehicular["Mecanismo_Registro"].isin(mecanismos)].copy()
    if df.empty:
        return vacio

    entradas = {}
    salidas = {}
    dias = {}
    for mecanismo in mecanismos:
        parte = df[df["Mecanismo_Registro"] == mecanismo]
        entradas[mecanismo] = int((parte["Movimiento"] == "ENTRADA").sum())
        salidas[mecanismo] = int((parte["Movimiento"] == "SALIDA").sum())
        dias[mecanismo] = int(parte["Fecha"].dropna().nunique())
    entradas["Consolidado"] = sum(entradas.values())
    salidas["Consolidado"] = sum(salidas.values())
    dias["Consolidado"] = int(df["Fecha"].dropna().nunique())
    promedios = {
        mecanismo: entradas[mecanismo] / dias[mecanismo] if dias[mecanismo] else 0.0
        for mecanismo in [*mecanismos, "Consolidado"]
    }

    fechas = pd.Index(sorted(df["Fecha"].dropna().unique()), name="Fecha")
    eventos_entrada = df[df["Movimiento"] == "ENTRADA"]
    if eventos_entrada.empty:
        diario_base = pd.DataFrame(0, index=fechas, columns=mecanismos)
    else:
        diario_base = (
            eventos_entrada.groupby(["Fecha", "Mecanismo_Registro"])
            .size()
            .unstack(fill_value=0)
            .reindex(index=fechas, columns=mecanismos, fill_value=0)
        )
    diario = diario_base.rename(
        columns={"Biométrico VEH": "Entradas biométrico VEH", "LPR": "Entradas LPR"}
    ).reset_index()
    diario.insert(
        1,
        "Dia_Semana",
        pd.to_datetime(diario["Fecha"]).dt.dayofweek.map(DIAS_SEMANA_MAP),
    )
    diario["Total registros de entrada"] = (
        diario["Entradas biométrico VEH"] + diario["Entradas LPR"]
    )

    ubicaciones_validas = ["25 de Junio", "Ferroviaria"]
    por_ubicacion = (
        df[
            df["Ubicacion_Ingreso"].isin(ubicaciones_validas)
            & df["Movimiento"].isin(DIRECCIONES_LPR_VALIDAS)
        ]
        .groupby(["Ubicacion_Ingreso", "Movimiento", "Mecanismo_Registro"], as_index=False)
        .size()
        .rename(
            columns={
                "Ubicacion_Ingreso": "Ubicacion",
                "Mecanismo_Registro": "Mecanismo",
                "size": "Registros",
            }
        )
    )

    periodos = []
    for mecanismo in mecanismos:
        parte = df[df["Mecanismo_Registro"] == mecanismo]
        conteo = parte.dropna(subset=["Hora_Dia"]).groupby("Hora_Dia").size()
        for rango, (hora, registros) in enumerate(conteo.nlargest(5).items(), start=1):
            periodos.append({
                "Mecanismo": mecanismo,
                "Rango": rango,
                "Franja": f"{int(hora):02d}:00–{(int(hora) + 1) % 24:02d}:00",
                "Registros": int(registros),
            })
    conteo_total = df.dropna(subset=["Hora_Dia"]).groupby("Hora_Dia").size()
    for rango, (hora, registros) in enumerate(conteo_total.nlargest(5).items(), start=1):
        periodos.append({
            "Mecanismo": "Consolidado",
            "Rango": rango,
            "Franja": f"{int(hora):02d}:00–{(int(hora) + 1) % 24:02d}:00",
            "Registros": int(registros),
        })

    return {
        "entradas": entradas,
        "salidas": salidas,
        "dias": dias,
        "promedios": promedios,
        "diario": diario[columnas_diario],
        "por_ubicacion": por_ubicacion[columnas_ubicacion],
        "periodos_pico": pd.DataFrame(periodos, columns=columnas_periodos),
        "flujo_por_carril": calcular_flujo_real_por_carril(df),
        "caudal_por_acceso": calcular_caudal_conjunto_por_acceso(df),
        "direccion_no_valida": int((~df["Movimiento"].isin(DIRECCIONES_LPR_VALIDAS)).sum()),
        "ubicacion_no_valida": int((~df["Ubicacion_Ingreso"].isin(ubicaciones_validas)).sum()),
    }


def generar_huella_movilidad(df_peatones: pd.DataFrame, df_vehiculos: pd.DataFrame) -> dict:
    tot_registros = 0
    tot_peatones_puros = 0
    tot_terminales_veh = 0
    tot_lpr = 0
    tot_biometricos_sin_clasificar = 0
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
        
        if "Tipo_Flujo_Consolidado" in df_peatones.columns:
            clasificacion = df_peatones["Tipo_Flujo_Consolidado"].astype(str)
            tot_terminales_veh = int(clasificacion.eq("Vehicular").sum())
            tot_peatones_puros = int(clasificacion.eq("Peatonal").sum())
            tot_biometricos_sin_clasificar = int(
                len(df_peatones) - tot_terminales_veh - tot_peatones_puros
            )
        elif col_acceso_p:
            mask_veh = df_peatones[col_acceso_p].astype(str).str.contains("VEH", case=False, na=False)
            tot_terminales_veh = int(mask_veh.sum())
            # Sin la clasificación normalizada solo puede inferirse la clase
            # vehicular; el resto se conserva como no clasificado.
            tot_biometricos_sin_clasificar = int(len(df_peatones) - tot_terminales_veh)
            tot_peatones_puros = 0
            
        else:
            tot_biometricos_sin_clasificar = len(df_peatones)

        if col_acceso_p and "Fecha" in df_peatones.columns and "Hora" in df_peatones.columns:
            df_p = df_peatones[["Fecha", "Hora", col_acceso_p]].copy()
            df_p.rename(columns={col_acceso_p: "Punto_Acceso"}, inplace=True)
            df_combined = pd.concat([df_combined, df_p])
            
    # 2. Analizar LPR
    if df_vehiculos is not None and not df_vehiculos.empty:
        tot_lpr = len(df_vehiculos)
        tot_registros += tot_lpr
        
        # Placas reconocidas (asumiendo que DESCONOCIDO o vacíos son no reconocidas)
        if "Matricula" in df_vehiculos.columns:
            matricula = df_vehiculos["Matricula"].astype(str).str.strip().str.upper()
            df_reconocidas = df_vehiculos[
                ~matricula.isin({"", "NAN", "NONE", "NULL", "DESCONOCIDO", "NO PLATE", "SIN PLACA"})
            ]
            placas_reconocidas = len(df_reconocidas)
            placas_unicas = df_reconocidas["Matricula"].nunique()
            
        col_acceso_v = None
        for col in ["Camara", "Punto_Acceso", "Punto de acceso", "Punto Acceso", "Punto", "Acceso"]:
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

    eventos_vehiculares = consolidar_eventos_vehiculares(df_peatones, df_vehiculos)
    if not eventos_vehiculares.empty:
        tot_terminales_veh = int(
            (eventos_vehiculares["Mecanismo_Registro"] == "Biométrico VEH").sum()
        )
        tot_lpr = int((eventos_vehiculares["Mecanismo_Registro"] == "LPR").sum())
        total_biometricos = len(df_peatones) if df_peatones is not None else 0
        if df_peatones is not None and "Tipo_Flujo_Consolidado" in df_peatones.columns:
            clasificacion = df_peatones["Tipo_Flujo_Consolidado"].astype(str)
            tot_peatones_puros = int(clasificacion.eq("Peatonal").sum())
            tot_biometricos_sin_clasificar = max(
                0, total_biometricos - tot_terminales_veh - tot_peatones_puros
            )

    # Cálculos de porcentajes
    pct_peatones_puros = round((tot_peatones_puros / tot_registros) * 100, 1) if tot_registros > 0 else 0
    pct_terminales_veh = round((tot_terminales_veh / tot_registros) * 100, 1) if tot_registros > 0 else 0
    pct_lpr = round((tot_lpr / tot_registros) * 100, 1) if tot_registros > 0 else 0
    pct_biometricos_sin_clasificar = round(
        (tot_biometricos_sin_clasificar / tot_registros) * 100, 1
    ) if tot_registros > 0 else 0

    return {
        "tot_registros": tot_registros,
        "tot_peatones_puros": tot_peatones_puros,
        "tot_terminales_veh": tot_terminales_veh,
        "tot_lpr": tot_lpr,
        "tot_biometricos_sin_clasificar": tot_biometricos_sin_clasificar,
        "pct_peatones_puros": pct_peatones_puros,
        "pct_terminales_veh": pct_terminales_veh,
        "pct_lpr": pct_lpr,
        "pct_biometricos_sin_clasificar": pct_biometricos_sin_clasificar,
        "placas_reconocidas": placas_reconocidas,
        "placas_unicas": placas_unicas,
        "dia_pico_str": dia_pico_str,
        "hora_pico_str": hora_pico_str,
        "acceso_pico_str": acceso_pico_str,
        "eventos_vehiculares": eventos_vehiculares,
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
