"""Historical interpreter score expression, selected only by explicit profiles."""


def format_interpretation_score(score: float | None) -> str:
    """Preserve the historical trajectory expression and missing-score marker."""
    return f"{score:.4f}" if score is not None else "skipped"
