# Motor y puntuación del piloto

`StructuredInterviewEngine` implementa el contrato async. Cada instancia representa una
entrevista; `start()` asume consentimiento persistido. `transcript()` incluye ambos
hablantes con IDs estables. Persistir las decisiones y sus banderas antes de emitir audio.
El motor no escribe almacenamiento ni inicia servicios.

Sin adaptadores, `OfflineAnswerAnalyzer` solicita conservadoramente aclaración STAR hasta
el límite sin pretender realizar evaluación semántica. Para un LLM, inyectar
`LLMAnswerAnalyzer(model)` y opcionalmente `LLMQuestionWriter(model)`. Los proveedores
implementan `async complete(system: str, user: str) -> str` devolviendo JSON. La aplicación
controla credenciales, presupuesto y transporte. Importar módulos nunca hace llamadas de red.

La demo de texto habilita `mock_single_followup`: pedir aclaración una vez, luego avanzar
con `mock_script_advance` sin afirmar evidencia suficiente. El progreso sobrevive a la
restauración. Este modo no modifica los analizadores LLM.

Para la seguridad del piloto, la salida del escritor debe coincidir exactamente con una
pregunta aprobada para la competencia actual. Otra redacción cae de vuelta a la pregunta
base con `question_fallback`. Esto restringe la paráfrasis hasta que la evaluación
semántica esté disponible. El código siempre controla las fases, terminación, repeticiones
y límites de tiempo.

`restore()` asume que la API verificó credenciales, UUID, vinculación de rol/versión y
candidato al Interview almacenado. SessionSnapshot no contiene esos atributos. El motor
verifica timestamps, competencias, plazo original y estado sin volver a hablar.
Preservar el origen del reloj monótono de turnos entre reconexiones.

`InterviewScorer(model).score(interview_id, role, turns, flags=None)` ejecuta tres
evaluaciones acotadas. Rechaza referencias fuera de las respuestas del candidato para la
competencia (excepto comunicación entre competencias), salida sensible y decisiones de
contratación. Si alguna ejecución carece de evidencia, dejar el puntaje final sin número.
Con tres números, usar la mediana y la dispersión máximo-menos-mínimo. La evaluación del
modelo y la revisión humana establecen la relevancia de las citas; los IDs y palabras clave
solos no pueden.

`MockScoringModel` es un proveedor offline explícito: todos los puntajes permanecen sin
número y los informes llevan `mock_scoring`. No mide la calidad del candidato.

`safe_text` excluye oraciones que coinciden con patrones sensibles y turnos que contienen
instrucciones maliciosas. Esta defensa léxica conservadora no garantiza la detección de
toda información sensible, inferencia o inyección indirecta. Los prompts refuerzan las
prohibiciones. Las evaluaciones reales, la revisión de privacidad y la calibración humana
son prerrequisitos para un piloto; las pruebas unitarias no establecen que las salvaguardas
semánticas estén resueltas. Preservar las transcripciones crudas en almacenamiento
autorizado; nunca imprimir ni enviar la transcripción cruda completa a la puntuación.

El scorer reconstruye `injection_attempt` desde la transcripción para que sobreviva a la
reanudación. La API debe persistir por separado otras banderas de decisión, corte y
degradación y pasarlas al scorer; SessionSnapshot no las contiene.

Las solicitudes de nombre se manejan por separado de las respuestas profesionales. Reconocen
el nombre preferido sin repetir la pregunta, avanzar la fase ni consumir seguimientos.
Las preferencias y la pregunta pendiente sobreviven a la restauración. Los turnos solo-nombre
se excluyen del análisis de respuestas y la evidencia de puntuación.
