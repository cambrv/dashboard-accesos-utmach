from datetime import date

import pandas as pd

from lpr_data_processing import clasificar_ubicacion_lpr, deduplicar_eventos_vehiculares
from lpr_statistics_calc import (
    calcular_estadisticas_vehiculares_consolidadas,
    consolidar_eventos_vehiculares,
    resumen_entradas_vehiculares,
    stats_movimientos_lpr_por_ubicacion_camara,
)


def _movimientos_base():
    return pd.DataFrame(
        {
            "Fecha": [date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 2)],
            "Direccion": ["ENTRADA", "SALIDA", "SALIDA"],
            "Ubicacion_Ingreso": ["25 de Junio", "25 de Junio", "Ferroviaria"],
            "Camara": ["25 JUNIO ING VEH 1", "25 JUNIO SAL VEH 1", "FERROV SAL VEH 1"],
        }
    )


def test_promedio_entradas_usa_todos_los_dias_con_datos():
    resumen = resumen_entradas_vehiculares(_movimientos_base())

    assert resumen["total_entradas"] == 1
    assert resumen["dias_con_datos"] == 2
    assert resumen["promedio_diario"] == 0.5
    assert resumen["diario"]["Entradas"].tolist() == [1, 0]


def test_totales_concilian_por_ubicacion_y_camara():
    stats = stats_movimientos_lpr_por_ubicacion_camara(_movimientos_base())

    assert stats["total_entradas"] == 1
    assert stats["total_salidas"] == 2
    assert stats["por_ubicacion"].groupby("Sentido")["Registros"].sum().to_dict() == {
        "Entrada": 1,
        "Salida": 2,
    }
    assert stats["por_camara"].groupby("Sentido")["Registros"].sum().to_dict() == {
        "Entrada": 1,
        "Salida": 2,
    }
    assert not any(stats["diferencias"].values())


def test_registro_sin_clasificar_se_informa_sin_alterar_total():
    df = _movimientos_base()
    df.loc[0, "Ubicacion_Ingreso"] = "Error de clasificación"
    stats = stats_movimientos_lpr_por_ubicacion_camara(df)

    assert stats["total_entradas"] == 1
    assert stats["diferencias"]["entradas_sin_ubicacion_valida"] == 1
    fila = stats["por_camara"].loc[
        stats["por_camara"]["Camara"] == "25 JUNIO ING VEH 1"
    ].iloc[0]
    assert fila["Ubicacion"] == "Sin clasificar"


def test_variantes_de_camara_se_normalizan_sin_clasificar_por_descarte():
    assert clasificar_ubicacion_lpr("25 DE JUNIO-ING-VEH-2") == "25 de Junio"
    assert clasificar_ubicacion_lpr("25JUNIO ING VEH 1") == "25 de Junio"
    assert clasificar_ubicacion_lpr("FERROVIARIA_SAL_VEH_1") == "Ferroviaria"
    assert clasificar_ubicacion_lpr("NORTE ING VEH 1") == "Error de clasificación"


def test_deduplicacion_lpr_conserva_cambios_de_direccion():
    df = pd.DataFrame(
        {
            "Matricula": ["ABC123", "ABC123", "ABC123"],
            "Hora": pd.to_datetime(["2026-01-01 08:00", "2026-01-01 08:05", "2026-01-01 08:10"]),
            "Direccion": ["ENTRADA", "ENTRADA", "SALIDA"],
        }
    )
    validos, duplicados = deduplicar_eventos_vehiculares(df)

    assert len(validos) == 2
    assert len(duplicados) == 1
    assert validos["Direccion"].tolist() == ["ENTRADA", "SALIDA"]


def test_consolidado_vehicular_separa_biometrico_lpr_y_excluye_peatones():
    horas = pd.to_datetime([
        "2026-01-01 08:00", "2026-01-01 09:00", "2026-01-01 10:00"
    ])
    bio = pd.DataFrame(
        {
            "Fecha": horas.date,
            "Hora": horas,
            "Hora_Dia": horas.hour,
            "Movimiento": ["ENTRADA", "SALIDA", "ENTRADA"],
            "Tipo_Flujo_Consolidado": ["Vehicular", "Vehicular", "Peatonal"],
            "Mecanismo_Registro": ["Biométrico"] * 3,
            "Ubicacion_Ingreso": ["25 de Junio", "Ferroviaria", "25 de Junio"],
            "Categoria_Ingreso": [
                "Vehicular por biométrico 25 de Junio",
                "Vehicular por biométrico Ferroviaria",
                "Peatonal 25 de Junio",
            ],
            "Punto de acceso": ["25 JUNIO ING VEH 2", "FERROV SAL VEH 1", "TOR 1"],
        }
    )
    lpr = pd.DataFrame(
        {
            "Fecha": [date(2026, 1, 1), date(2026, 1, 2)],
            "Hora": pd.to_datetime(["2026-01-01 08:00", "2026-01-02 08:00"]),
            "Hora_Dia": [8, 8],
            "Direccion": ["ENTRADA", "SALIDA"],
            "Ubicacion_Ingreso": ["25 de Junio", "Ferroviaria"],
            "Categoria_Ingreso": ["Vehicular por LPR 25 de Junio", "Vehicular por LPR Ferroviaria"],
            "Camara": ["25 JUNIO ING VEH 1", "FERROV SAL VEH 1"],
        }
    )

    consolidado = consolidar_eventos_vehiculares(bio, lpr)
    stats = calcular_estadisticas_vehiculares_consolidadas(consolidado)

    assert len(consolidado) == 4
    assert stats["entradas"] == {"Biométrico VEH": 1, "LPR": 1, "Consolidado": 2}
    assert stats["salidas"] == {"Biométrico VEH": 1, "LPR": 1, "Consolidado": 2}
    assert stats["dias"] == {"Biométrico VEH": 1, "LPR": 2, "Consolidado": 2}
    assert stats["promedios"] == {"Biométrico VEH": 1.0, "LPR": 0.5, "Consolidado": 1.0}
    assert stats["diario"]["Total registros de entrada"].tolist() == [2, 0]


def test_consolidado_no_deduplica_eventos_entre_mecanismos():
    instante = pd.Timestamp("2026-01-01 08:00")
    bio = pd.DataFrame(
        {
            "Fecha": [instante.date()], "Hora": [instante], "Hora_Dia": [8],
            "Movimiento": ["ENTRADA"], "Tipo_Flujo_Consolidado": ["Vehicular"],
            "Ubicacion_Ingreso": ["25 de Junio"],
            "Categoria_Ingreso": ["Vehicular por biométrico 25 de Junio"],
            "Punto de acceso": ["25 JUNIO ING VEH 2"],
        }
    )
    lpr = pd.DataFrame(
        {
            "Fecha": [instante.date()], "Hora": [instante], "Hora_Dia": [8],
            "Direccion": ["ENTRADA"], "Ubicacion_Ingreso": ["25 de Junio"],
            "Categoria_Ingreso": ["Vehicular por LPR 25 de Junio"],
            "Camara": ["25 JUNIO ING VEH 1"],
        }
    )

    stats = calcular_estadisticas_vehiculares_consolidadas(
        consolidar_eventos_vehiculares(bio, lpr)
    )

    assert stats["entradas"]["Consolidado"] == 2


def test_consolidado_con_solo_salidas_conserva_dia_con_cero_entradas():
    instante = pd.Timestamp("2026-01-01 18:00")
    eventos = pd.DataFrame(
        {
            "Fecha": [instante.date()], "Hora": [instante], "Hora_Dia": [18],
            "Movimiento": ["SALIDA"], "Ubicacion_Ingreso": ["Ferroviaria"],
            "Mecanismo_Registro": ["Biométrico VEH"],
            "Categoria_Ingreso": ["Vehicular por biométrico Ferroviaria"],
            "Punto_Acceso": ["FERROV SAL VEH 1"],
        }
    )

    stats = calcular_estadisticas_vehiculares_consolidadas(eventos)

    assert stats["diario"]["Total registros de entrada"].tolist() == [0]
    assert stats["promedios"]["Consolidado"] == 0.0
