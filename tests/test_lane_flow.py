import pandas as pd

from access_names import clasificar_carril_vehicular
from lpr_statistics_calc import (
    calcular_caudal_conjunto_por_acceso,
    calcular_flujo_real_por_carril,
)


def _eventos(carril, instantes, mecanismo="LPR", ubicacion="25 de Junio", sentido="ENTRADA"):
    return pd.DataFrame({
        "Hora": pd.to_datetime(instantes),
        "Fecha": pd.to_datetime(instantes).date,
        "Hora_Dia": pd.to_datetime(instantes).hour,
        "Movimiento": sentido,
        "Ubicacion_Ingreso": ubicacion,
        "Mecanismo_Registro": mecanismo,
        "Carril": carril,
    })


def test_clasifica_carriles_sin_mezclar_ubicacion_sentido_o_torniquetes():
    casos = {
        "25 JUNIO ING VEH 1": ("25 de Junio", "ENTRADA", "E1"),
        "25 JUNIO SAL VEH 2": ("25 de Junio", "SALIDA", "S2"),
        "FERROV ENT VEH 2": ("Ferroviaria", "ENTRADA", "E2"),
        "FERROV SAL VEH 1": ("Ferroviaria", "SALIDA", "S1"),
    }
    for nombre, esperado in casos.items():
        resultado = clasificar_carril_vehicular(nombre)
        assert (resultado["Ubicacion"], resultado["Sentido"], resultado["Carril"]) == esperado
    assert clasificar_carril_vehicular("TER ENTRADA 1 TOR 2_Door_1")["Carril"] == "Sin clasificar"


def test_hora_pico_y_minuto_maximo_son_intervalos_reales_no_acumulados():
    instantes = (
        ["2026-09-07 06:00:10"] * 8
        + ["2026-09-07 06:01:10"] * 10
        + ["2026-09-07 06:02:10"] * 7
        + ["2026-09-08 06:01:10"] * 9
    )
    resultado = calcular_flujo_real_por_carril(_eventos("E1", instantes)).iloc[0]
    assert resultado["Eventos"] == 34
    assert resultado["Maximo_observado_minuto"] == 10
    assert resultado["Minuto_maximo_inicio"] == pd.Timestamp("2026-09-07 06:01:00")
    assert resultado["Eventos_hora_pico"] == 25
    assert resultado["Hora_pico_inicio"] == pd.Timestamp("2026-09-07 06:00:00")
    assert resultado["Promedio_hora_pico_min"] == 25 / 60


def test_caudal_conjunto_alinea_carriles_y_no_suma_maximos_no_simultaneos():
    e1 = _eventos("E1", ["2026-09-07 06:00:10"] * 10 + ["2026-09-07 06:01:10"])
    e2 = _eventos("E2", ["2026-09-07 06:00:20"] * 2 + ["2026-09-07 06:01:20"] * 13)
    resultado = calcular_caudal_conjunto_por_acceso(pd.concat([e1, e2], ignore_index=True)).iloc[0]
    assert resultado["Caudal_maximo_eventos_min"] == 14
    assert resultado["Minuto_maximo_inicio"] == pd.Timestamp("2026-09-07 06:01:00")
    assert resultado["Promedio_por_carril_en_minuto_maximo"] == 7
    assert resultado["Caudal_maximo_eventos_min"] != 23


def test_mecanismos_se_calculan_por_separado():
    lpr = _eventos("E1", ["2026-09-07 06:00:10"] * 3, mecanismo="LPR")
    bio = _eventos("E1", ["2026-09-07 06:00:20"] * 4, mecanismo="Biométrico VEH")
    resultado = calcular_flujo_real_por_carril(pd.concat([lpr, bio], ignore_index=True))
    assert dict(zip(resultado["Mecanismo"], resultado["Eventos"])) == {"Biométrico VEH": 4, "LPR": 3}


def test_promedio_diario_incluye_dias_del_mecanismo_sin_eventos_del_carril():
    e1 = _eventos("E1", ["2026-09-07 06:00:10"] * 4)
    otro_carril = _eventos("Sin clasificar", ["2026-09-08 06:00:10"])
    resultado = calcular_flujo_real_por_carril(pd.concat([e1, otro_carril], ignore_index=True)).iloc[0]
    assert resultado["Dias_con_datos_mecanismo"] == 2
    assert resultado["Promedio_diario_sentido"] == 2
