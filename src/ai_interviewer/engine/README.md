# Motor y scoring del piloto

`StructuredInterviewEngine` implementa el contrato async. Cada instancia corresponde a
una entrevista; `start()` presupone consentimiento persistido. `transcript()` incluye
ambas voces, con IDs estables. Las decisiones y sus flags se deben persistir antes de
emitir audio. El motor no escribe storage ni inicia servicios.

Sin adaptadores, usa `OfflineAnswerAnalyzer`: solicita aclaraciones STAR conservadoras
hasta el límite, sin simular una evaluación semántica real. Para LLM se inyectan
`LLMAnswerAnalyzer(model)` y, opcionalmente, `LLMQuestionWriter(model)`. El proveedor debe
implementar `async complete(system: str, user: str) -> str` con JSON; la aplicación decide
credenciales, presupuesto y transporte. No hay llamadas de red por importación.

Por seguridad del piloto, la salida del writer debe coincidir con una de las preguntas
aprobadas de la competencia actual; otra redacción vuelve a la pregunta base y marca
`question_fallback`. Esto restringe la paráfrasis hasta contar con evaluación semántica.
Las fases, fin, repeticiones y límites de tiempo siempre los decide código.

`restore()` presupone que API comprobó credencial, UUID y asociación del rol/version y
candidato al Interview guardado. SessionSnapshot no contiene esos atributos. El motor
comprueba timestamps, competencias, deadline original y estado, sin volver a hablar al
restaurar. El reloj monotónico de turnos debe conservar su origen entre reconexiones.

Scoring: `InterviewScorer(model).score(interview_id, role, turns, flags=None)` ejecuta tres
corridas acotadas. Rechaza referencias que no correspondan a respuestas del candidato en
la competencia (salvo comunicación transversal), salida sensible y decisiones de contratación.
Sin evidencia en cualquiera de las tres corridas, el score final queda sin número; cuando
hay tres números usa mediana y rango máximo-mínimo. La pertinencia semántica de las citas
requiere evaluación del modelo y revisión humana, no se establece con IDs ni keywords.

`MockScoringModel` es un proveedor offline explícito: todos los scores quedan sin número
y el reporte lleva `mock_scoring`. No representa una medición de calidad del candidato.

`safe_text` excluye frases con patrones sensibles y turnos con instrucciones maliciosas.
Es una defensa lexical conservadora; no garantiza detectar toda información sensible,
inferencia o inyección indirecta. El prompt refuerza las prohibiciones. Las evals reales,
revisión de privacidad y calibración humana son requisitos antes del piloto; los tests
unitarios no acreditan que esas barreras semánticas estén resueltas. El transcript bruto
se conserva para storage autorizado; nunca se imprime ni envía entero al scoring.

El scorer recompone `injection_attempt` desde el transcript para conservar ese flag tras
reanudación. API debe persistir aparte otros flags de decisiones, cortes y degradación y
pasarlos al scorer; el contrato SessionSnapshot no los contiene.
