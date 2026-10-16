from __future__ import annotations

import os
import re
import statistics
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
        return self._nearest_text_cluster(data, point, scale)

    @classmethod
    def _nearest_text_cluster(
        cls,
        data: dict[str, list],
        point: tuple[int, int],
        scale: int = 1,
    ) -> str:
        """Select the coherent OCR word group nearest a point in the source image."""
        lines: dict[tuple[int, int, int], list[tuple[int, int, int, int, str]]] = {}
        for index, raw_text in enumerate(data["text"]):
            text = raw_text.strip()
            try:
                confidence = float(data["conf"][index])
            except (TypeError, ValueError):
                confidence = -1
            if not text or confidence < 35 or not cls._useful_token(text):
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
            ordered = sorted(words, key=lambda word: word[0])
            median_height = statistics.median(word[3] for word in ordered)
            gap_limit = max(18 * scale, int(median_height * 1.8))
            clusters: list[list[tuple[int, int, int, int, str]]] = [[]]
            for word in ordered:
                previous = clusters[-1][-1] if clusters[-1] else None
                if previous and word[0] - (previous[0] + previous[2]) > gap_limit:
                    clusters.append([])
                clusters[-1].append(word)

            for cluster in clusters:
                left = min(word[0] for word in cluster)
                top = min(word[1] for word in cluster)
                right = max(word[0] + word[2] for word in cluster)
                bottom = max(word[1] + word[3] for word in cluster)
                vertical = 0 if top - 8 * scale <= target_y <= bottom + 8 * scale else min(
                    abs(target_y - top), abs(target_y - bottom)
                )
                horizontal = 0 if left <= target_x <= right else min(
                    abs(target_x - left), abs(target_x - right)
                )
                cluster_text = " ".join(word[4] for word in cluster)
                candidates.append((vertical * 5 + horizontal, cluster_text))
        if not candidates:
            return ""
        score, closest = min(candidates, key=lambda candidate: candidate[0])
        return cls.clean_hover_text(closest) if score <= 100 * scale else ""

    def extract_hover_line(self, image: Image.Image, point: tuple[int, int] | None = None) -> str:
        """Read the coherent GUI text group nearest the mouse pointer."""
        self._configure_tesseract()
        scale = self._scale_for(image)
        processed = self.preprocess(image)
        data = pytesseract.image_to_data(
            processed,
            lang=self.language,
            config="--oem 1 --psm 6",
            output_type=Output.DICT,
        )
        target = point or (image.width // 2, image.height // 2)
        return self._nearest_text_cluster(data, target, scale)

    @staticmethod
    def _useful_token(text: str) -> bool:
        return bool(re.search(r"[A-Za-zÀ-ɏ0-9]", text))

    @classmethod
    def clean_hover_text(cls, text: str) -> str:
        """Remove tree icons and OCR punctuation without changing real label words."""
        tokens = text.replace("\r", " ").replace("\n", " ").split()
        tokens = [token for token in tokens if cls._useful_token(token)]
        if not tokens:
            return ""

        substantial = [
            index
            for index, token in enumerate(tokens)
            if len(re.findall(r"[A-Za-zÀ-ɏ]", token)) >= 3
        ]
        if not substantial:
            return ""
        tokens = tokens[substantial[0] : substantial[-1] + 1]
        cleaned = " ".join(tokens)
        cleaned = re.sub(r"^\d+\s*\([A-Za-z]\)\s*", "", cleaned)
        cleaned = re.sub(r"([()\[\]{}|<>])\1{2,}", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" |¦_~`'\".,:;<>[]{}")
        letters = len(re.findall(r"[A-Za-zÀ-ɏ]", cleaned))
        noisy = len(re.findall(r"[^\w\sÀ-ɏ.,()'/-]", cleaned))
        if letters < 3 or noisy > max(2, letters // 3):
            return ""
        return cleaned

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
