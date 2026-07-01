from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    ri_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    documents: Mapped[list[Document]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    metrics: Mapped[list[ExtractedMetric]] = relationship(back_populates="company")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_company_period", "company_id", "year", "quarter"),
        Index("ix_documents_sha256", "sha256", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_url: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="discovered")
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    company: Mapped[Company] = relationship(back_populates="documents")
    metrics: Mapped[list[ExtractedMetric]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    extraction_runs: Mapped[list[ExtractionRun]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class ExtractedMetric(Base):
    __tablename__ = "extracted_metrics"
    __table_args__ = (
        Index("ix_metrics_company_period", "company_id", "period_year", "period_quarter"),
        Index("ix_metrics_document", "document_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(160), nullable=False)
    period_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    document: Mapped[Document] = relationship(back_populates="metrics")
    company: Mapped[Company] = relationship(back_populates="metrics")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (Index("ix_extraction_runs_document", "document_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    document: Mapped[Document] = relationship(back_populates="extraction_runs")
