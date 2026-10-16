from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import ctranslate2
import sentencepiece as spm
from sacremoses import MosesDetokenizer, MosesPunctNormalizer, MosesTokenizer
from subword_nmt.apply_bpe import BPE

from app.services.translation_service import TranslationProvider

LOGGER = logging.getLogger(__name__)


class _Tokenizer:
    def encode(self, text: str) -> list[str]:
        raise NotImplementedError

    def decode(self, tokens: list[str]) -> str:
        raise NotImplementedError


class _SentencePieceTokenizer(_Tokenizer):
    def __init__(self, model_path: Path) -> None:
        self.processor = spm.SentencePieceProcessor(model_file=str(model_path))

    def encode(self, text: str) -> list[str]:
        return self.processor.encode(text, out_type=str)

    def decode(self, tokens: list[str]) -> str:
        return self.processor.decode_pieces(tokens).replace("▁", " ").replace("_", " ").strip()


class _BPETokenizer(_Tokenizer):
    def __init__(self, model_path: Path, source: str, target: str) -> None:
        self.normalizer = MosesPunctNormalizer(source)
        self.tokenizer = MosesTokenizer(source)
        self.detokenizer = MosesDetokenizer(target)
        with model_path.open("r", encoding="utf-8") as model_file:
            self.bpe = BPE(model_file)

    def encode(self, text: str) -> list[str]:
        normalized = self.normalizer.normalize(text)
        tokenized = self.tokenizer.tokenize(normalized)
        return self.bpe.segment_tokens(tokenized)

    def decode(self, tokens: list[str]) -> str:
        merged = " ".join(tokens).replace("@@ ", "")
        return self.detokenizer.detokenize(merged.split()).strip()


@dataclass(slots=True)
class _ModelRuntime:
    translator: ctranslate2.Translator
    tokenizer: _Tokenizer
    target_prefix: str = ""

    def translate(self, text: str) -> str:
        tokens = self.tokenizer.encode(text)
        if not tokens:
            return ""
        target_prefix = [[self.target_prefix]] if self.target_prefix else None
        batches = self.translator.translate_batch(
            [tokens],
            target_prefix=target_prefix,
            replace_unknowns=True,
            beam_size=4,
            num_hypotheses=1,
            length_penalty=0.2,
        )
        translated_tokens = list(batches[0].hypotheses[0])
        result = self.tokenizer.decode(translated_tokens)
        if self.target_prefix and result.startswith(self.target_prefix):
            result = result[len(self.target_prefix) :].lstrip()
        return result


class LocalModelTranslationProvider(TranslationProvider):
    """Lightweight offline provider using CTranslate2 models directly."""

    def __init__(self, bundled_models: Path | None = None) -> None:
        self._model_paths: dict[tuple[str, str], Path] = {}
        self._runtimes: dict[tuple[str, str], _ModelRuntime] = {}
        self._lock = threading.RLock()
        roots = []
        if bundled_models and bundled_models.exists():
            roots.append(bundled_models)
        user_models = Path.home() / ".local" / "share" / "argos-translate" / "packages"
        if user_models.exists():
            roots.append(user_models)
        for root in roots:
            self._discover_models(root)

    def _discover_models(self, root: Path) -> None:
        for metadata_path in root.rglob("metadata.json"):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                pair = (str(metadata["from_code"]), str(metadata["to_code"]))
                if (metadata_path.parent / "model" / "model.bin").exists():
                    self._model_paths.setdefault(pair, metadata_path.parent)
            except (OSError, KeyError, json.JSONDecodeError):
                LOGGER.warning("Ignoring invalid translation model metadata: %s", metadata_path)

    def translate(self, text: str, source_language: str, target_language: str) -> str | None:
        if source_language == target_language:
            return text
        pair = (source_language, target_language)
        model_path = self._model_paths.get(pair)
        if model_path is None:
            LOGGER.warning("No local translation model installed for %s -> %s", *pair)
            return None
        try:
            with self._lock:
                runtime = self._runtimes.get(pair)
                if runtime is None:
                    runtime = self._load_runtime(model_path, *pair)
                    self._runtimes[pair] = runtime
                return runtime.translate(text).strip() or None
        except Exception:
            LOGGER.exception("Local model translation failed for %s -> %s", *pair)
            return None

    @staticmethod
    def _load_runtime(model_path: Path, source: str, target: str) -> _ModelRuntime:
        sentencepiece_path = model_path / "sentencepiece.model"
        bpe_path = model_path / "bpe.model"
        if sentencepiece_path.exists():
            tokenizer: _Tokenizer = _SentencePieceTokenizer(sentencepiece_path)
        elif bpe_path.exists():
            tokenizer = _BPETokenizer(bpe_path, source, target)
        else:
            raise FileNotFoundError(f"No tokenizer found in {model_path}")
        metadata = json.loads((model_path / "metadata.json").read_text(encoding="utf-8"))
        return _ModelRuntime(
            translator=ctranslate2.Translator(
                str(model_path / "model"),
                device="cpu",
                inter_threads=1,
                intra_threads=0,
                compute_type="auto",
            ),
            tokenizer=tokenizer,
            target_prefix=str(metadata.get("target_prefix", "")),
        )
