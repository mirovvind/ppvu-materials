"""Пробует загрузить каждую конфигурацию из каталога sandbox/configs.

Запуск из корня проекта: uv run python -m sandbox.try_configs
"""

from pathlib import Path

from pydantic import ValidationError

from src.criteria import load_criteria

for path in sorted(Path("sandbox/configs").glob("*.toml")):
    try:
        rules = load_criteria(path)
        period = f"{rules.year_from}–{rules.year_to}"
        print(f"ПРИНЯТА   {path.name}: {period}, У{rules.max_level}")
    except ValidationError as error:
        first = error.errors()[0]
        print(f"ОТКЛОНЕНА {path.name}: {first['msg']}")
