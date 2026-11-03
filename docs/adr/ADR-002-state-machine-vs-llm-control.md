# ADR-002: fases controladas por código

Estado: aceptado en G1 por el responsable. Fecha: 2026-11-02.

## Contexto
El screening debe cubrir las mismas seis competencias y resistir instrucciones del candidato.

## Decisión
Una máquina determinística controla fases, tiempo y máximo dos repreguntas. El LLM redacta
solo el turno permitido y usa contexto mínimo. Roles y rúbrica son YAML versionado.
El scoring es posterior, con tres corridas, mediana, dispersión y evidencia validada.
Las decisiones humanas nunca se reemplazan por una aprobación/rechazo automática.

## Consecuencias
Motor y scoring se prueban sin red. Un LLM defectuoso no puede saltar fases ni fijar scores
sin evidencia. Inyección, cortes y degradaciones son flags para revisión humana.

## Enmienda: interrupción durante generación (2026-11-02)

El motor puede mutar estado antes de esperar al LLM. Cancelarlo o simplemente silenciar su
salida puede adelantar la competencia a una pregunta que el candidato nunca recibió.
Se conserva un checkpoint de la última respuesta entregada. Ante barge-in antes de entrega,
el coordinador persiste el turno real, descarta la instancia mutada y usa una factory para
restaurar un motor nuevo con fase/repreguntas anteriores, tiempo actualizado y deadline
original. No conserva el turno ficticio del entrevistador ni aborta una interrupción normal.
La reconstrucción no usa proveedores. Tests del pipeline deben probar siguiente competencia,
ambos turnos reales, ausencia de pregunta no entregada y límite duro sin nuevas llamadas.
