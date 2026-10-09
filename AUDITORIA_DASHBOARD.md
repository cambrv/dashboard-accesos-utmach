# Auditoría integral — Dashboard de Accesos UTMACH

Fecha de validación: 2026-10-08.

## 1. Mapa arquitectónico

Punto de entrada: `app.py`, ejecutado con `streamlit run app.py`. La navegación operativa expone únicamente **Todos los Eventos**.

| Clasificación | Archivos | Evidencia de uso |
|---|---|---|
| ACTIVO | `app.py` | Orquesta carga, filtros, estadísticas, pestañas y PDF. |
| ACTIVO | `all_events_data_loader.py`, `all_events_data_processing.py`, `all_events_statistics_calc.py`, `all_events_visualizations.py`, `all_events_pdf_report.py` | Importados por `app.py`; implementan lectura, clasificación, tasas, gráficos y reporte de Todos los Eventos. |
| ACTIVO | `lpr_data_loader.py`, `lpr_data_processing.py`, `lpr_statistics_calc.py`, `lpr_visualizations.py` | Importados por `app.py` y/o `all_events_pdf_report.py`; implementan la ruta LPR. |
| ACTIVO | `dashboard_filters.py`, `load_progress.py`, `styles.py` | Filtros puros, progreso de carga y tema utilizados directamente por `app.py`. |
| COMPARTIDO | `access_names.py`, `config.py`, `excel_processor.py` | Clasificación, constantes y lectura centralizada consumidas por módulos activos e históricos. |
| COMPARTIDO | `statistics_calc.py`, `visualizations.py`, `pdf_report.py` | Agregaciones y presentación base usadas por Todos los Eventos y por compatibilidad histórica. |
| HISTÓRICO | `deprecated/eventos_normales/*.py` | Solo `ejecutar_modo_exitoso`; import diferido y opción no expuesta en `main()`. |
| HISTÓRICO | `deprecated/eventos_fallidos/*.py` | Solo `ejecutar_modo_fallidos`; import diferido y opción no expuesta en `main()`. |
| SIN REFERENCIAS | `github_app.py`, `github_statistics_calc.py` | Copias antiguas UTF-16; ninguna referencia en código o configuración. Se conservaron por falta de evidencia suficiente para trasladarlas. |
| SIN REFERENCIAS / UTILIDAD MANUAL | `remove_emojis.py`, `test_secrets.py` | Scripts manuales sin imports entrantes. No se mueven ni ejecutan en producción. |
| CONFIGURACIÓN / INFRAESTRUCTURA | `.streamlit/config.toml`, `requirements.txt`, `packages.txt`, `.gitignore`, `specs/`, `tests/` | Tema/despliegue, dependencias, reglas y pruebas. |

Flujo operativo resumido:

`app.py` → `excel_processor` → loaders → processors → `dashboard_filters` → estadísticas compartidas/LPR → visualizaciones → `all_events_pdf_report` → `pdf_report`.

No existen cargas dinámicas de módulos fuera de los imports históricos explícitos. Los Excel, secretos y archivos locales ignorados no fueron modificados ni trasladados.

## 2. Código histórico trasladado

El detalle de rutas anteriores/nuevas, dependencias, compatibilidad y recuperación está en `deprecated/README.md`. Se trasladaron ocho archivos exclusivos de las dos secciones antiguas. Los imports se realizan dentro de sus funciones históricas; `deprecated` no participa en el arranque operativo.

## 3. Definiciones estadísticas auditadas

- **Registros totales:** número de filas del contexto filtrado, no personas ni accesos físicos.
- **Personas distintas:** `Nº de tarjeta` cuando está presente; nombre completo solo como respaldo explícito. El nombre continúa como etiqueta del buscador.
- **Placas únicas:** `nunique(Matricula)` sobre LPR válido y depurado; no equivale necesariamente a vehículos físicos distintos.
- **Éxito:** resultado biométrico `Exitoso / total biométrico evaluado`.
- **Fallo:** `(Denegado + Fallo de reconocimiento) / total biométrico evaluado`.
- **Otros:** `Otro / total biométrico evaluado`, separado del fallo.
- **Entradas LPR:** filas válidas cuya dirección normalizada es `ENTRADA`.
- **Promedio diario de entradas:** entradas LPR / número de fechas con cualquier dato LPR en el contexto filtrado. Una fecha con solo salidas aporta cero entradas. No se infieren días completamente ausentes del archivo.
- **Promedio por minuto de una franja:** registros acumulados en la hora / (`días con datos LPR` × 60).
- **Promedio diario de una franja:** registros acumulados en la hora / días con datos LPR.
- **Máximo real por minuto:** máximo de la agrupación por minuto calendario (`Fecha + hora + minuto`).
- **Mapas de calor:** conteos totales de eventos con fecha/hora válidas; no son promedios. Los registros con tiempo inválido quedan fuera de agregaciones temporales y permanecen visibles en calidad de datos.
- **Huella de movilidad:** peatonal, biométrico VEH, LPR y biométrico sin clasificar son categorías explícitas. La suma de mecanismos no representa accesos físicos únicos.

## 4. Hallazgos y correcciones

| ID | Indicador | Problema | Severidad | Causa / ubicación | Corrección | Prueba |
|---|---|---|---|---|---|---|
| EST-01 | LPR registros/minuto | 5.105 registros de 31 días se dividían solo entre 60. | Crítica | `lpr_statistics_calc.stats_flujo_vehicular_*` | Denominador días×60; se añadieron promedio/día y máximo real/minuto. Web, narrativas y PDF usan las mismas columnas. | Caso 5.105/31 y caso de un día. |
| EST-02 | Tasa de fallo | `Otro` se sumaba como fallo. | Alta | `all_events_statistics_calc` | Fallo = denegado + fallo de reconocimiento; `Otros` separado en web/PDF. | Distribución 60/30/10 y cruces. |
| EST-03 | Personas distintas | Se agrupaba solo por nombre/apellido aun existiendo tarjeta. | Alta | Loader/procesamiento y `statistics_calc` | Detección opcional de `Nº de tarjeta` y `Persona_Analitica`; respaldo nominal documentado. | Dos tarjetas con el mismo nombre producen dos identidades. |
| EST-04 | Huella peatonal | Todo biométrico no VEH se declaraba peatonal. | Alta | `generar_huella_movilidad` | Uso de `Tipo_Flujo_Consolidado`; clase no determinada informada aparte. | Reconciliación 1 peatonal + 1 VEH + 1 sin clasificar. |
| EST-05 | Matrículas inválidas | `NaN`, `None`, `No Plate` podían convertirse en cadenas y contar como placas. | Media | `lpr_data_processing` | Conjunto explícito de tokens inválidos antes de deduplicar. | Regresiones LPR existentes y auditoría. |
| EST-06 | Conteos con hora nula | Varias distribuciones no temporales usaban `count(Hora)` y perdían filas. | Media | `statistics_calc` | Conteos no temporales con `size`; los temporales conservan exclusión justificada. | Pruebas de totales y sintaxis. |
| FIL-01 | Rango de fechas | Límites derivados solo del biométrico. | Alta | `app.py` | Unión de fechas biométricas y LPR. | AppTest y filtro puro. |
| FIL-02 | Punto/movimiento | Faltaban en Todos los Eventos. | Media | `dashboard_filters.py`, `app.py` | Filtros conjuntos de punto/cámara y movimiento/dirección, con estado aplicado/restablecido. | Prueba combinada bio+LPR. |
| FIL-03 | Período anterior | Solo desplazaba fechas; ignoraba los otros filtros. | Alta | `_calcular_analitica_integral` | Reaplica el mismo contexto no temporal al período anterior. | Pruebas de filtros y revisión de llamada común. |
| FIL-04 | Contexto LPR | Duplicados/globales podían narrarse junto a un subconjunto filtrado. | Media | `app.py`, conclusiones LPR | Esos conteos se omiten cuando el contexto está filtrado. | Inspección y pruebas LPR. |
| FIL-05 | Resultado LPR-only | Se detenía si biométrico quedaba vacío aunque LPR tuviera filas. | Media | `app.py` | Solo se detiene cuando ambas fuentes están vacías; tasas vacías son seguras. | Pruebas de funciones vacías/AppTest. |
| MET-01 | Variación desde cero | Se mostraba 100 %, aunque la variación relativa es indefinida. | Media | `comparar_periodos` | Devuelve `None` y la interfaz muestra `N/D`. | Prueba de cálculo y revisión UI. |
| MET-02 | Anomalías | Una concentración se narraba como posible daño de sensor sin evidencia causal. | Media | `detectar_anomalias_avanzadas` | Se etiqueta como heurística que requiere revisión. | Inspección textual. |
| UX-01 | Tiempo de carga | La línea que actualizaba el texto de etapa estaba comentada y causaba `NameError`; el cronómetro no avanzaba. | Alta | `load_progress.start_stage` | Texto restaurado; cronómetro cliente continúa durante `read_excel` bloqueante y Python fija el tiempo final. | Pruebas monotónicas y AppTest. |

## 5. Comparación antes/después con los Excel reales

Período del archivo: 07/09/2026–07/10/2026.

| Métrica | Antes | Ahora | Explicación |
|---|---:|---:|---|
| Franja LPR 06:00–07:00 | 5.105 acumulados | 5.105 acumulados | El conteo no cambia. |
| “Registros/minuto” de esa franja | 85,1 | 2,745 | Antes: 5.105/60. Ahora: 5.105/(31×60). |
| Promedio diario 06:00–07:00 | No informado | 164,68 | 5.105/31. |
| Máximo real en un minuto | No informado | 13 | Máximo observado al agrupar por minuto calendario. |
| LPR válidos | 37.214 | 37.214 | La corrección temporal no altera la población. |
| Duplicados LPR descartados | 909 | 909 | Se conserva el algoritmo existente. |
| Personas por nombre | 17.711 | — | Medida nominal antigua, susceptible a homónimos/cambios. |
| Personas por tarjeta | — | 40.289 | Identificador presente en el Excel real. |

Resultados de conciliación real: 18.863 entradas y 18.351 salidas. Las sumas por ubicación y por cámara coinciden exactamente con ambos totales; no hubo dirección, ubicación ni cámara inválida en este archivo.

Biométrico real: 590.107 filas leídas y 590.107 procesadas; 546.966 exitosas, 10.152 denegadas y 32.989 fallos de reconocimiento. Las clases suman el total. En este archivo no existen resultados `Otro`, por lo que la tasa real visible permanece 92,69 % éxito y 7,31 % fallo, aunque la fórmula ya es correcta para futuros archivos con desconocidos.

## 6. Pruebas y validación

- `pytest`: **25 aprobadas**, incluida generación en memoria del PDF integral.
- Caso exacto 5.105/31, caso de un día, máximo real/minuto, tasas, identidad por tarjeta, huella, filtros combinados, deduplicación y conciliación LPR.
- AppTest: carga biométrica/LPR sintética, progreso al 100 %, reruns por filtros/tema sin reaparición del progreso.
- Excel real: lectura y procesamiento únicos, sin alterar archivos. Tiempo medido: biométrico 90,96 s de lectura + 31,66 s de procesamiento; LPR 8,60 s + 1,85 s; total 133,07 s.
- Sintaxis: `py_compile` aprobado para módulos activos e históricos.
- `git diff --check`: aprobado; solo avisos de normalización LF/CRLF.
- Puerto 8512: sin listener; `tests/_theme_preview.py` no existe y no se conserva ningún preview temporal.
- Puerto 8501: existe un `streamlit run app.py` iniciado antes de esta validación. No se detuvo por no ser un proceso temporal atribuible con certeza a esta prueba.
- Streamlit Cloud: dependencias y punto de entrada se conservan; no se realizó un despliegue remoto.
- PDF: se generó correctamente con datos sintéticos y las funciones estadísticas compartidas. No se repitió la lectura real de 133 s solo para generar el PDF.
- Tema: las reglas CSS y AppTest de ambos estados pasan. No se realizó en esta fase una inspección visual manual mediante navegador; por tanto, la legibilidad visual final no se declara validada manualmente.

## 7. Riesgos y limitaciones pendientes

1. La deduplicación LPR vigente descarta detecciones de la misma placa y dirección dentro de cuatro horas, incluso si aparecen en cámaras/sedes distintas. Se preservó por compatibilidad; cambiarla requiere decisión metodológica y validación de negocio.
2. “Días con datos” no prueba cobertura completa de las 24 horas. El promedio incluye cero para una franja cuando el día sí aparece en LPR, pero no inventa días ausentes.
3. Una tarjeta puede estar ausente o reasignarse. En ausencia de tarjeta se usa el nombre como respaldo marcado internamente; esto sigue siendo una limitación de la fuente.
4. Los eventos LPR y biométricos VEH pueden representar el mismo paso físico. El consolidado los denomina eventos y no deduplica entre mecanismos.
5. Los mapas temporales omiten filas con fecha/hora inválida; dichas filas permanecen en totales no temporales y deben interpretarse junto con Calidad de datos.
6. `github_app.py` y `github_statistics_calc.py` son copias antiguas sin referencias, con codificación heredada. Se conservaron hasta que el responsable confirme que pueden archivarse.

