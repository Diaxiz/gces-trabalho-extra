import pytest
from pydantic import ValidationError

from src.contracts.extraction import PROMPT_VERSION, validate_extraction_payload


def valid_payload() -> dict[str, object]:
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
                "nome_metrica": "VGV Lançado",
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
                "nome_metrica": "Unidades Lançadas",
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


def test_validate_good_extraction_payload() -> None:
    extraction = validate_extraction_payload(valid_payload())

    assert extraction.prompt_version == PROMPT_VERSION
    assert extraction.metrics[0].nome_metrica == "vgv lançado"
    assert extraction.metrics[0].valor == 1005.8
    assert extraction.metrics[1].valor is None


def test_reject_invalid_json_shape() -> None:
    payload = valid_payload()
    payload["metrics"] = [{"empresa": "Direcional", "valor": 100.0}]

    with pytest.raises(ValidationError):
        validate_extraction_payload(payload)


def test_reject_value_without_unit_or_currency() -> None:
    payload = valid_payload()
    metric = payload["metrics"][0]
    assert isinstance(metric, dict)
    metric["unidade"] = None
    metric["moeda"] = None

    with pytest.raises(ValidationError):
        validate_extraction_payload(payload)


def test_reject_extra_fields_from_llm() -> None:
    payload = valid_payload()
    payload["alucinacao"] = "campo fora do contrato"

    with pytest.raises(ValidationError):
        validate_extraction_payload(payload)


def test_reject_wrong_prompt_version() -> None:
    payload = valid_payload()
    payload["prompt_version"] = "extraction_v0"

    with pytest.raises(ValidationError):
        validate_extraction_payload(payload)


def test_reject_duplicate_metric_with_same_lineage() -> None:
    payload = valid_payload()
    metric = payload["metrics"][0]
    assert isinstance(metric, dict)
    payload["metrics"] = [metric, metric.copy()]

    with pytest.raises(ValidationError):
        validate_extraction_payload(payload)
