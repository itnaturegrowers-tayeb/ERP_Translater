from app.services.ocr_service import OCRService


def _ocr_data(words: list[tuple[int, int, int, int, str, float]]) -> dict[str, list]:
    return {
        "text": [word[4] for word in words],
        "conf": [word[5] for word in words],
        "left": [word[0] for word in words],
        "top": [word[1] for word in words],
        "width": [word[2] for word in words],
        "height": [word[3] for word in words],
        "block_num": [1] * len(words),
        "par_num": [1] * len(words),
        "line_num": [1] * len(words),
    }


def test_hover_selects_label_cluster_instead_of_distant_grid_values() -> None:
    data = _ocr_data(
        [
            (10, 10, 8, 12, "(j", 62),
            (24, 10, 58, 12, "Gestionar", 94),
            (88, 10, 72, 12, "confección", 95),
            (166, 10, 18, 12, "de", 96),
            (190, 10, 42, 12, "palets", 96),
            (360, 10, 70, 12, "124,000", 93),
            (438, 10, 52, 12, "PALETS", 93),
        ]
    )

    assert OCRService._nearest_text_cluster(data, (130, 16)) == "Gestionar confección de palets"


def test_hover_cleanup_discards_icon_noise_and_repeated_symbols() -> None:
    noisy = "y| (j Gestionar confección de palets | [|||> /10/ ZU ))))))"
    assert OCRService.clean_hover_text(noisy) == "Gestionar confección de palets"
