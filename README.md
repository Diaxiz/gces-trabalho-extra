# Projeto Individual 4 - Pipeline UDA para PDFs de RI

Pipeline de UDA (Unstructured Data Analysis) para coletar, catalogar, processar
e servir dados estruturados extraidos de PDFs de Relacoes com Investidores de
incorporadoras/construtoras.

O projeto prioriza arquitetura, idempotencia, contrato semantico, linhagem e API.
Nao ha foco em interface grafica.

## O Que Este Projeto Entrega

- Descoberta leve de PDFs em paginas de RI.
- Download e catalogacao local com SHA-256.
- Idempotencia: o mesmo PDF nao e processado duas vezes.
- Parsing com PyMuPDF e chunking por pagina/secao.
- Filtro de chunks candidatos por termos de negocio.
- Contrato Pydantic para validar respostas de LLM.
- Prompt versionado em `src/prompts/extraction_v1.md`.
- Cliente LLM configuravel, com modo `mock` para testes sem chave.
- Persistencia de runs e metricas validadas com linhagem.
- API FastAPI com filtros por empresa, ano e trimestre.
- Testes automatizados para idempotencia, contrato e API.

## Arquitetura Resumida

```text
Fontes RI
  -> descoberta de candidatos
  -> download do PDF
  -> SHA-256 e catalogo SQLite
  -> parsing PyMuPDF
  -> chunks candidatos
  -> LLM configuravel
  -> contrato Pydantic
  -> metricas com linhagem
  -> API FastAPI
```

Camadas obrigatorias:

1. Extracao de dados: descoberta, download, hash e parsing/chunking.
2. Contrato semantico: schemas Pydantic e prompt versionado.
3. Catalogo, linhagem e API: SQLite, runs, metricas e endpoints REST.

Detalhes de arquitetura estao em `docs/arquitetura.md`.

## Estrutura

```text
.
|-- data/
|   |-- processed/
|   `-- raw/
|-- docs/
|   |-- arquitetura.md
|   `-- evidencias.md
|-- src/
|   |-- api/
|   |-- catalog/
|   |-- contracts/
|   |-- ingestion/
|   |-- llm/
|   |-- processing/
|   `-- prompts/
|-- tests/
|-- .env.example
|-- pyproject.toml
`-- README.md
```

## Instalacao

Python recomendado: 3.11+.

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

Copie `.env.example` para `.env` se for configurar variaveis locais. O arquivo
`.env` real nao deve ser versionado.

## Variaveis De Ambiente

Padrao seguro para rodar sem chave externa:

```text
APP_ENV=development
DATABASE_URL=sqlite:///data/processed/catalog.db
LLM_PROVIDER=mock
LLM_MODEL=gpt-4.1-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
INGESTION_INTERVAL_HOURS=24
```

Para LLM real, configure `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL` e
`LLM_API_KEY`.

## Como Rodar

Inicializar banco:

```powershell
py -m src.db
```

Descobrir candidatos:

```powershell
py -m src.ingestion.discover
```

Baixar e catalogar PDFs:

```powershell
py -m src.ingestion.run
```

Demonstrar idempotencia:

```powershell
py -m src.ingestion.run
py -m src.ingestion.run
```

Na segunda execucao, documentos ja catalogados aparecem como
`skipped_duplicate`.

Extrair chunks dos PDFs:

```powershell
py -m src.processing.parse_pdf
```

Executar extracao semantica em modo mock:

```powershell
py -m src.processing.extract --document-id 1
```

Persistir uma run validada:

```powershell
py -m src.processing.extract --document-id 1 --persist
```

Consultar metricas persistidas:

```powershell
py -m src.catalog.show_metrics
```

Rodar testes:

```powershell
py -m pytest
```

## API

Subir servidor:

```powershell
py -m uvicorn src.api.main:app --reload
```

Endpoints:

```text
GET /health
GET /api/empresas
GET /api/documentos
GET /api/metricas
GET /api/conjuntura?empresa=Direcional&ano=2026&trimestre=1
```

Exemplo de resposta de `/api/conjuntura` quando ha metrica persistida:

```json
{
  "filters": {
    "empresa": "Direcional",
    "ano": 2026,
    "trimestre": 1
  },
  "count": 1,
  "metrics": [
    {
      "id": 1,
      "company": "Direcional",
      "metric_name": "vgv lancado",
      "period_year": 2026,
      "period_quarter": 1,
      "value": 1005.8,
      "unit": "R$ milhoes",
      "currency": "BRL",
      "page_number": 2,
      "source_excerpt": "VGV Lancado (VGV 100%) 1.005,8",
      "confidence": 0.92,
      "document": {
        "id": 1,
        "title": "Previa Operacional",
        "pdf_url": "https://example.com/previa.pdf",
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "year": 2026,
        "quarter": 1,
        "status": "processed"
      }
    }
  ]
}
```

No banco local atual, o modo `mock` registra a execucao mas nao gera metricas
reais. Com LLM real configurado, metricas validadas entram em
`extracted_metrics` e aparecem nesses endpoints.

## Evidencias

Evidencias de documentos, layouts, chunks e linhagem estao em
`docs/evidencias.md`.

Resumo local ja validado:

- 3 empresas/fonte no catalogo.
- 5 documentos catalogados.
- 5 arquivos de chunks gerados.
- 1 run de extracao mock registrada.
- 31 testes automatizados passando.

## Pontos De Avaliacao Cobertos

- Ingestao automatizavel por comando agendavel.
- Idempotencia por SHA-256 antes de custo de LLM.
- Chunking sem coordenadas fixas de PDF.
- Contrato Pydantic com `null` para ausentes.
- Prompt exigindo valores absolutos e ignorando percentuais de marketing quando
  nao forem a metrica principal.
- Linhagem por documento, URL, SHA-256, pagina e trecho-fonte.
- API filtravel por empresa, ano e trimestre.
