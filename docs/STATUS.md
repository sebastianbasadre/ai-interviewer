# Estado del proyecto

## Fase actual
Fase 0 preparada salvo credenciales; fase 1 completada, revisada y pendiente de G1. No iniciar construcción antes de G1.

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
- [ ] G1: aprobación del responsable antes de fase 2.

## Decisiones
- El responsable indicó que el equipo de ejecución es homelab 192.168.2.6 por SSH, no la PC local.
- Mantener stack y Python 3.12; ejecutar Linux mediante WSL2 del homelab.
- Avatar mock; no servicios pagos, evaluaciones reales ni contacto con candidatos.
- Git requiere excepción safe.directory por propiedad SMB; se usa solo por comando, sin cambiar configuración global.
- Rama de arquitectura: feat/architect-foundation. Sin merge ni push hasta pruebas y revisión.

## Pendientes
G1 arquitectura; G2 guion/rúbrica; G3 evals pagas; G4 Tavus; G5 piloto real.
La GPU es visible desde WSL; compatibilidad efectiva Whisper/CUDA aún no verificada.


