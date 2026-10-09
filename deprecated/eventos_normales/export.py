"""
Módulo de exportación de reportes.
Genera un Excel con múltiples hojas de estadísticas.
"""

import io
import pandas as pd
from access_names import aplicar_nombres_amigables_df
from statistics_calc import (
    flujo_por_punto_acceso,
    flujo_por_hora,
    flujo_diario,
    entradas_vs_salidas_general,
    flujo_por_tipo_usuario,
    flujo_por_ingreso,
    heatmap_dia_hora,
    tipo_usuario_ingreso,
    frecuencia_utilizacion,
)
from pdf_report import exportar_reporte_pdf, construir_graficos_reporte

def exportar_dataset_filtrado(df: pd.DataFrame) -> bytes:
    """Exporta el dataset filtrado actual a Excel."""
    output = io.BytesIO()
    # Seleccionar columnas relevantes para exportar (sin Persona por privacidad)
    columnas_export = [
        "Nombre", "Apellido", "Departamento", "Hora",
        "Device Name", "Punto de acceso",
        "Tipo_Usuario", "Ingreso", "Movimiento", "Fecha",
        "Hora_Dia", "Dia_Semana",
    ]
    cols_disponibles = [c for c in columnas_export if c in df.columns]
    df_export = df[cols_disponibles].copy()
    df_export = aplicar_nombres_amigables_df(df_export)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export.to_excel(writer, sheet_name="Datos Filtrados", index=False)
        _autoajustar_columnas(writer, df_export, "Datos Filtrados")
    return output.getvalue()


def exportar_reporte_completo(df: pd.DataFrame, metricas: dict, calidad: dict) -> bytes:
    """
    Genera un Excel de reporte con las hojas:
    1. Resumen
    2. Flujo por acceso
    3. Flujo por hora
    4. Flujo diario
    5. Entradas y salidas
    6. Por tipo de usuario
    7. Por ingreso
    8. Día y hora
    9. Calidad de datos
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # 1. Resumen
        resumen_data = {
            "Métrica": [
                "Total de eventos",
                "Usuarios únicos",
                "Puntos de acceso",
                "Ingreso",
                "Fecha inicial",
                "Fecha final",
                "Días registrados",
                "Entradas",
                "Salidas",
                "Otros eventos",
                "Promedio diario de eventos",
            ],
            "Valor": [
                metricas["total_eventos"],
                metricas["usuarios_unicos"],
                metricas["puntos_acceso"],
                metricas["ingreso_count"],
                str(metricas["fecha_inicial"]),
                str(metricas["fecha_final"]),
                metricas["dias_unicos"],
                metricas["entradas"],
                metricas["salidas"],
                metricas["otros"],
                metricas["promedio_diario"],
            ],
        }
        df_resumen = pd.DataFrame(resumen_data)
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
        _autoajustar_columnas(writer, df_resumen, "Resumen")

        # 2. Flujo por acceso
        df_acceso = flujo_por_punto_acceso(df)
        df_acceso.to_excel(writer, sheet_name="Flujo por Acceso")
        _autoajustar_columnas(writer, df_acceso.reset_index(), "Flujo por Acceso")

        # 3. Flujo por hora
        df_hora = flujo_por_hora(df)
        df_hora.to_excel(writer, sheet_name="Flujo por Hora", index=False)
        _autoajustar_columnas(writer, df_hora, "Flujo por Hora")

        # 4. Flujo diario
        df_diario = flujo_diario(df)
        df_diario.to_excel(writer, sheet_name="Flujo Diario", index=False)
        _autoajustar_columnas(writer, df_diario, "Flujo Diario")

        # 5. Entradas y salidas
        df_ev = entradas_vs_salidas_general(df)
        df_ev.to_excel(writer, sheet_name="Entradas y Salidas", index=False)
        _autoajustar_columnas(writer, df_ev, "Entradas y Salidas")

        # 6. Por tipo de usuario
        df_tipo = flujo_por_tipo_usuario(df)
        df_tipo.to_excel(writer, sheet_name="Por Tipo de Usuario", index=False)
        _autoajustar_columnas(writer, df_tipo, "Por Tipo de Usuario")

        # 7. Por ingreso
        df_ingreso = flujo_por_ingreso(df)
        df_ingreso.to_excel(writer, sheet_name="Por Ingreso", index=False)
        _autoajustar_columnas(writer, df_ingreso, "Por Ingreso")

        # 8. Día y hora (heatmap)
        df_dh = heatmap_dia_hora(df)
        df_dh.to_excel(writer, sheet_name="Día y Hora")
        _autoajustar_columnas(writer, df_dh.reset_index(), "Día y Hora")

        # 9. Calidad de datos
        calidad_data = {
            "Métrica": [
                "Total de registros",
                "Registros válidos",
                "Registros con fecha inválida",
                "Registros con punto de acceso vacío",
                "Registros con departamento vacío",
                "Registros sin nombre/apellido",
                "Valores únicos - Punto de acceso",
                "Valores únicos - Device Name",
            ],
            "Valor": [
                calidad["total_registros"],
                calidad["registros_validos"],
                calidad["fechas_invalidas"],
                calidad["acceso_vacio"],
                calidad["departamento_vacio"],
                calidad["registros_sin_nombre"],
                calidad["unicos_punto_acceso"],
                calidad["unicos_device_name"],
            ],
        }
        df_calidad = pd.DataFrame(calidad_data)
        df_calidad.to_excel(writer, sheet_name="Calidad de Datos", index=False)
        _autoajustar_columnas(writer, df_calidad, "Calidad de Datos")

    return output.getvalue()


def _autoajustar_columnas(writer, df: pd.DataFrame, sheet_name: str):
    """Ajusta el ancho de las columnas del Excel basándose en el contenido."""
    worksheet = writer.sheets[sheet_name]
    for i, col in enumerate(df.columns):
        try:
            max_len = max(
                df[col].astype(str).apply(len).max() if len(df) > 0 else 0,
                len(str(col))
            ) + 2
        except Exception:
            max_len = len(str(col)) + 2
        worksheet.set_column(i, i, min(max_len, 50))
