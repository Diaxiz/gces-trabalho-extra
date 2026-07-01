from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompanySource:
    company: str
    ticker: str | None
    ri_url: str
    source_url: str
    source_type: str = "html"
    preferred_terms: tuple[str, ...] = field(default_factory=tuple)
    default_year: int | None = None
    default_quarter: int | None = None
    notes: str | None = None


DEFAULT_TERMS = (
    "previa operacional",
    "pre-operacional",
    "operational preview",
    "release de resultados",
    "earnings release",
    "1t26",
    "1q26",
    "3t25",
)


SOURCES: tuple[CompanySource, ...] = (
    CompanySource(
        company="MRV",
        ticker="MRVE3",
        ri_url="https://ri.mrv.com.br/",
        source_url="https://ri.mrv.com.br/informacoes-financeiras/central-de-resultados/",
        preferred_terms=DEFAULT_TERMS,
        notes="Pagina de RI cadastrada; alguns arquivos podem depender de carregamento dinamico.",
    ),
    CompanySource(
        company="Direcional",
        ticker="DIRR3",
        ri_url="https://ri.direcional.com.br/",
        source_url="https://ri.direcional.com.br/informacoes-financeiras/central-de-resultados/",
        preferred_terms=DEFAULT_TERMS,
    ),
    CompanySource(
        company="Tenda",
        ticker="TEND3",
        ri_url="https://ri.tenda.com/",
        source_url="https://ri.tenda.com/informacoes-financeiras/central-de-resultados",
        preferred_terms=DEFAULT_TERMS,
        default_year=2026,
    ),
    CompanySource(
        company="Boletim Conjuntura",
        ticker=None,
        ri_url=(
            "https://github.com/unb-Sistemas-de-Machine-learning/"
            "Projetos-Individuais-2026-1/tree/main/projeto-individual-4"
        ),
        source_url=(
            "https://raw.githubusercontent.com/unb-Sistemas-de-Machine-learning/"
            "Projetos-Individuais-2026-1/main/projeto-individual-4/"
            "exemplo_Boletim_Conjuntura_2025_3T.pdf"
        ),
        source_type="direct_pdf",
        preferred_terms=("boletim", "conjuntura", "3t25"),
        default_year=2025,
        default_quarter=3,
    ),
)
