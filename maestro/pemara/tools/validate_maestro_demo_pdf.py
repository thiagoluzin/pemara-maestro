from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader


DEFAULT_PDF = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "demonstracao"
    / "MAESTRO_PRO_WORKFLOW_COMPLETO_DEMONSTRACAO_20260818.pdf"
)

REQUIRED = [
    "MAESTRO PRO",
    "Workflow de produção em 10 etapas",
    "PRECISION",
    "HunyuanVideo-Foley XXL",
    "404B4B0A693ACE82E9F1A608083CEE9A7F1BFE76AA1B75E9D1455A62158519AE",
    "IA produz candidatos; o proprietário aprova.",
]

FORBIDDEN = [
    "ELEVENLABS_API_KEY=",
    "NVIDIA_API_KEY=",
    "GOOGLE_OAUTH_ACCESS_TOKEN=",
    "MAESTRO_ADMIN_PASSWORD=",
]


def validate(pdf_path: Path) -> dict[str, object]:
    reader = PdfReader(str(pdf_path))
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    all_text = "\n".join(page_texts)
    result = {
        "path": str(pdf_path),
        "pages": len(reader.pages),
        "bytes": pdf_path.stat().st_size,
        "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest().upper(),
        "metadata": {str(key): str(value) for key, value in (reader.metadata or {}).items()},
        "required": {value: value in all_text for value in REQUIRED},
        "forbidden": {value: value in all_text for value in FORBIDDEN},
        "charsPerPage": [len(text) for text in page_texts],
    }
    required_ok = all(result["required"].values())
    forbidden_ok = not any(result["forbidden"].values())
    pages_ok = len(reader.pages) >= 12 and all(len(text) >= 80 for text in page_texts[1:])
    result["ok"] = required_ok and forbidden_ok and pages_ok
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida o PDF demonstrativo do Maestro.")
    parser.add_argument("pdf", nargs="?", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()
    result = validate(args.pdf.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
