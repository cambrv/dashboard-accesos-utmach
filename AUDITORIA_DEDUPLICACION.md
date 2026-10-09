# Auditoría de duplicados y archivos Excel

Fecha: 2026-10-08  
Alcance: análisis no destructivo. No se modificaron los Excel, no se movieron archivos y no se cambió el algoritmo utilizado por el dashboard.

## 1. Inventario de archivos Excel

| Archivo | Tamaño | Clasificación | Contenido observado | Uso por la aplicación | Git |
|---|---:|---|---|---|---|
| `EVENTOS_MES 7SEP-7OCT.xlsx` | 36.982.367 bytes | Exportación original HikCentral | Autenticación biométrica, 07/09/2026–07/10/2026, encabezado en fila 11 | El usuario debe subirlo; no hay ruta codificada | Ignorado por `*.xlsx` |
| `PLACAS_MES 7SEP-7OCT.xlsx` | 1.773.139 bytes | Exportación original HikCentral ANPR | 38.123 filas LPR, encabezado en fila 7 | El usuario debe subirlo; no hay ruta codificada | Ignorado por `*.xlsx` |
| `mock_lpr.xlsx` | 5.657 bytes | Muestra manual de prueba | Una fila con estructura ANPR | No referenciado; las pruebas automatizadas crean Excel en memoria | Ignorado por `*.xlsx` |
| `mock_lpr2.xlsx` | 5.767 bytes | Muestra manual de prueba | Dos filas con estructura ANPR | No referenciado | Ignorado por `*.xlsx` |
| `test_lpr_real.xlsx` | 5.856 bytes | Recorte local de prueba | Tres filas con estructura ANPR y datos con apariencia real | No referenciado | Ignorado por `*.xlsx` |

La búsqueda cubrió imports, llamadas a `read_excel`, rutas, nombres de archivo y configuración. `app.py` usa dos `st.file_uploader`; `excel_processor.leer_excel_centralizado()` recibe el objeto subido. Ningún script activo usa rutas absolutas o relativas hacia esos cinco archivos. `tests/test_app_load_flow.py` genera libros en memoria. Los imports `os` y `glob` presentes en `app.py` no se utilizan para localizar datasets.

### Recomendación de organización

No se movió ningún archivo durante esta auditoría. Cuando se autorice la organización:

- Guardar las dos exportaciones originales y los recortes con datos reales en `data/local/`, que debe permanecer ignorado por Git.
- Usar `data/samples/` únicamente para muestras completamente sintéticas y anonimizadas que puedan versionarse de forma intencional.
- No publicar los tres archivos pequeños actuales sin revisar matrículas y nombres. Sus valores tienen apariencia real, por lo que no deben asumirse sintéticos por llamarse `mock` o `test`.
- Mantener `*.xlsx` en `.gitignore`; opcionalmente añadir reglas explícitas para `data/local/` y un archivo documental sin datos.

## 2. Mapa del procesamiento y la deduplicación

| Etapa | Archivo y función | Comportamiento |
|---|---|---|
| Lectura | `excel_processor.py`, `leer_excel_centralizado()` | Detecta la fila de encabezado. Para LPR conserva matrícula, hora, cámara, lista y propietario. No deduplica. |
| Detección de columnas | `lpr_data_loader.py`, `detectar_columnas_lpr()` | Asocia columnas del export con matrícula, hora, cámara, lista y propietario. No deduplica. |
| Normalización LPR | `lpr_data_processing.py`, `procesar_datos_lpr()` | Matrícula: texto, `strip`, mayúsculas. Cámara: texto, `strip`, mayúsculas y espacios repetidos normalizados. Convierte la hora y clasifica dirección/campus. |
| Exclusiones por validez | `lpr_data_processing.py`, `procesar_datos_lpr()` | Elimina horas inválidas y matrículas vacías o tokens como `NAN`, `NONE`, `NO PLATE`. Actualmente no devuelve un DataFrame separado con esas exclusiones. |
| Deduplicación vigente | `lpr_data_processing.py`, `deduplicar_eventos_vehiculares()` | Se ejecuta después de normalizar y antes de calcular estadísticas. Devuelve `df_valido` y `df_duplicados`. |
| Orquestación | `app.py`, `_preparar_lpr_sesion()` | Llama al procesamiento y luego a la deduplicación una vez por archivo/sesión. Guarda ambos DataFrames en estado de sesión. |
| Estadísticas | `lpr_statistics_calc.py` | Recibe el DataFrame ya reducido. No realiza una segunda deduplicación. |
| Consolidación | `lpr_statistics_calc.py`, `consolidar_eventos_vehiculares()` | Combina biométrico VEH y LPR sin deduplicar entre mecanismos. |
| Biométrico | `all_events_data_processing.py`, `procesar_datos_todos()` | Normaliza y clasifica, pero no usa `drop_duplicates` ni elimina intentos consecutivos. |

No se encontró otra deduplicación activa después de `deduplicar_eventos_vehiculares()`.

## 3. Algoritmo LPR vigente, paso a paso

1. Ordena por `Matricula` y `Hora`.
2. Crea mediante `shift(1)` la matrícula, dirección y hora de la fila bruta inmediatamente anterior.
3. Conserva la fila cuando se cumple al menos una condición:
   - la matrícula cambió;
   - la dirección cambió;
   - el intervalo con la fila anterior es estrictamente mayor a 14.400 segundos.
4. Descarta el resto.
5. Elimina las columnas auxiliares y vuelve a ordenar solo los registros conservados por hora.

### Respuestas directas sobre la regla

- Columnas efectivas: matrícula, hora y dirección.
- Cámara: no se considera.
- Campus: no se considera.
- Dirección: sí; cualquier cambio entrada/salida conserva la fila incluso en el mismo segundo.
- Ventana: una diferencia exactamente igual a cuatro horas se descarta; debe ser mayor a cuatro horas para conservar.
- Referencia temporal: fila bruta inmediatamente anterior, no último evento conservado.
- Orden: las fechas distintas se ordenan cronológicamente. Para igual matrícula e igual segundo no existe desempate por cámara, dirección o identificador de origen, por lo que el orden de entrada puede cambiar el resultado.

Ejemplo del efecto de cadena: eventos de entrada a las 08:00, 11:00 y 13:00. Solo se conserva 08:00. El evento 13:00 está cinco horas después del último conservado, pero se compara contra 11:00 y se descarta.

En el Excel real, una versión equivalente que compara contra el último evento conservado retendría 37.220 filas, seis más que la regla vigente.

## 4. Reproducción con el Excel LPR real

| Etapa | Registros |
|---|---:|
| Filas exportadas | 38.123 |
| Filas válidas después de normalización | 38.123 |
| Conservadas por la regla vigente | 37.214 |
| Descartadas por la regla vigente | 909 |
| Filas completamente idénticas en las 13 columnas exportadas | 1 |

No hubo horas o matrículas inválidas en este archivo. La regla descarta el 2,38 % de los registros procesados. Solo una de las 909 exclusiones es una fila exactamente repetida.

### Clasificación exclusiva de los 909 descartes

Se usó un umbral descriptivo de 120 segundos para separar ráfagas cortas. Este umbral no prueba que exista un duplicado físico.

| Categoría | Casos | Porcentaje de los 909 | Interpretación permitida |
|---|---:|---:|---|
| Duplicado exacto normalizado | 1 | 0,11 % | Único caso con evidencia fuerte de repetición técnica. |
| Misma matrícula, cámara y dirección, 0–120 s | 375 | 41,25 % | Compatible con capturas repetidas, pero no concluyente. |
| Cámara diferente, mismo campus | 163 | 17,93 % | Puede representar cámaras consecutivas o un recorrido legítimo. |
| Campus diferente | 146 | 16,06 % | No debe tratarse automáticamente como la misma maniobra. |
| Misma matrícula, cámara y dirección, más de 120 s | 224 | 24,64 % | Alta ambigüedad; incluye posibles nuevas visitas. |
| Otros | 0 | 0,00 % | No hubo direcciones/campus inválidos entre los descartes. |

Distribución de intervalos de los descartes:

| Medida | Segundos |
|---|---:|
| Mínimo | 0 |
| Percentil 25 | 14 |
| Mediana | 60 |
| Percentil 75 | 5.524 |
| Percentil 90 | 10.377,8 |
| Percentil 95 | 12.669,6 |
| Máximo | 14.393 |

178 casos están dentro de 10 segundos, 426 dentro de 30, 455 dentro de 60 y 470 dentro de 120. Hay 439 casos por encima de 120 segundos y 295 por encima de una hora.

### Ejemplos reales anonimizados

Los alias no conservan la matrícula ni el propietario.

| Categoría | Alias | Fecha y hora | Cámara previa → cámara actual | Dirección | Intervalo |
|---|---|---|---|---|---:|
| Exacto | PLACA-0509 | 14/09/2026 05:53:45 | FERROV ENT VEH 1 → FERROV ENT VEH 1 | Entrada | 0 s |
| Misma cámara, corto | PLACA-0097 | 25/09/2026 11:45:08 | FERROV SAL VEH 1 → FERROV SAL VEH 1 | Salida | 1 s |
| Otra cámara, mismo campus | PLACA-0815 | 28/09/2026 04:40:20 | FERROV ENT VEH 2 → FERROV ENT VEH 1 | Entrada | 1 s |
| Campus diferente | PLACA-0770 | 07/10/2026 11:02:21 | 25 JUNIO SAL VEH 2 → FERROV SAL VEH 2 | Salida | 87 s |
| Misma cámara, intervalo largo | PLACA-0246 | 22/09/2026 21:51:48 | FERROV SAL VEH 1 → FERROV SAL VEH 1 | Salida | 121 s |

Estos ejemplos son candidatos estadísticos. La información disponible no permite afirmar si corresponden al mismo cruce físico.

## 5. Sensibilidad al orden

Se encontraron cinco grupos con la misma matrícula y el mismo segundo; cuatro contienen más de una dirección. Al invertir el orden original y volver a ordenar con las mismas claves incompletas:

- los registros conservados pasaron de 37.214 a 37.212;
- cuatro identificadores cambiaron de estado entre conservado y descartado.

La causa es que secuencias empatadas `Entrada, Entrada, Salida` conservan dos filas, mientras que `Entrada, Salida, Entrada` conserva tres. Una regla futura debe utilizar un identificador de origen como desempate y definir explícitamente el tratamiento de eventos simultáneos.

## 6. Estrategias simuladas

Las simulaciones C y D comparan con el último evento conservado dentro de su clave. No modifican el Excel ni el algoritmo productivo.

- A: regla vigente de matrícula + dirección + cuatro horas, comparando con la fila bruta previa.
- B: elimina únicamente filas exactamente iguales en los campos analíticos normalizados. Coincide con una fila idéntica en las 13 columnas originales.
- C: matrícula + cámara + dirección + ventana corta.
- D: matrícula + campus + dirección + ventana corta.

| Estrategia | Conservados | Descartados | Entradas | Salidas | Ferroviaria | 25 de Junio | Hora pico | Reg. hora pico | Prom./min franja pico | Máx. minuto en franja pico | Máx. minuto global |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A actual 4 h | 37.214 | 909 | 18.863 | 18.351 | 12.816 | 24.398 | 06:00 | 5.105 | 2,745 | 13 | 14 |
| B exactos | 38.122 | 1 | 19.410 | 18.712 | 13.346 | 24.776 | 06:00 | 5.207 | 2,799 | 13 | 17 |
| C cámara 10 s | 37.963 | 160 | 19.333 | 18.630 | 13.247 | 24.716 | 06:00 | 5.190 | 2,790 | 13 | 17 |
| D campus 10 s | 37.958 | 165 | 19.329 | 18.629 | 13.244 | 24.714 | 06:00 | 5.190 | 2,790 | 13 | 17 |
| C cámara 30 s | 37.820 | 303 | 19.224 | 18.596 | 13.111 | 24.709 | 06:00 | 5.173 | 2,781 | 13 | 17 |
| D campus 30 s | 37.730 | 393 | 19.135 | 18.595 | 13.104 | 24.626 | 06:00 | 5.128 | 2,757 | 13 | 14 |
| C cámara 60 s | 37.766 | 357 | 19.181 | 18.585 | 13.063 | 24.703 | 06:00 | 5.168 | 2,778 | 13 | 17 |
| D campus 60 s | 37.676 | 447 | 19.092 | 18.584 | 13.055 | 24.621 | 06:00 | 5.123 | 2,754 | 13 | 14 |
| C cámara 120 s | 37.741 | 382 | 19.165 | 18.576 | 13.045 | 24.696 | 06:00 | 5.167 | 2,778 | 13 | 17 |
| D campus 120 s | 37.648 | 475 | 19.074 | 18.574 | 13.035 | 24.613 | 06:00 | 5.122 | 2,754 | 13 | 14 |

Todos los escenarios mantienen 06:00–07:00 como la franja de mayor volumen. El máximo real dentro de esa franja permanece en 13; el máximo global cambia porque la mayor concentración de un minuto concreto ocurre fuera de la franja pico acumulada.

### Efecto por cámara

La tabla muestra el escenario vigente y dos alternativas de 30 segundos. B solo resta una fila en `FERROV ENT VEH 1`.

| Cámara | Original | A actual | B exacta | C 30 s | D 30 s | Cambio A | Cambio C30 | Cambio D30 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 JUNIO ING VEH 1 | 4.344 | 4.219 | 4.344 | 4.341 | 4.259 | -125 | -3 | -85 |
| 25 JUNIO ING VEH 2 | 8.506 | 8.408 | 8.506 | 8.487 | 8.487 | -98 | -19 | -19 |
| 25 JUNIO SAL VEH 1 | 7.777 | 7.680 | 7.777 | 7.760 | 7.759 | -97 | -17 | -18 |
| 25 JUNIO SAL VEH 2 | 4.149 | 4.091 | 4.149 | 4.121 | 4.121 | -58 | -28 | -28 |
| FERROV ENT VEH 1 | 4.670 | 4.448 | 4.669 | 4.568 | 4.566 | -222 | -102 | -104 |
| FERROV ENT VEH 2 | 1.891 | 1.788 | 1.891 | 1.828 | 1.823 | -103 | -63 | -68 |
| FERROV SAL VEH 1 | 6.102 | 5.961 | 6.102 | 6.042 | 6.042 | -141 | -60 | -60 |
| FERROV SAL VEH 2 | 684 | 619 | 684 | 673 | 673 | -65 | -11 | -11 |

La estrategia D agrupa cámaras del mismo campus y, por ello, elimina eventos adicionales aunque provengan de cámaras distintas. Sin un mapa físico de carriles y secuencia de cámaras, esa agrupación es metodológicamente más arriesgada que C.

## 7. Eventos biométricos

No existe deduplicación biométrica en `all_events_data_processing.py`, en el loader ni en las estadísticas activas. El número de tarjeta se usa como identidad analítica, no como criterio de eliminación.

Auditoría no destructiva del Excel real:

| Diagnóstico | Pares o filas observados |
|---|---:|
| Filas cargadas y conservadas | 590.107 |
| Filas completamente idénticas | 117 |
| Misma identidad dentro de 1 segundo | 2.276 |
| Misma identidad, dispositivo y resultado dentro de 10 segundos | 74.758 |
| Misma identidad y dispositivo, pero resultado distinto dentro de 30 segundos | 2.428 |
| Misma identidad, dispositivo distinto, dentro de 30 segundos | 15.240 |

Los diagnósticos temporales son conteos de pares adyacentes y pueden solaparse; no deben sumarse. Ninguno se elimina. Este comportamiento es adecuado para preservar intentos fallidos, reintentos y eventos de dispositivos diferentes. Las 117 filas exactas pueden auditarse por separado en el futuro, pero no deberían eliminarse sin una política de trazabilidad porque incluso filas idénticas pueden representar mensajes repetidos del equipo o eventos reenviados por el sistema.

## 8. Trazabilidad recomendada

La implementación actual separa `df_valido` y `df_duplicados`, pero elimina las columnas de referencia antes de devolverlos. Los registros con hora o matrícula inválida se filtran antes y no se devuelven como población auditable.

Una implementación futura debería conservar una tabla de decisiones con:

- `Registro_ID_Origen`: identificador inmutable asignado al leer la fila.
- `Estado_Validacion`: válido, hora inválida o matrícula inválida.
- `Estado_Deduplicacion`: conservado, duplicado exacto o repetición potencial.
- `Razon_Decision`: código explícito de la regla aplicada.
- `Registro_Referencia_ID`: evento contra el que se comparó.
- `Delta_Segundos`, cámara, campus y dirección de ambos eventos.
- `Clave_Regla` y `Version_Regla`.
- `Incluido_Analitica`: booleano derivado, sin borrar el registro original.

Las cinco poblaciones deben poder reconciliarse:

`originales = inválidos + duplicados exactos + repeticiones potenciales excluidas + analíticos conservados`.

Las repeticiones potenciales que solo se marquen, sin excluirse, siguen perteneciendo a los analíticos conservados; la tabla debe evitar doble conteo mediante estados excluyentes y banderas auxiliares.

## 9. Recomendación final

La estrategia A no es apropiada como deduplicación automática para medir movilidad vehicular. Elimina registros en cámaras y campus diferentes, acepta cadenas dependientes de la fila previa y presenta sensibilidad al orden en empates.

Recomendación conservadora:

1. Usar B como única exclusión automática inicialmente: fila exactamente repetida, con razón trazable.
2. Crear una bandera de `repetición potencial` basada en C con matrícula + cámara + dirección y una ventana inicial de 10 segundos.
3. Mantener esas repeticiones disponibles y publicar, durante un período de validación, ambas cifras: eventos LPR observados y eventos después de excluir candidatos técnicos.
4. Validar la ventana con información física de cámaras, carriles, frecuencia de captura y secuencia esperada antes de aumentar a 30, 60 o 120 segundos.
5. No usar D ni una ventana de cuatro horas sin evidencia adicional. Campus no identifica una misma cámara o maniobra, y cuatro horas permite eliminar nuevas visitas plausibles.

Si se exige una única población para movilidad antes de contar con esa evidencia, B es la opción más defendible porque solo altera una fila y evita afirmar que eventos ambiguos son duplicados físicos.

## 10. Pruebas añadidas

`tests/test_deduplication_audit.py` caracteriza sin modificar producción:

- cámara y campus ignorados por la regla actual;
- cambios de dirección conservados;
- límite exacto de cuatro horas;
- comparación contra fila bruta anterior;
- sensibilidad al orden en el mismo segundo;
- diferencia de alcance entre estrategias por cámara y por campus;
- conservación de duplicados exactos e intentos biométricos con resultado diferente.

