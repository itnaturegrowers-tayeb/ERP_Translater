from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GlossaryMatch:
    spanish: str
    english: str
    explanation: str = ""
    category: str = ""


@dataclass(slots=True)
class TranslationResult:
    original: str
    translated: str
    matches: list[GlossaryMatch] = field(default_factory=list)
    explanation: str = ""
    corrected_original: str = ""
    target_language: str = "English"
