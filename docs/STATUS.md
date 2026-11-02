# Estado del proyecto

## Fase actual
Fase 0 preparada salvo credenciales; G1 aprobado por el responsable; G2 aprobado por el responsable; fase 2 en construcción.

## Tareas
- [x] Leer CLAUDE.md, README, prompt del orquestador y siete agentes.
- [x] Verificar acceso SSH a sbasadre@192.168.2.6 con identidad existente.
- [x] Verificar Windows 11 + WSL2 NVIDIA-Workbench y GPU RTX 3090 (24 GB).
- [x] Instalar Python 3.12.16 en espacio de usuario WSL mediante uv 0.13.6.
- [x] Crear venv /home/workbench/.venvs/ai-interviewer en homelab.
- [ ] Completar credenciales en .env: plantilla creada y gitignored; ningún secreto leído ni impreso.
- [x] Arquitectura, contratos, ADRs, configuración, Makefile y CI (architect).
- [x] make test en homelab: 15 passed (Python 3.12.16).
- [x] Revisión independiente: APROBAR; eventos de motor y restauración de snapshot corregidos.
- [x] G1: aprobado por el responsable (OK).
- [x] G2: guion y rúbrica PM/PO aprobados por el responsable (SI), con revisión técnica APROBAR y 19 tests correctos.
- [ ] API/storage y pipeline mock en ramas aisladas; integrar solo tras tests y APROBAR.

## Decisiones
- El responsable indicó que el equipo de ejecución es homelab 192.168.2.6 por SSH, no la PC local.
- Mantener stack y Python 3.12; ejecutar Linux mediante WSL2 del homelab.
- Avatar mock; no servicios pagos, evaluaciones reales ni contacto con candidatos.
- Git requiere excepción safe.directory por propiedad SMB; se usa solo por comando, sin cambiar configuración global.
- Arquitectura integrada por fast-forward tras tests, APROBAR y G1. Fase 2 en ramas feat/interview-engine-role, feat/web-api-pilot y feat/pipeline-mock.

## Pendientes
G3 evals pagas; G4 Tavus; G5 piloto real.
La GPU es visible desde WSL; compatibilidad efectiva Whisper/CUDA aún no verificada.



Retención propuesta de 30 días conservada. Video persistido pendiente de definición; no implementarlo aún.


Checkpoints fase 2: web/API y pipeline en worktrees aislados, sin integrar ni declarar completos. Retomados tras aprobación de G2.


