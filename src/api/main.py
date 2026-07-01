from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.db import create_db_and_tables, get_session
from src.models import Company, Document, ExtractedMetric


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    yield


app = FastAPI(
    title="Pipeline UDA - Conjuntura Habitacional",
    version="0.1.0",
    description="API REST para consultar metricas extraidas de PDFs de RI com linhagem.",
    lifespan=lifespan,
)


def serialize_decimal(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def serialize_company(company: Company) -> dict[str, Any]:
    return {
        "id": company.id,
        "name": company.name,
        "ticker": company.ticker,
        "ri_url": company.ri_url,
    }


def serialize_document(document: Document) -> dict[str, Any]:
    return {
        "id": document.id,
        "company_id": document.company_id,
        "company": document.company.name,
        "title": document.title,
        "pdf_url": document.pdf_url,
        "sha256": document.sha256,
        "year": document.year,
        "quarter": document.quarter,
        "status": document.status,
        "downloaded_at": document.downloaded_at.isoformat() if document.downloaded_at else None,
        "processed_at": document.processed_at.isoformat() if document.processed_at else None,
        "local_path": document.local_path,
    }


def serialize_metric(metric: ExtractedMetric) -> dict[str, Any]:
    document = metric.document
    return {
        "id": metric.id,
        "company": metric.company.name,
        "metric_name": metric.metric_name,
        "period_year": metric.period_year,
        "period_quarter": metric.period_quarter,
        "value": serialize_decimal(metric.value),
        "unit": metric.unit,
        "currency": metric.currency,
        "page_number": metric.page_number,
        "source_excerpt": metric.source_excerpt,
        "confidence": serialize_decimal(metric.confidence),
        "created_at": metric.created_at.isoformat() if metric.created_at else None,
        "document": {
            "id": document.id,
            "title": document.title,
            "pdf_url": document.pdf_url,
            "sha256": document.sha256,
            "year": document.year,
            "quarter": document.quarter,
            "status": document.status,
        },
    }


def company_filter(statement, company_name: str | None):
    if not company_name:
        return statement
    normalized = f"%{company_name.strip()}%"
    return statement.where(Company.name.ilike(normalized))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/empresas")
def list_companies(session: SessionDep) -> dict[str, Any]:
    companies = session.scalars(select(Company).order_by(Company.name)).all()
    return {"items": [serialize_company(company) for company in companies]}


@app.get("/api/documentos")
def list_documents(
    session: SessionDep,
    empresa: str | None = Query(default=None),
    ano: int | None = Query(default=None),
    trimestre: int | None = Query(default=None, ge=1, le=4),
) -> dict[str, Any]:
    statement = (
        select(Document)
        .join(Document.company)
        .options(selectinload(Document.company))
        .order_by(Document.id)
    )
    statement = company_filter(statement, empresa)
    if ano is not None:
        statement = statement.where(Document.year == ano)
    if trimestre is not None:
        statement = statement.where(Document.quarter == trimestre)

    documents = session.scalars(statement).all()
    return {
        "filters": {"empresa": empresa, "ano": ano, "trimestre": trimestre},
        "items": [serialize_document(document) for document in documents],
    }


@app.get("/api/metricas")
def list_metrics(
    session: SessionDep,
    empresa: str | None = Query(default=None),
    ano: int | None = Query(default=None),
    trimestre: int | None = Query(default=None, ge=1, le=4),
) -> dict[str, Any]:
    statement = (
        select(ExtractedMetric)
        .join(ExtractedMetric.company)
        .options(
            selectinload(ExtractedMetric.company),
            selectinload(ExtractedMetric.document).selectinload(Document.company),
        )
        .order_by(ExtractedMetric.id)
    )
    statement = company_filter(statement, empresa)
    if ano is not None:
        statement = statement.where(ExtractedMetric.period_year == ano)
    if trimestre is not None:
        statement = statement.where(ExtractedMetric.period_quarter == trimestre)

    metrics = session.scalars(statement).all()
    return {
        "filters": {"empresa": empresa, "ano": ano, "trimestre": trimestre},
        "items": [serialize_metric(metric) for metric in metrics],
    }


@app.get("/api/conjuntura")
def get_conjuntura(
    session: SessionDep,
    empresa: str | None = Query(default=None),
    ano: int | None = Query(default=None),
    trimestre: int | None = Query(default=None, ge=1, le=4),
) -> dict[str, Any]:
    statement = (
        select(ExtractedMetric)
        .join(ExtractedMetric.company)
        .options(
            selectinload(ExtractedMetric.company),
            selectinload(ExtractedMetric.document).selectinload(Document.company),
        )
        .order_by(ExtractedMetric.metric_name, ExtractedMetric.id)
    )
    statement = company_filter(statement, empresa)
    if ano is not None:
        statement = statement.where(ExtractedMetric.period_year == ano)
    if trimestre is not None:
        statement = statement.where(ExtractedMetric.period_quarter == trimestre)

    metrics = session.scalars(statement).all()
    return {
        "filters": {"empresa": empresa, "ano": ano, "trimestre": trimestre},
        "count": len(metrics),
        "metrics": [serialize_metric(metric) for metric in metrics],
    }
