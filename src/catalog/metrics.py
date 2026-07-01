from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.contracts.extraction import MetricExtraction
from src.models import Document, ExtractedMetric, ExtractionRun


def create_extraction_run(
    session: Session,
    document: Document,
    *,
    model_name: str | None,
    prompt_version: str | None,
    status: str,
    error_message: str | None = None,
) -> ExtractionRun:
    run = ExtractionRun(
        document_id=document.id,
        model_name=model_name,
        prompt_version=prompt_version,
        status=status,
        error_message=error_message,
    )
    session.add(run)
    session.flush()
    return run


def replace_document_metrics(
    session: Session,
    document: Document,
    extraction: MetricExtraction,
) -> list[ExtractedMetric]:
    session.execute(delete(ExtractedMetric).where(ExtractedMetric.document_id == document.id))
    metrics: list[ExtractedMetric] = []

    for item in extraction.metrics:
        metric = ExtractedMetric(
            document_id=document.id,
            company_id=document.company_id,
            metric_name=item.nome_metrica,
            period_year=item.ano,
            period_quarter=item.trimestre,
            value=Decimal(str(item.valor)) if item.valor is not None else None,
            unit=item.unidade,
            currency=item.moeda,
            page_number=item.pagina,
            source_excerpt=item.trecho_fonte,
            confidence=Decimal(str(item.confianca)),
        )
        session.add(metric)
        metrics.append(metric)

    session.flush()
    return metrics


def persist_successful_extraction(
    session: Session,
    document: Document,
    extraction: MetricExtraction,
    *,
    model_name: str | None,
) -> tuple[ExtractionRun, list[ExtractedMetric]]:
    run = create_extraction_run(
        session,
        document,
        model_name=model_name,
        prompt_version=extraction.prompt_version,
        status="success",
    )
    metrics = replace_document_metrics(session, document, extraction)
    document.status = "processed"
    document.processed_at = datetime.now(UTC)
    session.flush()
    return run, metrics


def persist_failed_extraction(
    session: Session,
    document: Document,
    *,
    model_name: str | None,
    prompt_version: str | None,
    error_message: str,
) -> ExtractionRun:
    run = create_extraction_run(
        session,
        document,
        model_name=model_name,
        prompt_version=prompt_version,
        status="failed",
        error_message=error_message,
    )
    document.status = "failed"
    document.processed_at = datetime.now(UTC)
    session.flush()
    return run
