from pathlib import Path

from app.services.glossary_service import GlossaryService
from app.services.translation_service import TranslationProvider, TranslationService


class StubProvider(TranslationProvider):
    def translate(self, text: str, source_language: str, target_language: str) -> str | None:
        return {"y": "and", "Texto desconocido": "Unknown text"}.get(text)


def service() -> TranslationService:
    return TranslationService(GlossaryService(Path("data/glossary.json")))


def test_exact_glossary_translation() -> None:
    result = service().translate("Partida", include_explanations=True)
    assert result.translated == "Lot / Batch"
    assert "Traceability identifier" in result.explanation


def test_phrase_replacement_in_longer_text() -> None:
    result = service().translate("Proveedor y Almacén de destino")
    assert result.translated == "Supplier y Destination Warehouse"
    assert len(result.matches) == 2


def test_unmatched_text_is_marked() -> None:
    result = service().translate("Texto desconocido")
    assert result.translated == "[Untranslated] Texto desconocido"


def test_generic_provider_translates_around_authoritative_glossary() -> None:
    translator = TranslationService(service().glossary, StubProvider())
    result = translator.translate("Proveedor y Almacén de destino")
    assert result.translated == "Supplier and Destination Warehouse"


def test_generic_provider_translates_unmatched_text() -> None:
    translator = TranslationService(service().glossary, StubProvider())
    assert translator.translate("Texto desconocido").translated == "Unknown text"


def test_repairs_damaged_ocr_using_known_erp_term() -> None:
    result = service().translate("6 comsatareaciones y situación Sujeto IES")
    assert result.translated == "Business Partner Relationships and Status"
    assert result.corrected_original == "Consulta relaciones y situación Sujeto"
