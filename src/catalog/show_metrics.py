from __future__ import annotations

from sqlalchemy import select

from src.db import SessionLocal
from src.models import Document, ExtractedMetric


def main() -> None:
    with SessionLocal() as session:
        metrics = session.scalars(
            select(ExtractedMetric).join(Document).order_by(ExtractedMetric.id)
        ).all()
        if not metrics:
            print("Nenhuma metrica extraida foi encontrada.")
            return

        for metric in metrics:
            document = metric.document
            print(
                " | ".join(
                    [
                        f"id={metric.id}",
                        metric.company.name,
                        metric.metric_name,
                        str(metric.value),
                        metric.unit or "-",
                        f"{metric.period_year}T{metric.period_quarter}",
                        f"page={metric.page_number}",
                        document.sha256[:12],
                        document.pdf_url,
                    ]
                )
            )


if __name__ == "__main__":
    main()
