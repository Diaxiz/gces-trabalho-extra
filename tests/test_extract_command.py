import json
from pathlib import Path

from src.processing.extract import load_chunk_rows


def test_load_chunk_rows_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "chunks.jsonl"
    path.write_text(
        json.dumps({"page_number": 1, "is_candidate": True, "text": "VGV"}) + "\n",
        encoding="utf-8",
    )

    rows = load_chunk_rows(path)

    assert rows == [{"page_number": 1, "is_candidate": True, "text": "VGV"}]
