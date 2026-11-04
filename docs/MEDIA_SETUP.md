# Demo de audio y avatar

## Estado verificado

La sala abre un canal WebRTC autenticado por la cookie de sesión. Pipecat 1.15.0 recibe
el audio del micrófono, Silero detecta los turnos y Whisper local detecta el idioma sin
forzar el español. Piper originalmente usaba `en_US-lessac-high` para inglés y
`es_AR-daniela-high` para español; la configuración actual de voz femenina se describe a
continuación. Ambas modalidades comparten el motor de fases y la persistencia de texto.
El informe inicial era simulado sin puntajes numéricos; la puntuación real opcional se
describe en REPORTS.md. No se solicita la cámara del candidato para la entrevista. Esta
demo no almacena archivos de audio ni video, tal como se indica en el consentimiento. La
grabación audiovisual del piloto está pendiente; no se declara como implementada.

TavusVideoService es una etapa opcional entre la salida TTS y del transporte. Sin una clave
API, Face, PAL Echo y habilitación explícita, no se instancia y no consume minutos. Se
verificó una prueba real autorizada: Chrome recibió video Anna a 1280×720 y audio, Whisper
transcribió una respuesta sintética y el motor avanzó a warmup. Después del cierre, la
API de Tavus confirmó `ended`. No existe medición formal de latencia/sincronización. Los
fallos de media cierran el canal y permiten la continuación por texto; el fallback automático
de Tavus a audio aún no está verificado. No usar este estado para entrevistas reales con
candidatos.

## Configuración

Ejecutar en WSL2 con Python 3.12, desde la raíz del proyecto:

```bash
python -m pip install -e '.[test,media]'
python -m pytest
```

Configurar `.env` sin imprimir valores. Ejemplo de demo local:

```dotenv
APP_MODE=mock
AVATAR_MODE=mock
REALTIME_ENABLED=true
TAVUS_ENABLED=false
TTS_PROVIDER=piper
PIPER_VOICE=es_AR-daniela-high
PIPER_ENGLISH_VOICE=en_GB-jenny_dioco-medium
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
MEDIA_MAX_MINUTES=3
PUBLIC_BASE_URL=https://192.168.2.6:8443
LISTEN_PORT=8443
TLS_CERT_FILE=/ruta/privada/server.crt
TLS_KEY_FILE=/ruta/privada/server.key
TURN_URL=turn:192.168.2.6:3479?transport=tcp
```

El inicio prepara los modelos locales; la primera ejecución descarga los pesos. Los errores
de preparación deshabilitan media mientras mantienen el texto disponible. `/admin/health`
reporta `media_ready` y aún requiere `X-Admin-Key`. Los SDKs no se importan en modo solo
texto.

Esta configuración limita media a una conexión global y tres minutos por conexión. Tavus
también recibe `properties.max_call_duration`, acotado por el tiempo restante de la
entrevista, `MEDIA_MAX_MINUTES` y `TAVUS_MAX_MINUTES_PER_SESSION`. Desconectar media
preserva el plazo original de la entrevista en lugar de reiniciar el máximo de 30 minutos.
No existe una reserva acumulativa global de gasto de Tavus: mantenerlo deshabilitado hasta
que el presupuesto de prueba sea acordado y monitoreado.

## HTTPS y NAT de WSL

El lanzador escucha solo en loopback. El portproxy de Windows homelab reenvía
`192.168.2.6:8443` a `127.0.0.1:8443` y `:3479` a `127.0.0.1:3479`. Firewall:
TCP 8443/3479 solo desde `192.168.2.0/24`. El puerto HTTP 8000 ejecuta
`python -m ai_interviewer.redirect`, redirigiendo los navegadores a HTTPS preservando
las rutas de invitación sin registro de acceso.

El certificado de desarrollo incluye IP y SANs de localhost. No se instaló ninguna
autoridad raíz en los dispositivos: los navegadores pueden advertir hasta que el
certificado sea explícitamente de confianza. Usar un hostname y certificado de confianza
para un despliegue estable. Los certificados/claves permanecen bajo `data/tls/`, fuera de Git.

El sistema Coturn 4.5.2 sirve TURN sobre TCP 3479 con credenciales HMAC temporales emitidas
solo a sesiones autenticadas. `TURN_SHARED_SECRET` coincide con el `static-auth-secret`
de coturn y nunca se envía a los navegadores. Los navegadores usan `relay` para atravesar
el NAT de WSL. Los puertos de relay UDP 49160–49200 permanecen dentro de WSL; no exponer
ese rango a la LAN. La configuración inicial de la demo y el PID estaban bajo `data/`.
Reiniciar WSL puede cambiar su IP de relay; actualizar `relay-ip` y reiniciar coturn si
es necesario. Los procesos iniciales de la demo no se registraron como servicios de inicio
del sistema.

Corrección operacional: el servicio del sistema coturn ahora usa la configuración TURN de
la aplicación. Una configuración del sistema anterior no coincidente impedía la asignación
de relay ICE autenticado aunque el puerto TCP fuera alcanzable. La recopilación de relay
de Chrome se verificó después de corregir la configuración. El navegador permite hasta
25 segundos para la preparación ICE.

## Configurar y repetir una prueba de avatar

1. Establecer `TAVUS_API_KEY`, `TAVUS_FACE_ID` y `TAVUS_PAL_ID` en `.env`; no pegarlos
   en chats. Crear el PAL con `pipeline_mode: "echo"`: Tavus solo renderiza el habla de
   Piper y no controla el guión. No usar un PAL conversacional completo.
   Crearlo usando `POST /v2/pals` con este cuerpo:

   ```json
   {"pal_name": "AI Interviewer Echo", "pipeline_mode": "echo", "default_face_id": "rc9cff32ceba"}
   ```

   `TAVUS_REPLICA_ID` se acepta como alias legacy cuando `TAVUS_FACE_ID` está vacío;
   Face tiene precedencia cuando ambos están establecidos. El alias adapta la configuración
   existente, no los recursos de la cuenta; no los convierte ni verifica automáticamente.
2. Acordar minutos estimados y costo con el dueño antes de habilitar Tavus (G4).
3. Establecer `AVATAR_MODE=tavus`, `TAVUS_ENABLED=true` y reiniciar el runtime.
4. Crear una nueva invitación. El consentimiento `media-tavus-v1` explica que Tavus recibe
   la voz sintética del entrevistador. El consentimiento de texto/audio local no autoriza
   este nuevo receptor; las entrevistas existentes no se convierten silenciosamente.
5. Conectar el micrófono y verificar habla, video, sincronización, interrupción y cierre
   remoto. Registrar duración/uso reales. Finalizar o desconectar después de la prueba.

Fuentes verificadas: código instalado y el ejemplo oficial de Pipecat v1.15.0:
https://github.com/pipecat-ai/pipecat/blob/v1.15.0/examples/video-avatar/video-avatar-tavus-video-service.py

## Compatibilidad Face/PAL

El SDK fijado aún usa `replica_id` y `persona_id` en su constructor y llamadas REST.
`pipeline/tavus_compat.py` adapta solo su sesión HTTP sin modificar el SDK:

- `POST /v2/conversations` envía `face_id`, `pal_id`, límite de duración y grabación
  deshabilitada.
- `GET /v2/personas/{id}` se convierte en `GET /v2/pals/{id}`; devolver `pal_name` al
  SDK como `persona_name`, sin propagar prompts de PAL ni claves de herramientas.
- `POST /v2/conversations/{id}/end` retiene el endpoint actual.

Pipecat aún maneja audio `conversation.echo`, interrupciones, video y limpieza.
El adaptador permite solo esos endpoints y deshabilita las redirecciones HTTP. Las pruebas
ejercitan clientes/constructores reales de Pipecat 1.15 contra un doble de sesión, sin
red ni costo. Esto verifica compatibilidad de software, no la prueba de video en vivo G4.

Contrato REST verificado: https://docs.tavus.io/openapi.yaml.
Guía Echo: https://docs.tavus.io/sections/conversational-video-interface/echo-mode.

## Actualización de idioma y continuidad (2026-11-04)

Las interfaces de consentimiento, sala y revisión usan inglés. Las entrevistas audiovisuales
comienzan en inglés y detectan localmente respuestas en inglés/español usando langdetect.
Las respuestas cortas o ambiguas retienen el idioma anterior. "Spanish please" y
"English please" cambian de idioma sin avanzar la fase. El idioma se reconstruye desde
la transcripción al reanudar. Las preguntas usan traducciones fijas; la detección no
cambia la rúbrica ni permite que un modelo controle las fases.

Las voces se descargan/cargan durante la preparación de media. El VAD espera 0.8 segundos
de silencio; la detección de ruido sola no interrumpe el TTS. Solo una transcripción
reconocida activa la interrupción. El navegador tolera hasta ocho segundos de desconexión
transitoria. El habla de cierre se reproduce antes del apagado de media.

El presupuesto de Tavus del entorno de prueba permanece en un minuto por conexión hasta
que se extienda explícitamente, aplicado tanto por el proveedor como por el proceso local.
Prueba local sin Tavus: 22 segundos de WebRTC, 1036 frames recibidos, 667 con audio, con
una apertura en inglés. Esto no reemplaza una prueba de Tavus en la red del usuario. Los
informes e historiales citados retienen su contenido original.

## Voz de entrevistadora femenina

El inglés usa `PIPER_ENGLISH_VOICE=en_GB-jenny_dioco-medium`; el español retiene
`PIPER_VOICE=es_AR-daniela-high`. Ambas son voces Piper locales. La selección de voz en
inglés es configurable en lugar de estar hardcodeada. La sala acredita a Jenny (Dioco),
según lo requiere la licencia del dataset: https://github.com/dioco-group/jenny-tts-dataset .
Los cambios de voz se aplican a las nuevas conexiones de media. El proveedor de avatar
no cambia.
