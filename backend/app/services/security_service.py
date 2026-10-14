import re


# ============================================================
# US-012 — FILTRAGE DES INJECTIONS
# ============================================================

INJECTION_PATTERNS = [

    # Prompt injection
    (
        "prompt_injection",
        re.compile(
            r"\b(ignore|oublie|oubliez)\b.{0,80}"
            r"\b(instructions?|consignes?|regles?)\b",
            re.IGNORECASE,
        ),
    ),

    (
        "prompt_injection",
        re.compile(
            r"\b(revele|révèle|affiche|montre|donne)\b.{0,80}"
            r"\b(prompt systeme|system prompt|instructions systeme|instructions internes)\b",
            re.IGNORECASE,
        ),
    ),

    (
        "prompt_injection",
        re.compile(
            r"\b(jailbreak|bypass|contourne|contourner)\b",
            re.IGNORECASE,
        ),
    ),

    # SQL injection
    (
        "sql_injection",
        re.compile(
            r"\bunion\s+(all\s+)?select\b",
            re.IGNORECASE,
        ),
    ),

    (
        "sql_injection",
        re.compile(
            r"\b(drop|truncate|alter)\s+(table|database)\b",
            re.IGNORECASE,
        ),
    ),

    (
        "sql_injection",
        re.compile(
            r"\b(insert\s+into|delete\s+from|update\s+\w+\s+set)\b",
            re.IGNORECASE,
        ),
    ),

    (
        "sql_injection",
        re.compile(
            r"(--|/\*|\*/)",
            re.IGNORECASE,
        ),
    ),

    # Commandes système
    (
        "system_command",
        re.compile(
            r"\b(rm\s+-rf|sudo|chmod|chown|shutdown)\b",
            re.IGNORECASE,
        ),
    ),

    (
        "system_command",
        re.compile(
            r"\b(powershell|cmd\.exe|bash|sh\s+-c)\b",
            re.IGNORECASE,
        ),
    ),

    (
        "system_command",
        re.compile(
            r"\b(curl|wget|netcat|nc)\b.{0,80}"
            r"\b(http|https|127\.0\.0\.1|localhost)\b",
            re.IGNORECASE,
        ),
    ),
]


def check_message_security(message):
    """
    Retourne :

    {
        "allowed": True,
        "reason": None,
        "type": None
    }

    ou :

    {
        "allowed": False,
        "reason": "...",
        "type": "..."
    }
    """

    if not message:
        return {
            "allowed": True,
            "reason": None,
            "type": None,
        }

    for pattern_type, pattern in INJECTION_PATTERNS:

        if pattern.search(message):

            return {
                "allowed": False,
                "reason": (
                    "Tentative de manipulation des instructions "
                    "ou d'exécution non autorisée détectée."
                ),
                "type": pattern_type,
            }

    return {
        "allowed": True,
        "reason": None,
        "type": None,
    }