"""Сопоставление публикаций со справочником изданий."""

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

from src.criteria import Matching
from src.models import Journal, Publication

# публикация, найденное издание (None — не найдено), достоверность
Match = tuple[Publication, Journal | None, float]

AUTO = "принято"  # сходство не ниже порога принятия
REVIEW = "на проверку"  # сходство между порогами
NOT_FOUND = "не найдено"  # сходство ниже порога проверки


def normalize_title(title: str | None, abbreviations: dict[str, str]) -> str:
    """Приводит название к виду для сравнения."""
    raise NotImplementedError


def numbers(text: str) -> list[str]:
    """Числа в названии: номер серии, номер конференции."""
    raise NotImplementedError


def classify(score: float, same_numbers: bool, rules: Matching) -> str:
    """Решение по сходству названий и совпадению чисел."""
    raise NotImplementedError


def match_titles(
    titles: list[str], journals: pd.DataFrame, rules: Matching
) -> pd.DataFrame:
    """Лучший кандидат справочника для каждого названия."""
    words = rules.abbreviations
    query = [normalize_title(t, words) for t in titles]
    names = [normalize_title(t, words) for t in journals["title"]]
    scores = process.cdist(
        query, names, scorer=fuzz.ratio, dtype=np.uint8, workers=-1
    )
    best = scores.argmax(axis=1)  # номер лучшего кандидата в строке
    result = pd.DataFrame(
        {
            "container_title": titles,
            "journal_id": journals["journal_id"].to_numpy()[best],
            "candidate": journals["title"].to_numpy()[best],
            "score": scores[np.arange(len(query)), best],
        }
    )
    same = [numbers(query[i]) == numbers(names[j]) for i, j in enumerate(best)]
    result["same_numbers"] = same
    result["status"] = [
        classify(score, ok, rules) for score, ok in zip(result["score"], same)
    ]
    return result


def quality(
    found: pd.DataFrame, labels: pd.DataFrame, threshold: int
) -> tuple[float, float]:
    """Точность и полнота автоматического принятия на разметке."""
    raise NotImplementedError


def by_issn(publication: Publication, registry: dict[str, Journal]) -> Match:
    """Сопоставление по ISSN: точное совпадение номера."""
    for issn in publication.issns:
        if issn in registry:
            return publication, registry[issn], 1.0
    return publication, None, 0.0


def by_title(
    publication: Publication, journals: list[Journal], rules: Matching
) -> Match:
    """Сопоставление по названию издания с порогами из правил."""
    if publication.journal_title is None:
        return publication, None, 0.0
    words = rules.abbreviations
    query = normalize_title(publication.journal_title, words)
    names = [normalize_title(journal.title, words) for journal in journals]
    _, score, index = process.extractOne(query, names, scorer=fuzz.ratio)
    status = classify(score, numbers(query) == numbers(names[index]), rules)
    if status == AUTO:
        return publication, journals[index], score / 100
    if status == REVIEW:
        return publication, None, score / 100
    return publication, None, 0.0


def match_publications(
    publications: list[Publication],
    registry: dict[str, Journal],
    rules: Matching | None = None,
) -> list[Match]:
    """Сначала по ISSN, затем по названию; без правил — только по ISSN."""
    journals = list({j.title: j for j in registry.values()}.values())
    result: list[Match] = []
    for publication in publications:
        found = by_issn(publication, registry)
        if found[1] is None and rules is not None:
            found = by_title(publication, journals, rules)
        result.append(found)
    return result


def assign(scores: np.ndarray) -> list[tuple[int, int]]:
    """Задача о назначениях: пары с наибольшим суммарным сходством."""
    raise NotImplementedError


def greedy(scores: np.ndarray) -> list[tuple[int, int]]:
    """Жадный алгоритм: наилучшая из оставшихся пар на каждом шаге."""
    left = scores.astype(float)  # копия: исходная таблица не меняется
    pairs = []
    for _ in range(min(left.shape)):
        i, j = np.unravel_index(left.argmax(), left.shape)
        pairs.append((int(i), int(j)))
        left[i, :] = -1  # строка занята
        left[:, j] = -1  # столбец занят
    return sorted(pairs)
