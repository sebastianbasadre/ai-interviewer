# ADR-003: consentimiento y borrado del conjunto de datos

Estado: aceptado en G1 por el responsable. Fecha: 2026-11-02.

## Contexto
Una entrevista contiene datos personales, audio y texto; el piloto necesita límites simples
y borrado comprobable. Este ADR define ingeniería, no sustituye revisión legal.

## Decisión
Consentimiento versionado antes de captura o llamadas a proveedores. Tokens de invitación
aleatorios de 32 bytes, hash persistido, siete días y claim atómico de un solo uso. IP con HMAC.
Retención predeterminada 30 días; borrar candidato, consentimiento, turnos, reporte y archivos,
manteniendo solo estadísticas anónimas. Borrado a pedido usa la misma operación idempotente.
El deadline se toma del cierre, o creación si no llegó a iniciarse. Backups deben vencer y
respetar un registro de borrados al restaurar. No almacenar datos sensibles en logs.

## Consecuencias
Storage necesita tests de consentimiento, concurrencia, retención y borrado de archivos.
El piloto no comienza hasta documentar quién accede, proveedores, contacto, política de
backups y aviso de IA. Grabación persistida de video queda pendiente de definición en G1.

