# Submissao Do Projeto 4

## Status Final

Projeto preparado para submissao do Projeto Individual 4: Pipeline UDA para PDFs
de Relacoes com Investidores de construtoras.

## Checklist De Entrega

- [x] Estrutura Python organizada em `src/`, `tests/`, `docs/` e `data/`.
- [x] Arquitetura documentada em `docs/arquitetura.md`.
- [x] Descoberta de PDFs em fontes de RI.
- [x] Download e catalogacao com SHA-256.
- [x] Idempotencia demonstravel por hash.
- [x] Parsing de PDFs com PyMuPDF.
- [x] Chunking por pagina/secao, sem coordenadas fixas.
- [x] Contrato semantico Pydantic.
- [x] Prompt versionado para LLM.
- [x] Cliente LLM configuravel com modo mock.
- [x] Persistencia de runs e metricas validadas com linhagem.
- [x] API REST com filtros por empresa, ano e trimestre.
- [x] Testes automatizados para pontos criticos.
- [x] Evidencias em `docs/evidencias.md`.
- [x] `.env` real fora do versionamento.

## Evidencias Principais

- 5 documentos catalogados.
- 3 fontes/empresas no catalogo local.
- 2 layouts diferentes demonstrados:
  - boletim/tabela de uma pagina;
  - previas/releases multi-pagina de RI.
- 5 arquivos JSONL de chunks gerados localmente.
- 31 testes automatizados passando.

## Como Validar

```powershell
py -m pip install -e ".[dev]"
py -m pytest
py -m ruff check .
py -m src.ingestion.discover
py -m src.processing.parse_pdf
py -m src.processing.extract --document-id 1 --persist
py -m uvicorn src.api.main:app --reload
```

Depois, acessar:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/api/documentos
http://127.0.0.1:8000/api/conjuntura?empresa=Direcional&ano=2026&trimestre=1
```

## Texto Sugerido Para Pull Request

Titulo:

```text
Projeto 4 - Pipeline UDA para PDFs de RI
```

Descricao:

```text
Este PR entrega o Projeto Individual 4: um pipeline UDA para PDFs de Relacoes com
Investidores de construtoras.

Principais pontos:
- Descoberta leve de documentos em paginas de RI.
- Download, SHA-256 e idempotencia no catalogo local.
- Parsing com PyMuPDF e chunking por pagina/secao.
- Contrato semantico com Pydantic e prompt versionado.
- Cliente LLM configuravel, com modo mock para testes sem chave.
- Persistencia de runs/metricas com linhagem.
- API FastAPI para consulta por empresa, ano e trimestre.
- Evidencias de dois layouts diferentes em docs/evidencias.md.
- Testes automatizados cobrindo idempotencia, contrato e filtros da API.

Validacoes:
- py -m pytest
- py -m ruff check .
```

## Observacao Sobre Modo Mock

Por seguranca, `.env.example` usa `LLM_PROVIDER=mock`. Esse modo valida o fluxo
sem chamar API externa e sem chave. Para gerar metricas reais, basta configurar
um provedor LLM compativel em `.env`.
