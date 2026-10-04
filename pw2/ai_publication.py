from dataclasses import dataclass


@dataclass
class Publication:
    title: str
    authors: str  # авторы через запятую
    year: str
    doi: str = ""  # пустая строка — DOI не указан
    issn: str = ""


def same_publication(a: Publication, b: Publication) -> bool:
    """Проверяет, описывают ли две записи одну публикацию."""
    return a.title.normalize() == b.title.normalize()
