from pathlib import Path

import fitz

from src.processing.parse_pdf import (
    PdfChunk,
    candidate_terms,
    split_page_text,
    write_chunks_jsonl,
)


def test_candidate_terms_normalizes_accents() -> None:
    terms = candidate_terms("VGV lançado, vendas líquidas, unidades e geração de caixa.")

    assert "vgv" in terms
    assert "lancamentos" in terms
    assert "vendas liquidas" in terms
    assert "unidades" in terms
    assert "geracao de caixa" in terms


def test_split_page_text_respects_max_chars() -> None:
    text = "\n".join(["VGV lancado no trimestre"] * 20)

    chunks = split_page_text(text, max_chars=80)

    assert len(chunks) > 1
    assert all(len(chunk) <= 80 for chunk in chunks)


def test_write_chunks_jsonl(tmp_path: Path) -> None:
    chunk = PdfChunk(
        document_id=1,
        company="Direcional",
        title="Previa Operacional",
        pdf_url="https://example.com/previa.pdf",
        sha256="a" * 64,
        page_number=1,
        chunk_index=1,
        text="VGV lancado somou R$ 1,0 bilhao.",
        text_length=34,
        is_candidate=True,
        candidate_terms=("vgv", "lancamentos"),
    )
    output_path = tmp_path / "chunks.jsonl"

    write_chunks_jsonl([chunk], output_path)

    content = output_path.read_text(encoding="utf-8")
    assert '"document_id": 1' in content
    assert '"candidate_terms": ["vgv", "lancamentos"]' in content


def test_pymupdf_can_extract_generated_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "VGV lancado e vendas liquidas no 1T26")
    pdf.save(pdf_path)
    pdf.close()

    with fitz.open(pdf_path) as opened_pdf:
        text = opened_pdf[0].get_text("text")

    assert "VGV lancado" in text
