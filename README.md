# Projeto Individual 4 - Pipeline UDA para PDFs de RI

Este projeto implementara, em fases, um pipeline de UDA (Unstructured Data Analysis) para coletar, catalogar, processar e servir dados estruturados extraidos de PDFs de Relacoes com Investidores de incorporadoras/construtoras.

O foco da entrega e demonstrar uma arquitetura robusta para documentos com layouts variados, mantendo idempotencia por hash, contrato semantico para a extracao por LLM, catalogo com linhagem e API REST para consulta dos dados.

## Escopo atual

As fases 1 a 9 criam a estrutura inicial, documentam a arquitetura, implementam o catalogo local em SQLite, listam documentos candidatos em fontes de RI, baixam/catalogam PDFs com idempotencia por SHA-256, extraem chunks por pagina/secao, definem o contrato semantico, integram um cliente LLM configuravel e persistem metricas validadas com linhagem. Ainda nao ha API.

Estrutura criada:

```text
.
|-- data/
|   |-- processed/
|   `-- raw/
|-- docs/
|-- src/
|-- tests/
|-- .env.example
|-- .gitignore
|-- pyproject.toml
`-- README.md
```

## Stack planejada

- Python 3.11+
- FastAPI para a API REST
- SQLite e SQLAlchemy para catalogo local e linhagem
- httpx e BeautifulSoup para descoberta leve de PDFs
- PyMuPDF para parsing de PDFs
- Pydantic para contrato semantico
- Cliente LLM configuravel por variavel de ambiente
- pytest para testes automatizados

## Camadas previstas

1. Ingestao de dados: descoberta de PDFs em paginas de RI, download, hash SHA-256 e controle de duplicidade.
2. Processamento UDA: parsing/chunking de PDFs e extracao semantica por LLM com saida estruturada.
3. Servico/API: endpoints REST para consultar metricas por empresa, ano e trimestre, preservando linhagem.

## Configuracao inicial

Crie um ambiente virtual e instale as dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Copie `.env.example` para `.env` quando as proximas fases precisarem de configuracao local. O arquivo `.env` real nao deve ser versionado.

## Validacao da Fase 1

```bash
python --version
```

Tambem confira se as pastas `src/`, `tests/`, `data/raw/`, `data/processed/` e `docs/` existem.

## Validacao da Fase 3

Inicialize o catalogo local:

```bash
python -m src.db
```

No Windows, se `python` apontar para o atalho da Microsoft Store, use:

```powershell
py -m src.db
```

Execute os testes:

```bash
pytest
```

## Validacao da Fase 4

Liste candidatos descobertos nas fontes cadastradas:

```bash
python -m src.ingestion.discover
```

No Windows, se necessario:

```powershell
py -m src.ingestion.discover
```

Para saida estruturada em JSON:

```powershell
py -m src.ingestion.discover --json
```

## Validacao da Fase 5

Baixe e catalogue os documentos descobertos:

```powershell
py -m src.ingestion.run
```

Para demonstrar idempotencia, rode o mesmo comando duas vezes. Na segunda execucao, documentos ja registrados pelo mesmo SHA-256 devem aparecer com status `skipped_duplicate`.

Durante testes rapidos, limite a quantidade de downloads:

```powershell
py -m src.ingestion.run --limit 2
```

## Validacao da Fase 6

Extraia texto dos PDFs catalogados e gere chunks em `data/processed/`:

```powershell
py -m src.processing.parse_pdf
```

Para processar apenas um documento:

```powershell
py -m src.processing.parse_pdf --document-id 1
```

Os arquivos gerados seguem o formato `document_<id>_<sha>_chunks.jsonl` e incluem pagina, texto, tamanho aproximado, termos candidatos e metadados de linhagem do documento.

## Validacao da Fase 7

O contrato semantico fica em `src/contracts/extraction.py` e o prompt versionado em `src/prompts/extraction_v1.md`.

Execute:

```powershell
py -m pytest tests/test_extraction_contract.py
```

O contrato rejeita campos extras, versao de prompt incorreta, JSON incompleto e valores numericos sem unidade/moeda. Valores ausentes devem ser representados como `null`.

## Validacao da Fase 8

Por padrao, `.env.example` usa `LLM_PROVIDER=mock`, entao o fluxo roda sem chave de API:

```powershell
py -m src.processing.extract --document-id 1
```

Para modo real, configure `.env` com `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL` e `LLM_API_KEY`. A resposta do provedor deve ser JSON validavel por `MetricExtraction`; JSON invalido falha antes de qualquer persistencia.

## Validacao da Fase 9

Persistir a extracao validada no catalogo:

```powershell
py -m src.processing.extract --document-id 1 --persist
```

Consultar metricas persistidas:

```powershell
py -m src.catalog.show_metrics
```

O modo mock registra a execucao e atualiza o documento como `processed`, mas nao cria metricas reais. Com um provedor LLM real configurado, metricas validadas entram em `extracted_metrics` com `document_id`, URL/hash do PDF, pagina e trecho-fonte.
