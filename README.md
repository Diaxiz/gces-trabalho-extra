# Projeto Individual 4 - Pipeline UDA para PDFs de RI

Este projeto implementara, em fases, um pipeline de UDA (Unstructured Data Analysis) para coletar, catalogar, processar e servir dados estruturados extraidos de PDFs de Relacoes com Investidores de incorporadoras/construtoras.

O foco da entrega e demonstrar uma arquitetura robusta para documentos com layouts variados, mantendo idempotencia por hash, contrato semantico para a extracao por LLM, catalogo com linhagem e API REST para consulta dos dados.

## Escopo da Fase 1

Esta primeira fase cria apenas a estrutura inicial do projeto Python. Ainda nao ha implementacao de crawler, banco de dados, LLM ou API.

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
