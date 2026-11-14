"""Самопроверка практической работы № 6.

Запуск из корня проекта: uv run python -m checks.pw6_check
Для быстрой проверки без запуска тестов: ... -m checks.pw6_check --fast
Сервер-имитатор запускать не нужно: программа запускает его сама на
свободном порту без задержек.
"""

import asyncio
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

CONFIG = Path("config/criteria.toml")
SCENARIO = Path("data/raw/works.json")
ROWS = Path("data/output/bonus_rows.csv")
TEMPLATE = Path("templates/memo.docx")
BASIC_WORDS = {
    "вестн": "вестник",
    "изв": "известия",
    "тр": "труды",
    "j": "journal",
    "int": "international",
}
# ожидаемые результаты на учебных данных (словарь сокращений работы 5)
EXPECTED_STATUS = {"found": 75, "not_found": 3, "unavailable": 1}
EXPECTED_DECISIONS = (73, 3, 2, 1)  # подтверждена, не найдена, год, нет ответа
EXPECTED_FUND = (73, 18, 851000, 838500, 0.7155, 599940)
REGISTRY_SHA = "cd1e30eeff33"  # начало SHA-256 файла journals.csv

results: list[bool] = []


def report(ok: bool, text: str) -> None:
    results.append(ok)
    print(("ВЕРНО   " if ok else "ОШИБКА  ") + text)


def load(module_name: str, name: str) -> Any:
    """Функция модуля проекта или None, если её нет."""
    try:
        module = importlib.import_module(module_name)
        return getattr(module, name)
    except (ImportError, AttributeError) as error:
        print(f"НЕТ     {module_name}.{name}: {error}")
        return None


def missing(*items: Any) -> bool:
    return any(item is None for item in items)


def guarded(title: str, check: Any, *args: Any) -> Any:
    """Выполняет проверку; любая ошибка — проверка не пройдена."""
    try:
        return check(*args)
    except NotImplementedError as error:
        where = error.__traceback__
        while where is not None and where.tb_next is not None:
            where = where.tb_next
        name = where.tb_frame.f_code.co_name if where else "?"
        report(False, f"{title}: функция {name} ещё не реализована")
    except Exception as error:  # noqa: BLE001 — сообщаем о любой ошибке
        report(False, f"{title}: {type(error).__name__}: {error}")
    return None


def check_api() -> Any:
    load_api = load("src.criteria", "load_api")
    if missing(load_api):
        report(False, "Настройки [api]: нет функции load_api")
        return None
    api = load_api(CONFIG)
    report(
        api.base_url == "http://127.0.0.1:8765"
        and (api.attempts, api.concurrency) == (4, 5)
        and (api.backoff, api.max_wait) == (0.5, 4.0),
        "Настройки [api]: адрес, 4 попытки, задержка 0,5 и 4 с, 5 запросов",
    )
    return api


def check_memo_settings() -> None:
    load_memo = load("src.criteria", "load_memo")
    if missing(load_memo):
        report(False, "Настройки [memo]: нет функции load_memo")
        return
    memo = load_memo(CONFIG)
    report(
        memo.recipient == "Директору института ПИИТМ",
        "Настройки [memo]: адресат «Директору института ПИИТМ»",
    )


def answer(code: int, **details: Any) -> httpx.Response:
    request = httpx.Request("GET", "http://127.0.0.1/works/10.1/a")
    return httpx.Response(code, request=request, **details)


def check_parse() -> None:
    parse = load("src.client", "parse_response")
    retryable = load("src.client", "Retryable")
    if missing(parse, retryable):
        report(False, "Ответ сервиса: нет функции parse_response")
        return
    ok = parse(answer(200, json={"message": {"DOI": "10.1/a"}})) == {
        "DOI": "10.1/a"
    }
    ok = ok and parse(answer(404)) is None
    for code, wait in ((429, 1.0), (503, None)):
        headers = {"Retry-After": "1"} if wait else {}
        try:
            parse(answer(code, headers=headers))
            ok = False
        except retryable as error:
            ok = ok and error.retry_after == wait
    report(ok, "Ответ сервиса: 200 — сведения, 404 — None, 429 и 503 — повтор")


def check_delay(api: Any) -> None:
    delay = load("src.client", "delay")
    retryable = load("src.client", "Retryable")
    if missing(delay, retryable, api):
        report(False, "Задержка перед повтором: нет функции delay")
        return
    got = [
        delay(api, retryable(429, 2.0), 1),
        delay(api, retryable(429, 30.0), 1),
        delay(api, retryable(503, None), 1),
        delay(api, retryable(503, None), 3),
        delay(api, None, 6),
    ]
    report(
        got == [2.0, 4.0, 0.5, 2.0, 4.0],
        "Задержка перед повтором: Retry-After, рост вдвое, не больше 4 с",
    )


def start_server() -> Any:
    """Сервер-имитатор в отдельном потоке без задержек."""
    mock = importlib.import_module("sandbox.mock_server")
    server = mock.start(port=0, scale=0.0, scenario=SCENARIO)
    return server, mock.address(server)


def scenario_dois() -> dict[str, str]:
    """По одной публикации каждого вида из сценария сервера."""
    data = json.loads(SCENARIO.read_text(encoding="utf-8"))
    errors = data["errors"]
    premium = pd.read_csv(ROWS)["doi"].drop_duplicates().tolist()
    return {
        "found": next(d for d in premium if d in data["works"]
                      and d not in errors),
        "not_found": next(d for d in premium if d not in data["works"]),
        "too_many": next(d for d, e in errors.items() if e == [429]),
        "twice": next(d for d, e in errors.items() if e == [503, 503]),
        "down": data["down"][0],
    }  # fmt: skip


def check_fetch(fast_api: Any, server: Any) -> None:
    fetch_work = load("src.client", "fetch_work")
    make_client = load("src.client", "make_client")
    if missing(fetch_work, make_client, fast_api):
        report(False, "Получение публикации: нет функции fetch_work")
        return
    server.state.reset()
    expected = {
        "found": ("found", 1),
        "not_found": ("not_found", 1),
        "too_many": ("found", 2),
        "twice": ("found", 3),
        "down": ("unavailable", 4),
    }
    got = {}
    with make_client(fast_api) as client:
        for kind, doi in scenario_dois().items():
            result = fetch_work(client, doi, fast_api)
            got[kind] = (result.status, result.attempts)
    report(
        got == expected,
        "Получение публикации: 200, 404, 429→200, 503→503→200, 503 всегда",
    )


def check_async(fast_api: Any, server: Any) -> list[Any] | None:
    fetch_all_async = load("src.client", "fetch_all_async")
    if missing(fetch_all_async, fast_api):
        report(False, "Асинхронная загрузка: нет функции fetch_all_async")
        return None
    server.state.reset()
    dois = pd.read_csv(ROWS)["doi"].drop_duplicates().tolist()
    found = asyncio.run(fetch_all_async(dois, fast_api))
    counts = dict(Counter(result.status for result in found))
    stats = server.state.stats()
    ok = [result.doi for result in found] == dois
    ok = ok and stats["peak"] <= fast_api.concurrency
    ok = ok and (counts == EXPECTED_STATUS or not basic())
    report(
        ok,
        f"Асинхронная загрузка: {counts}, одновременно не больше "
        f"{fast_api.concurrency}",
    )
    return list(found)


def check_cache(fast_api: Any, server: Any, tmp: Path) -> None:
    connect = load("src.storage", "connect")
    fetch_cached = load("src.storage", "fetch_cached")
    if missing(connect, fetch_cached, fast_api):
        report(False, "Кэш ответов: нет функций connect или fetch_cached")
        return
    dois = pd.read_csv(ROWS)["doi"].drop_duplicates().tolist()
    down = set(json.loads(SCENARIO.read_text(encoding="utf-8"))["down"])
    server.state.reset()
    with closing(connect(tmp / "cache.db")) as connection:
        asyncio.run(fetch_cached(connection, dois, fast_api))
        before = server.state.stats()["requests"]
        again = asyncio.run(fetch_cached(connection, dois, fast_api))
        requests = server.state.stats()["requests"] - before
        query = "SELECT status, count(*) FROM responses GROUP BY status"
        stored = dict(connection.execute(query).fetchall())
    asked = {result.doi for result in again if result.attempts > 0}
    report(
        asked == down & set(dois) and "unavailable" not in stored,
        f"Кэш ответов: повторно запрошено {len(asked)} (обращений "
        f"{requests}), в кэше {stored}",
    )


def check_history(tmp: Path) -> None:
    names = ("connect", "file_sha256", "start_run", "save_decisions")
    f = {name: load("src.storage", name) for name in names}
    f["history"] = load("src.storage", "history")
    if missing(*f.values()):
        report(False, "История запусков: нет функций модуля storage")
        return
    registry = Path("data/reference/journals.csv")
    sha = f["file_sha256"](registry)
    with closing(f["connect"](tmp / "history.db")) as connection:
        run_id = f["start_run"](connection, "v", registry, CONFIG)
        decisions = pd.DataFrame(
            {"doi": ["d1", "d2"], "decision": ["подтверждена", "x"]}
        ).assign(reason="")
        f["save_decisions"](connection, run_id, decisions)
        runs = f["history"](connection)
    ok = sha.startswith(REGISTRY_SHA) and run_id == 1 and len(runs) == 1
    ok = ok and runs["confirmed"].iloc[0] == 1
    report(ok, f"История запусков: SHA-256 справочника {sha[:12]}, запуск 1")


def check_decide() -> None:
    decide = load("src.verify", "decide")
    work_result = load("src.client", "WorkResult")
    if missing(decide, work_result):
        report(False, "Сверка: нет функции decide")
        return

    def work(year: int) -> Any:
        issued = {"date-parts": [[year]]}
        message = {"DOI": "d", "title": ["T"], "issued": issued}
        return work_result("d", "found", message, 1)

    got = [
        decide(work(2025), 2025)[0],
        decide(work(2024), 2025)[0],
        decide(work_result("d", "not_found", None, 1), 2025)[0],
        decide(work_result("d", "unavailable", None, 4), 2025)[0],
    ]
    expected = [
        "подтверждена",
        "расхождение года",
        "не найдена в сервисе",
        "сервис недоступен",
    ]
    report(got == expected, "Сверка: четыре решения по публикации")


def check_plural() -> None:
    plural = load("src.memo", "plural")
    if missing(plural):
        report(False, "Числительные: нет функции plural")
        return
    forms = ("публикация", "публикации", "публикаций")
    numbers = [1, 2, 5, 11, 14, 21, 22, 111, 0]
    got = [plural(n, forms)[-1] for n in numbers]
    report(
        got == ["я", "и", "й", "й", "й", "я", "и", "й", "й"],
        "Числительные: 1, 2, 5, 11, 14, 21, 22, 111, 0",
    )


def check_service(api: Any, address: str) -> None:
    available = load("src.client", "service_available")
    if missing(available, api):
        report(False, "Доступность сервиса: нет функции service_available")
        return
    closed = api.model_copy(update={"base_url": "http://127.0.0.1:9"})
    report(
        available(api.model_copy(update={"base_url": address}))
        and not available(closed),
        "Доступность сервиса: запущенный — да, закрытый порт — нет",
    )


def basic() -> bool:
    rules = load("src.criteria", "load_matching")(CONFIG)
    return bool(rules.abbreviations == BASIC_WORDS)


def check_decisions(found: list[Any] | None) -> Any:
    verify_rows = load("src.verify", "verify_rows")
    if found is None or missing(verify_rows):
        report(False, "Полная сверка: решения — сначала пройдите проверки")
        return None
    rows = pd.read_csv(ROWS, dtype={"staff_id": str})
    decisions = verify_rows(rows, found)
    counts = decisions["decision"].value_counts()
    names = [
        "подтверждена",
        "не найдена в сервисе",
        "расхождение года",
        "сервис недоступен",
    ]
    got = tuple(int(counts.get(name, 0)) for name in names)
    report(
        got == EXPECTED_DECISIONS or not basic() and sum(got) == len(found),
        f"Полная сверка: подтверждено {got[0]}, не найдено {got[1]}, "
        f"расхождение года {got[2]}, нет ответа {got[3]}",
    )
    return decisions


def check_fund(decisions: Any) -> Any:
    confirmed_rows = load("src.verify", "confirmed_rows")
    distribute = load("src.verify", "distribute")
    if decisions is None or missing(confirmed_rows, distribute):
        report(False, "Полная сверка: фонд — сначала пройдите проверки")
        return None
    rows = pd.read_csv(ROWS, dtype={"staff_id": str})
    bonus = load("src.criteria", "load_bonus")(CONFIG)
    confirmed = confirmed_rows(rows, decisions)
    paid = distribute(confirmed, bonus)
    numbers = (
        len(confirmed),
        len(paid),
        int(paid["accrued"].sum()),
        int(paid["capped"].sum()),
        round(float(paid["share"].iloc[0]), 4),
        int(paid["paid"].sum()),
    )
    ok = numbers == EXPECTED_FUND or not basic()
    ok = ok and numbers[5] <= bonus.fund
    report(
        ok,
        f"Полная сверка: строк {numbers[0]}, сотрудников {numbers[1]}, "
        f"начислено {numbers[2]}, с пределом {numbers[3]}, доля "
        f"{numbers[4]}, выплачивается {numbers[5]} руб.",
    )
    return paid


def check_memo(paid: pd.DataFrame | None, tmp: Path) -> None:
    names = ("MemoInfo", "memo_context", "render_memo")
    f = {name: load("src.memo", name) for name in names}
    if paid is None or missing(*f.values()):
        report(False, "Записка DOCX: сначала пройдите проверки выше")
        return
    from docx import Document  # библиотека python-docx (зависимость docxtpl)

    info = f["MemoInfo"](
        memo=load("src.criteria", "load_memo")(CONFIG),
        criteria=load("src.criteria", "load_criteria")(CONFIG),
        bonus=load("src.criteria", "load_bonus")(CONFIG),
        run_id=3,
        registry_sha256="0" * 64,
        review=6,
        today=date(2026, 11, 20),
    )
    path = tmp / "memo.docx"
    f["render_memo"](TEMPLATE, f["memo_context"](paid, info), path)
    document = Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs)
    rows = document.tables[0].rows[1:-1]
    amounts = [int(r.cells[4].text.replace(" ", "")) for r in rows]
    ok = len(rows) == len(paid) and sum(amounts) == paid["paid"].sum()
    ok = ok and "Директору института ПИИТМ" in text and "6 публикаций" in text
    report(
        ok,
        f"Записка DOCX: строк таблицы {len(rows)}, к выплате {sum(amounts)} "
        "руб., на проверке 6 публикаций",
    )


def check_service_parts(tmp: Path) -> None:
    """Проверки, которым нужен сервер-имитатор."""
    api = guarded("Настройки [api]", check_api)
    guarded("Настройки [memo]", check_memo_settings)
    guarded("Ответ сервиса", check_parse)
    guarded("Задержка перед повтором", check_delay, api)
    if not ROWS.exists() or not SCENARIO.exists():
        print(f"НЕТ     {ROWS} или {SCENARIO}: запустите prepare.py и "
              "allocate.py, скопируйте works.json (п. 4.1)")  # fmt: skip
        for _ in range(10):
            report(False, "Проверка с сервером-имитатором не выполнена")
        return
    server, address = start_server()
    fast = None
    if api is not None:
        update = {"base_url": address, "backoff": 0.0, "max_wait": 0.0}
        fast = api.model_copy(update=update)
    try:
        guarded("Доступность сервиса", check_service, api, address)
        guarded("Получение публикации", check_fetch, fast, server)
        found = guarded("Асинхронная загрузка", check_async, fast, server)
        guarded("Кэш ответов", check_cache, fast, server, tmp)
        guarded("История запусков", check_history, tmp)
        guarded("Сверка", check_decide)
        guarded("Числительные", check_plural)
        decisions = guarded("Полная сверка", check_decisions, found)
        paid = guarded("Полная сверка", check_fund, decisions)
        guarded("Записка DOCX", check_memo, paid, tmp)
    finally:
        server.shutdown()
        server.server_close()


DEFECTS = [
    (
        "src/client.py",
        "Ответ: 404 считается временным отказом",
        (
            "\n_parse_response_ok = parse_response\n\n\n"
            "def parse_response(response):\n"
            "    if response.status_code == 404:\n"
            "        raise Retryable(404, None)\n"
            "    return _parse_response_ok(response)\n"
        ),
    ),
    (
        "src/client.py",
        "Ответ: 429 не повторяется",
        (
            "\n_parse_response_ok = parse_response\n\n\n"
            "def parse_response(response):\n"
            "    if response.status_code == 429:\n"
            "        response.raise_for_status()\n"
            "    return _parse_response_ok(response)\n"
        ),
    ),
    (
        "src/client.py",
        "Ответ: 5xx не повторяется",
        (
            "\n_parse_response_ok = parse_response\n\n\n"
            "def parse_response(response):\n"
            "    if response.status_code >= 500:\n"
            "        response.raise_for_status()\n"
            "    return _parse_response_ok(response)\n"
        ),
    ),
    (
        "src/client.py",
        "Задержка: Retry-After не учитывается",
        (
            "\ndef delay(api, error, attempt):\n"
            "    return min(api.backoff * 2 ** (attempt - 1), api.max_wait)\n"
        ),
    ),
    (
        "src/client.py",
        "Задержка: не растёт от попытки к попытке",
        (
            "\n_delay_ok = delay\n\n\n"
            "def delay(api, error, attempt):\n"
            "    return _delay_ok(api, error, 1)\n"
        ),
    ),
    (
        "src/client.py",
        "Повторы: после последней попытки — исключение",
        (
            "\n_fetch_work_ok = fetch_work\n\n\n"
            "def fetch_work(client, doi, api):\n"
            "    result = _fetch_work_ok(client, doi, api)\n"
            "    if result.status == UNAVAILABLE:\n"
            "        raise RuntimeError('сервис недоступен')\n"
            "    return result\n"
        ),
    ),
    (
        "src/client.py",
        "Повторы: число попыток больше заданного",
        (
            "\n_retry_options_ok = retry_options\n\n\n"
            "def retry_options(api):\n"
            "    more = {'attempts': api.attempts + 2}\n"
            "    return _retry_options_ok(api.model_copy(update=more))\n"
        ),
    ),
    (
        "src/client.py",
        "Повторы: сетевые ошибки не повторяются",
        "\nRETRY_ON = (Retryable,)\n",
    ),
    (
        "src/client.py",
        "Асинхронно: семафор не ограничивает число запросов",
        (
            "\n_fetch_all_async_ok = fetch_all_async\n\n\n"
            "async def fetch_all_async(dois, api):\n"
            "    many = api.model_copy(update={'concurrency': 1000})\n"
            "    return await _fetch_all_async_ok(dois, many)\n"
        ),
    ),
    (
        "src/client.py",
        "Асинхронно: порядок результатов не совпадает с порядком DOI",
        (
            "\n_fetch_all_async_ok = fetch_all_async\n\n\n"
            "async def fetch_all_async(dois, api):\n"
            "    found = await _fetch_all_async_ok(dois, api)\n"
            "    return sorted(found, key=lambda result: result.status)\n"
        ),
    ),
    (
        "src/storage.py",
        "Кэш: сохраняется ответ «сервис недоступен»",
        (
            "\nimport json as _json\n\n\n"
            "def save_result(connection, result):\n"
            "    body = None if result.work is None else "
            "_json.dumps(result.work)\n"
            "    with connection:\n"
            "        connection.execute(\n"
            "            'INSERT OR REPLACE INTO responses '\n"
            "            'VALUES (?, ?, ?, ?)',\n"
            "            (result.doi, result.status, body, '2026-11-20'),\n"
            "        )\n"
        ),
    ),
    (
        "src/storage.py",
        "Кэш: сохранённые ответы не используются",
        "\ndef load_cached(connection, dois):\n    return {}\n",
    ),
    (
        "src/storage.py",
        "История: контрольная сумма MD5 вместо SHA-256",
        (
            "\nimport hashlib as _hashlib\n\n\n"
            "def file_sha256(path):\n"
            "    return _hashlib.md5(path.read_bytes()).hexdigest()\n"
        ),
    ),
    (
        "src/verify.py",
        "Сверка: год не сравнивается",
        (
            "\n_decide_ok = decide\n\n\n"
            "def decide(result, year):\n"
            "    if result.status == 'found':\n"
            "        return CONFIRMED, ''\n"
            "    return _decide_ok(result, year)\n"
        ),
    ),
    (
        "src/verify.py",
        "Сверка: публикация, не найденная в сервисе, подтверждается",
        (
            "\n_decide_ok = decide\n\n\n"
            "def decide(result, year):\n"
            "    if result.status == 'not_found':\n"
            "        return CONFIRMED, ''\n"
            "    return _decide_ok(result, year)\n"
        ),
    ),
    (
        "src/verify.py",
        "Сверка: неподтверждённые строки не исключаются",
        (
            "\ndef confirmed_rows(rows, decisions):\n"
            "    return rows.reset_index(drop=True)\n"
        ),
    ),
    (
        "src/memo.py",
        "Числительные: 11–14 согласуются как 1–4",
        (
            "\ndef plural(number, forms):\n"
            "    rest = abs(number) % 10\n"
            "    if rest == 1:\n"
            "        return forms[0]\n"
            "    if 2 <= rest <= 4:\n"
            "        return forms[1]\n"
            "    return forms[2]\n"
        ),
    ),
    (
        "src/memo.py",
        "Записка: в столбце «К выплате» — начисленное",
        (
            "\n_table_rows_ok = table_rows\n\n\n"
            "def table_rows(paid):\n"
            "    return _table_rows_ok(paid.assign(paid=paid['capped']))\n"
        ),
    ),
]


def run_tests(root: Path) -> bool:
    """Запускает тесты проекта; True — все тесты пройдены."""
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def copy_project(tmp: Path) -> Path:
    root = tmp / "project"
    shutil.copytree("src", root / "src")
    shutil.copytree("tests", root / "tests")
    shutil.copytree("templates", root / "templates")
    shutil.copy("pyproject.toml", root)
    return root


def check_tests(tmp: Path) -> None:
    if not Path("tests").is_dir() or not TEMPLATE.exists():
        report(False, "Тесты: нет каталога tests или шаблона записки")
        return
    root = copy_project(tmp)
    if not run_tests(root):
        report(False, "Тесты: не пройдены на исходном коде (uv run pytest)")
        return
    report(True, "Тесты: пройдены на исходном коде")
    for file, name, code in DEFECTS:
        shutil.rmtree(root)
        root = copy_project(tmp)
        with (root / file).open("a", encoding="utf-8") as target:
            target.write("\n" + code)
        caught = not run_tests(root)
        report(caught, f"Дефектный вариант обнаружен тестами: {name}")


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        check_service_parts(Path(name))
    if "--fast" not in sys.argv:
        with tempfile.TemporaryDirectory() as name:
            check_tests(Path(name))
    print(f"Выполнено проверок: {sum(results)} из {len(results)}")


if __name__ == "__main__":
    main()
