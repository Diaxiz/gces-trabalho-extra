from __future__ import annotations

import argparse
import json
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT
from src.db import SessionLocal
from src.models import Document


PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_MAX_CHARS = 3500
BUSINESS_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lancamentos", ("lancamentos", "lancamento", "lancado", "lancada", "lancadas")),
    ("vendas liquidas", ("vendas liquidas", "venda liquida")),
    ("vendas brutas", ("vendas brutas", "venda bruta")),
    ("vgv", ("vgv",)),
    ("unidades", ("unidades", "unidade")),
    ("distratos", ("distratos", "distrato")),
    ("vso", ("vso", "vendas sobre oferta")),
    ("landbank", ("landbank",)),
    ("banco de terrenos", ("banco de terrenos", "terrenos")),
    ("repasses", ("repasses", "repasse")),
    ("estoque", ("estoque",)),
    ("geracao de caixa", ("geracao de caixa", "consumo de caixa")),
    ("receita liquida", ("receita liquida",)),
)


@dataclass(frozen=True)
class PdfChunk:
    document_id: int
    company: str
    title: str
    pdf_url: str
    sha256: str
    page_number: int
    chunk_index: int
    text: str
    text_length: int
    is_candidate: bool
    candidate_terms: tuple[str, ...]


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: str) -> str:
    value = strip_accents(value)
    return " ".join(value.lower().split())


def candidate_terms(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
    terms: list[str] = []
    for canonical_term, patterns in BUSINESS_KEYWORDS:
        if any(pattern in normalized for pattern in patterns):
            terms.append(canonical_term)
    return tuple(terms)


def clean_text(value: str) -> str:
    lines = [" ".join(line.split()) for line in value.splitlines()]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines)


def split_page_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)
        next_length = current_length + paragraph_length + (1 if current else 0)
        if current and next_length > max_chars:
            chunks.append("\n".join(current))
            current = [paragraph]
            current_length = paragraph_length
            continue

        current.append(paragraph)
        current_length = next_length

    if current:
        chunks.append("\n".join(current))
    return chunks


def resolve_document_path(document: Document) -> Path:
    if not document.local_path:
        raise ValueError(f"Documento {document.id} nao possui local_path.")

    path = Path(document.local_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def extract_pdf_chunks(
    document: Document,
    pdf_path: Path,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[PdfChunk]:
    chunks: list[PdfChunk] = []
    with fitz.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf, start=1):
            page_text = page.get_text("text")
            for chunk_index, chunk_text in enumerate(split_page_text(page_text, max_chars), start=1):
                terms = candidate_terms(chunk_text)
                chunks.append(
                    PdfChunk(
                        document_id=document.id,
                        company=document.company.name,
                        title=document.title,
                        pdf_url=document.pdf_url,
                        sha256=document.sha256,
                        page_number=page_index,
                        chunk_index=chunk_index,
                        text=chunk_text,
                        text_length=len(chunk_text),
                        is_candidate=bool(terms),
                        candidate_terms=terms,
                    )
                )
    return chunks


def chunk_output_path(document: Document, output_dir: Path = PROCESSED_DATA_DIR) -> Path:
    filename = f"document_{document.id}_{document.sha256[:12]}_chunks.jsonl"
    return output_dir / filename


def write_chunks_jsonl(chunks: list[PdfChunk], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            data = asdict(chunk)
            data["candidate_terms"] = list(chunk.candidate_terms)
            file.write(json.dumps(data, ensure_ascii=False) + "\n")


def parse_document(
    document: Document,
    output_dir: Path = PROCESSED_DATA_DIR,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> tuple[Path, list[PdfChunk]]:
    pdf_path = resolve_document_path(document)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF nao encontrado para documento {document.id}: {pdf_path}")

    chunks = extract_pdf_chunks(document, pdf_path, max_chars=max_chars)
    output_path = chunk_output_path(document, output_dir)
    write_chunks_jsonl(chunks, output_path)
    return output_path, chunks


def load_documents(session: Session, document_id: int | None, limit: int | None) -> list[Document]:
    statement = select(Document).where(Document.local_path.is_not(None)).order_by(Document.id)
    if document_id is not None:
        statement = statement.where(Document.id == document_id)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement).all())


def print_summary(document: Document, output_path: Path, chunks: list[PdfChunk]) -> None:
    candidate_count = sum(1 for chunk in chunks if chunk.is_candidate)
    pages = sorted({chunk.page_number for chunk in chunks})
    page_summary = f"{len(pages)} paginas" if len(pages) != 1 else "1 pagina"
    print(
        " | ".join(
            [
                f"document_id={document.id}",
                document.company.name,
                page_summary,
                f"chunks={len(chunks)}",
                f"candidate_chunks={candidate_count}",
                str(output_path),
            ]
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai texto de PDFs catalogados e gera chunks por pagina/secao."
    )
    parser.add_argument("--document-id", type=int, default=None, help="Processa apenas um documento.")
    parser.add_argument("--limit", type=int, default=None, help="Limita a quantidade de documentos.")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="Tamanho maximo aproximado de cada chunk.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        documents = load_documents(session, args.document_id, args.limit)
        if not documents:
            print("Nenhum documento catalogado com PDF local foi encontrado.")
            return

        for document in documents:
            output_path, chunks = parse_document(
                document,
                output_dir=PROCESSED_DATA_DIR,
                max_chars=args.max_chars,
            )
            print_summary(document, output_path, chunks)


if __name__ == "__main__":
    main()
