"""Professional-only synthetic answers for reviewing report output, never a person."""
from ai_interviewer.contracts import Turn, InterviewPhase


ANSWERS = {
    "discovery": "En el checkout de una tienda observamos un abandono del 40%. Mi hipótesis era que faltaban medios de pago, pero revisé tickets y entrevisté a ocho usuarios antes de construir. Encontré que el formulario pedía datos innecesarios. Contrasté esa explicación con las sesiones y propuse probar una versión con menos pasos. En una prueba limitada el abandono bajó al 20%; mantuve abierta la duda sobre si el cambio se sostendría con más tráfico.",
    "prioritization": "En un trimestre teníamos capacidad para una iniciativa y dos pedidos: integrar un proveedor para un contrato con fecha límite o renovar el buscador. Comparé valor esperado, esfuerzo, riesgo contractual y dependencias con ingeniería y comercial. Propuse priorizar la integración y postergar el buscador, documentando la renuncia y las estimaciones inciertas. Entregamos la integración antes del límite y revisamos la prioridad dos semanas después al cambiar la capacidad disponible.",
    "metrics_outcomes": "He trabajado con métricas, pero en esta entrevista no tengo un caso concreto ni puedo describir una medición o un resultado propio.",
    "stakeholders": "En una integración, comercial prometía un alcance que ingeniería no podía entregar en el plazo acordado. Reuní a ambos equipos, explicitamos el objetivo del contrato y contrastamos los pedidos con dependencias y estimaciones. Propuse un primer alcance verificable y documenté los puntos pendientes y sus responsables. El cliente aceptó el alcance inicial, entregamos a tiempo y mantuvimos una revisión semanal de riesgos sin ocultar lo que quedaba afuera.",
    "execution": "En el lanzamiento de pagos dividí el cambio en incrementos con el equipo, fijamos criterios de aceptación y validamos primero la dependencia del proveedor. Al aparecer un retraso revisé el alcance con ingeniería en lugar de agregar trabajo simultáneo. Probamos el incremento en un grupo acotado, encontramos un error y pausamos la expansión hasta corregirlo. El despliegue posterior no registró el mismo error y sumamos esa verificación al checklist del equipo.",
    "communication": "Para explicar ese lanzamiento preparé un resumen con el problema, la evidencia, las alternativas y la decisión. Separé lo que habíamos observado de la hipótesis de impacto, adapté el detalle para comercial e ingeniería y pedí que devolvieran el acuerdo con sus propias palabras. Detectamos una contradicción sobre el alcance antes de empezar, la resolvimos por escrito y el equipo pudo trabajar con criterios de aceptación compartidos.",
}


def report_turns(role):
    turns = []
    for index, comp in enumerate(role.competencies):
        turns.append(Turn(speaker="interviewer", text=comp.questions[0].text,
            ts_start=index, ts_end=index, phase=InterviewPhase.COMPETENCIES, competency_id=comp.id))
        turns.append(Turn(speaker="candidate", text=ANSWERS[comp.id],
            ts_start=index, ts_end=index, phase=InterviewPhase.COMPETENCIES, competency_id=comp.id))
    return turns
