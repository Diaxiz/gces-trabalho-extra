from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from src.config import load_dotenv
from src.contracts.extraction import MetricExtraction, PROMPT_VERSION, validate_extraction_payload


DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None


class ExtractionLLMClient(Protocol):
    def extract_metrics(
        self,
        *,
        system_prompt: str,
        document_context: dict[str, Any],
        chunks: list[dict[str, Any]],
    ) -> MetricExtraction:
        pass


def load_llm_config() -> LLMConfig:
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    model = os.getenv("LLM_MODEL", "mock-extractor").strip()
    api_key = os.getenv("LLM_API_KEY") or None
    base_url = os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URLS.get(provider)
    return LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)


def extract_json_object(raw_content: str) -> dict[str, Any]:
    content = raw_content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Resposta do LLM nao e JSON valido: {exc}") from exc

    if not isinstance(parsed, dict):
        raise LLMError("Resposta do LLM deve ser um objeto JSON.")
    return parsed


def validate_llm_json_response(raw_content: str) -> MetricExtraction:
    payload = extract_json_object(raw_content)
    try:
        return validate_extraction_payload(payload)
    except Exception as exc:
        raise LLMError(f"Resposta do LLM falhou no contrato semantico: {exc}") from exc


class MockLLMClient:
    def extract_metrics(
        self,
        *,
        system_prompt: str,
        document_context: dict[str, Any],
        chunks: list[dict[str, Any]],
    ) -> MetricExtraction:
        _ = system_prompt
        payload = {
            "document_id": document_context["document_id"],
            "pdf_url": document_context["pdf_url"],
            "sha256": document_context["sha256"],
            "prompt_version": PROMPT_VERSION,
            "metrics": [],
            "warnings": [
                (
                    "Modo mock ativo: nenhum LLM real foi chamado; "
                    f"{len(chunks)} chunks candidatos foram recebidos."
                )
            ],
        }
        return validate_extraction_payload(payload)


class OpenAICompatibleLLMClient:
    def __init__(self, config: LLMConfig, client: httpx.Client | None = None) -> None:
        if not config.api_key:
            raise LLMError("LLM_API_KEY e obrigatoria para modo real.")
        if not config.base_url:
            raise LLMError("LLM_BASE_URL e obrigatoria para modo real.")

        self.config = config
        self.client = client or httpx.Client(timeout=httpx.Timeout(60.0))
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def extract_metrics(
        self,
        *,
        system_prompt: str,
        document_context: dict[str, Any],
        chunks: list[dict[str, Any]],
    ) -> MetricExtraction:
        user_payload = {
            "document": document_context,
            "chunks": chunks,
        }
        response = self.client.post(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    },
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Resposta do provedor LLM nao contem choices[0].message.content.") from exc
        return validate_llm_json_response(content)


def build_llm_client(config: LLMConfig | None = None) -> ExtractionLLMClient:
    config = config or load_llm_config()
    if config.provider == "mock" or not config.api_key:
        return MockLLMClient()
    if config.provider in {"openai", "deepseek", "openai-compatible"}:
        return OpenAICompatibleLLMClient(config)
    raise LLMError(f"Provedor LLM nao suportado nesta fase: {config.provider}")
