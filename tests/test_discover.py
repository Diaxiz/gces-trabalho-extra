from bs4 import BeautifulSoup

from src.ingestion.discover import (
    extract_anchor_candidates,
    extract_table_candidates,
    infer_period,
)
from src.ingestion.sources import SOURCES, CompanySource


def test_required_sources_are_registered() -> None:
    companies = {source.company for source in SOURCES}

    assert "MRV" in companies
    assert "Direcional" in companies
    assert "Boletim Conjuntura" in companies


def test_infer_period_from_pt_and_en_patterns() -> None:
    assert infer_period("Previa Operacional 1T26") == (2026, 1)
    assert infer_period("Operational Preview 3Q25") == (2025, 3)
    assert infer_period("sem periodo", default_year=2026, default_quarter=2) == (2026, 2)


def test_extract_anchor_candidates_from_results_page() -> None:
    source = CompanySource(
        company="Direcional",
        ticker="DIRR3",
        ri_url="https://ri.direcional.com.br/",
        source_url="https://ri.direcional.com.br/informacoes-financeiras/central-de-resultados/",
        preferred_terms=("previa operacional", "1t26"),
    )
    html = """
    <html>
      <body>
        <h2>Resultados 1T26</h2>
        <a href="https://api.mziq.com/mzfilemanager/v2/d/x/y?origin=2">
          Previa Operacional
        </a>
      </body>
    </html>
    """

    candidates = extract_anchor_candidates(
        BeautifulSoup(html, "html.parser"),
        source,
        source.source_url,
    )

    assert len(candidates) == 1
    assert candidates[0].company == "Direcional"
    assert candidates[0].year == 2026
    assert candidates[0].quarter == 1
    assert candidates[0].url.startswith("https://api.mziq.com/")


def test_extract_table_candidates_with_quarter_header() -> None:
    source = CompanySource(
        company="Tenda",
        ticker="TEND3",
        ri_url="https://ri.tenda.com/",
        source_url="https://ri.tenda.com/informacoes-financeiras/central-de-resultados",
        preferred_terms=("previa operacional",),
    )
    html = """
    <table>
      <thead>
        <tr><th></th><th>1T26</th><th>2T26</th></tr>
      </thead>
      <tbody>
        <tr>
          <td>Previa Operacional</td>
          <td><a href="/docs/previa-tenda-1t26.pdf">PDF</a></td>
          <td></td>
        </tr>
      </tbody>
    </table>
    """

    candidates = extract_table_candidates(
        BeautifulSoup(html, "html.parser"),
        source,
        source.source_url,
    )

    assert len(candidates) == 1
    assert candidates[0].title == "Previa Operacional 1T26"
    assert candidates[0].year == 2026
    assert candidates[0].quarter == 1
    assert candidates[0].url == "https://ri.tenda.com/docs/previa-tenda-1t26.pdf"
