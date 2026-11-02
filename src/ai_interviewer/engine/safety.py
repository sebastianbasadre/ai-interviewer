"""Conservative text filtering shared by prompts and rendered scoring evidence.

This is a defense-in-depth fallback, not a guarantee of semantic PII detection.
Sensitive sentences are excluded rather than rewritten into inferred attributes.
"""
import re
import unicodedata


def normalized(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(char))


SENSITIVE = re.compile(
    r"\b(edad|anos de edad|tengo \d{1,3} anos|hijos?|hijas?|embaraz\w*|casad\w*|solter\w*|"
    r"divorciad\w*|estado civil|salud|enfermedad\w*|diagnostic\w*|discapacidad\w*|"
    r"religio\w*|catolic\w*|judi[oa]\w*|musulman\w*|cristian\w*|politic\w*|partido|"
    r"nacionalidad|origen etnico|raza|racial|soy de|naci en|"
    r"age|children|pregnan\w*|married|single|health|religion|ethnic\w*|nationality|"
    r"acento|accent|apariencia|appearance|voz|voice|cara|face|emocion\w*|emotion\w*)\b"
)
INJECTION = re.compile(
    r"(ignor\w* (?:tus|las|all|previous)|ignore (?:all|your|previous)|"
    r"poneme\s*[1-5]|(?:dame|asigna\w*) (?:un )?5|score (?:me )?5|"
    r"(?:revela\w*|decime|mostra\w*|reveal|show).{0,35}(?:prompt|instrucciones|instructions)|"
    r"system prompt|developer message|</?(?:system|assistant)>)"
)


def has_sensitive(text: str) -> bool:
    return bool(SENSITIVE.search(normalized(text)))


def is_injection(text: str) -> bool:
    return bool(INJECTION.search(normalized(text)))


def safe_text(text: str) -> str:
    """Keep only professional sentences; remove whole injection-bearing turns."""
    if is_injection(text):
        return ""
    return " ".join(
        sentence.strip() for sentence in re.split(r"(?<=[.!?;])\s+|\n+", text)
        if sentence.strip() and not has_sensitive(sentence)
    )
