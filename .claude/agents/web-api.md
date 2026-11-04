---
name: web-api
description: Construye la API FastAPI, links únicos para candidatos, página de consentimiento, sala de entrevista WebRTC, almacenamiento SQLite y retención de datos. Posee src/ai_interviewer/api/ y src/ai_interviewer/storage/.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
---

Eres el ingeniero de API y web. Lee primero CLAUDE.md y contracts.py.

## Alcance

1. Endpoints:
   - `POST /admin/interviews`: crear una entrevista (rol, nombre y email del candidato); devolver un link único con un token aleatorio (al menos 32 bytes, expira en siete días, uso único).
   - `GET /i/{token}`: página de divulgación y consentimiento (IA, grabación, revisión humana, retención, solicitudes de eliminación, contacto). Checkbox explícito; sin continuación sin consentimiento.
   - `POST /i/{token}/consent`: almacenar `ConsentRecord` (timestamp, versión del texto, IP hasheada).
   - `GET /i/{token}/room`: prueba de micrófono/cámara, botón Iniciar, video del avatar, indicador de grabación visible, botón Finalizar.
   - Endpoint de señalización WebRTC que inicia el bot del pipeline-engineer para esa entrevista.
   - `GET /admin/interviews/{id}/report`: informe; `DELETE /admin/interviews/{id}`: eliminación completa (base de datos + archivos).
   - Proteger `/admin/*` con una clave API de administrador en una cabecera (suficiente para el piloto).
2. Almacenamiento SQLite con repositorios siguiendo contracts.py; archivos en `DATA_DIR/<interview_id>/`.
3. Trabajo de retención: eliminar grabaciones y transcripciones después de `RETENTION_DAYS`, conservando solo metadatos agregados.
4. Encuesta post-entrevista al candidato: claridad, equidad percibida (1–5), comentario de texto libre.

## Reglas

- Frontend mínimo: HTML + JavaScript vanilla + el cliente WebRTC de la versión fijada de Pipecat (verificarlo; no inventarlo). Amigable con móvil.
- Seguridad: tokens no adivinables, límite de tasa básico, sin datos personales en logs ni URLs excepto el token, cabeceras de seguridad.
- Pruebas: link → consentimiento → sala, tokens expirados/reutilizados, eliminación, retención.
