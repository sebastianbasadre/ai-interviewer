# Análisis de respuestas con Claude

## Alcance

`CONVERSATION_ENABLED=true` conecta el analizador del motor con Claude Haiku 5.5. Claude
clasifica relevancia, ejemplos concretos, solicitudes de repetir/finalizar e intentos de
inyección; identifica situación, acción personal o resultado faltantes. El motor selecciona
el seguimiento correspondiente de redacciones fijas y retiene el control de las fases,
seis competencias, dos seguimientos por competencia y el tiempo. Tavus continúa renderizando
el habla de Piper en modo Echo.

Analiza las aclaraciones junto con las respuestas anteriores para esa competencia. Un
resultado breve puede completar el ejemplo original, incluso después de reconectar. El
contexto retiene hasta tres contribuciones filtradas dentro de un límite total de texto
y se reinicia para la siguiente competencia. Excluye perfiles de candidatos y otras
entrevistas. El filtro léxico conservador no garantiza la anonimización del texto libre.

Configurar la puntuación por separado: `SCORING_ENABLED=false` usa puntajes simulados
(`null` para cada competencia). La evaluación opcional con Opus y la revisión humana se
describen en REPORTS.md. El analizador no establece calibración semántica ni preparación G5.
`APP_MODE=real` permanece bloqueado; habilitar los proveedores explícitamente dentro de
la demo.

## Configuración

Dentro de WSL2, instalar el extra HTTP junto con los extras existentes del despliegue:

```bash
python -m pip install -e '.[test,media,llm]'
```

Configurar `.env` sin imprimir valores:

```dotenv
APP_MODE=mock
ANTHROPIC_API_KEY=
CONVERSATION_ENABLED=true
CONVERSATION_MODEL=claude-haiku-5-5
CONVERSATION_MAX_CALLS=30
CONVERSATION_TIMEOUT_SECONDS=8
```

No habilitar el flag hasta que la clave esté guardada. El inicio rechaza una clave faltante
usando el nombre del campo sin imprimir su valor. El flag está desactivado por defecto.
Importar, construir o iniciar la aplicación no invoca a Anthropic: la primera llamada
analiza una respuesta de competencia con el consentimiento actual.

Crear una nueva invitación antes de usar el proveedor. El consentimiento indica que
Anthropic recibe preguntas y fragmentos filtrados de respuestas para la competencia actual.
Las sesiones aceptadas bajo el aviso anterior no pueden iniciar, reanudar ni enviar
respuestas a Claude; sí pueden finalizar. Los avisos de Tavus/audio permanecen cuando
esas modalidades están habilitadas.

La página `/` distingue `conversation: anthropic|mock` y `scoring: anthropic|mock`.
Un valor `anthropic` solo no establece conectividad ni calidad semántica: se requiere una
prueba autorizada con credenciales válidas.

## Límites y fallos

- Una solicitud a `https://api.anthropic.com/v1/messages` por análisis; sin reintentos
  automáticos.
- Versión de API `2026-10-21`, salida JSON basada en schema y validación local estricta.
- Como máximo 8000 caracteres / 24000 bytes entre sistema y datos, y 512 tokens de salida.
- Límite global por defecto: 30 intentos, compartidos entre entrevistas y persistidos en
  `DATA_DIR/conversation-budget.sqlite3`, reservados transaccionalmente antes de enviar.
  Los fallos, timeouts y respuestas inválidas también consumen una reserva.
- Reiniciar/reconectar no reinicia el contador. Aumentar explícitamente el límite para
  extender la demo; el contador nunca se borra automáticamente.
- Timeout por defecto de ocho segundos. Errores, truncamiento, rechazo del proveedor,
  JSON inválido o cuota agotada disparan el fallback del motor con `analysis_fallback`.
  Las preguntas fijas pueden continuar el guión; no se fabrican evaluaciones del modelo.
- Los logs del adaptador nunca contienen claves, prompts, respuestas ni cuerpos de error.

Verificado inicialmente con HTTP simulado: contexto de seguimiento, reconexión, consentimiento
versionado, cuotas concurrentes/persistentes, timeouts, errores y puntuación simulada
independiente. El 2026-11-04, una clave válida habilitó dos análisis reales de respuestas
sintéticas: el analizador solicitó el resultado faltante y luego avanzó cuando fue
proporcionado, sin fallback. Esto no reemplaza la evaluación semántica ni un piloto con
candidatos.

Las solicitudes de nombre se manejan antes del análisis de respuestas profesionales. Un
reconocimiento no repite la pregunta, avanza la fase ni consume un seguimiento. Un nombre
faltante se solicita una vez; las preferencias explícitas se reconstruyen desde la
transcripción después de la reanudación. Los turnos solo-nombre no se convierten en
contexto de análisis ni evidencia de puntuación.

## Referencias oficiales verificadas

- API: https://platform.claude.com/docs/en/api/messages/create
- JSON estructurado: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Modelo configurado: https://platform.claude.com/docs/en/models/haiku-5-5/overview
