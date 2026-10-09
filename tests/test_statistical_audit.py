from datetime import date, timedelta

import pandas as pd
import pytest

import all_events_statistics_calc as ats
import lpr_statistics_calc as lprs
from all_events_data_loader import detectar_columnas_todos
from all_events_data_processing import procesar_datos_todos
from dashboard_filters import aplicar_filtros_integrales


def _lpr_hour_fixture(total: int, days: int) -> pd.DataFrame:
    start = pd.Timestamp("2026-09-07 06:00:00")
    timestamps = []
    # Distribución circular por todos los minutos de todos los días: permite
    # comprobar tanto el promedio como el máximo real en una ventana de minuto.
    for i in range(total):
        slot = i % (days * 60)
        day_offset, minute = divmod(slot, 60)
        timestamps.append(start + pd.Timedelta(days=day_offset, minutes=minute))
    hora = pd.Series(timestamps)
    return pd.DataFrame(
        {
            "Fecha": hora.dt.date,
            "Hora": hora,
            "Hora_Dia": 6,
            "Punto_Acceso": "25 JUNIO ING VEH 1",
        }
    )


def test_5105_records_over_31_days_are_not_divided_only_by_60():
    resultado = lprs.stats_flujo_vehicular_por_hora(_lpr_hour_fixture(5105, 31))
    fila = resultado.loc[resultado["Hora"] == 6].iloc[0]

    assert fila["Registros"] == 5105
    assert fila["Dias_considerados"] == 31
    assert fila["Promedio_registros_minuto"] == pytest.approx(5105 / (31 * 60), abs=0.0005)
    assert fila["Promedio_por_dia"] == pytest.approx(5105 / 31, abs=0.005)
    assert fila["Maximo_real_por_minuto"] == 3
    assert fila["Promedio_registros_minuto"] != pytest.approx(5105 / 60)


def test_one_day_minute_average_and_observed_maximum():
    resultado = lprs.stats_flujo_vehicular_por_hora(_lpr_hour_fixture(120, 1))
    fila = resultado.loc[resultado["Hora"] == 6].iloc[0]

    assert fila["Promedio_registros_minuto"] == 2
    assert fila["Promedio_por_dia"] == 120
    assert fila["Maximo_real_por_minuto"] == 2


def test_unknown_results_are_separate_from_failures():
    df = pd.DataFrame(
        {"Resultado": ["Exitoso"] * 6 + ["Denegado"] * 2 + ["Fallo de reconocimiento"] + ["Otro"]}
    )
    tasas = ats.calcular_tasas_generales(df)

    assert tasas["fallidos"] == 3
    assert tasas["otros"] == 1
    assert tasas["tasa_exito"] == 60
    assert tasas["tasa_fallo_general"] == 30
    assert tasas["tasa_otros"] == 10


def test_card_number_is_used_as_stable_person_identity():
    raw = pd.DataFrame(
        {
            "Nombre": ["ANA", "ANA"],
            "Apellido": ["PEREZ", "PEREZ"],
            "Nº de tarjeta": ["100", "200"],
            "Departamento": ["All > ESTUDIANTES"] * 2,
            "Hora": ["2026-09-07 08:00", "2026-09-07 09:00"],
            "Device Name": ["T1", "T1"],
            "Punto de acceso": ["TER ING TOR FER", "TER ING TOR FER"],
            "Tipo de evento": ["Acceso concedido", "Acceso concedido"],
        }
    )
    mapping = detectar_columnas_todos(raw)
    processed, _ = procesar_datos_todos(raw, mapping)

    assert mapping["identificador_persona"] == "Nº de tarjeta"
    assert processed["Persona"].nunique() == 1
    assert processed["Persona_Analitica"].nunique() == 2


def test_point_and_movement_filters_apply_to_biometric_and_lpr():
    bio = pd.DataFrame(
        {
            "Fecha": [date(2026, 9, 7), date(2026, 9, 8)],
            "Punto de acceso": ["BIO ENTRADA", "BIO SALIDA"],
            "Movimiento": ["ENTRADA", "SALIDA"],
            "Resultado": ["Exitoso", "Exitoso"],
            "Ingreso": ["Peatonal", "Peatonal"],
            "Tipo_Usuario": ["A", "A"],
            "Ubicacion_Ingreso": ["25 de Junio", "25 de Junio"],
        }
    )
    lpr = pd.DataFrame(
        {
            "Fecha": [date(2026, 9, 7), date(2026, 9, 8)],
            "Camara": ["LPR ENTRADA", "LPR SALIDA"],
            "Direccion": ["ENTRADA", "SALIDA"],
            "Ubicacion_Ingreso": ["25 de Junio", "25 de Junio"],
        }
    )

    bio_f, lpr_f = aplicar_filtros_integrales(
        bio, lpr, {"movimientos": ["ENTRADA"], "puntos_acceso": ["BIO ENTRADA", "LPR ENTRADA"]}
    )
    assert bio_f["Punto de acceso"].tolist() == ["BIO ENTRADA"]
    assert lpr_f["Camara"].tolist() == ["LPR ENTRADA"]


def test_huella_keeps_unclassified_biometrics_outside_peatonal():
    hora = pd.to_datetime(["2026-09-07 08:00"] * 3)
    bio = pd.DataFrame(
        {
            "Fecha": hora.date,
            "Hora": hora,
            "Punto de acceso": ["PEAT", "VEH", "SIN CLASE"],
            "Tipo_Flujo_Consolidado": ["Peatonal", "Vehicular", "Error"],
            "Categoria_Ingreso": ["Peatonal", "Vehicular por biométrico", "Error"],
            "Ubicacion_Ingreso": ["25 de Junio"] * 3,
            "Movimiento": ["ENTRADA"] * 3,
            "Hora_Dia": [8] * 3,
        }
    )
    huella = lprs.generar_huella_movilidad(bio, pd.DataFrame())

    assert huella["tot_peatones_puros"] == 1
    assert huella["tot_terminales_veh"] == 1
    assert huella["tot_biometricos_sin_clasificar"] == 1
    assert huella["tot_registros"] == 3

