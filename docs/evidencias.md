# Evidencias Da Execucao

Este arquivo registra evidencias da execucao local do pipeline ate a Fase 12.
Os dados abaixo foram produzidos com os comandos documentados no README.

## Fontes E PDFs Usados

| Documento | Empresa/Fonte | Periodo | Layout | URL |
| --- | --- | --- | --- | --- |
| Previa Operacional | Direcional | 1T26 | Comunicado/previa operacional multi-pagina | https://api.mziq.com/mzfilemanager/v2/d/ada9bc2c-f7d0-4359-9eaf-851b679ab788/b9e3e792-da8b-5e49-f50f-4c097cf08623?origin=2 |
| Release de Resultados | Direcional | 1T26 | Release/apresentacao multi-pagina | https://api.mziq.com/mzfilemanager/v2/d/ada9bc2c-f7d0-4359-9eaf-851b679ab788/44d38c37-baad-14bd-442e-10af6efc7c91?origin=2 |
| Release de Resultados 1T26 | Tenda | 1T26 | Release/apresentacao multi-pagina | https://ri.tenda.com/docs/Press-release-Tenda-2026-03-31-B6TLLD8z.pdf |
| Previa Operacional 1T26 | Tenda | 1T26 | Previa operacional multi-pagina | https://ri.tenda.com/docs/Press-release-Tenda-2026-03-31-gmDwJCdg.pdf |
| Boletim Conjuntura 2025 3T | Boletim Conjuntura | 3T25 | Boletim/tabela de uma pagina | https://raw.githubusercontent.com/unb-Sistemas-de-Machine-learning/Projetos-Individuais-2026-1/main/projeto-individual-4/exemplo_Boletim_Conjuntura_2025_3T.pdf |

Dois layouts diferentes ficam cobertos claramente:

- boletim/tabela de uma pagina: Boletim Conjuntura 2025 3T;
- documentos RI multi-pagina: previas/releases de Direcional e Tenda.

## Catalogo Local

Consulta local do catalogo:

```text
companies 3
documents 5
runs 1
metrics 0
```

Documentos registrados:

```text
1 Direcional Previa Operacional 2026 1 processed 8ee867bab353
2 Direcional Release de Resultados 2026 1 downloaded 61a3ca5f9635
3 Tenda Release de Resultados 1T26 2026 1 downloaded 74fad5ff2d0d
4 Tenda Previa Operacional 1T26 2026 1 downloaded f0c7dc571a0e
5 Boletim Conjuntura exemplo_Boletim_Conjuntura_2025_3T.pdf 2025 3 downloaded e53f30f5f67e
```

Observacao: `metrics 0` e esperado no modo `mock`; ele valida o fluxo sem chamar
LLM real. Com LLM real configurado, metricas validadas sao persistidas em
`extracted_metrics`.

## Idempotencia

Comando:

```powershell
py -m src.ingestion.run
py -m src.ingestion.run
```

Comportamento esperado na segunda execucao:

```text
skipped_duplicate | Direcional | 8ee867bab353...
skipped_duplicate | Direcional | 61a3ca5f9635...
skipped_duplicate | Tenda | 74fad5ff2d0d...
skipped_duplicate | Tenda | f0c7dc571a0e...
skipped_duplicate | Boletim Conjuntura | e53f30f5f67e...
```

Os testes tambem cobrem o caso em que duas URLs diferentes retornam exatamente o
mesmo conteudo. Nesse caso, o SHA-256 impede duplicidade no banco e no arquivo
local.

## Chunking Gerado

Arquivos gerados em `data/processed/`:

```text
document_1_8ee867bab353_chunks.jsonl Direcional Previa Operacional chunks 8 candidates 7
document_2_61a3ca5f9635_chunks.jsonl Direcional Release de Resultados chunks 34 candidates 25
document_3_74fad5ff2d0d_chunks.jsonl Tenda Release de Resultados 1T26 chunks 32 candidates 25
document_4_f0c7dc571a0e_chunks.jsonl Tenda Previa Operacional 1T26 chunks 8 candidates 6
document_5_e53f30f5f67e_chunks.jsonl Boletim Conjuntura chunks 1 candidates 1
```

Cada linha JSONL contem:

- `document_id`;
- empresa;
- titulo;
- URL do PDF;
- SHA-256;
- pagina;
- indice do chunk;
- texto;
- tamanho aproximado;
- flag `is_candidate`;
- termos candidatos encontrados.

Exemplo resumido:

```json
{
  "document_id": 1,
  "company": "Direcional",
  "title": "Previa Operacional",
  "pdf_url": "https://api.mziq.com/...",
  "sha256": "8ee867bab353cab109eff2124dee9b2f7fe9e6f7ed175807664d756d6ad35ebb",
  "page_number": 2,
  "chunk_index": 1,
  "is_candidate": true,
  "candidate_terms": ["lancamentos", "vgv", "unidades"]
}
```

## Contrato Semantico

Arquivos principais:

- `src/contracts/extraction.py`
- `src/prompts/extraction_v1.md`

Regras cobertas:

- resposta deve ser JSON validavel;
- valores ausentes devem ser `null`;
- campos extras sao rejeitados;
- versao de prompt incorreta e rejeitada;
- valor numerico precisa de unidade ou moeda;
- metrica duplicada com mesma linhagem e rejeitada;
- cada metrica deve ter pagina e trecho-fonte.

## API E Linhagem

Endpoint principal:

```text
GET /api/conjuntura?empresa=Direcional&ano=2026&trimestre=1
```

Quando existem metricas persistidas, cada item retorna a metrica e o documento
de origem:

```json
{
  "metric_name": "vgv lancado",
  "period_year": 2026,
  "period_quarter": 1,
  "value": 1005.8,
  "unit": "R$ milhoes",
  "page_number": 2,
  "source_excerpt": "VGV Lancado (VGV 100%) 1.005,8",
  "document": {
    "id": 1,
    "title": "Previa Operacional",
    "pdf_url": "https://example.com/previa.pdf",
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
}
```

Assim, para cada numero servido pela API, e possivel responder:

- de qual empresa veio;
- de qual PDF veio;
- qual e o hash do PDF;
- em qual pagina apareceu;
- qual trecho sustentou a extracao.

## Testes

Comando:

```powershell
py -m pytest
```

Resultado local:

```text
31 passed
```

Cobertura principal:

- schema do banco;
- descoberta de PDFs;
- idempotencia por SHA-256;
- parsing/chunking;
- contrato Pydantic;
- cliente LLM mock e validacao de JSON;
- persistencia de runs/metricas;
- filtros e linhagem da API.
