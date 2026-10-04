"""Сопоставление публикаций со справочником изданий."""

from src.models import Journal, Publication

# публикация, найденное издание (None — не найдено), достоверность
Match = tuple[Publication, Journal | None, float]


def match_publications(
    publications: list[Publication], registry: dict[str, Journal]
) -> list[Match]:
    """Заглушка: сопоставление будет реализовано в работе 5."""
    # каждая публикация получает отметку «издание не найдено»
    return [(item, None, 0.0) for item in publications]
