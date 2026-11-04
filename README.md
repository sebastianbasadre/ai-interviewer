# AI Interviewer

Entrevistas estructuradas para PM/PO con revisión humana. El flujo actual proporciona un
**flujo de demostración**: consentimiento, sesión, transcripción e informe. Permite audio
local con Whisper/Piper y un avatar opcional de Tavus, verificado en una sesión sintética
con video 1280×720. La puntuación simulada deja los puntajes como `null`; la puntuación
opcional con Claude genera puntajes con evidencia para revisión humana y requiere validación
piloto.
Configuración de audio/avatar y límites: [docs/MEDIA_SETUP.md](docs/MEDIA_SETUP.md).
Análisis de respuestas con Claude: [docs/CONVERSATION_SETUP.md](docs/CONVERSATION_SETUP.md).
Informes reales e interfaz de revisor: [docs/REPORTS.md](docs/REPORTS.md).

## Ejecutar en el homelab

Entorno verificado: Windows 11, WSL2 NVIDIA-Workbench, Python 3.12 y RTX 3090.
Ejecutar los siguientes comandos dentro de WSL2 desde la raíz del repositorio. El lanzador
escucha únicamente en `127.0.0.1:8000`, con un solo worker y sin registros de acceso,
para proteger los tokens de invitación.

```bash
make install-test
cp .env.example .env  # solo la primera vez; no sobreescribir configuración existente
```

Establecer valores independientes para `ADMIN_API_KEY` e `IP_HASH_SECRET` en `.env`, cada
uno con al menos 32 caracteres aleatorios. Configurar `PRIVACY_CONTACT` con la persona
real responsable de las solicitudes de eliminación. Generar secretos con un gestor de
secretos; no pegarlos en commits, logs ni chats. Mantener `APP_MODE=mock`,
`AVATAR_MODE=mock` y `PUBLIC_BASE_URL=http://localhost:8000`. Este flujo no requiere claves
de Anthropic, OpenAI ni Tavus. El inicio rechaza secretos faltantes o cortos. Los errores
muestran nombres de campos, nunca valores.

```bash
make test
make dev
```

Para un entorno virtual en otra ruta, usar `make VENV=/ruta/al/venv test` y el mismo
parámetro para `dev`. El entorno del homelab está en
`/home/workbench/.venvs/ai-interviewer`. Usar un túnel SSH al puerto local al abrir la
aplicación desde otra máquina; no exponer este lanzador directamente a la LAN.
La URL pública debe coincidir con el origen del navegador. Fuera de localhost, la API
requiere HTTPS.

Para una demo simulada autorizada por HTTP en una LAN privada, habilitar
`ALLOW_MOCK_LAN_HTTP=true` y establecer `PUBLIC_BASE_URL=http://192.168.2.6:8000`. Esta
excepción acepta únicamente IPs privadas RFC1918 con la app y el avatar en modo simulado;
otros orígenes aún requieren HTTPS. El lanzador sigue escuchando en loopback: configurar
el reenvío de puertos del host y una regla de firewall restringida a la subred local.

## Recorrido sintético

1. Abrir `/` y confirmar `mode: mock`. Crear una invitación con
   `POST /admin/interviews`, cabecera `X-Admin-Key`, y JSON
   `{"role_id":"pm_po","name":"Synthetic","email":"synthetic@example.invalid"}`.
   Configurar la cabecera en un cliente HTTP privado; mantener el secreto fuera del historial
   de comandos.
2. Abrir el `link` devuelto, aceptar el consentimiento y entrar a la sala de texto.
3. Completar o finalizar la sesión. Generar el informe con
   `POST /admin/interviews/{id}/report` usando la misma cabecera de administrador.
4. Leerlo con `GET` en esa ruta. Debe contener `mock_scoring` y seis puntajes `null`.
   Eliminar datos de prueba con `DELETE /admin/interviews/{id}`.

El link es una credencial: no compartirlo ni registrarlo. Los endpoints de administración
requieren autenticación incluso en modo simulado. Las entrevistas no pueden comenzar sin
consentimiento. SQLite y los archivos se almacenan en `DATA_DIR`, con retención configurable
(30 días por defecto).

## Evaluaciones y audio/video

```bash
make eval        # harness offline; sin proveedores ni costos de tokens
make install     # también instala Pipecat 1.15.0 para pruebas de frames opcionales
```

El harness offline verifica estructura y seguridad usando dobles de prueba. Las métricas
semánticas no evaluadas no se presentan como aprobadas. Las evaluaciones reales con LLM
grande requieren G3 y una estimación de costos. `APP_MODE=real` y `make dev-tavus`
permanecen bloqueados hasta la integración con proveedores y las compuertas correspondientes.
Tavus requiere G4 antes de consumir minutos.

La sala soporta WebRTC opcional con STT/TTS local. Se verificó audio de Chrome por LAN,
incluyendo transcripción sintética y respuestas habladas. La grabación audiovisual,
la latencia p50/p95, la sincronización medida y la calidad semántica están pendientes.
No declarar preparación piloto hasta que las evaluaciones, la revisión de privacidad y G5
estén completas; no usar con candidatos reales aún.

Arquitectura y decisiones: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Estado y compuertas: [docs/STATUS.md](docs/STATUS.md). Reglas de agentes: [CLAUDE.md](CLAUDE.md).
