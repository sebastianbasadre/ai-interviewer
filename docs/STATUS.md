# Estado del proyecto

Este archivo registra puntos de control cronológicos. Las entradas posteriores reemplazan
elementos pendientes anteriores; los conteos históricos de pruebas se refieren a snapshots
separados y no son acumulativos.

## Fase inicial

Fase 0 preparada excepto credenciales; G1 y G2 aprobados por el dueño; Fase 2 en
desarrollo.

## Tareas en el punto de control inicial

- [x] Leer CLAUDE.md, README, el prompt del orquestador y las siete guías de agentes.
- [x] Verificar acceso SSH a sbasadre@192.168.2.6 con la identidad existente.
- [x] Verificar Windows 11 + WSL2 NVIDIA-Workbench y RTX 3090 (24 GB).
- [x] Instalar Python 3.12.16 en el espacio de usuario WSL usando uv 0.13.6.
- [x] Crear /home/workbench/.venvs/ai-interviewer en el homelab.
- [ ] Completar credenciales .env: plantilla creada y en .gitignore; sin secretos leídos ni impresos en este punto de control.
- [x] Arquitectura, contratos, ADRs, configuración, Makefile y CI (architect).
- [x] Homelab make test: 15 pasados (Python 3.12.16).
- [x] Revisión independiente: APPROVE; eventos del motor y restauración de snapshot corregidos.
- [x] G1 aprobado por el dueño (OK).
- [x] G2 guión/rúbrica PM/PO aprobado por el dueño (SÍ), con revisión técnica APPROVE y 19 pruebas pasando.
- [ ] API/almacenamiento y pipeline simulado en ramas aisladas; integrar solo después de pruebas pasando y APPROVE.

## Decisiones iniciales

- El dueño especificó la ejecución en el homelab 192.168.2.6 por SSH, no en el PC local.
- Mantener el stack y Python 3.12; ejecutar Linux a través del WSL2 del homelab.
- Avatar simulado; sin servicios pagados, evaluaciones reales ni contacto con candidatos en este punto de control.
- Git necesita una excepción safe.directory para la propiedad SMB; aplicar por comando, no globalmente.
- Arquitectura integrada por fast-forward después de pruebas, APPROVE y G1. Ramas de Fase 2:
  feat/interview-engine-role, feat/web-api-pilot y feat/pipeline-mock.

## Trabajo pendiente inicial

Evaluaciones pagadas G3; Tavus G4; piloto real G5. GPU visible en WSL; compatibilidad real
Whisper/CUDA sin verificar. Mantener retención propuesta de 30 días. Alcance de video
persistido pendiente; no implementarlo aún. Los puntos de control web/API y pipeline de
Fase 2 usaron worktrees aislados, aún no integrados ni declarados completos; reanudados
después de la aprobación G2.

## Desarrollo después de G2

- Motor/puntuación: implementación offline lista; correcciones STAR y prueba de privacidad
  en e86e064 (53 pruebas homelab), esperando re-revisión.
- API/almacenamiento: eaac62c (34 pruebas); correcciones de carrera start/watchdog y
  recuperación de finish en progreso.
- Pipeline: 7d27646 (36 pruebas con Pipecat); control de habla/concurrencia corregido.
  Las interrupciones durante la generación se detienen de forma segura hasta la integración
  transaccional de factory/restore.
- Contrato factory/restore: fb44d52 del architect, esperando integración/revisión.
- QA: harness offline/E2E en desarrollo; 78 pruebas en el snapshot de trabajo combinado,
  sin llamadas reales.
- Runtime: composición local con simulados y comandos de desarrollo en progreso.

Los conteos se refieren a snapshots diferentes y no deben sumarse. Ninguna rama de
implementación se integra sin re-revisión y pruebas.

## Integración verificada

- Motor e86e064 y API 12b30e6: re-revisión APPROVE, integrados en orden.
- QA 36b0508: herramientas offline APROBADAS; integradas por cherry-pick 36f6b11.
- Homelab main combinado: 82 pruebas pasando; 33 sesiones sintéticas offline, cero fallos
  estructurales.
- Runtime 6451d2a: APROBADO; runtime.py, __main__.py, replace_progress implementado,
  transacciones BEGIN IMMEDIATE reforzadas, VACUUM por lotes. Integrado en main.
- Calidad semántica real, ranking y latencia sin evaluar.
- Antes de G3: integrar feat/pipeline-mock (requiere re-revisión con el contrato
  factory/restore de main), luego preparar un adaptador real con reserva de presupuesto y
  una fábrica de eval auditada.

## Demo de audio local — 2026-11-03

- El checkout de esta carpeta desplegado por separado en
  `/home/workbench/projects/ai-interviewer-folder-review`; cambios sin fusionar/confirmar.
- API de texto, seguimiento simulado limitado a uno por competencia y acceso LAN verificados.
- HTTPS en `https://192.168.2.6:8443`, certificado de desarrollo con IP SAN.
- Pipecat 1.15.0, Silero, Whisper small CPU y Piper es_AR-daniela-high conectados a la sala.
- Coturn TCP autenticado habilita WebRTC de Chrome por LAN a través del NAT de WSL.
- Smoke real del navegador: contexto seguro, par conectado, 819 paquetes de audio recibidos,
  habla sintética transcrita, motor avanzado a warmup. Sin voces de candidatos reales.
- 96 pruebas offline pasando antes de ajustes finales de documentación/lanzador.
- Sin archivos de audio/video retenidos: transcripción almacenada con consentimiento específico.
- TavusVideoService preparado como etapa opcional; claves/réplica faltantes, sin uso.
- G4 pendiente: proporcionar claves, confirmar minutos/costo, probar video/sincronización/cierre.
- Modelo de evaluación aún simulado; G3, latencia cuantitativa y G5 no aprobados.
- Operaciones, reinicio y limitaciones: MEDIA_SETUP.md.

## Migración Tavus Face/PAL — 2026-11-03

- Configuración: TAVUS_API_KEY, TAVUS_FACE_ID, TAVUS_PAL_ID (Echo PAL).
- TAVUS_REPLICA_ID retenido como fallback de configuración legacy.
- Adaptador HTTP-session de Pipecat 1.15: crear con face_id/pal_id, consultar nombres
  mediante /pals, cerrar mediante /conversations/{id}/end; SDK instalado sin cambios.
- Duración máxima también enviada a Tavus; grabación explícitamente deshabilitada.
- Dobles HTTP y validación real del cliente/constructor SDK; sin llamadas pagadas.
- Validación final: 114 pruebas Pipecat-venv pasando; 112 pasadas y dos omitidas (SDK
  opcional) en el venv de texto. Runtime desplegado con health/media_ready saludable.
- Compatibilidad de video en vivo/recurso de cuenta aún esperando G4 en este punto de control.
- Dueño confirmó nuestro motor con Tavus solo como avatar: Pipecat, Whisper/Piper y Echo
  PAL. No reemplazar esto con el embed completo del pipeline de Tavus.
- Credencial Tavus configurada; Echo PAL creado con Anna Face rc9cff32ceba y verificado
  desde el homelab. IDs y secreto almacenados en archivos .env locales/runtime.
- Sin conversación Tavus iniciada aún; video permaneció deshabilitado pendiente G4.

## Primera prueba real de Tavus — 2026-11-03

- Dueño aprobó G4 para una prueba de hasta un minuto. Límites de media/Tavus establecidos
  en un minuto, enviados al proveedor como max_call_duration=60.
- Conversación real Anna Echo PAL probada en Chrome por HTTPS LAN.
- Video 1280×720 recibido (185 frames decodificados), audio (417 paquetes recibidos),
  transcripción sintética y avance del motor a warmup. Sin candidatos reales.
- El botón Finalizar cerró la entrevista; API de Tavus confirmó finalización. Datos
  sintéticos de la entrevista local eliminados. Uso monetario exacto pendiente de la
  cuenta Tavus.
- Avatar runtime habilitado con un minuto por conexión; las nuevas conexiones consumen
  minutos de la cuenta. Esto no aprueba un piloto ni evaluación de candidatos reales.
- Sin medición formal de latencia p50/p95 ni sincronización audiovisual; G5 no reclamado.

## Integración del analizador Claude — 2026-11-03

- Adaptador Anthropic Messages opcional con salida JSON y clasificación estricta.
- Los seguimientos apuntan a situación/acción/resultado faltantes; contexto acotado a la
  competencia y retenido al reconectar. El motor retiene las transiciones.
- El consentimiento versionado identifica a Anthropic y bloquea el consentimiento anterior
  antes del envío al proveedor.
- Límite global persistente de 30 intentos; 512 tokens de salida, timeout, errores sin
  contenido y sin reintentos automáticos.
- 132 pruebas homelab pasando con dobles HTTP. Puntuación aún simulada.
- ANTHROPIC_API_KEY faltante del .env local/runtime cuando se implementó; CONVERSATION_ENABLED
  deshabilitado. Sin llamadas reales ni costo de Anthropic.
- Activación/prueba esperando credenciales; ver CONVERSATION_SETUP.md.

## Credencial Anthropic verificada — 2026-11-04

- ANTHROPIC_API_KEY presente localmente; autenticación/acceso al modelo confirmado mediante
  GET /v1/models/claude-haiku-5-5, sin inferencia.
- Homelab 192.168.2.6 inalcanzable por SSH/22 y HTTP(S)/8000/8443 desde esta sesión.
- No se pudo sincronizar la clave ni activar el runtime remoto. Recuperar conectividad
  y ejecutar el smoke test de respuesta sintética.

## Claude habilitado y probado — 2026-11-04

- Homelab alcanzable nuevamente. Clave sincronizada por SSH y CONVERSATION_ENABLED=true
  en la configuración del runtime; runtime y media saludables preparados.
- Smoke real de la API con consentimiento actualizado: ejemplo sin resultado disparó un
  seguimiento STAR (3.620 s); una aclaración del resultado completó el ejemplo y avanzó a
  la siguiente competencia (1.409 s), sin analysis_fallback. Estos son tiempos de
  clasificación, no medidas de latencia audiovisual p50/p95.
- Dos intentos Anthropic reservados del límite persistente de 30 intentos. Datos sintéticos
  eliminados.
- Sin conversación Tavus durante esta prueba. Media permanece limitado a un minuto por
  conexión. Nueva invitación preparada con consentimiento Anthropic.
- Puntuación aún simulada; sin evaluaciones grandes ni piloto real aprobado.
- Windows retuvo reglas portproxy sin escuchas LAN después de la interrupción; reiniciar
  IP Helper (iphlpsvc) restauró 8000, 8443 y 3479 en 192.168.2.6. HTTPS, nuevo consentimiento
  y TURN TCP verificados desde otra máquina LAN.

## Informe Opus y revisión humana — 2026-11-04

- Puntuación real opcional con Claude Opus 5.5 con tres ejecuciones; retiene validación
  de rúbrica/citación de candidatos, mediana/dispersión, y null si alguna ejecución carece
  de evidencia.
- Reserva global persistente de tres intentos por informe; límite configurado de 12.
- Generación automática en segundo plano cuando terminan sesiones con consentimiento
  actualizado. Los fallos y cancelaciones no invalidan el cierre ni publican informes
  parciales.
- /admin/review privado; ADMIN_API_KEY solo en memoria. Las descargas de datos/HTML
  requieren autenticación. Incluye citas filtradas, anclajes de rúbrica y estado de
  revisión humana pendiente.
- Prueba real de fixture sintético: Métricas null; otros cinco puntajes numéricos citan
  evidencia existente. Tres evaluaciones completadas en 33.2 segundos. Sin Tavus.
- Error HTTP 400 de rechazo de schema (enum nullable) corregido con anyOf y validación de
  rango local. Reservas conservadoras consumidas: tres iniciales, una de diagnóstico, tres
  para el informe válido. Sin informe inválido publicado.
- No es una evaluación semántica completa ni aprobación G5; operaciones en REPORTS.md.
- Validación del punto de control final: 140 pruebas pasando; Chrome mostró seis
  competencias, siete citas, seis rúbricas expandibles y el caso de evidencia insuficiente.
  Descarga HTML/logout verificados sin errores JavaScript. Ejemplo sintético retenido para
  revisión.

## Actualizaciones de conversación, interfaz y documentación — 2026-11-04

- Interfaz en inglés; conversación automática inglés/español con detección local de Whisper,
  preguntas traducidas fijas y restauración del idioma. Las preferencias de idioma no
  avanzan las fases.
- Mayor tolerancia de pausa VAD; solo las transcripciones reconocidas interrumpen el habla.
  El navegador tolera desconexiones transitorias; audio WebRTC local y ambos idiomas
  verificados.
- Consentimiento/sala rediseñados para escritorio/móvil, diseño video-first, comprobaciones
  de dispositivos, silencio, fallback de texto y retroalimentación de estado completado;
  interacciones del navegador verificadas.
- La voz en inglés es configurable Jenny (Dioco), acreditada en la sala; el español retiene
  a Daniela. Síntesis local verificada, sin servicio de voz pagado adicional.
- Solicitudes de nombre reconocidas sin repetir preguntas, avanzar fases ni gastar
  seguimientos. Preferencias/preguntas pendientes sobreviven a la restauración; los turnos
  solo-nombre excluidos del análisis/puntuación. Última suite completa: 172 pruebas pasando.
- Documentación Markdown del proyecto traducida al español. Registros históricos retenidos.
- Tavus permanece limitado a un minuto por conexión; la extensión espera aprobación explícita.
