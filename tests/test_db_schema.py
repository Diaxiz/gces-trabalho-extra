from sqlalchemy import create_engine, inspect

from src.db import create_db_and_tables
from src.models import Base


def test_create_catalog_schema_in_memory() -> None:
    engine = create_engine("sqlite:///:memory:")

    create_db_and_tables(engine)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "companies",
        "documents",
        "extracted_metrics",
        "extraction_runs",
    }

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    metric_columns = {column["name"] for column in inspector.get_columns("extracted_metrics")}

    assert {"pdf_url", "sha256", "company_id", "local_path"}.issubset(document_columns)
    assert {"document_id", "company_id", "page_number", "source_excerpt"}.issubset(
        metric_columns
    )

    Base.metadata.drop_all(bind=engine)
