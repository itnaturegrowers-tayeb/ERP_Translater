from __future__ import annotations

import os
import re
from pathlib import Path

import pytesseract
from pytesseract import Output
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


class OCRService:
    def __init__(
        self,
        tesseract_path: str = "",
        language: str = "spa",
        tessdata_dir: Path | None = None,
    ) -> None:
        default_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        self.tesseract_path = tesseract_path or (str(default_path) if default_path.exists() else "")
        self.language = language
        self.tessdata_dir = tessdata_dir

    def extract_text(self, image: Image.Image) -> str:
        self._configure_tesseract()
        processed = self.preprocess(image)
        config_parts = ["--oem 1", "--psm 6"]
        if self.tessdata_dir and self.tessdata_dir.exists():
            os.environ["TESSDATA_PREFIX"] = str(self.tessdata_dir.resolve())
        text = pytesseract.image_to_string(
            processed,
            lang=self.language,
            config=" ".join(config_parts),
        )
        return self.clean_text(text)

    def extract_line_near_point(self, image: Image.Image, point: tuple[int, int]) -> str:
        """OCR a GUI region and return only the text line nearest the mouse pointer."""
        self._configure_tesseract()
        scale = self._scale_for(image)
        processed = self.preprocess(image)
        data = pytesseract.image_to_data(
            processed,
            lang=self.language,
            config="--oem 1 --psm 6",
            output_type=Output.DICT,
        )
        lines: dict[tuple[int, int, int], list[tuple[int, int, int, int, str]]] = {}
        for index, raw_text in enumerate(data["text"]):
            text = raw_text.strip()
            try:
                confidence = float(data["conf"][index])
            except (TypeError, ValueError):
                confidence = -1
            if not text or confidence < 20 or text in {"|", "¦", "_"}:
                continue
            key = (
                int(data["block_num"][index]),
                int(data["par_num"][index]),
                int(data["line_num"][index]),
            )
            lines.setdefault(key, []).append(
                (
                    int(data["left"][index]),
                    int(data["top"][index]),
                    int(data["width"][index]),
                    int(data["height"][index]),
                    text,
                )
            )
        if not lines:
            return ""

        target_x, target_y = point[0] * scale, point[1] * scale
        candidates: list[tuple[float, str]] = []
        for words in lines.values():
            left = min(word[0] for word in words)
            top = min(word[1] for word in words)
            right = max(word[0] + word[2] for word in words)
            bottom = max(word[1] + word[3] for word in words)
            vertical = 0 if top - 10 <= target_y <= bottom + 10 else min(abs(target_y - top), abs(target_y - bottom))
            horizontal = 0 if left - 50 <= target_x <= right + 50 else min(abs(target_x - left), abs(target_x - right))
            line_text = " ".join(word[4] for word in sorted(words, key=lambda word: word[0]))
            candidates.append((vertical * 4 + horizontal, line_text))
        score, closest = min(candidates, key=lambda candidate: candidate[0])
        return self.clean_text(closest) if score <= 180 * scale else ""

    def extract_hover_line(self, image: Image.Image) -> str:
        """Read a narrow screen strip as one GUI text row."""
        self._configure_tesseract()
        processed = self.preprocess(image)
        text = pytesseract.image_to_string(
            processed,
            lang=self.language,
            config="--oem 1 --psm 7",
        )
        cleaned = self.clean_text(text).replace(os.linesep, " ").strip()
        # Tree-view icons are occasionally recognized as prefixes such as "4 (E)".
        cleaned = re.sub(r"^\s*\d+\s*\([A-Za-z]\)\s*", "", cleaned)
        cleaned = re.sub(r"^[|¦_~`'\".,:;<>]+\s*", "", cleaned)
        return cleaned.strip()

    def _configure_tesseract(self) -> None:
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path or "tesseract"
        if self.tessdata_dir and self.tessdata_dir.exists():
            os.environ["TESSDATA_PREFIX"] = str(self.tessdata_dir.resolve())

    @staticmethod
    def preprocess(image: Image.Image) -> Image.Image:
        scale = OCRService._scale_for(image)
        resized = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
        grayscale = ImageOps.grayscale(resized)
        contrasted = ImageEnhance.Contrast(grayscale).enhance(1.8)
        return contrasted.filter(ImageFilter.SHARPEN)

    @staticmethod
    def _scale_for(image: Image.Image) -> int:
        return 2 if min(image.size) >= 40 else 3

    @staticmethod
    def clean_text(text: str) -> str:
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
        while lines and not lines[-1]:
            lines.pop()
        return os.linesep.join(lines)
