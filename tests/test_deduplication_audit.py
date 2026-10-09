"""Pruebas de caracterización: documentan la regla vigente sin cambiarla."""

import pandas as pd

from all_events_data_loader import detectar_columnas_todos
from all_events_data_processing import procesar_datos_todos
from lpr_data_processing import deduplicar_eventos_vehiculares


def _lpr(times, directions, cameras=None, sites=None):
    count = len(times)
    return pd.DataFrame(
        {
            "Matricula": ["ABC123"] * count,
            "Hora": pd.to_datetime(times),
            "Direccion": directions,
            "Camara": cameras or ["CAM 1"] * count,
            "Ubicacion_Ingreso": sites or ["25 de Junio"] * count,
        }
    )


def _deduplicar_ventana_corta(df, claves, segundos):
    """Simulación usada por la auditoría; compara con el último conservado."""
    ordenado = df.sort_values([*claves, "Hora"], kind="stable")
    conservar = pd.Series(False, index=ordenado.index)
    for _, indices in ordenado.groupby(claves, sort=False, dropna=False).groups.items():
        ultima_conservada = None
        for indice in indices:
            hora = ordenado.at[indice, "Hora"]
            if ultima_conservada is None or (hora - ultima_conservada).total_seconds() > segundos:
                conservar.at[indice] = True
                ultima_conservada = hora
    return ordenado.loc[conservar]


def test_current_rule_ignores_camera_and_campus_for_same_plate_direction():
    df = _lpr(
        ["2026-09-07 08:00", "2026-09-07 08:01", "2026-09-07 08:02"],
        ["ENTRADA"] * 3,
        cameras=["25 JUNIO ING VEH 1", "25 JUNIO ING VEH 2", "FERROV ENT VEH 1"],
        sites=["25 de Junio", "25 de Junio", "Ferroviaria"],
    )

    validos, descartados = deduplicar_eventos_vehiculares(df)

    assert len(validos) == 1
    assert len(descartados) == 2


def test_current_rule_keeps_direction_changes_even_in_the_same_second():
    df = _lpr(
        ["2026-09-07 08:00:00", "2026-09-07 08:00:00"],
        ["ENTRADA", "SALIDA"],
    )

    validos, descartados = deduplicar_eventos_vehiculares(df)

    assert len(validos) == 2
    assert descartados.empty


def test_four_hour_boundary_is_discarded_and_greater_gap_is_kept():
    df = _lpr(
        ["2026-09-07 08:00:00", "2026-09-07 12:00:00", "2026-09-07 16:00:01"],
        ["ENTRADA"] * 3,
    )

    validos, descartados = deduplicar_eventos_vehiculares(df)

    assert validos["Hora"].tolist() == pd.to_datetime(
        ["2026-09-07 08:00:00", "2026-09-07 16:00:01"]
    ).tolist()
    assert descartados["Hora"].tolist() == pd.to_datetime(["2026-09-07 12:00:00"]).tolist()


def test_current_rule_compares_with_previous_raw_event_not_last_kept():
    df = _lpr(
        ["2026-09-07 08:00", "2026-09-07 11:00", "2026-09-07 13:00"],
        ["ENTRADA"] * 3,
    )

    validos, descartados = deduplicar_eventos_vehiculares(df)

    # 13:00 está a cinco horas del último conservado (08:00), pero solo a dos
    # horas de la fila bruta anterior (11:00), por lo que también se descarta.
    assert len(validos) == 1
    assert len(descartados) == 2


def test_equal_timestamp_input_order_can_change_current_result():
    grouped = _lpr(
        ["2026-09-07 08:00"] * 3,
        ["ENTRADA", "ENTRADA", "SALIDA"],
    )
    alternating = _lpr(
        ["2026-09-07 08:00"] * 3,
        ["ENTRADA", "SALIDA", "ENTRADA"],
    )

    validos_grouped, _ = deduplicar_eventos_vehiculares(grouped)
    validos_alternating, _ = deduplicar_eventos_vehiculares(alternating)

    assert len(validos_grouped) == 2
    assert len(validos_alternating) == 3


def test_camera_and_campus_short_window_strategies_have_different_scope():
    df = _lpr(
        ["2026-09-07 08:00:00", "2026-09-07 08:00:05"],
        ["ENTRADA", "ENTRADA"],
        cameras=["25 JUNIO ING VEH 1", "25 JUNIO ING VEH 2"],
        sites=["25 de Junio", "25 de Junio"],
    )

    por_camara = _deduplicar_ventana_corta(
        df, ["Matricula", "Camara", "Direccion"], 10
    )
    por_campus = _deduplicar_ventana_corta(
        df, ["Matricula", "Ubicacion_Ingreso", "Direccion"], 10
    )

    assert len(por_camara) == 2
    assert len(por_campus) == 1


def test_biometric_processing_preserves_exact_and_mixed_result_attempts():
    raw = pd.DataFrame(
        {
            "Nombre": ["ANA", "ANA", "ANA"],
            "Apellido": ["PEREZ", "PEREZ", "PEREZ"],
            "Nº de tarjeta": ["100", "100", "100"],
            "Departamento": ["All > ESTUDIANTES"] * 3,
            "Hora": ["2026-09-07 08:00:00", "2026-09-07 08:00:00", "2026-09-07 08:00:01"],
            "Device Name": ["T1", "T1", "T1"],
            "Punto de acceso": ["TER ING TOR FER"] * 3,
            "Tipo de evento": ["Acceso concedido", "Acceso concedido", "Acceso denegado"],
        }
    )

    procesado, _ = procesar_datos_todos(raw, detectar_columnas_todos(raw))

    assert len(procesado) == 3
    assert procesado["Resultado"].tolist() == ["Exitoso", "Exitoso", "Denegado"]

