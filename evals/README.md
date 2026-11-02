# Evaluaciones sintéticas y pruebas de integración

Estado: herramientas offline implementadas; **G3 pendiente**. Ninguna evaluación con
modelos reales se ejecutó. Los perfiles son fixtures sintéticos y sus niveles esperados
son hipótesis de calibración que debe revisar una persona, no verdad objetiva.

## Uso sin red ni costos

Desde la raíz del repo, con Python 3.12 y dependencias de test:

```bash
python -m evals.run_evals
python -m evals.run_evals --runs 3 --output evals/results
python -m pytest tests/integration
```

El comando predeterminado usa `StructuredInterviewEngine` sin LLM, respuestas guionadas
y `MockScoringModel`. Recorre el código real de fases, repreguntas, flags y scoring, pero
el analizador offline pide aclaraciones conservadoras y el scoring devuelve solo notas
nulas con `mock_scoring`. **Esto no mide calidad conversacional, ranking ni precisión.**
Todos los gates de calidad aparecen `not_evaluated`; nunca se presenta un pass de mocks
como autorización de piloto. El JSON contiene observaciones estructurales aparte de las
métricas: cobertura del flujo, límites, fin, repreguntas ante fixtures sin ejemplo y
canarios sensibles sintéticos. Los archivos Markdown enumeran fallas con persona y turno;
el JSON conserva el transcript sintético para investigar la evidencia.

Hay once perfiles: fuerte, promedio, débil, evasivo, verborrágico, monosilábico, vacilante,
inyección, datos sensibles, cambio a inglés y consultas sobre salario/beneficios.
`expected_scores: null` significa que el perfil no permite fijar una nota de referencia,
no que deba recibir 1. El tiempo de tres minutos es una anotación del fixture verborrágico,
no audio ni latencia medida.

## Inyección de servicios reales (después de G3)

Una factory de confianza debe devolver `Components` de `evals.run_evals` con:

- Motor nuevo por sesión con analizador/redactor del proveedor real configurado.
- Responder de candidato que reciba el perfil y produzca `Answer` con límites de contexto.
- Scorer nuevo por sesión usando el modelo grande y las tres corridas del scorer real.
- `real_models=True` y descripción de los modelos/configuración usados.
- Auditor independiente de cumplimiento y grounding. Debe devolver booleanos o `None`
  para `injection_resistance`, `sensitive_content_absent`, `company_facts_grounded`.

```bash
python -m evals.run_evals --factory trusted_package:components --allow-paid --runs 3
```

`--allow-paid` representa la aprobación explícita del responsable; nunca se agrega desde
un Makefile ni desde defaults. Sin ese flag ni siquiera se importa la factory real.
La factory real no se entrega como activación automática de proveedores. El runner limita
hasta 100 sesiones, diez repeticiones y 64 turnos por sesión, con timeout de 600 s por
sesión. No es un límite de dólares: la factory debe reservar presupuesto antes de cada
llamada, limitar tokens/reintentos y registrar usage sin contenidos ni keys.

Los checks de cobertura y repreguntas se calculan automáticamente, pero su acreditación
como calidad requiere un engine real. Ranking, acuerdo esperado y dispersión se calculan
solo con scoring real, nunca con notas mock. La inspección de frases sensibles, fuga de
prompts y hechos inventados necesita auditoría semántica independiente: los canarios y
keywords no la reemplazan. Inyección requiere además comparar un caso profesional base
con el mismo caso atacado y revisar que no cambien las notas ni se revelen instrucciones;
la factory/auditor debe aportar esa evidencia, o devolver `None`. Sin auditor o evidencia
suficiente el gate queda `not_evaluated`. Un perfil de solo inyección debe quedar sin nota
numérica y no acredita por sí solo invariancia en un caso profesional mixto.

Los resultados reales pueden contener texto generado y se guardan en `evals/results/`
(gitignored). Solo usar datos sintéticos; no apuntar el harness a transcripciones reales.
Las excepciones de proveedores se registran por tipo, sin texto que pueda contener secrets.

## Latencia

`latency_probe.py` agrega muestras de servicios reales, no crea una medición ficticia.
Entrada JSONL, una muestra por turno, sin audio, texto ni datos personales:

```json
{"real_services": true, "stages_ms": {"vad": 200, "stt": 200, "llm_ttfb": 300, "tts_ttfb": 250, "avatar": 200, "total": 1150}}
```

Ese ejemplo muestra formato, **no un resultado del sistema**.

```bash
python -m evals.latency_probe /path/to/measured-latencies.jsonl
```

Reporta p50/p95 por etapa y total. El total debe medirse desde fin de habla del candidato
hasta primer audio del avatar/salida, con el mismo reloj monotónico; no se suman percentiles
de etapas. El objetivo p50 <1200 ms solo se evalúa con al menos 30 muestras reales. Datos
mock o muestras insuficientes devuelven `not_evaluated`. Campos de contenido y valores
negativos/no finitos se rechazan. Aún no hay muestras reales ni latencia validada.

## Propuesta G3 (no ejecutada)

Primera corrida: **11 perfiles × 3 repeticiones = 33 conversaciones de texto**, con tres
scorings por conversación (99 llamadas grandes) y una auditoría independiente por sesión
(33 llamadas grandes, más comparación base/ataque cuando corresponda). Sin STT/TTS/Tavus.
Primero un smoke de una sesión dentro del mismo presupuesto para comprobar JSON y usage;
si falla, detener en lugar de reintentar el lote. Máximo tres iteraciones de corrección
antes de escalar el diagnóstico; cada lote adicional necesita presupuesto explícito.

Los IDs configurados `claude-haiku-5-5` y `claude-opus-5-5` figuran en el
[catálogo oficial](https://platform.claude.com/docs/en/models/overview), consultado el
2026-11-02. Las tarifas estándar consultadas son Haiku 5.5: USD 0.10/MTok de entrada y
0.50/MTok de salida para prompts de hasta 100k tokens; Opus 5.5: USD 4/MTok de entrada y
20/MTok de salida. Son tarifas de la [documentación oficial de precios](https://platform.claude.com/docs/en/about-claude/pricing).
Verificar disponibilidad efectiva de la cuenta, tarifas y credenciales antes del smoke.

Estimación de escenario, **no uso medido ni garantía de factura**:

| Trabajo por conversación | Tokens entrada | Tokens salida | Costo USD |
| --- | ---: | ---: | ---: |
| Hasta 70 llamadas Haiku (candidato + analizador + redactor), promedio 1500/300 tokens | 105000 | 21000 | 0.021 |
| Tres scorings Opus, 15000/1500 tokens cada uno | 45000 | 4500 | 0.270 |
| Auditor Opus, 15000/1000 tokens | 15000 | 1000 | 0.080 |
| Total estimado por conversación | | | 0.371 |
| 33 conversaciones | | | 12.243 |

Fórmula: `(entrada × tarifa_entrada + salida × tarifa_salida) / 1_000_000`, sumada por
modelo y llamada. Un margen de 50% da aproximadamente **USD 18.40**. Propuesta de techo:
**USD 20** para el lote, incluyendo smoke y comparaciones de inyección. No se garantizan
las 33 sesiones si el presupuesto se agota: detener antes de la siguiente llamada.
Pensamiento, retries, auditoría adicional y contexto más largo consumen presupuesto;
no asumir descuentos Batch/cache, impuestos incluidos ni límites de tokens ficticios.
El control monetario y el adaptador real deben existir y probarse antes de usar el flag.

Pendientes para ejecutar G3: aprobación del responsable con techo, factory real auditada,
credenciales configuradas sin imprimirlas, límites de tokens/reintentos y budget reservation,
y evidencia de comparación base/ataque para acreditar resistencia a inyección.
