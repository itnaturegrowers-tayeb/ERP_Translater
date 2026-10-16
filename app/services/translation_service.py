from __future__ import annotations

from abc import ABC, abstractmethod
import logging

from app.models.translation_result import GlossaryMatch, TranslationResult
from app.services.glossary_service import GlossaryService

LOGGER = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "es": "Spanish",
    "en": "English",
    "fr": "French",
    "ar": "Arabic",
}


class TranslationProvider(ABC):
    """Replace this provider to add an API or local language model later."""

    @abstractmethod
    def translate(self, text: str, source_language: str, target_language: str) -> str | None:
        raise NotImplementedError


class DisabledTranslationProvider(TranslationProvider):
    def translate(self, text: str, source_language: str, target_language: str) -> None:
        return None


class LocalArgosTranslationProvider(TranslationProvider):
    """Offline neural translation using an installed Argos language model."""

    def __init__(self) -> None:
        self._translate_module = None
        try:
            import argostranslate.translate

            self._translate_module = argostranslate.translate
        except Exception as exc:
            LOGGER.warning("Local Argos translation is unavailable: %s", exc)

    def translate(self, text: str, source_language: str, target_language: str) -> str | None:
        if self._translate_module is None or not text.strip():
            return None
        try:
            translated = self._translate_module.translate(text, source_language, target_language)
            return translated.strip() or None
        except Exception as exc:
            LOGGER.warning("Local translation failed: %s", exc)
            return None


class TranslationService:
    def __init__(self, glossary: GlossaryService, provider: TranslationProvider | None = None) -> None:
        self.glossary = glossary
        self.provider = provider or DisabledTranslationProvider()

    def translate(
        self,
        text: str,
        include_explanations: bool = False,
        target_language: str = "en",
    ) -> TranslationResult:
        target_language = target_language if target_language in LANGUAGE_NAMES else "en"
        original = text.strip()
        if not original:
            return TranslationResult(
                original="",
                translated="No text was recognized.",
                target_language=LANGUAGE_NAMES[target_language],
            )

        output: list[str] = []
        corrected_source: list[str] = []
        matches: list[GlossaryMatch] = []
        for line in original.splitlines():
            if not line.strip():
                output.append("")
                corrected_source.append("")
                continue
            exact = self.glossary.exact_match(line)
            if exact:
                output.append(exact.english)
                corrected_source.append(exact.spanish)
                self._append_unique(matches, [exact])
                continue

            fuzzy = self.glossary.fuzzy_match(line)
            if fuzzy:
                output.append(fuzzy.english)
                corrected_source.append(fuzzy.spanish)
                self._append_unique(matches, [fuzzy])
                continue

            segments, line_matches = self.glossary.segment(line)
            corrected_source.append(line)
            self._append_unique(matches, line_matches)
            if line_matches:
                translated_segments: list[str] = []
                for segment, glossary_match in segments:
                    if glossary_match is not None or not segment.strip():
                        translated_segments.append(segment)
                        continue
                    core = segment.strip()
                    generic_segment = self.provider.translate(core, "es", "en")
                    if generic_segment:
                        leading = segment[: len(segment) - len(segment.lstrip())]
                        trailing = segment[len(segment.rstrip()) :]
                        translated_segments.append(leading + generic_segment + trailing)
                    else:
                        translated_segments.append(segment)
                output.append("".join(translated_segments).strip())
                continue

            generic = self.provider.translate(line, "es", "en")
            output.append(generic if generic else f"[Untranslated] {line}")

        explanation = ""
        if include_explanations:
            explanation = "\n".join(
                f"{match.spanish}: {match.explanation}"
                for match in matches
                if match.explanation
            )
        english_translation = "\n".join(output)
        corrected_original = "\n".join(corrected_source)
        if target_language == "es":
            translated = corrected_original
        elif target_language == "en":
            translated = english_translation
        else:
            translated = self._translate_multiline(english_translation, "en", target_language)

        if explanation and target_language != "en":
            explanation = self._translate_multiline(explanation, "en", target_language)

        return TranslationResult(
            original=original,
            translated=translated,
            matches=matches,
            explanation=explanation,
            corrected_original=corrected_original,
            target_language=LANGUAGE_NAMES[target_language],
        )

    def _translate_multiline(self, text: str, source: str, target: str) -> str:
        translated_lines: list[str] = []
        for line in text.splitlines():
            if not line.strip():
                translated_lines.append("")
                continue
            translated_lines.append(self.provider.translate(line, source, target) or line)
        return "\n".join(translated_lines)

    @staticmethod
    def _append_unique(target: list[GlossaryMatch], additions: list[GlossaryMatch]) -> None:
        existing = {item.spanish for item in target}
        for item in additions:
            if item.spanish not in existing:
                target.append(item)
                existing.add(item.spanish)
