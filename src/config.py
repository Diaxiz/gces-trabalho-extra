from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "catalog.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str


def load_dotenv() -> None:
    try:
        from dotenv import load_dotenv as load_dotenv_file
    except ImportError:
        return

    load_dotenv_file(PROJECT_ROOT / ".env")


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )


def sqlite_path_from_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None

    raw_path = database_url.replace("sqlite:///", "", 1)
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def ensure_database_directory(database_url: str) -> None:
    sqlite_path = sqlite_path_from_url(database_url)
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
