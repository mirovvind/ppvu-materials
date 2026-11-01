"""Предварительный расчёт премирования авторов-сотрудников кафедры."""

import duckdb
import pandas as pd

from src.criteria import Bonus, Criteria

ORCID = r"[0-9]{15}[0-9X]"


def normalize_orcid_column(orcid: pd.Series) -> pd.Series:
    """Приводит ORCID к 16 символам без дефисов и адреса сайта.

    Пример: "https://orcid.org/0000-0002-1694-233x" -> "000000021694233X".
    Недопустимое значение становится пропуском.
    """
    raise NotImplementedError


def department_staff(staff: pd.DataFrame, department: str) -> pd.DataFrame:
    """Сотрудники кафедры с ORCID: по одной строке на ORCID.

    Столбцы результата: orcid (нормализованный), staff_id, full_name.
    Повтор ORCID среди сотрудников кафедры — ошибка (ValueError).
    """
    raise NotImplementedError


def accepted_publications(
    matched: pd.DataFrame, criteria: Criteria, bonus: Bonus
) -> pd.DataFrame:
    """Засчитанные публикации с суммой премирования за публикацию.

    Публикация засчитывается, если год входит в отчётный период, а уровень
    издания не ниже порогового (правило функции decide из работы 3).
    Добавляется столбец pub_amount: сумма за публикацию по её уровню.
    """
    raise NotImplementedError


def bonus_table(
    matched: pd.DataFrame,
    authorships: pd.DataFrame,
    staff: pd.DataFrame,
    criteria: Criteria,
    bonus: Bonus,
) -> pd.DataFrame:
    """Строки «публикация — сотрудник кафедры — сумма».

    Столбцы результата: doi, year, level, n_authors, staff_id, full_name,
    amount. Строки упорядочены по full_name, затем по doi.
    """
    raise NotImplementedError


def summary_by_person(bonus_rows: pd.DataFrame) -> pd.DataFrame:
    """Итоги по сотрудникам: число публикаций и сумма."""
    relation = duckdb.sql("""
        SELECT full_name,
               count(*) AS publications,
               CAST(sum(amount) AS BIGINT) AS amount
        FROM bonus_rows
        GROUP BY full_name
        ORDER BY amount DESC, full_name
    """)
    if relation is None:  # запрос не вернул таблицу
        raise ValueError("пустой результат запроса")
    return relation.df()
