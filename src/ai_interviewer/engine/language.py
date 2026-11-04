"""Local language detection and fixed interview wording; no generated questions."""
import re

COMPETENCY_ENGLISH = {
    "discovery": "Discovery and user understanding",
    "prioritization": "Prioritization and trade-offs",
    "metrics_outcomes": "Metrics and outcomes",
    "stakeholders": "Stakeholder management and alignment",
    "execution": "Execution and team delivery",
    "communication": "Communication and structured thinking",
}


def language_preference(text: str) -> str | None:
    value = text.casefold().strip(" .!?¿¡")
    if re.fullmatch(r"(?:please |por favor )?(?:speak |habla |hablá |hablemos |continue in |let's speak |en |in )?(english|inglés|ingles|spanish|español)(?: please| por favor)?", value):
        return "es" if any(word in value for word in ("spanish", "español")) else "en"
    return None


def detect_language(text: str, current: str = "en") -> str:
    from langdetect import DetectorFactory, detect_langs, LangDetectException
    DetectorFactory.seed = 0
    # An explicit language preference is safe; it cannot change interview phases.
    preference = language_preference(text)
    if preference:
        return preference
    if len(re.findall(r"\w+", text)) < 4:
        return current
    try:
        result = detect_langs(text[:4000])[0]
        return result.lang if result.lang in {"en", "es"} and result.prob >= .90 else current
    except LangDetectException:
        return current


# Maps English (primary) → Spanish for bilingual mode.
SPANISH = {
    "I am an AI interviewer. This interview is recorded as a transcript and reviewed by a person. To start, tell me about your professional background: what is your current role and what product responsibilities do you have? You can answer in English or Spanish.": "Soy un entrevistador de IA; esta entrevista se graba y la revisa una persona. Para empezar, contame tu contexto profesional: ¿cuál es tu rol actual y qué responsabilidades de producto tenés?",
    "I am an AI interviewer. This interview is recorded as a transcript and reviewed by a person. Shall we start?": "Soy un entrevistador de IA; esta entrevista se graba y la revisa una persona. ¿Podemos empezar?",
    "Briefly describe your product responsibilities in a recent role.": "Para ubicarnos, contame brevemente qué responsabilidades de producto tuviste en una experiencia reciente.",
    "Thank you for your time. The interview is complete. A human reviewer will review your answers.": "Gracias por tu tiempo; terminamos la entrevista. El equipo humano revisará las respuestas.",
    "What would you like to ask the team about the role or the company?": "¿Qué te gustaría preguntarle al equipo sobre el rol o la empresa?",
    "Thank you for sharing your experience. The team will review this interview and answer your outstanding questions.": "Gracias por compartir tu experiencia. El equipo humano revisará la entrevista y responderá las consultas pendientes.",
    "The team will answer that question. Do you have another question?": "Esa información la va a responder el equipo humano. ¿Tenés otra consulta?",
    "Let us focus on your professional experience. Tell me about a specific example related to the question.": "Sigamos con tu experiencia profesional; contame un caso concreto relacionado con la pregunta.",
    "Let us continue with a specific example from your professional experience related to the question.": "Sigamos con un ejemplo de tu experiencia profesional relacionado con la pregunta.",
    "Let us return to product work. Describe a specific situation, what you did and the outcome you observed.": "Volvamos al trabajo de producto; contame una situación concreta, qué hiciste y qué resultado observaste.",
    "Let us return to the question. Choose a specific situation related to that product decision.": "Volvamos a la pregunta; elegí una situación concreta vinculada con esa decisión de producto.",
    "To complete this example, what outcome did you observe or what did you learn? We will then move to the next competency.": "Para completar este ejemplo, ¿qué resultado observaste o qué aprendiste? Después seguimos con la próxima competencia.",
    "Which specific project or situation was this? What problem did you need to solve?": "¿En qué proyecto o situación concreta pasó? Contame cuál era el problema que necesitaban resolver.",
    "What did you personally do in that situation, and why did you choose that action?": "¿Qué hiciste vos específicamente en ese caso y por qué elegiste esa acción?",
    "What specific outcome did you observe after that action, or what did you learn?": "¿Qué resultado concreto observaste después de esa acción o qué aprendiste de lo que pasó?",
    "Could you give a specific example describing the situation, your own actions and the outcome or learning?": "¿Podés darme un ejemplo concreto con la situación, qué hiciste vos y qué resultado o aprendizaje hubo?",
    "Are you still there?": "¿Seguís ahí?",
}

# Spanish translations of questions identified by ID.
QUESTION_SPANISH = {
    "discovery_problem": "Contame una situación concreta en la que tuviste que entender un problema de usuarios antes de decidir qué construir. ¿Qué hiciste y qué cambió a partir de lo que aprendiste?",
    "discovery_assumption": "Contame un caso en que una hipótesis de producto tuya resultó equivocada. ¿Cómo lo descubriste y qué decisión tomaste?",
    "prioritization_choice": "Contame una decisión concreta en la que no alcanzaban el tiempo o los recursos para hacer todo. ¿Qué priorizaste, qué dejaste afuera y por qué?",
    "prioritization_no": "Contame una vez que dijiste que no, o propusiste postergar, a un pedido importante. ¿Cómo tomaste esa decisión y qué pasó después?",
    "metrics_impact": "Contame una iniciativa cuyo impacto hayas evaluado. ¿Qué resultado buscaban y qué evidencia usaste para saber si lo lograron?",
    "metrics_disappointment": "Contame una vez que lanzaron algo y el resultado no fue el esperado. ¿Cómo lo detectaste y qué decidiste hacer?",
    "stakeholders_conflict": "Contame un desacuerdo concreto entre personas o áreas sobre una decisión de producto. ¿Qué hiciste para resolverlo y a qué acuerdo llegaron?",
    "stakeholders_change": "Contame una vez que tuviste que comunicar un cambio de plan que afectaba un compromiso. ¿Cómo lo planteaste y qué ocurrió?",
    "execution_delivery": "Contame cómo llevaste una iniciativa concreta desde el objetivo hasta una entrega con el equipo. ¿Cómo definieron el alcance y manejaron las dependencias?",
    "execution_obstacle": "Contame una entrega que se complicó por una dependencia o un imprevisto. ¿Qué hiciste con el equipo para adaptar el plan y qué aprendieron?",
    "communication_synthesis": "Elegí una decisión de las que conversamos y resumí el problema, tu aporte y el resultado. ¿Qué aprendizaje te llevarías a una situación parecida?",
    "communication_explanation": "Contame una vez que explicaste una decisión de producto a alguien que no tenía el mismo contexto. ¿Cómo elegiste qué contar y cómo verificaste que se entendiera?",
}


def interview_text(text, language, role):
    if language == "en":
        return text
    # Spanish mode: translate English primary text → Spanish.
    if text in SPANISH:
        return SPANISH[text]
    for competency in role.competencies:
        for question in competency.questions:
            if question.text == text:
                return QUESTION_SPANISH.get(question.id, text)
    return text
