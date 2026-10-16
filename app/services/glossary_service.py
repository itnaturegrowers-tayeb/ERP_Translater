from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from app.models.translation_result import GlossaryMatch


class GlossaryService:
    def __init__(self, glossary_path: Path) -> None:
        raw_entries = json.loads(glossary_path.read_text(encoding="utf-8"))
        self.entries = [GlossaryMatch(**entry) for entry in raw_entries]
        self._exact = {self.normalize(entry.spanish): entry for entry in self.entries}
        self._ordered = sorted(self.entries, key=lambda item: len(item.spanish), reverse=True)
        alternatives = "|".join(re.escape(entry.spanish) for entry in self._ordered)
        self._phrase_pattern = re.compile(alternatives, flags=re.IGNORECASE)

    @staticmethod
    def normalize(text: str) -> str:
        return unicodedata.normalize("NFKC", text).strip().casefold()

    def exact_match(self, text: str) -> GlossaryMatch | None:
        return self._exact.get(self.normalize(text))

    @staticmethod
    def ocr_normalize(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text)
        ascii_text = decomposed.encode("ascii", "ignore").decode("ascii").casefold()
        return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_text).split())

    def fuzzy_match(self, text: str) -> GlossaryMatch | None:
        """Correct a damaged OCR line when it strongly resembles a known ERP term."""
        normalized = self.ocr_normalize(text)
        if len(normalized) < 5:
            return None
        best_entry: GlossaryMatch | None = None
        best_score = 0.0
        for entry in self.entries:
            candidate = self.ocr_normalize(entry.spanish)
            score = SequenceMatcher(None, normalized, candidate).ratio()
            if score > best_score:
                best_score = score
                best_entry = entry
        threshold = 0.78 if len(normalized) >= 10 else 0.88
        return best_entry if best_score >= threshold else None

    def replace_phrases(self, text: str) -> tuple[str, list[GlossaryMatch]]:
        result = text
        found: list[GlossaryMatch] = []
        for entry in self._ordered:
            pattern = re.compile(re.escape(entry.spanish), flags=re.IGNORECASE)
            result, count = pattern.subn(lambda _: entry.english, result)
            if count and entry not in found:
                found.append(entry)
        return result, found

    def segment(self, text: str) -> tuple[list[tuple[str, GlossaryMatch | None]], list[GlossaryMatch]]:
        """Split text into untranslated spans and authoritative glossary spans."""
        segments: list[tuple[str, GlossaryMatch | None]] = []
        found: list[GlossaryMatch] = []
        cursor = 0
        for match in self._phrase_pattern.finditer(text):
            if match.start() > cursor:
                segments.append((text[cursor:match.start()], None))
            entry = self.exact_match(match.group())
            if entry is not None:
                segments.append((entry.english, entry))
                if entry not in found:
                    found.append(entry)
            cursor = match.end()
        if cursor < len(text):
            segments.append((text[cursor:], None))
        return segments, found
