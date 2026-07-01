from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PROMPT_VERSION = "extraction_v1"


class MetricItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    empresa: str = Field(min_length=1, description="Nome da empresa a que a metrica se refere.")
    ano: int | None = Field(default=None, ge=2000, le=2100)
    trimestre: int | None = Field(default=None, ge=1, le=4)
    nome_metrica: str = Field(min_length=1)
    valor: float | None = Field(
        default=None,
        description="Valor absoluto extraido. Use null quando nao houver evidencia.",
    )
    unidade: str | None = Field(default=None, description="Ex: unidades, %, R$ milhoes.")
    moeda: Literal["BRL", "USD"] | None = Field(default=None)
    pagina: int = Field(ge=1)
    trecho_fonte: str = Field(min_length=8, max_length=1200)
    confianca: float = Field(ge=0, le=1)

    @field_validator("nome_metrica")
    @classmethod
    def normalize_metric_name(cls, value: str) -> str:
        return " ".join(value.lower().split())

    @field_validator("trecho_fonte")
    @classmethod
    def require_source_excerpt_with_context(cls, value: str) -> str:
        if len(value.split()) < 3:
            raise ValueError("trecho_fonte deve conter evidencia textual suficiente.")
        return value

    @model_validator(mode="after")
    def validate_value_metadata(self) -> MetricItem:
        if self.valor is not None and self.unidade is None and self.moeda is None:
            raise ValueError("valor numerico deve trazer unidade ou moeda.")
        if self.moeda is not None and self.unidade is None:
            raise ValueError("moeda informada deve vir acompanhada da unidade monetaria.")
        return self


class MetricExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    document_id: int = Field(ge=1)
    pdf_url: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    prompt_version: str = Field(default=PROMPT_VERSION)
    metrics: list[MetricItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("prompt_version")
    @classmethod
    def prompt_version_must_match(cls, value: str) -> str:
        if value != PROMPT_VERSION:
            raise ValueError(f"prompt_version deve ser {PROMPT_VERSION}.")
        return value

    @field_validator("metrics")
    @classmethod
    def reject_duplicate_metric_lineage(cls, value: list[MetricItem]) -> list[MetricItem]:
        seen: set[tuple[str, int | None, int | None, int, str]] = set()
        for metric in value:
            key = (
                metric.nome_metrica,
                metric.ano,
                metric.trimestre,
                metric.pagina,
                metric.trecho_fonte,
            )
            if key in seen:
                raise ValueError("metricas duplicadas com mesma linhagem nao sao permitidas.")
            seen.add(key)
        return value


def validate_extraction_payload(payload: dict[str, Any]) -> MetricExtraction:
    return MetricExtraction.model_validate(payload)
