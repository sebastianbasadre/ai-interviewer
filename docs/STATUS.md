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



## Construcción posterior a G2
- Motor/scoring: implementación offline lista; correcciones STAR y test de privacidad en e86e064 (53 tests en homelab). Pendiente re-review.
- API/storage: eaac62c (34 tests); correcciones en curso por carrera inicio/watchdog y recuperación al finalizar.
- Pipeline: 7d27646 (36 tests con Pipecat); control de habla/concurrencia corregido. Interrupción durante generación se detiene de forma segura hasta integrar factory/restore transaccional.
- Contrato factory/restore: fb44d52 de architect, pendiente integración/revisión.
- QA: harness y E2E offline en construcción; 78 tests en snapshot combinado de trabajo, sin llamadas reales.
- Runtime: composición local con mocks y comandos de desarrollo en construcción.

Los conteos corresponden a snapshots distintos y no se suman. Ninguna rama de implementación se integra sin re-review y tests.

## Integración verificada
- Engine e86e064 y API12b30e6: re-review APROBAR, integrados en orden.
- QA36b0508: APROBAR herramientas offline; integrado por cherry-pick36f6b11.
- Homelab main combinado:82 tests correctos;33 sesiones sintéticas offline y0 fallas estructurales.
- Runtime 6451d2a: APROBAR; runtime.py, __main__.py, replace_progress implementado, transacciones BEGIN IMMEDIATE endurecidas, VACUUM por lote. Integrado en main.
- Calidad semántica, ranking y latencia reales siguen sin evaluar.
- Pendiente antes G3: integrar feat/pipeline-mock (requiere re-review con contrato factory/restore de main); luego preparar adaptador real con reserva de presupuesto y factory de evals auditada.
