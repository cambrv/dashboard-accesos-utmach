"""
Módulo de cálculo de estadísticas.
Genera todas las estadísticas obligatorias definidas en REPORTES_ACCESOS_REGLAS.md.
Trabaja con datos agregados para rendimiento óptimo.
"""

import pandas as pd
import numpy as np
from access_names import obtener_nombre_amigable
from config import (
    RANGOS_FRECUENCIA,
    DIAS_SEMANA_ORDEN,
    DECIMALES_PORCENTAJE,
    MOVIMIENTO_ENTRADA,
    MOVIMIENTO_SALIDA,
)


# ─── 9.2 Flujo por punto de acceso ──────────────────────────────────────────
def flujo_por_punto_acceso(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera tabla de flujo por punto de acceso con eventos, porcentaje,
    ingreso, movimiento y usuarios únicos. Ordenado de mayor a menor.
    """
    total = len(df)
    grupo = df.groupby("Punto de acceso").agg(
        Eventos=("Hora", "count"),
        Ingreso=("Ingreso", "first"),
        Movimiento=("Movimiento", "first"),
        Usuarios_Unicos=("Persona", lambda x: x[x != ""].nunique()),
    ).reset_index()
    grupo["Porcentaje"] = (grupo["Eventos"] / total * 100).round(DECIMALES_PORCENTAJE)
    grupo = grupo.sort_values("Eventos", ascending=False).reset_index(drop=True)
    grupo.index = grupo.index + 1
    grupo.index.name = "Ranking"
    grupo["Punto de acceso"] = grupo["Punto de acceso"].apply(obtener_nombre_amigable)
    return grupo


# ─── 9.3 Flujo por hora ─────────────────────────────────────────────────────
def flujo_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Eventos agrupados por hora del día (0-23)."""
    grupo = df.groupby("Hora_Dia").agg(
        Eventos=("Hora", "count"),
        Usuarios_Unicos=("Persona", lambda x: x[x != ""].nunique()),
    ).reset_index()
    grupo = grupo.rename(columns={"Hora_Dia": "Hora"})
    # Asegurar todas las horas 0-23
    todas_horas = pd.DataFrame({"Hora": range(24)})
    grupo = todas_horas.merge(grupo, on="Hora", how="left").fillna(0)
    grupo["Eventos"] = grupo["Eventos"].astype(int)
    grupo["Usuarios_Unicos"] = grupo["Usuarios_Unicos"].astype(int)
    return grupo


def horas_pico(df: pd.DataFrame) -> dict:
    """Identifica las horas pico general, de entrada y de salida."""
    resultado = {}

    # Hora pico general
    conteo_hora = df.groupby("Hora_Dia").size()
    max_val = conteo_hora.max()
    horas_max = conteo_hora[conteo_hora == max_val].index.tolist()
    resultado["general"] = {
        "horas": horas_max,
        "eventos": int(max_val),
        "empate": len(horas_max) > 1,
    }

    # Hora pico menor flujo
    min_val = conteo_hora[conteo_hora > 0].min()
    horas_min = conteo_hora[conteo_hora == min_val].index.tolist()
    resultado["menor_flujo"] = {
        "horas": horas_min,
        "eventos": int(min_val),
        "empate": len(horas_min) > 1,
    }

    # Hora pico de entrada
    entradas = df[df["Movimiento"] == MOVIMIENTO_ENTRADA]
    if len(entradas) > 0:
        conteo_entrada = entradas.groupby("Hora_Dia").size()
        max_e = conteo_entrada.max()
        horas_e = conteo_entrada[conteo_entrada == max_e].index.tolist()
        resultado["entrada"] = {
            "horas": horas_e,
            "eventos": int(max_e),
            "empate": len(horas_e) > 1,
        }

    # Hora pico de salida
    salidas = df[df["Movimiento"] == MOVIMIENTO_SALIDA]
    if len(salidas) > 0:
        conteo_salida = salidas.groupby("Hora_Dia").size()
        max_s = conteo_salida.max()
        horas_s = conteo_salida[conteo_salida == max_s].index.tolist()
        resultado["salida"] = {
            "horas": horas_s,
            "eventos": int(max_s),
            "empate": len(horas_s) > 1,
        }

    # Hora pico por ingreso
    resultado["por_ingreso"] = {}
    for ingreso in df["Ingreso"].unique():
        sub = df[df["Ingreso"] == ingreso]
        conteo_c = sub.groupby("Hora_Dia").size()
        max_c = conteo_c.max()
        horas_c = conteo_c[conteo_c == max_c].index.tolist()
        resultado["por_ingreso"][ingreso] = {
            "horas": horas_c,
            "eventos": int(max_c),
            "empate": len(horas_c) > 1,
        }

    # Hora pico por punto de acceso
    resultado["por_punto"] = {}
    for punto in df["Punto de acceso"].unique():
        sub = df[df["Punto de acceso"] == punto]
        conteo_p = sub.groupby("Hora_Dia").size()
        max_p = conteo_p.max()
        horas_p = conteo_p[conteo_p == max_p].index.tolist()
        nombre_amigable = obtener_nombre_amigable(punto)
        resultado["por_punto"][nombre_amigable] = {
            "horas": horas_p,
            "eventos": int(max_p),
            "empate": len(horas_p) > 1,
        }

    return resultado


# ─── 9.4 Flujo por punto de acceso y hora ───────────────────────────────────
def flujo_punto_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz de punto de acceso × hora con cantidad de eventos."""
    pivot = df.pivot_table(
        index="Punto de acceso",
        columns="Hora_Dia",
        values="Hora",
        aggfunc="count",
        fill_value=0,
    )
    # Asegurar todas las columnas 0-23
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]
    pivot.index = pivot.index.map(obtener_nombre_amigable)
    return pivot


# ─── 9.5 Entradas vs salidas ────────────────────────────────────────────────
def entradas_vs_salidas_general(df: pd.DataFrame) -> pd.DataFrame:
    """Comparación general de entradas vs salidas."""
    total = len(df)
    grupo = df.groupby("Movimiento").agg(
        Eventos=("Hora", "count"),
    ).reset_index()
    grupo["Porcentaje"] = (grupo["Eventos"] / total * 100).round(DECIMALES_PORCENTAJE)
    return grupo.sort_values("Eventos", ascending=False)


def entradas_vs_salidas_por_ingreso(df: pd.DataFrame) -> pd.DataFrame:
    """Entradas vs salidas desglosadas por ingreso."""
    grupo = df.groupby(["Ingreso", "Movimiento"]).size().reset_index(name="Eventos")
    total_ingreso = df.groupby("Ingreso").size().reset_index(name="Total_Ingreso")
    grupo = grupo.merge(total_ingreso, on="Ingreso")
    grupo["Porcentaje"] = (grupo["Eventos"] / grupo["Total_Ingreso"] * 100).round(DECIMALES_PORCENTAJE)
    return grupo


def entradas_vs_salidas_por_punto(df: pd.DataFrame) -> pd.DataFrame:
    """Entradas vs salidas por punto de acceso."""
    grupo = df.groupby(["Punto de acceso", "Movimiento"]).agg(
        Eventos=("Hora", "count"),
        Usuarios_Unicos=("Persona", lambda x: x[x != ""].nunique()),
    ).reset_index()
    grupo["Punto de acceso"] = grupo["Punto de acceso"].apply(obtener_nombre_amigable)
    return grupo.sort_values(["Punto de acceso", "Eventos"], ascending=[True, False])


def entradas_vs_salidas_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Entradas vs salidas por hora del día."""
    grupo = df.groupby(["Hora_Dia", "Movimiento"]).size().reset_index(name="Eventos")
    return grupo


# ─── 9.6 Flujo por ingreso ──────────────────────────────────────────────────
def flujo_por_ingreso(df: pd.DataFrame) -> pd.DataFrame:
    """Flujo agrupado por ingreso."""
    total = len(df)
    grupo = df.groupby("Ingreso").agg(
        Eventos=("Hora", "count"),
        Usuarios_Unicos=("Persona", lambda x: x[x != ""].nunique()),
    ).reset_index()
    grupo["Porcentaje"] = (grupo["Eventos"] / total * 100).round(DECIMALES_PORCENTAJE)
    return grupo.sort_values("Eventos", ascending=False)


# ─── 9.7 Flujo por tipo de usuario ──────────────────────────────────────────
def flujo_por_tipo_usuario(df: pd.DataFrame) -> pd.DataFrame:
    """Flujo agrupado por tipo de usuario."""
    total = len(df)
    grupo = df.groupby("Tipo_Usuario").agg(
        Eventos=("Hora", "count"),
        Usuarios_Unicos=("Persona", lambda x: x[x != ""].nunique()),
    ).reset_index()
    grupo["Porcentaje"] = (grupo["Eventos"] / total * 100).round(DECIMALES_PORCENTAJE)
    return grupo.sort_values("Eventos", ascending=False)


# ─── 9.8 Tipo de usuario + ingreso ──────────────────────────────────────────
def tipo_usuario_ingreso(df: pd.DataFrame) -> pd.DataFrame:
    """Cruce de Ingreso × Tipo_Usuario."""
    total = len(df)
    grupo = df.groupby(["Ingreso", "Tipo_Usuario"]).size().reset_index(name="Eventos")
    grupo["Porcentaje"] = (grupo["Eventos"] / total * 100).round(DECIMALES_PORCENTAJE)
    return grupo.sort_values("Eventos", ascending=False)


# ─── 9.9 Flujo diario ───────────────────────────────────────────────────────
def flujo_diario(df: pd.DataFrame) -> pd.DataFrame:
    """Eventos y usuarios únicos por fecha."""
    grupo = df.groupby("Fecha").agg(
        Eventos=("Hora", "count"),
        Usuarios_Unicos=("Persona", lambda x: x[x != ""].nunique()),
    ).reset_index()
    grupo = grupo.sort_values("Fecha")
    return grupo


def flujo_diario_por_ingreso(df: pd.DataFrame) -> pd.DataFrame:
    """Eventos por fecha desglosados por ingreso."""
    grupo = df.groupby(["Fecha", "Ingreso"]).size().reset_index(name="Eventos")
    return grupo.sort_values("Fecha")


def dias_pico(df: pd.DataFrame) -> dict:
    """Identifica los días con mayor y menor flujo."""
    diario = df.groupby("Fecha").size()
    resultado = {}

    # Mayor flujo
    max_val = diario.max()
    dias_max = diario[diario == max_val].index.tolist()
    resultado["mayor_flujo"] = {"dias": dias_max, "eventos": int(max_val)}

    # Menor flujo
    min_val = diario.min()
    dias_min = diario[diario == min_val].index.tolist()
    resultado["menor_flujo"] = {"dias": dias_min, "eventos": int(min_val)}

    # Mayor entrada
    entradas = df[df["Movimiento"] == MOVIMIENTO_ENTRADA].groupby("Fecha").size()
    if len(entradas) > 0:
        max_e = entradas.max()
        resultado["mayor_entrada"] = {
            "dias": entradas[entradas == max_e].index.tolist(),
            "eventos": int(max_e),
        }

    # Mayor salida
    salidas = df[df["Movimiento"] == MOVIMIENTO_SALIDA].groupby("Fecha").size()
    if len(salidas) > 0:
        max_s = salidas.max()
        resultado["mayor_salida"] = {
            "dias": salidas[salidas == max_s].index.tolist(),
            "eventos": int(max_s),
        }

    return resultado


# ─── 9.10 Día de la semana ──────────────────────────────────────────────────
def flujo_dia_semana(df: pd.DataFrame) -> pd.DataFrame:
    """Flujo por día de la semana con total y promedio."""
    grupo = df.groupby("Dia_Semana").agg(
        Eventos=("Hora", "count"),
    ).reset_index()

    # Contar cuántas veces aparece cada día de la semana en el dataset
    dias_por_semana = df.groupby("Dia_Semana")["Fecha"].nunique().reset_index(name="Ocurrencias")
    grupo = grupo.merge(dias_por_semana, on="Dia_Semana")
    grupo["Promedio"] = (grupo["Eventos"] / grupo["Ocurrencias"]).round(1)

    # Ordenar por día de la semana
    cat = pd.CategoricalDtype(categories=DIAS_SEMANA_ORDEN, ordered=True)
    grupo["Dia_Semana"] = grupo["Dia_Semana"].astype(cat)
    grupo = grupo.sort_values("Dia_Semana").reset_index(drop=True)
    return grupo


# ─── 9.11 Día + hora (heatmap) ──────────────────────────────────────────────
def heatmap_dia_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz de Día de semana × Hora con cantidad de eventos."""
    pivot = df.pivot_table(
        index="Dia_Semana",
        columns="Hora_Dia",
        values="Hora",
        aggfunc="count",
        fill_value=0,
    )
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]
    # Reordenar filas
    dias_presentes = [d for d in DIAS_SEMANA_ORDEN if d in pivot.index]
    pivot = pivot.reindex(dias_presentes)
    return pivot


# ─── 9.12 Ingreso + hora ────────────────────────────────────────────────────
def ingreso_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Flujo horario comparativo por ingreso."""
    grupo = df.groupby(["Ingreso", "Hora_Dia"]).size().reset_index(name="Eventos")
    return grupo


# ─── 9.13 Punto de acceso + tipo de usuario ─────────────────────────────────
def punto_tipo_usuario(df: pd.DataFrame) -> pd.DataFrame:
    """Qué tipos de usuarios utilizan más cada acceso."""
    grupo = df.groupby(["Punto de acceso", "Tipo_Usuario"]).size().reset_index(name="Eventos")
    grupo["Punto de acceso"] = grupo["Punto de acceso"].apply(obtener_nombre_amigable)
    return grupo.sort_values(["Punto de acceso", "Eventos"], ascending=[True, False])


# ─── 9.14 Punto de acceso + entrada/salida ──────────────────────────────────
def punto_movimiento(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada punto: tipo de movimiento, eventos, usuarios únicos."""
    grupo = df.groupby(["Punto de acceso", "Movimiento"]).agg(
        Eventos=("Hora", "count"),
        Usuarios_Unicos=("Persona", lambda x: x[x != ""].nunique()),
    ).reset_index()
    grupo["Punto de acceso"] = grupo["Punto de acceso"].apply(obtener_nombre_amigable)
    return grupo.sort_values(["Punto de acceso", "Eventos"], ascending=[True, False])


# ─── 11. Frecuencia de utilización ──────────────────────────────────────────
def frecuencia_utilizacion(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calcula la distribución de frecuencia de uso por persona.
    Retorna:
        - Tabla de distribución por rangos
        - Top usuarios por frecuencia (sin nombres, solo estadísticas)
    """
    # Filtrar personas con identificador válido
    personas = df[df["Persona"] != ""].groupby("Persona").size().reset_index(name="Eventos")

    # Distribución por rangos
    rangos_data = []
    for inicio, fin, etiqueta in RANGOS_FRECUENCIA:
        if fin == float("inf"):
            count = int((personas["Eventos"] >= inicio).sum())
        else:
            count = int(((personas["Eventos"] >= inicio) & (personas["Eventos"] <= fin)).sum())
        rangos_data.append({"Rango": etiqueta, "Usuarios": count})

    rangos_df = pd.DataFrame(rangos_data)

    # Estadísticas de frecuencia
    stats = pd.DataFrame({
        "Métrica": [
            "Promedio de eventos por usuario",
            "Mediana de eventos por usuario",
            "Máximo de eventos por usuario",
            "Mínimo de eventos por usuario",
            "Desviación estándar",
        ],
        "Valor": [
            round(personas["Eventos"].mean(), 2),
            round(personas["Eventos"].median(), 2),
            int(personas["Eventos"].max()),
            int(personas["Eventos"].min()),
            round(personas["Eventos"].std(), 2),
        ],
    })

    return rangos_df, stats


# ─── Conclusiones automáticas ───────────────────────────────────────────────
def generar_conclusiones(df: pd.DataFrame, metricas: dict) -> list[str]:
    """
    Genera conclusiones/hallazgos automáticos basados en datos observados.
    Distingue entre dato observado e interpretación.
    No afirma causalidad.
    """
    conclusiones = []
    total = len(df)

    # 1. Volumen general
    conclusiones.append(
        f"Se registraron **{total:,}** eventos normales correspondientes a "
        f"**{metricas['usuarios_unicos']:,}** usuarios únicos en el período "
        f"del **{metricas['fecha_inicial'].strftime('%d/%m/%Y')}** al "
        f"**{metricas['fecha_final'].strftime('%d/%m/%Y')}**."
    )

    # 2. Promedio diario
    conclusiones.append(
        f"El promedio diario de eventos fue de **{metricas['promedio_diario']:,.1f}** "
        f"eventos en **{metricas['dias_unicos']}** días registrados."
    )

    # 3. Punto de acceso más utilizado
    top_acceso = df.groupby("Punto de acceso").size().sort_values(ascending=False)
    if len(top_acceso) > 0:
        nombre_top = obtener_nombre_amigable(top_acceso.index[0])
        eventos_top = int(top_acceso.iloc[0])
        pct_top = round(eventos_top / total * 100, 2)
        conclusiones.append(
            f"El punto de acceso con mayor flujo fue **{nombre_top}** con "
            f"**{eventos_top:,}** eventos ({pct_top}% del total)."
        )

    # 4. Hora pico
    hora_conteo = df.groupby("Hora_Dia").size()
    hora_max = hora_conteo.idxmax()
    eventos_hora_max = int(hora_conteo.max())
    empate_hora = (hora_conteo == eventos_hora_max).sum() > 1
    if empate_hora:
        horas_empatadas = hora_conteo[hora_conteo == eventos_hora_max].index.tolist()
        horas_str = ", ".join([f"{h:02d}:00" for h in horas_empatadas])
        conclusiones.append(
            f"Se observó empate en las horas de mayor flujo: **{horas_str}** "
            f"con **{eventos_hora_max:,}** eventos cada una."
        )
    else:
        conclusiones.append(
            f"El mayor volumen de eventos se registró a las **{hora_max:02d}:00** "
            f"con **{eventos_hora_max:,}** eventos."
        )

    # 5. Entradas vs salidas
    entradas = metricas["entradas"]
    salidas = metricas["salidas"]
    otros = metricas["otros"]
    conclusiones.append(
        f"Del total de eventos: **{entradas:,}** fueron entradas ({entradas/total*100:.1f}%), "
        f"**{salidas:,}** fueron salidas ({salidas/total*100:.1f}%)"
        + (f" y **{otros:,}** fueron clasificados como otros ({otros/total*100:.1f}%)." if otros > 0 else ".")
    )

    # 6. Ingreso
    ingreso_conteo = df.groupby("Ingreso").size().sort_values(ascending=False)
    for ingreso_nombre in ingreso_conteo.index:
        eventos_c = int(ingreso_conteo[ingreso_nombre])
        pct_c = round(eventos_c / total * 100, 2)
        conclusiones.append(
            f"Ingreso **{ingreso_nombre}**: **{eventos_c:,}** eventos ({pct_c}%)."
        )

    # 7. Día de mayor flujo
    diario = df.groupby("Fecha").size()
    dia_max = diario.idxmax()
    conclusiones.append(
        f"El día con mayor flujo fue **{dia_max}** con **{int(diario.max()):,}** eventos."
    )

    # 8. Día de menor flujo
    dia_min = diario.idxmin()
    conclusiones.append(
        f"El día con menor flujo fue **{dia_min}** con **{int(diario.min()):,}** eventos."
    )

    # 9. Tipo de usuario predominante
    tipo_conteo = df.groupby("Tipo_Usuario").size().sort_values(ascending=False)
    if len(tipo_conteo) > 0:
        tipo_top = tipo_conteo.index[0]
        eventos_tipo = int(tipo_conteo.iloc[0])
        pct_tipo = round(eventos_tipo / total * 100, 2)
        conclusiones.append(
            f"El tipo de usuario con mayor número de eventos fue **{tipo_top}** "
            f"con **{eventos_tipo:,}** eventos ({pct_tipo}%)."
        )

    # 10. Contraste entre ingresos
    if len(ingreso_conteo) >= 2:
        ing_1 = ingreso_conteo.index[0]
        ing_2 = ingreso_conteo.index[1]
        ev_1 = int(ingreso_conteo.iloc[0])
        ev_2 = int(ingreso_conteo.iloc[1])
        ratio = round(ev_1 / ev_2, 1) if ev_2 > 0 else 0
        conclusiones.append(
            f"El ingreso **{ing_1}** registró **{ratio}x** más eventos que el ingreso **{ing_2}** "
            f"({ev_1:,} vs {ev_2:,})."
        )

    return conclusiones
