# AI Interviewer

Entrevistas estructuradas para PM/PO con revisión humana. El runtime actual ofrece un
**flujo de texto mock**: consentimiento, sesión, transcript y reporte de prueba. No genera
voz/video reales ni evalúa calidad de candidatos. Todos los scores mock son `null`.

## Ejecutar en el homelab

Entorno confirmado: Windows 11, WSL2 NVIDIA-Workbench, Python 3.12 y RTX 3090. Ejecutar
los comandos siguientes dentro de WSL2, en la raíz del checkout. El launcher escucha solo
en `127.0.0.1:8000`, con un worker y sin access logs para proteger tokens de invitación.

```bash
make install-test
cp .env.example .env  # solo la primera vez; no sobrescribir configuración existente
```

Completar `.env` con `ADMIN_API_KEY` e `IP_HASH_SECRET` independientes, de al menos 32
caracteres aleatorios cada uno, y `PRIVACY_CONTACT` con el responsable real de solicitudes
de borrado. Generarlos con un gestor de secretos; no pegarlos en commits, logs ni chats.
Mantener `APP_MODE=mock`, `AVATAR_MODE=mock` y `PUBLIC_BASE_URL=http://localhost:8000`.
No hacen falta claves de Anthropic, OpenAI o Tavus para este flujo. No se inicia con secretos
faltantes o cortos. El error muestra nombres de campos y nunca valores.

```bash
make test
make dev
```

Si el venv ya está en otra ruta, usar `make VENV=/ruta/al/venv test` y el mismo parámetro
para `dev`. El homelab tiene el entorno en `/home/workbench/.venvs/ai-interviewer`.
Usar un túnel SSH al puerto local al abrir la aplicación desde otra máquina; no exponer
este launcher directamente a la LAN. La URL pública debe coincidir con el origen usado por
el navegador. Fuera de localhost, la API exige HTTPS.

## Recorrido sintético

1. Abrir `/` para confirmar `mode: mock`. Crear una invitación mediante
   `POST /admin/interviews`, header `X-Admin-Key`, y JSON
   `{"role_id":"pm_po","name":"Synthetic","email":"synthetic@example.invalid"}`.
   Configurar el header en un cliente HTTP privado; no incorporar el secreto al historial.
2. Abrir el `link` devuelto, aceptar el consentimiento y entrar a la sala de texto.
3. Completar o finalizar la sesión. Generar el reporte con
   `POST /admin/interviews/{id}/report` y el mismo header de admin.
4. Consultarlo con `GET` en esa ruta. Debe incluir `mock_scoring` y seis scores `null`.
   Borrar los datos de prueba con `DELETE /admin/interviews/{id}`.

El link es una credencial: no compartirlo ni registrarlo en logs. Los endpoints admin
requieren autenticación incluso en mock. Sin consentimiento no se inicia la entrevista.
SQLite y archivos quedan en `DATA_DIR`, con retención configurable (30 días por defecto).

## Evaluaciones y audio/video

```bash
make eval        # harness offline; no proveedores ni costo de tokens
make install     # agrega SDK Pipecat 1.15.0 para pruebas opcionales de frames
```

El harness offline verifica estructura y seguridad con dobles; las métricas semánticas no
evaluadas no se presentan como aprobadas. Las evaluaciones LLM reales necesitan G3 y costo
estimado. `APP_MODE=real` y `make dev-tavus` están bloqueados hasta integrar proveedores y
pasar los gates correspondientes. Tavus requiere G4 antes de consumir minutos.

El pipeline tiene pruebas con frames de Pipecat y servicios mock. Todavía faltan conexión
WebRTC desde la sala, STT/TTS reales, grabación audiovisual y latencia medida. No se declara
el piloto listo hasta completar evals, privacidad y G5; no usar con personas reales todavía.

Arquitectura y decisiones: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Estado y gates: [docs/STATUS.md](docs/STATUS.md). Reglas de agentes: [CLAUDE.md](CLAUDE.md).
