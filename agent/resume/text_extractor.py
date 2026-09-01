from pathlib import Path

from pypdf import PdfReader


def extract_text(file_path: str | Path) -> str:
    """
    Extract plain text from a PDF resume.
    """

    reader = PdfReader(file_path)

    pages_text = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages_text.append(text)

    return "\n".join(pages_text).strip()