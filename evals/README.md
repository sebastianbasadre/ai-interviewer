# Evaluaciones sintéticas y pruebas de integración

Estado: herramientas offline implementadas; **G3 pendiente**. No se ha ejecutado ningún
lote real de evaluación de modelos. Los perfiles son fixtures sintéticos; los niveles
esperados son hipótesis de calibración para revisión humana, no verdad objetiva.

## Uso offline sin costos

Desde la raíz del repositorio, con Python 3.12 y dependencias de prueba:

```bash
python -m evals.run_evals
python -m evals.run_evals --runs 3 --output evals/results
python -m pytest tests/integration
```

El uso por defecto utiliza `StructuredInterviewEngine` sin un LLM, respuestas con guión y
`MockScoringModel`. Ejercita el código real de fases, seguimientos, banderas y puntuación,
pero el analizador offline solicita aclaraciones conservadoras y la puntuación devuelve
solo puntajes null con `mock_scoring`. **Esto no mide calidad de conversación, ranking
ni precisión.** Cada compuerta de calidad es `not_evaluated`; los simulados pasando nunca
autorizan un piloto. El JSON separa observaciones estructurales de métricas: cobertura de
flujo, límites, terminación, seguimientos para fixtures sin ejemplos y canarios sintéticos
de datos sensibles. Los informes Markdown listan fallos por persona/turno; el JSON retiene
transcripciones sintéticas para investigación de evidencias.

Hay once perfiles: fuerte, promedio, débil, evasivo, verboso, monosilábico, dubitativo,
inyección, datos sensibles, cambio a inglés y preguntas de salario/beneficios.
`expected_scores: null` significa que el perfil no puede establecer un puntaje de
referencia, no que merezca 1. La duración de tres minutos del fixture verboso es una
anotación, no audio ni latencia medida.

## Inyectar servicios reales (después de G3)

Una fábrica de confianza debe devolver `Components` desde `evals.run_evals` con:

- Un nuevo motor por sesión con el analizador/escritor del proveedor real configurado.
- Un respondedor de candidatos que recibe el perfil y produce `Answer` con contexto acotado.
- Un nuevo scorer por sesión usando el modelo grande y las tres ejecuciones del scorer real.
- `real_models=True` y una descripción de los modelos/configuración utilizados.
- Un auditor independiente de cumplimiento/grounding que devuelva booleanos o `None` para
  `injection_resistance`, `sensitive_content_absent`, `company_facts_grounded`.

```bash
python -m evals.run_evals --factory paquete_confianza:components --allow-paid --runs 3
```

`--allow-paid` representa aprobación explícita del dueño; nunca agregarlo en un Makefile
ni en los valores por defecto. Sin el flag, la fábrica real ni siquiera se importa. La
fábrica real no se proporciona como activación automática del proveedor. El runner limita
la ejecución a 100 sesiones, diez repeticiones, 64 turnos por sesión y un timeout de 600
segundos por sesión. Esto no es un límite monetario: la fábrica debe reservar presupuesto
antes de cada llamada, acotar tokens/reintentos y registrar el uso sin contenido ni claves.

Las verificaciones de cobertura/seguimiento se calculan automáticamente, pero establecer
calidad requiere un motor real. Ranking, acuerdo esperado y dispersión se calculan solo
con puntuación real, nunca con puntajes simulados. Las verificaciones de lenguaje sensible,
filtración de prompts y hechos inventados necesitan auditoría semántica independiente;
los canarios y palabras clave no pueden reemplazarla. La inyección también requiere
comparar una línea base profesional con el mismo ejemplo atacado y verificar que los
puntajes no cambien y las instrucciones no sean divulgadas. La fábrica/auditor debe
proporcionar esta evidencia o devolver `None`. Sin un auditor o evidencia suficiente, la
compuerta permanece `not_evaluated`. Un perfil solo-inyección no debe tener puntaje
numérico; no establece independientemente la invarianza en casos mixtos
profesionales/atacados.

Los resultados reales pueden contener texto generado y se almacenan en `evals/results/`
(en .gitignore). Usar solo datos sintéticos; nunca apuntar el harness a transcripciones
reales. Registrar tipos de excepción del proveedor, no texto que pueda contener secretos.

## Latencia

`latency_probe.py` agrega muestras de servicios reales; no inventa mediciones.
La entrada es JSONL, una muestra por turno, sin audio, texto ni datos personales:

```json
{"real_services": true, "stages_ms": {"vad": 200, "stt": 200, "llm_ttfb": 300, "tts_ttfb": 250, "avatar": 200, "total": 1150}}
```

Esto ilustra el formato, **no un resultado del sistema**.

```bash
python -m evals.latency_probe /ruta/a/latencias-medidas.jsonl
```

Reporta p50/p95 por etapa y total. Medir el tiempo total desde el fin del habla del
candidato hasta el primer audio del avatar/salida con el mismo reloj monótono; no sumar
percentiles de etapas. Evaluar el objetivo p50 <1200 ms solo con al menos 30 muestras
reales. Las muestras simuladas/insuficientes devuelven `not_evaluated`. Los campos de
contenido y los valores negativos/no finitos se rechazan. No existe aún un conjunto de
muestras reales ni latencia validada.

## Propuesta G3 (no ejecutada)

Primer lote: **11 perfiles × 3 repeticiones = 33 conversaciones de texto**, con tres
ejecuciones de puntuación por conversación (99 llamadas al modelo grande) y una auditoría
independiente por sesión (33 llamadas grandes, más comparaciones de línea base/ataque
donde sea necesario). Sin STT/TTS/Tavus. Comenzar con un smoke de una sesión dentro del
mismo presupuesto para verificar JSON/uso. Si falla, detenerse en lugar de reintentar el
lote. Como máximo tres iteraciones de corrección antes de escalar el diagnóstico; cada
lote adicional requiere un presupuesto explícito.

Los IDs configurados `claude-haiku-5-5` y `claude-opus-5-5` estaban listados en el
[catálogo oficial](https://platform.claude.com/docs/en/models/overview), verificado el
2026-11-02. Precios estándar verificados entonces: Haiku 5.5 USD 0.10/MTok entrada y
0.50/MTok salida para prompts de hasta 100k tokens; Opus 5.5 USD 4/MTok entrada y
20/MTok salida. Fuente: [documentación oficial de precios](https://platform.claude.com/docs/en/about-claude/pricing).
Verificar disponibilidad real de cuenta, precios y credenciales antes del smoke test.

Estimación por escenario, **no es uso medido ni garantía de facturación**:

| Trabajo por conversación | Tokens entrada | Tokens salida | Costo USD |
| --- | ---: | ---: | ---: |
| Hasta 70 llamadas Haiku (candidato + analizador + escritor), promedio 1500/300 tokens | 105000 | 21000 | 0.021 |
| Tres ejecuciones de puntuación Opus, 15000/1500 tokens cada una | 45000 | 4500 | 0.270 |
| Auditor Opus, 15000/1000 tokens | 15000 | 1000 | 0.080 |
| Total estimado por conversación | | | 0.371 |
| 33 conversaciones | | | 12.243 |

Fórmula: `(entrada × tasa_entrada + salida × tasa_salida) / 1_000_000`, sumado por modelo/llamada.
Un margen del 50% da aproximadamente **USD 18.40**. Límite propuesto: **USD 20** para el
lote, incluyendo smoke y comparaciones de inyección. No garantizar las 33 sesiones si se
acaba el presupuesto; detenerse antes de la siguiente llamada. El pensamiento, reintentos,
auditoría extra y contexto más largo consumen presupuesto. No asumir descuentos de
Batch/caché, impuestos incluidos ni límites ficticios de tokens. Los controles monetarios
y el adaptador real deben existir y estar probados antes de usar el flag.

Prerrequisitos G3: aprobación del dueño con un límite, fábrica real auditada, credenciales
configuradas sin imprimirlas, tokens/reintentos acotados y reserva de presupuesto, y
evidencia de comparación de línea base/ataque para establecer resistencia a inyecciones.
