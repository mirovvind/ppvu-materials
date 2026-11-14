"""Учебный сервер-имитатор сервиса метаданных публикаций (подобие Crossref).

Запуск из корня проекта (во втором терминале):
    uv run python -m sandbox.mock_server
Параметры: --port 8765 — порт; --scale 1 — множитель задержек
(0 — без задержек); --recovered — сервис восстановлен: публикации, на
которые он всегда отвечал 503, отвечают 200. Сервер принимает запросы
только с адреса 127.0.0.1.

Запросы:
    GET /works/<DOI>  — сведения о публикации (ответ в формате Crossref);
    GET /works        — проверка доступности сервиса;
    GET /stats        — число обращений и ответов с каждым кодом;
    POST /reset       — сброс счётчиков и сценария.
Поведение задаётся файлом data/raw/works.json и одинаково при каждом
запуске: 404 — публикации нет в сервисе, 429 — слишком много запросов
(заголовок Retry-After), 503 — сервис временно недоступен.
"""

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

SCENARIO = Path("data/raw/works.json")
HOST = "127.0.0.1"
PORT = 8765


class State:
    """Сценарий и счётчики сервера."""

    def __init__(self, scenario: dict[str, Any], scale: float) -> None:
        self.scenario = scenario
        self.scale = scale  # множитель задержек
        self.lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """Обнуляет счётчики: сценарий начинается заново."""
        with self.lock:
            self.tries: dict[str, int] = {}  # DOI -> число обращений
            self.codes: dict[str, int] = {}  # код ответа -> число ответов
            self.active = 0  # запросов в обработке
            self.peak = 0  # наибольшее число запросов в обработке

    def enter(self) -> bool:
        """Начало обработки; False — превышен предел одновременных."""
        with self.lock:
            if self.active >= self.scenario["limit"]:
                return False
            self.active += 1
            self.peak = max(self.peak, self.active)
            return True

    def leave(self) -> None:
        with self.lock:
            self.active -= 1

    def code(self, doi: str) -> int:
        """Код ответа на очередное обращение к публикации по сценарию."""
        with self.lock:
            number = self.tries.get(doi, 0)
            self.tries[doi] = number + 1
        if doi in self.scenario["down"]:
            return 503
        errors = self.scenario["errors"].get(doi, [])
        if number < len(errors):
            return int(errors[number])
        return 200 if doi in self.scenario["works"] else 404

    def count(self, code: int) -> None:
        with self.lock:
            key = str(code)
            self.codes[key] = self.codes.get(key, 0) + 1

    def stats(self) -> dict[str, Any]:
        with self.lock:
            total = sum(self.codes.values())
            return {"requests": total, "codes": self.codes, "peak": self.peak}


class Server(ThreadingHTTPServer):
    """Сервер с состоянием; каждый запрос обрабатывается в своём потоке."""

    request_queue_size = 256  # очередь соединений: до 256 запросов сразу
    daemon_threads = True

    def __init__(self, port: int, state: State, quiet: bool) -> None:
        super().__init__((HOST, port), Handler)
        self.state = state
        self.quiet = quiet


class Handler(BaseHTTPRequestHandler):
    """Обработка запросов к серверу-имитатору."""

    server: Server

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/stats":
            self.reply(200, self.server.state.stats())
        elif path in ("/works", "/works/"):
            total = len(self.server.state.scenario["works"])
            self.reply(200, {"status": "ok", "total-results": total})
        elif path.startswith("/works/"):
            self.work(unquote(path.removeprefix("/works/")).lower())
        else:
            self.reply(404, "Resource not found.")

    def do_POST(self) -> None:
        if urlsplit(self.path).path == "/reset":
            self.server.state.reset()
            self.reply(200, {"status": "ok"})
        else:
            self.reply(404, "Resource not found.")

    def work(self, doi: str) -> None:
        state = self.server.state
        if not state.enter():
            self.reply(429, "Too many concurrent requests.", doi)
            return
        try:
            code = state.code(doi)
            time.sleep(state.scenario["delay"] * state.scale)
        finally:
            state.leave()  # до отправки ответа: клиент может сразу спросить
        if code == 200:
            message = state.scenario["works"][doi]
            body = {"status": "ok", "message-type": "work", "message": message}
            self.reply(200, body, doi)
        elif code == 404:
            self.reply(404, "Resource not found.", doi)
        elif code == 429:
            self.reply(429, "Rate limit exceeded.", doi)
        else:
            self.reply(code, "Service temporarily unavailable.", doi)

    def reply(self, code: int, body: Any, doi: str | None = None) -> None:
        if doi is not None:
            self.server.state.count(code)
            self.show(f"GET /works/{doi} -> {code}")
        is_text = isinstance(body, str)
        data = body if is_text else json.dumps(body, ensure_ascii=False)
        raw = data.encode("utf-8")
        self.send_response(code)
        kind = "text/plain" if is_text else "application/json"
        self.send_header("Content-Type", f"{kind}; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        if code == 429:
            state = self.server.state
            wait = state.scenario["retry_after"] * state.scale
            self.send_header("Retry-After", f"{wait:g}")
        self.end_headers()
        self.wfile.write(raw)

    def show(self, text: str) -> None:
        if not self.server.quiet:
            print(time.strftime("%H:%M:%S"), text, flush=True)

    def log_message(self, format: str, *args: Any) -> None:
        """Стандартный журнал запросов не выводится (см. show)."""


def load_scenario(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        scenario: dict[str, Any] = json.load(file)
    scenario["down"] = set(scenario["down"])
    return scenario


def start(
    port: int = 0,
    scale: float = 0.0,
    scenario: Path = SCENARIO,
    quiet: bool = True,
) -> Server:
    """Запускает сервер в отдельном потоке (порт 0 — любой свободный)."""
    server = Server(port, State(load_scenario(scenario), scale), quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def address(server: Server) -> str:
    return f"http://{HOST}:{server.server_address[1]}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Учебный сервер-имитатор")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--scenario", type=Path, default=SCENARIO)
    parser.add_argument("--recovered", action="store_true")
    args = parser.parse_args()
    scenario = load_scenario(args.scenario)
    if args.recovered:
        scenario["down"] = set()  # сбой сервиса устранён
    state = State(scenario, args.scale)
    server = Server(args.port, state, quiet=False)
    works = len(state.scenario["works"])
    print(f"Сервер-имитатор: http://{HOST}:{args.port}, публикаций: {works}")
    print("Остановка: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Сервер остановлен")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
