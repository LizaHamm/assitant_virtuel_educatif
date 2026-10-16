"""US-032 bilingual adapter for the existing rule-based ESIC response service.

English requests are translated to French for the existing intent/rules engine,
then the complete answer (including knowledge-base content) is translated back.
The translation provider requires an internet connection. See README for privacy note.
"""
from typing import Optional

from deep_translator import GoogleTranslator
from app.services.response_service import generate_response as generate_response_fr


class TranslationUnavailable(RuntimeError):
    pass


def _translate_chunks(text: str, target: str, source: str = "auto") -> str:
    if not text or not text.strip():
        return text
    translator = GoogleTranslator(source=source, target=target)
    # Translate paragraph-by-paragraph to avoid URL-length limits on long rules.
    paragraphs = text.split("\n")
    translated = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            translated.append("")
            continue
        if len(paragraph) <= 3500:
            translated.append(translator.translate(paragraph) or paragraph)
            continue
        # Long paragraph: preserve line structure and translate smaller pieces.
        pieces = re_split_long_text(paragraph, 3000)
        translated.extend(translator.translate(piece) or piece for piece in pieces)
    return "\n".join(translated)


def re_split_long_text(text: str, limit: int):
    pieces, current = [], ""
    for sentence in text.replace("! ", "!\n").replace("? ", "?\n").replace(". ", ".\n").split("\n"):
        if current and len(current) + len(sentence) + 1 > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def translate_text(text: str, target: str, source: str = "auto") -> str:
    if target not in {"fr", "en"}:
        raise ValueError("Unsupported language")
    if target == "fr":
        return _translate_chunks(text, "fr", source=source)
    return _translate_chunks(text, "en", source=source)


def generate_response(question: str, language: str = "fr") -> str:
    """Generate a response in the requested language, not just translate UI labels."""
    if language != "en":
        return generate_response_fr(question)
    try:
        french_question = _translate_chunks(question, "fr", source="auto")
        french_answer = generate_response_fr(french_question)
        return _translate_chunks(french_answer, "en", source="auto")
    except Exception as exc:
        # Never silently return a French answer when English was requested.
        return (
            "I couldn't generate an English answer because the translation service is "
            "temporarily unavailable. Please try again or switch to French."
        )
