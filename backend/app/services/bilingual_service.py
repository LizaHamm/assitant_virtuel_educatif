"""Bilingual adapter for the ESIC rule-based response service.

The knowledge base and NLP pipeline operate in French. English requests are
translated to French, answered by response_service, and translated back.
Provider failures are handled so that a temporary translation outage does not
turn /api/chat into an HTTP 500.
"""

from functools import lru_cache
import logging
import re

from deep_translator import GoogleTranslator, MyMemoryTranslator
from app.services.response_service import generate_response as generate_response_fr

logger = logging.getLogger(__name__)


class TranslationUnavailable(RuntimeError):
    """Raised when all available translation providers fail."""


# MyMemory may require regional language codes in some deep-translator versions.
_MYMEMORY_CODES = {
    "en": ("en-GB", "en-US", "en"),
    "fr": ("fr-FR", "fr"),
}


ENGLISH_TRANSLATION_ERROR = (
    "I'm temporarily unable to translate your question. Please try again, "
    "or switch to French while the translation service is unavailable."
)


def _split_long_text(text: str, limit: int = 3000) -> list[str]:
    """Split long text into pieces accepted by online translation providers."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    pieces: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > limit:
            if current:
                pieces.append(current)
                current = ""
            # Preserve the complete text without exceeding the provider limit.
            pieces.extend(
                sentence[start:start + limit]
                for start in range(0, len(sentence), limit)
            )
        elif current and len(current) + len(sentence) + 1 > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        pieces.append(current)
    return pieces


def _argos_translation_available(source: str, target: str) -> bool:
    """Return True when an Argos translation path is available locally."""
    try:
        import argostranslate.translate

        installed = {
            language.code: language
            for language in argostranslate.translate.get_installed_languages()
        }
        if source == "auto" or source not in installed or target not in installed:
            return False
        return installed[source].get_translation(installed[target]) is not None
    except Exception as exc:
        logger.debug("Argos availability check failed: %r", exc)
        return False


def _argos_translate(text: str, source: str, target: str) -> str:
    """Translate using installed Argos language packages; no network required."""
    import argostranslate.translate

    if source == "auto":
        raise TranslationUnavailable("Argos requires an explicit source language.")

    installed = {
        language.code: language
        for language in argostranslate.translate.get_installed_languages()
    }
    if source not in installed or target not in installed:
        raise TranslationUnavailable(f"Argos model missing: {source} -> {target}")

    translation = installed[source].get_translation(installed[target])
    if translation is None:
        raise TranslationUnavailable(f"Argos model missing: {source} -> {target}")

    result = translation.translate(text)
    if not result or not result.strip():
        raise TranslationUnavailable("Argos returned an empty result.")
    return result.strip()


def _translate_with_mymemory(text: str, source: str, target: str) -> str:
    errors = []
    source_codes = _MYMEMORY_CODES.get(source, (source,))
    target_codes = _MYMEMORY_CODES.get(target, (target,))

    for source_code in source_codes:
        for target_code in target_codes:
            try:
                result = MyMemoryTranslator(
                    source=source_code,
                    target=target_code,
                ).translate(text)
                if result and result.strip():
                    return result.strip()
                errors.append(f"{source_code}->{target_code}: empty result")
            except Exception as exc:
                errors.append(f"{source_code}->{target_code}: {exc!r}")
                # Unsupported locale is a configuration error, not a reason to
                # prevent trying the other known forms of the same language.
                logger.debug("MyMemory %s->%s failed: %r", source_code, target_code, exc)

    raise TranslationUnavailable("MyMemory failed: " + "; ".join(errors))


@lru_cache(maxsize=1000)
def _translate_piece(text: str, source: str, target: str) -> str:
    if source == target:
        return text

    errors: list[str] = []

    # Prefer offline Argos when the required model is already installed. This
    # avoids API quotas during demos and repeated chat requests.
    if source != "auto" and _argos_translation_available(source, target):
        try:
            return _argos_translate(text, source, target)
        except Exception as exc:
            errors.append(f"Argos local: {exc!r}")
            logger.warning("Local Argos translation failed: %r", exc)

    # Online services are useful when Argos is not installed or cannot translate.
    # Google's supported language IDs are the standard two-letter ISO codes.
    try:
        result = GoogleTranslator(source=source, target=target).translate(text)
        if result and result.strip():
            return result.strip()
        errors.append("Google: empty result")
    except Exception as exc:
        errors.append(f"Google: {exc!r}")
        logger.warning("Google translation failed: %r", exc)

    try:
        result = _translate_with_mymemory(text, source, target)
        if result and result.strip():
            return result.strip()
        errors.append("MyMemory: empty result")
    except Exception as exc:
        errors.append(f"MyMemory: {exc!r}")
        logger.warning("MyMemory translation failed: %r", exc)

    # Final local fallback. When source is auto, try both supported directions.
    argos_sources = [source] if source != "auto" else ["en", "fr"]
    for argos_source in argos_sources:
        if argos_source == target:
            return text
        try:
            return _argos_translate(text, argos_source, target)
        except Exception as exc:
            errors.append(f"Argos {argos_source}: {exc!r}")
            logger.warning("Argos translation failed: %r", exc)

    raise TranslationUnavailable(
        "All translation providers failed (" + "; ".join(errors) + ")"
    )


def translate_text(text: str, target: str, source: str = "auto") -> str:
    """Translate text while preserving paragraph breaks.

    Raises TranslationUnavailable if the translation could not be completed.
    Callers handling user-facing HTTP endpoints should catch this exception.
    """
    if target not in {"fr", "en"}:
        raise ValueError("Unsupported target language")
    if source not in {"auto", "fr", "en"}:
        raise ValueError("Unsupported source language")
    if not text or not text.strip():
        return text
    if source == target:
        return text

    paragraphs: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            paragraphs.append("")
            continue
        translated_pieces = [
            _translate_piece(piece, source, target)
            for piece in _split_long_text(paragraph)
        ]
        paragraphs.append(" ".join(translated_pieces))
    return "\n".join(paragraphs)


def generate_response(question: str, language: str = "fr") -> str:
    """Generate a response without allowing translation outages to crash chat."""
    if language != "en":
        return generate_response_fr(question)

    try:
        french_question = translate_text(question, target="fr", source="en")
    except Exception as exc:
        logger.warning("Could not translate incoming English question: %r", exc)
        return ENGLISH_TRANSLATION_ERROR

    try:
        french_answer = generate_response_fr(french_question)
    except Exception:
        logger.exception("French response engine failed for an English request")
        return (
            "I'm sorry, I couldn't prepare an answer right now. "
            "Please try again or ask in French."
        )

    try:
        return translate_text(french_answer, target="en", source="fr")
    except Exception as exc:
        logger.warning("Could not translate French answer to English: %r", exc)
        return ENGLISH_TRANSLATION_ERROR
