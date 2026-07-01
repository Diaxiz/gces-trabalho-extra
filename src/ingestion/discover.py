from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.ingestion.sources import DEFAULT_TERMS, SOURCES, CompanySource


REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; gces-uda-pipeline/0.1; "
        "+https://github.com/unb-Sistemas-de-Machine-learning)"
    )
}
PERIOD_RE = re.compile(r"\b([1-4])\s*[TQ]\s*(20)?(\d{2})\b", re.IGNORECASE)
PDF_URL_RE = re.compile(r"\.pdf(?:$|[?#])", re.IGNORECASE)


@dataclass(frozen=True)
class DocumentCandidate:
    company: str
    ticker: str | None
    title: str
    url: str
    source_url: str
    year: int | None
    quarter: int | None
    matched_terms: tuple[str, ...]


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: str) -> str:
    value = strip_accents(value)
    return " ".join(value.lower().split())


def infer_period(
    *texts: str,
    default_year: int | None = None,
    default_quarter: int | None = None,
) -> tuple[int | None, int | None]:
    for text in texts:
        match = PERIOD_RE.search(strip_accents(text))
        if match:
            quarter = int(match.group(1))
            year_suffix = int(match.group(3))
            year = year_suffix if year_suffix >= 100 else 2000 + year_suffix
            return year, quarter
    return default_year, default_quarter


def matched_terms(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    normalized = normalize_text(text)
    return tuple(term for term in terms if normalize_text(term) in normalized)


def looks_like_pdf(url: str) -> bool:
    parsed_path = urlparse(url).path
    return bool(PDF_URL_RE.search(parsed_path)) or "mzfilemanager" in url.lower()


def candidate_title(raw_title: str, url: str) -> str:
    title = " ".join(raw_title.split())
    if title:
        return title

    filename = urlparse(url).path.rsplit("/", 1)[-1]
    filename = filename.replace("-", " ").replace("_", " ")
    return filename or "Documento candidato"


def build_candidate(
    source: CompanySource,
    title: str,
    url: str,
    context: str,
    period_hint: str = "",
) -> DocumentCandidate:
    year, quarter = infer_period(
        title,
        url,
        context,
        period_hint,
        default_year=source.default_year,
        default_quarter=source.default_quarter,
    )
    terms = matched_terms(f"{title} {url} {context}", source.preferred_terms or DEFAULT_TERMS)
    return DocumentCandidate(
        company=source.company,
        ticker=source.ticker,
        title=candidate_title(title, url),
        url=url,
        source_url=source.source_url,
        year=year,
        quarter=quarter,
        matched_terms=terms,
    )


def page_period_hint(soup: BeautifulSoup, source: CompanySource) -> str:
    text = soup.get_text(" ", strip=True)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    year, quarter = infer_period(title, text, default_year=source.default_year, default_quarter=source.default_quarter)
    if year and quarter:
        return f"{quarter}T{str(year)[-2:]}"
    if year:
        return str(year)
    return ""


def extract_anchor_candidates(soup: BeautifulSoup, source: CompanySource, base_url: str) -> list[DocumentCandidate]:
    candidates: list[DocumentCandidate] = []
    period_hint = page_period_hint(soup, source)
    terms = source.preferred_terms or DEFAULT_TERMS

    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor["href"])
        title = anchor.get_text(" ", strip=True)
        parent_text = anchor.parent.get_text(" ", strip=True) if anchor.parent else ""
        context = f"{title} {parent_text} {href}"
        term_matches = matched_terms(context, terms)

        if not looks_like_pdf(href):
            continue
        if not term_matches:
            continue

        candidates.append(build_candidate(source, title, href, context, period_hint))

    return candidates


def extract_table_candidates(soup: BeautifulSoup, source: CompanySource, base_url: str) -> list[DocumentCandidate]:
    candidates: list[DocumentCandidate] = []
    terms = source.preferred_terms or DEFAULT_TERMS

    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True) for cell in table.find_all("th")]
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            row_title = cells[0].get_text(" ", strip=True)
            row_context = row.get_text(" ", strip=True)
            if not matched_terms(row_title, terms) and not matched_terms(row_context, terms):
                continue

            for index, cell in enumerate(cells[1:], start=1):
                anchor = cell.find("a", href=True)
                if not anchor:
                    continue
                href = urljoin(base_url, anchor["href"])
                if not looks_like_pdf(href):
                    continue
                header = headers[index] if index < len(headers) else ""
                title = f"{row_title} {header}".strip()
                candidates.append(build_candidate(source, title, href, row_context, header))

    return candidates


def discover_direct_pdf(source: CompanySource) -> list[DocumentCandidate]:
    return [
        build_candidate(
            source,
            title=source.source_url.rsplit("/", 1)[-1],
            url=source.source_url,
            context=" ".join(source.preferred_terms),
        )
    ]


def fetch_html(source: CompanySource, client: httpx.Client) -> BeautifulSoup:
    response = client.get(source.source_url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def deduplicate(candidates: list[DocumentCandidate]) -> list[DocumentCandidate]:
    seen: set[str] = set()
    unique: list[DocumentCandidate] = []
    for candidate in candidates:
        key = candidate.url
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def discover_source(source: CompanySource, client: httpx.Client | None = None) -> list[DocumentCandidate]:
    if source.source_type == "direct_pdf":
        return discover_direct_pdf(source)

    close_client = client is None
    active_client = client or httpx.Client(
        follow_redirects=True,
        headers=REQUEST_HEADERS,
        timeout=httpx.Timeout(20.0),
    )
    try:
        soup = fetch_html(source, active_client)
        candidates = extract_table_candidates(soup, source, source.source_url)
        candidates.extend(extract_anchor_candidates(soup, source, source.source_url))
        return deduplicate(candidates)
    finally:
        if close_client:
            active_client.close()


def discover_all(sources: tuple[CompanySource, ...] = SOURCES) -> list[DocumentCandidate]:
    candidates: list[DocumentCandidate] = []
    with httpx.Client(
        follow_redirects=True,
        headers=REQUEST_HEADERS,
        timeout=httpx.Timeout(20.0),
    ) as client:
        for source in sources:
            try:
                candidates.extend(discover_source(source, client))
            except httpx.HTTPError as exc:
                print(f"[WARN] Falha ao consultar {source.company}: {exc}")
    return deduplicate(candidates)


def candidate_to_dict(candidate: DocumentCandidate) -> dict[str, object]:
    data = asdict(candidate)
    data["matched_terms"] = list(candidate.matched_terms)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Lista documentos candidatos nas fontes de RI.")
    parser.add_argument("--json", action="store_true", help="Imprime a saida como JSON.")
    args = parser.parse_args()

    candidates = discover_all()
    if args.json:
        print(json.dumps([candidate_to_dict(candidate) for candidate in candidates], indent=2))
        return

    if not candidates:
        print("Nenhum documento candidato encontrado.")
        return

    for candidate in candidates:
        period = "-"
        if candidate.year and candidate.quarter:
            period = f"{candidate.quarter}T{str(candidate.year)[-2:]}"
        elif candidate.year:
            period = str(candidate.year)
        print(f"{candidate.company} | {period} | {candidate.title} | {candidate.url}")


if __name__ == "__main__":
    main()
