import json

import pytest

from src.contracts.extraction import PROMPT_VERSION
from src.llm.client import LLMError, MockLLMClient, validate_llm_json_response


def test_mock_llm_returns_valid_contract() -> None:
    client = MockLLMClient()

    extraction = client.extract_metrics(
        system_prompt="prompt",
        document_context={
            "document_id": 1,
            "pdf_url": "https://example.com/a.pdf",
            "sha256": "a" * 64,
        },
        chunks=[{"page_number": 1, "text": "VGV lancado"}],
    )

    assert extraction.document_id == 1
    assert extraction.prompt_version == PROMPT_VERSION
    assert extraction.metrics == []
    assert extraction.warnings


def test_validate_llm_json_response_accepts_fenced_json() -> None:
    raw = json.dumps(
        {
            "document_id": 1,
            "pdf_url": "https://example.com/a.pdf",
            "sha256": "a" * 64,
            "prompt_version": PROMPT_VERSION,
            "metrics": [],
            "warnings": ["sem metricas"],
        }
    )

    extraction = validate_llm_json_response(f"```json\n{raw}\n```")

    assert extraction.document_id == 1


def test_validate_llm_json_response_rejects_invalid_json() -> None:
    with pytest.raises(LLMError):
        validate_llm_json_response("nao e json")


def test_validate_llm_json_response_rejects_contract_violation() -> None:
    raw = json.dumps({"document_id": 1, "metrics": []})

    with pytest.raises(LLMError):
        validate_llm_json_response(raw)
