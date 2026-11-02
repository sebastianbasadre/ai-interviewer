# ADR-002: fases controladas por código

Estado: propuesto para G1. Fecha: 2026-11-02.

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
