from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.catalog.metrics import persist_failed_extraction, persist_successful_extraction
from src.contracts.extraction import PROMPT_VERSION, validate_extraction_payload
from src.models import Base, Company, Document, ExtractedMetric, ExtractionRun


def create_document(session) -> Document:
    company = Company(name="Direcional", ticker="DIRR3", ri_url="https://ri.example.com")
    session.add(company)
    session.flush()
    document = Document(
        company_id=company.id,
        title="Previa Operacional",
        pdf_url="https://example.com/previa.pdf",
        sha256="a" * 64,
        year=2026,
        quarter=1,
        status="downloaded",
        local_path="data/raw/previa.pdf",
    )
    session.add(document)
    session.flush()
    return document


def extraction_payload() -> dict[str, object]:
    return {
        "document_id": 1,
        "pdf_url": "https://example.com/previa.pdf",
        "sha256": "a" * 64,
        "prompt_version": PROMPT_VERSION,
        "metrics": [
            {
                "empresa": "Direcional",
                "ano": 2026,
                "trimestre": 1,
                "nome_metrica": "VGV Lancado",
                "valor": 1005.8,
                "unidade": "R$ milhoes",
                "moeda": "BRL",
                "pagina": 2,
                "trecho_fonte": "VGV Lancado (VGV 100%) 1.005,8",
                "confianca": 0.92,
            },
            {
                "empresa": "Direcional",
                "ano": 2026,
                "trimestre": 1,
                "nome_metrica": "Unidades Lancadas",
                "valor": None,
                "unidade": "unidades",
                "moeda": None,
                "pagina": 2,
                "trecho_fonte": "Unidades Lancadas aparece sem valor legivel no trecho.",
                "confianca": 0.3,
            },
        ],
        "warnings": [],
    }


def test_persist_successful_extraction_saves_metrics_and_lineage() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        document = create_document(session)
        extraction = validate_extraction_payload(extraction_payload())

        run, metrics = persist_successful_extraction(
            session,
            document,
            extraction,
            model_name="mock-extractor",
        )
        session.commit()

        assert run.status == "success"
        assert len(metrics) == 2
        saved_metrics = session.scalars(select(ExtractedMetric)).all()
        assert len(saved_metrics) == 2
        assert saved_metrics[0].document.pdf_url == "https://example.com/previa.pdf"
        assert saved_metrics[0].document.sha256 == "a" * 64
        assert saved_metrics[0].page_number == 2
        assert saved_metrics[0].source_excerpt.startswith("VGV Lancado")
        assert saved_metrics[1].value is None
        assert document.status == "processed"
        assert document.processed_at is not None

    Base.metadata.drop_all(bind=engine)


def test_persist_failed_extraction_updates_document_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        document = create_document(session)

        run = persist_failed_extraction(
            session,
            document,
            model_name="mock-extractor",
            prompt_version=PROMPT_VERSION,
            error_message="json invalido",
        )
        session.commit()

        assert run.status == "failed"
        assert run.error_message == "json invalido"
        assert session.scalar(select(ExtractionRun)).status == "failed"
        assert document.status == "failed"

    Base.metadata.drop_all(bind=engine)
