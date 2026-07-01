from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.catalog.metrics import persist_failed_extraction, persist_successful_extraction
from src.config import PROJECT_ROOT
from src.contracts.extraction import MetricExtraction, PROMPT_VERSION
from src.db import SessionLocal
from src.llm.client import LLMConfig, LLMError, build_llm_client, load_llm_config
from src.models import Document
from src.processing.parse_pdf import chunk_output_path, parse_document


PROMPT_PATH = PROJECT_ROOT / "src" / "prompts" / "extraction_v1.md"
DEFAULT_MAX_CHUNKS = 8


def load_system_prompt(prompt_path: Path = PROMPT_PATH) -> str:
    return prompt_path.read_text(encoding="utf-8")


def load_chunk_rows(chunk_path: Path) -> list[dict[str, Any]]:
    if not chunk_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in chunk_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_candidate_chunks(document: Document, max_chunks: int = DEFAULT_MAX_CHUNKS) -> list[dict[str, Any]]:
    chunk_path = chunk_output_path(document)
    rows = load_chunk_rows(chunk_path)
    if not rows:
        _, parsed_chunks = parse_document(document)
        rows = [
            {
                "document_id": chunk.document_id,
                "company": chunk.company,
                "title": chunk.title,
                "pdf_url": chunk.pdf_url,
                "sha256": chunk.sha256,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "text_length": chunk.text_length,
                "is_candidate": chunk.is_candidate,
                "candidate_terms": list(chunk.candidate_terms),
            }
            for chunk in parsed_chunks
        ]

    candidate_rows = [row for row in rows if row.get("is_candidate")]
    selected_rows = candidate_rows[:max_chunks]
    return [
        {
            "page_number": row["page_number"],
            "chunk_index": row["chunk_index"],
            "candidate_terms": row.get("candidate_terms", []),
            "text": row["text"],
        }
        for row in selected_rows
    ]


def document_context(document: Document) -> dict[str, Any]:
    return {
        "document_id": document.id,
        "company": document.company.name,
        "title": document.title,
        "pdf_url": document.pdf_url,
        "sha256": document.sha256,
        "year": document.year,
        "quarter": document.quarter,
    }


def extract_document_metrics(
    document: Document,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    llm_config: LLMConfig | None = None,
) -> MetricExtraction:
    llm_config = llm_config or load_llm_config()
    prompt = load_system_prompt()
    chunks = load_candidate_chunks(document, max_chunks=max_chunks)
    client = build_llm_client(llm_config)
    try:
        return client.extract_metrics(
            system_prompt=prompt,
            document_context=document_context(document),
            chunks=chunks,
        )
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def load_document(document_id: int) -> Document:
    with SessionLocal() as session:
        document = session.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            raise ValueError(f"Documento {document_id} nao encontrado.")
        document.company.name
        session.expunge(document)
        return document


def extract_and_optionally_persist(
    document_id: int,
    *,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    persist: bool = False,
) -> MetricExtraction:
    llm_config = load_llm_config()
    if not persist:
        document = load_document(document_id)
        return extract_document_metrics(document, max_chunks=max_chunks, llm_config=llm_config)

    with SessionLocal() as session:
        document = session.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            raise ValueError(f"Documento {document_id} nao encontrado.")

        try:
            extraction = extract_document_metrics(
                document,
                max_chunks=max_chunks,
                llm_config=llm_config,
            )
        except Exception as exc:
            persist_failed_extraction(
                session,
                document,
                model_name=llm_config.model,
                prompt_version=PROMPT_VERSION,
                error_message=str(exc),
            )
            session.commit()
            raise

        persist_successful_extraction(
            session,
            document,
            extraction,
            model_name=llm_config.model,
        )
        session.commit()
        return extraction


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Envia chunks candidatos ao LLM e valida a resposta estruturada."
    )
    parser.add_argument("--document-id", type=int, required=True)
    parser.add_argument("--max-chunks", type=int, default=DEFAULT_MAX_CHUNKS)
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Salva extraction_run, metricas e status do documento no catalogo.",
    )
    args = parser.parse_args()

    try:
        extraction = extract_and_optionally_persist(
            args.document_id,
            max_chunks=args.max_chunks,
            persist=args.persist,
        )
    except (LLMError, ValueError) as exc:
        print(f"extraction_failed | document_id={args.document_id} | {exc}")
        raise SystemExit(1) from exc

    print(extraction.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
