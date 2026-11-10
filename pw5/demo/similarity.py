"""Меры сходства строк на парах названий изданий."""

from rapidfuzz import fuzz

from src.matching import normalize_title, numbers

PAIRS = [
    ("Journal of Food Engineering", "JOURNAL OF FOOD ENGINEERING"),
    ("Journal of Food Engineering", "Journal of Food Enginering"),
    ("Journal of Food Engineering", "J. of Food Engineering"),
    ("Вестник Малозаводского государственного университета",
     "Вестн. Малозаводского гос. ун-та"),
    ("Food Chemistry and Nutrition Letters",
     "Food Chemistry & Nutrition Letters"),
    ("Вестник Тихокамского научного центра. Серия 2. Экономика",
     "Вестник Тихокамского научного центра. Серия 3. Экономика"),
    ("Труды Малозаводского государственного университета",
     "Труды Малозаводского аграрного университета"),
    ("Journal of Food Science", "Journal of Food Science and Nutrition"),
    ("Food Science and Nutrition Letters",
     "Nutrition and Food Science Letters"),
    ("Достижения пищевой химии", "Dostizheniya pishchevoy khimii"),
]  # fmt: skip


def scores(left: str, right: str) -> str:
    """Сходство пары до и после нормализации, %."""
    a, b = normalize_title(left, {}), normalize_title(right, {})
    same = "да" if numbers(a) == numbers(b) else "НЕТ"
    values = (
        fuzz.ratio(left, right),
        fuzz.ratio(a, b),
        fuzz.token_sort_ratio(a, b),
        fuzz.token_set_ratio(a, b),
    )
    return "".join(f"{value:11.1f}" for value in values) + f"  {same}"


if __name__ == "__main__":
    names = ("без норм.", "ratio", "token_sort", "token_set")
    print(
        "Пара  " + "".join(f"{name:>11}" for name in names) + "  Числа равны"
    )
    for number, (left, right) in enumerate(PAIRS, start=1):
        try:
            print(f"{number:4}  {scores(left, right)}")
        except NotImplementedError:
            print("Функции normalize_title и numbers ещё не написаны")
            break
