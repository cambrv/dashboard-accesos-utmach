# Mejoras de Analítica Avanzada y Seguridad — Especificaciones

Este documento define formalmente las nuevas funcionalidades de analítica avanzada y el sistema de autenticación para el Dashboard de Accesos Peatonales. Sigue la misma estructura y convención del archivo `REPORTES_ACCESOS_REGLAS.md`.

---

# SPEC A — Analítica Avanzada

## A.1 Usuarios recurrentes con fallos

El sistema debe identificar y reportar a los usuarios que presentan una cantidad inusualmente alta de fallos de reconocimiento facial.

- **Definición de Fallo:** Se tomarán en cuenta los eventos clasificados como `Fallo de reconocimiento`.
- **Top 10:** El dashboard mostrará una tabla o gráfico con el Top 10 de usuarios con mayor cantidad de fallos en el periodo filtrado.
- **Campos mostrados:**
  - `Usuario` (Nombre + Apellido)
  - `Cantidad de fallos`
  - `% del total` (porcentaje que representan sus fallos frente al total de fallos de todos los usuarios en ese periodo)
  - `Punto(s) de acceso` (en cuáles torniquetes o dispositivos ocurrieron)
- **Umbral de Anomalía:** Se define un umbral dinámico o estático para considerar una cantidad de fallos como anormal. Por defecto, un usuario con **más de 5 fallos** en una sola semana, o que represente **más del 5% del total de fallos**, se marcará con una alerta visual.
- **Recomendación:** Para usuarios que superen el umbral, se mostrará el mensaje explícito: > "Se recomienda revisar el registro biométrico o considerar un nuevo enrolamiento."
- **Casos borde:**
  - Usuarios "Desconocido" o vacíos deben excluirse de este ranking para evitar que una categoría genérica acapare el Top 1.
  - El recuento de fallos debe calcularse después de aplicar deduplicaciones estándar de eventos idénticos en el mismo segundo (si las hubiere).

## A.2 Comparación entre periodos

El usuario podrá elegir visualizar una comparativa entre el periodo actual (definido por los filtros generales de fecha) y un periodo anterior de referencia.

- **Selección de periodos:**
  - El sistema tomará el rango de fechas actual seleccionado en la barra lateral (ej. 1 de julio a 7 de julio).
  - Automáticamente calculará un "periodo previo equivalente" (ej. 7 días inmediatamente anteriores, o mismamente el mes anterior si selecciona un mes completo).
  - Alternativamente, puede permitirse seleccionar un "Periodo Base" y un "Periodo de Comparación" personalizados.
- **Métricas a comparar:**
  - Total de eventos registrados.
  - Total de accesos exitosos.
  - Total de accesos denegados.
  - Total de fallos de reconocimiento.
- **Visualización (Tarjetas tipo KPI):**
  - Valor actual.
  - Valor del periodo anterior.
  - Variación Absoluta (`Valor Actual - Valor Anterior`).
  - Variación Porcentual (`(Valor Actual - Valor Anterior) / Valor Anterior * 100`).
  - Indicador de flecha (Arriba/Abajo) y colores (Verde si bajan los fallos, Rojo si suben).
- **Casos borde matemáticos:**
  - Si el periodo anterior tuvo `0` eventos (división por cero), se debe mostrar `N/A` o `---` en lugar de un error o porcentaje infinito.
  - Manejo de fechas inválidas o periodos sin ningún registro.

## A.3 Detección de anomalías

Se implementará un motor básico de alertas automatizadas para identificar comportamientos fuera de lo normal basándose en el dataset filtrado.

- **Tipos de Anomalías:**
  - **Accesos fuera de horario:** Eventos (exitosos o denegados) ocurridos entre las 23:00 y las 05:00 horas.
  - **Pico inusual de denegados:** Un incremento repentino de accesos denegados en una misma hora que supere la desviación estándar histórica o un umbral configurable (ej. más de 20 denegados en 1 hora en un solo punto).
  - **Concentración de fallos en un punto:** Si un único punto de acceso aglomera más del 50% de los fallos de un día, sugiriendo un daño en el equipo.
- **Niveles de severidad:**
  - `INFO`: Comportamientos ligeramente fuera de la media pero explicables (ej. ligeros picos de tráfico).
  - `WARNING`: Anomalías moderadas (ej. un usuario con muchos fallos, accesos nocturnos aislados).
  - `CRITICAL`: Anomalías graves (ej. avalancha de denegados en un punto de acceso, sugiriendo falla técnica o vulneración).
- **Visualización:**
  - Se presentará como un panel de "Alertas" o "Insights".
  - Cada alerta debe indicar: Tipo, Fecha/Hora, Punto de acceso afectado (si aplica), Magnitud (ej. "30 denegados en 1 hora") y Nivel de severidad.

---

# SPEC B — Seguridad y Autenticación

## B.1 Login y Control de Sesión

La aplicación estará protegida por una pantalla de inicio de sesión inicial usando un paquete estándar como `streamlit-authenticator` o un mecanismo de session_state robusto.

- **Flujo:**
  - El usuario ingresa a la aplicación. No se carga ningún dato del Excel ni se muestra información hasta autenticarse.
  - Formulario de Login: Usuario y Contraseña.
  - Mensajes de credenciales incorrectas que no revelen información extra.
  - Botón de Logout en la barra lateral una vez autenticado, que destruya la sesión.
- **Gestión de credenciales:**
  - Las credenciales y configuraciones de seguridad (como *cookies*, claves de firma) **NO estarán hardcodeadas** en el código fuente.
  - Se leerán del archivo `.streamlit/secrets.toml` de Streamlit, asegurando que no se suban al repositorio (`.gitignore`).
  - Las contraseñas en el archivo de secrets estarán cifradas (hasheadas, ej. `bcrypt`).

## B.2 Roles y Permisos

El sistema soportará múltiples niveles de autorización, representados mediante un campo de "rol" asociado al usuario.

- **Roles iniciales:**
  - `admin` (Administrador): Tiene acceso total a todas las funcionalidades, configuración avanzada y exportaciones de todos los niveles.
  - `viewer` (Consulta): Puede visualizar los dashboards interactivos y aplicar filtros, pero sin acceso a exportar reportes (si así se define) o a ver las métricas de seguridad críticas que puedan comprometer la privacidad.
- **Implementación técnica:**
  - El rol se almacenará en `st.session_state` tras un login exitoso.
  - En el flujo principal, se usarán condiciones `if st.session_state.rol == "admin":` para renderizar ciertos componentes (como descargas masivas o configuraciones).

## B.3 Protección de datos

- Los mensajes de error de la aplicación atraparán excepciones genéricas sin exponer rastros de pila (stack traces) ni variables internas.
- Ningún archivo temporal (`.pdf`, `.xlsx`) debe quedar almacenado públicamente en el sistema de archivos del servidor sin protección.
- El archivo `.gitignore` debe asegurar que `.streamlit/secrets.toml` y cualquier base de datos SQLite futura no suba a GitHub.
