import json
import os
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent.parent


def get_secret(
    key: str,
    default_value: Optional[str] = None,
    json_path: str = str(BASE_DIR / "secrets.json"),
):
    value = os.getenv(key)
    if value:
        return value

    try:
        with open(json_path, encoding="utf-8") as f:
            secrets = json.load(f)
        return secrets[key]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        pass

    if default_value is not None:
        return default_value

    raise EnvironmentError(f"Set the {key} environment variable")


def get_secret_any(*keys: str):
    for key in keys:
        try:
            return get_secret(key)
        except EnvironmentError:
            pass

    raise EnvironmentError(f"Set one of these environment variables: {', '.join(keys)}")


try:
    MONGO_DB_NAME = get_secret_any("MONGO_DB_NAME", "MONGODB_DB_NAME")
except EnvironmentError:
    MONGO_DB_NAME = "kyungbokbook"

try:
    MONGO_URL = get_secret_any("MONGO_URI", "MONGODB_URI")
except EnvironmentError:
    MONGO_URL = "mongodb://localhost:27017"

MONGODB_DB_NAME = MONGO_DB_NAME
MONGODB_URI = MONGO_URL
