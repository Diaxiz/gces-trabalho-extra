from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from src.config import ensure_database_directory, get_settings, sqlite_path_from_url
from src.models import Base


settings = get_settings()
ensure_database_directory(settings.database_url)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_db_and_tables(db_engine: Engine = engine) -> None:
    Base.metadata.create_all(bind=db_engine)


def drop_db_and_tables(db_engine: Engine = engine) -> None:
    Base.metadata.drop_all(bind=db_engine)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def list_table_names(db_engine: Engine = engine) -> list[str]:
    return sorted(inspect(db_engine).get_table_names())


def main() -> None:
    create_db_and_tables()
    sqlite_path = sqlite_path_from_url(settings.database_url)
    location = str(sqlite_path) if sqlite_path is not None else settings.database_url
    tables = ", ".join(list_table_names())
    print(f"Catalogo inicializado em: {location}")
    print(f"Tabelas criadas: {tables}")


if __name__ == "__main__":
    main()
