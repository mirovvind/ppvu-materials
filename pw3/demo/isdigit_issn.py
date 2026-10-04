"""Вариант нормализации ISSN с дефектом: цифры проверяются isdigit."""


def normalize_issn(value: str | None) -> str | None:
    """Приводит ISSN к восьми символам или возвращает None."""
    if not value:
        return None
    chars = "".join(c for c in value.upper() if c.isalnum())
    if len(chars) != 8 or not chars[:7].isdigit():
        return None
    if chars[7].isdigit() or chars[7] == "X":
        return chars
    return None
