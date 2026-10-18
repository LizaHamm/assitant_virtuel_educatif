import re
import unicodedata


# ============================================================
# US-012 — SÉCURITÉ DES QUESTIONS UTILISATEUR
# Protection démonstrative contre :
# - prompt injection / jailbreak
# - XSS / HTML exécutable
# - injections SQL évidentes
# - commandes système évidentes
#
# Le but est de bloquer les charges clairement malveillantes sans
# empêcher les questions étudiantes normales contenant, par exemple,
# les mots « script », « système » ou « SQL » dans un contexte de cours.
# ============================================================

MAX_SECURITY_SCAN_LENGTH = 10_000


def _normalize_for_security(value: str) -> str:
    """Normalisation légère pour rendre les règles moins sensibles aux accents."""
    value = unicodedata.normalize("NFKC", value or "")
    return value.strip()


SECURITY_PATTERNS = [
    # --------------------------------------------------------
    # Prompt injection / jailbreak
    # --------------------------------------------------------
    (
        "prompt_injection",
        re.compile(
            r"\b(ignore|ignorer|ignorez|oublie|oublier|oubliez|disregard|forget)\b"
            r".{0,120}\b(instructions?|consignes?|regles?|règles?|prompt|system)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "prompt_injection",
        re.compile(
            r"\b(revele|révèle|reveler|révéler|affiche|afficher|montre|montrer|donne|donner|show|reveal)\b"
            r".{0,120}\b(system\s*prompt|prompt\s*systeme|prompt\s*système|instructions?\s*(internes?|systeme|système))\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "prompt_injection",
        re.compile(
            r"\b(jailbreak|bypass|developer\s*mode|mode\s*developpeur|mode\s*développeur|"
            r"contourne|contourner|override\s+instructions?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prompt_injection",
        re.compile(
            r"\b(act\s+as|pretends?\s+to\s+be|fais\s+comme\s+si)\b.{0,120}"
            r"\b(system|developer|administrateur|admin|sans\s+regles?|sans\s+règles?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),

    # --------------------------------------------------------
    # XSS / HTML exécutable
    # --------------------------------------------------------
    (
        "xss",
        re.compile(r"<\s*script\b[^>]*>", re.IGNORECASE),
    ),
    (
        "xss",
        re.compile(r"<\s*/\s*script\s*>", re.IGNORECASE),
    ),
    (
        "xss",
        re.compile(
            r"<[^>]+\bon(?:error|load|click|mouseover|focus|submit|input|change)\s*=",
            re.IGNORECASE,
        ),
    ),
    (
        "xss",
        re.compile(r"\bjavascript\s*:\s*", re.IGNORECASE),
    ),
    (
        "xss",
        re.compile(r"<\s*(iframe|object|embed|svg)\b[^>]*>", re.IGNORECASE),
    ),

    # --------------------------------------------------------
    # SQL injection évidente
    # --------------------------------------------------------
    (
        "sql_injection",
        re.compile(r"\bunion\s+(all\s+)?select\b", re.IGNORECASE),
    ),
    (
        "sql_injection",
        re.compile(r"\b(drop|truncate|alter)\s+(table|database)\b", re.IGNORECASE),
    ),
    (
        "sql_injection",
        re.compile(r"\b(insert\s+into|delete\s+from|update\s+\w+\s+set)\b", re.IGNORECASE),
    ),
    (
        "sql_injection",
        re.compile(
            r"(?:'|\")\s*(?:or|and)\s+(?:'[^']*'|\"[^\"]*\"|\d+)\s*=\s*"
            r"(?:'[^']*'|\"[^\"]*\"|\d+)",
            re.IGNORECASE,
        ),
    ),

    # --------------------------------------------------------
    # Commandes système évidentes
    # --------------------------------------------------------
    (
        "system_command",
        re.compile(r"\b(rm\s+-rf|sudo\s+|chmod\s+|chown\s+|shutdown\s+|reboot\s*)", re.IGNORECASE),
    ),
    (
        "system_command",
        re.compile(r"\b(cmd\.exe|powershell(?:\.exe)?|bash\s+-c|sh\s+-c)\b", re.IGNORECASE),
    ),
    (
        "system_command",
        re.compile(
            r"\b(curl|wget|netcat|nc)\b.{0,100}\b(https?://|127\.0\.0\.1|localhost)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
]


REASONS = {
    "prompt_injection": "Tentative de manipulation des instructions du chatbot détectée.",
    "xss": "Contenu HTML/JavaScript potentiellement exécutable détecté.",
    "sql_injection": "Motif d'injection SQL potentiellement dangereux détecté.",
    "system_command": "Commande système potentiellement dangereuse détectée.",
}


def check_message_security(message):
    """
    Retourne toujours un dictionnaire :

        {"allowed": True, "reason": None, "type": None}

    ou :

        {"allowed": False, "reason": "...", "type": "xss"}

    Cette couche est une protection applicative de démonstration. Elle ne
    remplace pas l'échappement React côté affichage, les requêtes SQL
    paramétrées, les contrôles d'accès ni les protections du serveur web.
    """
    if message is None:
        return {"allowed": True, "reason": None, "type": None}

    text = _normalize_for_security(str(message))
    if not text:
        return {"allowed": True, "reason": None, "type": None}

    # Évite qu'une charge anormalement énorme monopolise le moteur regex.
    scan_text = text[:MAX_SECURITY_SCAN_LENGTH]

    for pattern_type, pattern in SECURITY_PATTERNS:
        if pattern.search(scan_text):
            return {
                "allowed": False,
                "reason": REASONS.get(
                    pattern_type,
                    "Contenu potentiellement dangereux détecté.",
                ),
                "type": pattern_type,
            }

    return {"allowed": True, "reason": None, "type": None}
