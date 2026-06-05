import os
from pathlib import Path


def load_dotenv(dotenv_path: str | os.PathLike = ".env", *, override: bool = False) -> dict[str, str]:
    path = Path(dotenv_path)
    if not path.exists() or not path.is_file():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        if (not override) and (key in os.environ):
            continue
        os.environ[key] = value
        loaded[key] = value

    return loaded
