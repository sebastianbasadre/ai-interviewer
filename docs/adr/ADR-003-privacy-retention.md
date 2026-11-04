# ADR-003: consentimiento y eliminación completa del conjunto de datos

Estado: aceptado por el dueño del proyecto en G1. Fecha: 2026-11-02.

## Contexto

Una entrevista contiene datos personales, audio y texto. El piloto necesita límites simples
y eliminación verificable. Este ADR define requisitos de ingeniería; no reemplaza la
revisión legal.

## Decisión

Requerir consentimiento versionado antes de la captura o las llamadas a proveedores. Usar
tokens de invitación aleatorios de 32 bytes, persistir solo sus hashes, expirarlos a los
siete días y reclamarlos atómicamente para uso único. Proteger las direcciones IP con HMAC.
La retención por defecto es de 30 días: eliminar candidato, consentimiento, turnos, informe
y archivos, conservando solo estadísticas anónimas. La eliminación solicitada usa la misma
operación idempotente. Calcular el plazo desde el cierre, o la creación si la entrevista
nunca comenzó. Los respaldos deben expirar y respetar un registro de eliminaciones al
restaurar. Nunca almacenar datos sensibles en logs.

## Consecuencias

El almacenamiento necesita pruebas de consentimiento, concurrencia, retención y eliminación
de archivos. El piloto no puede comenzar hasta que el acceso a datos, los proveedores, el
contacto de privacidad, la política de respaldo y la divulgación de IA estén documentados.
La grabación de video persistida espera una decisión de alcance G1.
