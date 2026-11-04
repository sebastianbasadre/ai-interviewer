# Informes basados en evidencia y revisión humana

## Uso

Abrir `https://192.168.2.6:8443/admin/review` e ingresar `ADMIN_API_KEY` desde `.env`.
La clave permanece en memoria del navegador hasta el logout/recarga, nunca en localStorage,
cookies ni URLs. La página de inicio de sesión es pública, pero la lista, los informes,
las citas y la descarga HTML requieren la cabecera `X-Admin-Key`.

La lista muestra entrevistas y el estado del informe. Con la generación automática
habilitada, el cierre normal inicia un trabajo en segundo plano. La entrevista termina
inmediatamente; la evaluación aparece cuando las tres ejecuciones se completan. Generar/
reintentar informes de entrevistas completadas desde la lista. Reintentar puede consumir
otras tres evaluaciones; solicitar un informe ya almacenado devuelve el resultado existente
sin otra llamada al proveedor.

Cada competencia muestra un puntaje de 1–5 o **Evidencia insuficiente**, fundamento,
citas literales de fragmentos filtrados y la dispersión entre tres evaluaciones. Expandir
los anclajes de la rúbrica para comparar puntajes. Los informes permanecen pendientes de
revisión humana y nunca toman decisiones de contratación. La descarga HTML independiente
escapa el contenido del candidato/modelo.

## Evaluación

`SCORING_ENABLED=true` usa Claude Opus 5.5 con la rúbrica aprobada y la transcripción
profesional filtrada. Excluye perfiles de candidatos, audio, video y company_info.
La sanitización es conservadora y léxica; no puede garantizar la anonimización de texto
libre arbitrario. Validar las seis competencias, puntajes enteros 1–5 y referencias a
turnos reales del candidato. Cada cita debe pertenecer a la competencia, excepto
Comunicación, que acepta evidencia entre competencias. IDs desconocidos, turnos del
entrevistador, duplicados y contenido excluido no pueden justificar un puntaje.

Ejecutar tres evaluaciones. Si alguna encuentra evidencia insuficiente, dejar el puntaje
final como `null`; nunca convertirlo automáticamente en 1. Con tres números válidos, usar
la mediana junto con el fundamento/citas de esa evaluación. Marcar diferencias mayores a
un punto. Nunca publicar un informe parcial sin tres evaluaciones válidas.

Esto valida estructura y referencias, no relevancia semántica, calibración ni ausencia de
sesgo. El ejemplo retenido es completamente sintético, no es una evaluación de una persona
real.

## Configuración

```dotenv
ANTHROPIC_API_KEY=
SCORING_ENABLED=true
SCORING_MODEL=claude-opus-5-5
SCORING_AUTO_GENERATE=true
SCORING_MAX_CALLS=12
SCORING_TIMEOUT_SECONDS=45
```

Requiere el extra `llm` basado en HTTPX. La plantilla deja el flag deshabilitado por
defecto. `APP_MODE=mock` retiene el motor de demo; `/` distingue los proveedores de
conversación/puntuación por separado. Construir o iniciar la app no llama a Opus.

Cada informe reserva atómicamente tres intentos en `DATA_DIR/scoring-budget.sqlite3`.
El límite global persiste entre entrevistas, reconexiones y reinicios. Sin reintentos
automáticos. Los fallos, cancelaciones y rechazos de schema también consumen reservas
conservadoras. El modelo recibe como máximo 50000 caracteres / 100000 bytes de contexto
y genera como máximo 4096 tokens por ejecución. Estos límites no son un presupuesto
monetario.

Las claves faltantes causan rechazo en el inicio nombrando el campo. Los errores/salida
inválida dejan un trabajo fallido que requiere reintento explícito. Al reiniciar, los
trabajos interrumpidos se marcan como fallidos en lugar de facturarse automáticamente
de nuevo. Los informes almacenados sobreviven. Eliminar una entrevista también elimina
su informe/estado de trabajo; el contador global de uso se retiene y no contiene datos
personales.

## Consentimiento y privacidad

Habilitar la puntuación agrega un aviso explícito: Anthropic recibe la rúbrica y fragmentos
de la transcripción para proponer puntajes con citas para revisión humana. Crear una nueva
invitación después de habilitarlo. El aviso anterior de puntuación simulada no autoriza
evaluación real; el inicio/reanudación/envío de respuestas o la generación de informes
reales con ese consentimiento se rechaza. Los informes simulados existentes permanecen
etiquetados como registros históricos. Los candidatos pueden finalizar sesiones antiguas
sin autorizar la puntuación real.

## Endpoints

- `GET /admin/review`: shell de inicio de sesión y revisión; no contiene datos privados.
- `GET /admin/interviews`: lista autenticada, estado de sesión/informe, modo de puntuación.
- `POST /admin/interviews/{id}/report`: generar o devolver el informe existente.
- `GET /admin/interviews/{id}/report`: JSON validado.
- `GET /admin/interviews/{id}/review`: informe, citas filtradas y rúbrica para la UI.
- `GET /admin/interviews/{id}/report.html`: descarga autenticada para revisión humana.

## Verificación real — 2026-11-04

Usado `evals/report_fixture.py`: seis competencias, omitiendo deliberadamente un ejemplo
de Métricas. Opus dejó Métricas null y citó evidencia existente para los cinco puntajes
numéricos. Tres ejecuciones completadas en aproximadamente 33 segundos. Un rechazo de
API de enum nullable se corrigió usando anyOf y validación de rango local estricta. Sin
sesiones Tavus utilizadas. Verificación en Chrome: seis competencias, siete citas y seis
rúbricas; descarga HTML válida, logout y cero errores JavaScript. Suite final en ese punto
de control: 140 pruebas.

Fuente del modelo/precios: https://platform.claude.com/docs/en/models/opus-5-5/overview.
JSON estructurado: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.
