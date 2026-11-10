"""Сопоставление авторов без ORCID со справочником сотрудников."""

import numpy as np
import pandas as pd

from src.criteria import Matching

# транслитерация, использованная в выгрузке публикаций
ONE_LETTER = dict(zip("абвгдезийклмнопрстуфыэ", "abvgdeziyklmnoprstufye"))
TRANSLIT = str.maketrans(
    ONE_LETTER
    | {"ё": "e", "ж": "zh", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh"}
    | {"щ": "shch", "ъ": "", "ь": "", "ю": "yu", "я": "ya"}
)


def translit(text: str) -> str:
    """Записывает русский текст латиницей."""
    return text.lower().translate(TRANSLIT)


def author_key(author: str) -> str:
    """Запись автора «Фамилия И. О.» -> «фамилия ио»."""
    raise NotImplementedError


def staff_keys(full_name: str) -> tuple[str, str]:
    """ФИО сотрудника -> запись кириллицей и латиницей."""
    surname, name, patronymic = full_name.lower().replace("ё", "е").split()
    cyrillic = f"{surname} {name[0]}{patronymic[0]}"
    initials = translit(name)[0] + translit(patronymic)[0]
    return cyrillic, f"{translit(surname)} {initials}"


def name_scores(authors: list[str], staff: pd.DataFrame) -> np.ndarray:
    """Сходство каждого автора с каждым сотрудником, %."""
    raise NotImplementedError


def match_authors(
    candidates: pd.DataFrame,
    found: pd.DataFrame,
    staff: pd.DataFrame,
    rules: Matching,
) -> pd.DataFrame:
    """Авторы без ORCID -> сотрудники кафедры внутри каждой публикации.

    candidates — авторы без ORCID (doi, author); found — сотрудники,
    уже найденные по ORCID (doi, staff_id): им пара не назначается.
    """
    raise NotImplementedError


def name_rows(
    accepted: pd.DataFrame, authorships: pd.DataFrame, names: pd.DataFrame
) -> pd.DataFrame:
    """Строки «публикация — сотрудник — сумма» для найденных по ФИО."""
    raise NotImplementedError
