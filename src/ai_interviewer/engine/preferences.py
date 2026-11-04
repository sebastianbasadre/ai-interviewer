"""Small conversational preferences, separate from professional interview answers."""
import re
from dataclasses import dataclass

from .safety import has_sensitive, is_injection, normalized


def clean_name(value: str) -> str | None:
    value = value.strip().strip(".!?¿¡,\"“”")
    words = value.split()
    if not 1 <= len(words) <= 3 or len(value) > 50:
        return None
    if not all(all(c.isalpha() or c in "-'’" for c in word) and any(c.isalpha() for c in word) for word in words):
        return None
    blocked = {"synthetic", "sintetica", "sintetico", "test", "prueba", "example", "candidate", "ignore", "instructions", "system", "score", "repeat", "name", "nombre", "please", "yes", "no", "si", "i", "am", "soy", "trabajo", "lead", "product", "director", "manager", "work", "team", "and", "y", "me", "my", "by"}
    if set(normalized(value).split()) & blocked or has_sensitive(value) or is_injection(value):
        return None
    return " ".join(words)


ASK_EN = "Of course. What would you like me to call you?"
ASK_ES = "Claro. ¿Cómo te gustaría que te llame?"


def is_preference_reply(text: str) -> bool:
    return text in {ASK_EN, ASK_ES} or (
        text.startswith(("Of course, ", "Claro, ")) and
        text.endswith(("Take your time. I'm listening.", "Tomate tu tiempo. Te escucho."))
    )


def preference_language(text: str, current: str) -> str:
    value = normalized(text)
    if re.search(r"llam|mi nombre", value):
        return "es"
    if re.search(r"call me|use my name|my name is", value):
        return "en"
    return current


@dataclass
class NamePreference:
    name: str | None = None
    awaiting_name: bool = False

    def handle(self, text: str, language: str = "en") -> str | None:
        if is_injection(text) or has_sensitive(text):
            self.awaiting_name = False
            return None
        value = text.strip().strip(".!?¿¡")
        general = re.fullmatch(
            r"(?:please )?(?:(?:can|could|would|will) you |(?:podés|podes|podrías|podrias|puedes) )?"
            r"(?:call me (?:by )?(?:my )?name|use my name|llamarme (?:por )?mi nombre|usar mi nombre)(?: please)?",
            value, re.IGNORECASE,
        )
        specific = re.fullmatch(
            r"(?:(?:no,? |please )?)(?:(?:can|could|would|will) you |(?:podés|podes|podrías|podrias|puedes) )?"
            r"(?:call me|my name is|llamame|llámame|llamarme|me llamo|mi nombre es)\s+(.+?)(?:,? please| por favor)?",
            value, re.IGNORECASE,
        )
        proposed = clean_name(specific.group(1)) if specific and not general else None
        if not general and proposed is None:
            if self.awaiting_name:
                proposed = clean_name(value)
                self.awaiting_name = False
            if proposed is None:
                return None
        if proposed:
            self.name = proposed
        self.awaiting_name = self.name is None
        if self.awaiting_name:
            return ASK_ES if language == "es" else ASK_EN
        return (f"Claro, {self.name}. Tomate tu tiempo. Te escucho." if language == "es" else
                f"Of course, {self.name}. Take your time. I'm listening.")


def replay_preferences(turns, candidate_name: str = ""):
    preference = NamePreference(clean_name(candidate_name))
    excluded = set()
    for turn in turns:
        if turn.speaker == "candidate" and preference.handle(turn.text) is not None:
            excluded.add(turn.id)
        elif turn.speaker == "interviewer" and is_preference_reply(turn.text):
            match = re.fullmatch(r"(?:Of course, |Claro, )(.+?)\. (?:Take your time\. I'm listening\.|Tomate tu tiempo\. Te escucho\.)", turn.text)
            if match and (name := clean_name(match.group(1))):
                preference.name = name
                preference.awaiting_name = False
    return preference, excluded
