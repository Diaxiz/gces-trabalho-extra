from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.db import get_session
from src.models import Base, Company, Document, ExtractedMetric


def build_test_client() -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_factory() as session:
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
            status="processed",
            local_path="data/raw/previa.pdf",
        )
        session.add(document)
        session.flush()
        metric = ExtractedMetric(
            document_id=document.id,
            company_id=company.id,
            metric_name="vgv lancado",
            period_year=2026,
            period_quarter=1,
            value=Decimal("1005.8"),
            unit="R$ milhoes",
            currency="BRL",
            page_number=2,
            source_excerpt="VGV Lancado (VGV 100%) 1.005,8",
            confidence=Decimal("0.92"),
        )
        session.add(metric)
        session.commit()

    def override_get_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_health() -> None:
    client = build_test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    app.dependency_overrides.clear()


def test_list_companies() -> None:
    client = build_test_client()

    response = client.get("/api/empresas")

    assert response.status_code == 200
    assert response.json()["items"][0]["ticker"] == "DIRR3"
    app.dependency_overrides.clear()


def test_list_documents_with_lineage() -> None:
    client = build_test_client()

    response = client.get("/api/documentos?empresa=Direcional&ano=2026&trimestre=1")
    body = response.json()

    assert response.status_code == 200
    assert body["filters"] == {"empresa": "Direcional", "ano": 2026, "trimestre": 1}
    assert body["items"][0]["sha256"] == "a" * 64
    assert body["items"][0]["pdf_url"] == "https://example.com/previa.pdf"
    app.dependency_overrides.clear()


def test_conjuntura_filters_metrics_and_returns_lineage() -> None:
    client = build_test_client()

    response = client.get("/api/conjuntura?empresa=Direcional&ano=2026&trimestre=1")
    body = response.json()

    assert response.status_code == 200
    assert body["count"] == 1
    metric = body["metrics"][0]
    assert metric["metric_name"] == "vgv lancado"
    assert metric["value"] == 1005.8
    assert metric["document"]["sha256"] == "a" * 64
    assert metric["document"]["pdf_url"] == "https://example.com/previa.pdf"
    assert metric["page_number"] == 2
    assert metric["source_excerpt"].startswith("VGV Lancado")
    app.dependency_overrides.clear()


def test_metricas_endpoint_filters_by_company_and_period() -> None:
    client = build_test_client()

    response = client.get("/api/metricas?empresa=Direcional&ano=2026&trimestre=1")
    body = response.json()

    assert response.status_code == 200
    assert body["filters"] == {"empresa": "Direcional", "ano": 2026, "trimestre": 1}
    assert len(body["items"]) == 1
    assert body["items"][0]["metric_name"] == "vgv lancado"
    app.dependency_overrides.clear()


def test_conjuntura_returns_empty_list_when_no_match() -> None:
    client = build_test_client()

    response = client.get("/api/conjuntura?empresa=MRV&ano=2026&trimestre=1")
    body = response.json()

    assert response.status_code == 200
    assert body["count"] == 0
    assert body["metrics"] == []
    app.dependency_overrides.clear()
