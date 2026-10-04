"""Пробует загрузить каждую конфигурацию из каталога sandbox/configs.

Запуск из корня проекта: uv run python -m sandbox.try_configs
"""

from pathlib import Path

from pydantic import ValidationError

from src.criteria import load_criteria

for path in sorted(Path("sandbox/configs").glob("*.toml")):
    try:
        rules = load_criteria(path)
        print(f"ПРИНЯТА   {path.name}: {rules}")
    except ValidationError as error:
        first = error.errors()[0]
        print(f"ОТКЛОНЕНА {path.name}: {first['msg']}")
