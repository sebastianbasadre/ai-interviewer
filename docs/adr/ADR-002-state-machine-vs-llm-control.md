# ADR-002: fases controladas por código

Estado: aceptado por el dueño del proyecto en G1. Fecha: 2026-11-02.

## Contexto

La selección debe cubrir las mismas seis competencias y resistir las instrucciones del
candidato.

## Decisión

Una máquina determinista controla las fases, el tiempo y un máximo de dos seguimientos.
El LLM escribe únicamente el turno permitido usando contexto mínimo. Los roles y la rúbrica
usan YAML versionado. La puntuación se ejecuta después, usando tres evaluaciones, mediana,
dispersión y evidencia validada. La aprobación/rechazo automático nunca reemplaza las
decisiones humanas.

## Consecuencias

El motor y la puntuación se prueban offline. Un LLM defectuoso no puede saltar fases ni
asignar puntajes sin evidencia. Las inyecciones, cortes y degradaciones se marcan para
revisión humana.

## Enmienda: interrupción durante la generación (2026-11-02)

El motor puede mutar el estado antes de esperar el LLM. Cancelar o simplemente silenciar
su salida puede avanzar la competencia a una pregunta que el candidato nunca recibió.
Mantener un punto de control de la última respuesta entregada. En barge-in antes de la
entrega, el coordinador persiste el turno real del candidato, descarta la instancia mutada
y usa una fábrica para restaurar un nuevo motor con la fase/conteo de seguimientos anterior,
tiempo transcurrido actualizado y plazo original. No conservar el turno ficticio del
entrevistador ni abortar una interrupción normal. La reconstrucción no usa proveedores.
Las pruebas del pipeline deben verificar la siguiente competencia, ambos turnos reales,
la ausencia de la pregunta no entregada y el límite duro sin nuevas llamadas.
