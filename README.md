# Sistema de Reportes — Flujo de Ingresos Peatonales

Aplicación de análisis de datos para el sistema de control de accesos peatonales
de la universidad. Procesa registros de eventos de ingreso/salida y genera
estadísticas, visualizaciones interactivas y reportes exportables.

## Inicio Rápido

### 1. Activar entorno virtual

```bash
# Windows
.venv\Scripts\activate
```

### 2. Instalar dependencias (si no se han instalado)

```bash
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación

```bash
streamlit run app.py
```

La aplicación buscará automáticamente el archivo Excel (`.xlsx`) en la carpeta
del proyecto.

## Estructura del Proyecto

```
├── app.py                  # Aplicación principal Streamlit
├── config.py               # Configuración y constantes
├── data_loader.py          # Carga y validación del Excel
├── data_processing.py      # Limpieza y transformación de datos
├── statistics_calc.py      # Cálculo de estadísticas
├── visualizations.py       # Gráficos interactivos con Plotly
├── export.py               # Exportación de reportes Excel
├── requirements.txt        # Dependencias del proyecto
├── README.md               # Este archivo
├── REPORTES_ACCESOS_REGLAS.md  # Reglas funcionales
├── PROMPT_MAESTRO.md       # Especificación del proyecto
└── limpio_jul27_ago14.xlsx # Datos de entrada
```

## Funcionalidades

### Estadísticas
- Resumen general (eventos, usuarios únicos, entradas/salidas)
- Flujo por punto de acceso con ranking
- Flujo por hora del día con horas pico
- Flujo por punto de acceso × hora (heatmap)
- Entradas vs salidas (general, por campus, por hora, por punto)
- Flujo por campus
- Flujo por tipo de usuario
- Tipo de usuario × campus
- Flujo diario con tendencia
- Flujo por día de la semana
- Heatmap día × hora
- Campus × hora (comparativo)
- Punto × tipo de usuario
- Frecuencia de utilización por usuario
- Conclusiones/hallazgos automáticos
- Calidad de datos

### Filtros Interactivos
- Rango de fechas
- Campus
- Tipo de usuario
- Movimiento (Entrada/Salida/Otro)
- Punto de acceso
- Rango de horas
- Botón "Restablecer filtros"

### Exportación
- Reporte completo (Excel con 9 hojas)
- Dataset filtrado

## Dependencias

- Python 3.x
- pandas
- openpyxl
- streamlit
- plotly
- xlsxwriter

## Reglas de Negocio

- **Eventos ≠ Personas**: El sistema registra eventos, no personas.
- **Sin deduplicación automática**: Los datos ya fueron limpiados previamente.
- **Campus**: Puntos con "FER" → Ferroviaria; puntos con "TOR 1/2/3" o "DISCAP" → 25 de Junio.
- **Movimiento**: Se determina por el nombre del punto de acceso (ENTRADA/SALIDA/OTRO).
- **Tipo de usuario**: Se extrae de la columna Departamento.
- **Privacidad**: No se muestran nombres en gráficos generales.
