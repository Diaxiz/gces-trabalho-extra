from __future__ import annotations

import argparse
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT
from src.db import SessionLocal, create_db_and_tables
from src.ingestion.discover import DocumentCandidate, REQUEST_HEADERS, discover_all
from src.models import Company, Document


RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


@dataclass(frozen=True)
class IngestionResult:
    candidate: DocumentCandidate
    status: str
    sha256: str
    local_path: Path
    document_id: int | None


def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def safe_filename(value: str) -> str:
    value = strip_accents(value)
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "documento"


def filename_for_candidate(candidate: DocumentCandidate, sha256: str) -> str:
    parsed_name = Path(urlparse(candidate.url).path).name
    title_name = safe_filename(candidate.title)
    base_name = safe_filename(parsed_name) if parsed_name else title_name
    if not base_name.endswith(".pdf"):
        base_name = f"{title_name}.pdf"
    return f"{safe_filename(candidate.company)}-{sha256[:12]}-{base_name}"


def catalog_path(local_path: Path) -> str:
    try:
        return str(local_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(local_path)


def resolve_catalog_path(value: str | None) -> Path:
    if not value:
        return RAW_DATA_DIR
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def download_document(candidate: DocumentCandidate, client: httpx.Client) -> bytes:
    response = client.get(candidate.url)
    response.raise_for_status()
    return response.content


def get_or_create_company(session: Session, candidate: DocumentCandidate) -> Company:
    company = session.scalar(select(Company).where(Company.name == candidate.company))
    if company is not None:
        if candidate.ticker and company.ticker != candidate.ticker:
            company.ticker = candidate.ticker
        return company

    company = Company(
        name=candidate.company,
        ticker=candidate.ticker,
        ri_url=candidate.source_url,
    )
    session.add(company)
    session.flush()
    return company


def existing_document_for_url(session: Session, candidate: DocumentCandidate) -> Document | None:
    return session.scalar(select(Document).where(Document.pdf_url == candidate.url))


def catalog_document(
    session: Session,
    candidate: DocumentCandidate,
    sha256: str,
    local_path: Path,
) -> tuple[str, int | None]:
    existing = session.scalar(select(Document).where(Document.sha256 == sha256))
    if existing is not None:
        return "skipped_duplicate", existing.id

    company = get_or_create_company(session, candidate)
    document = Document(
        company_id=company.id,
        title=candidate.title,
        pdf_url=candidate.url,
        sha256=sha256,
        year=candidate.year,
        quarter=candidate.quarter,
        status="downloaded",
        downloaded_at=datetime.now(UTC),
        local_path=catalog_path(local_path),
    )
    session.add(document)
    session.flush()
    return "downloaded", document.id


def ingest_candidate(
    candidate: DocumentCandidate,
    session: Session,
    client: httpx.Client,
    raw_dir: Path = RAW_DATA_DIR,
) -> IngestionResult:
    existing_by_url = existing_document_for_url(session, candidate)
    if existing_by_url is not None:
        return IngestionResult(
            candidate=candidate,
            status="skipped_duplicate",
            sha256=existing_by_url.sha256,
            local_path=resolve_catalog_path(existing_by_url.local_path),
            document_id=existing_by_url.id,
        )

    content = download_document(candidate, client)
    sha256 = calculate_sha256(content)
    raw_dir.mkdir(parents=True, exist_ok=True)
    local_path = raw_dir / filename_for_candidate(candidate, sha256)

    if not local_path.exists():
        local_path.write_bytes(content)

    status, document_id = catalog_document(session, candidate, sha256, local_path)
    session.commit()
    return IngestionResult(candidate, status, sha256, local_path, document_id)


def ingest_candidates(
    candidates: list[DocumentCandidate],
    session: Session,
    client: httpx.Client,
    limit: int | None = None,
) -> list[IngestionResult]:
    results: list[IngestionResult] = []
    selected_candidates = candidates if limit is None else candidates[:limit]
    for candidate in selected_candidates:
        results.append(ingest_candidate(candidate, session, client))
    return results


def print_result(result: IngestionResult) -> None:
    print(
        " | ".join(
            [
                result.status,
                result.candidate.company,
                result.sha256,
                str(result.local_path),
                result.candidate.url,
            ]
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descobre, baixa e cataloga PDFs usando SHA-256 para idempotencia."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de candidatos baixados nesta execucao.",
    )
    args = parser.parse_args()

    create_db_and_tables()
    candidates = discover_all()
    if not candidates:
        print("Nenhum documento candidato encontrado.")
        return

    with (
        SessionLocal() as session,
        httpx.Client(
            follow_redirects=True,
            headers=REQUEST_HEADERS,
            timeout=httpx.Timeout(30.0),
        ) as client,
    ):
        results = ingest_candidates(candidates, session, client, limit=args.limit)

    for result in results:
        print_result(result)


if __name__ == "__main__":
    main()
