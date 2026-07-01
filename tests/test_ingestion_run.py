from pathlib import Path

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.ingestion.discover import DocumentCandidate
from src.ingestion.run import calculate_sha256, ingest_candidate
from src.models import Base, Company, Document


def test_calculate_sha256() -> None:
    assert (
        calculate_sha256(b"pdf-content")
        == "3c41d3835155c97d51a836c887be9c0063b7b45f61e14017a9d653fa4c655802"
    )


def test_ingest_candidate_skips_duplicate_hash(tmp_path: Path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    pdf_content = b"%PDF-1.4 fake content"
    request_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, content=pdf_content)

    candidate = DocumentCandidate(
        company="Direcional",
        ticker="DIRR3",
        title="Previa Operacional 1T26",
        url="https://example.com/previa.pdf",
        source_url="https://ri.example.com/central-de-resultados",
        year=2026,
        quarter=1,
        matched_terms=("previa operacional",),
    )

    with session_factory() as session, httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first = ingest_candidate(candidate, session, client, raw_dir=tmp_path)
        second = ingest_candidate(candidate, session, client, raw_dir=tmp_path)

        assert first.status == "downloaded"
        assert second.status == "skipped_duplicate"
        assert first.sha256 == second.sha256
        assert first.local_path == second.local_path
        assert request_count == 1

        assert session.scalar(select(Company).where(Company.name == "Direcional")) is not None
        assert len(session.scalars(select(Document)).all()) == 1

    Base.metadata.drop_all(bind=engine)
