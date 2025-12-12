from pathlib import Path
from pypdf import PdfReader

# reads a PDF and returns a list of strings, one per page where each string is the cleaned text of that page
def extract_text_from_pdf(pdf_path: Path) -> list[str]:
    reader = PdfReader(pdf_path)

    pages_text: list[str] = []

    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""

        if raw_text == "":
            raise ValueError("The text from the page could not be extracted")
        
        lines = raw_text.splitlines()

        cleaned_lines = [line.strip() for line in lines if line.strip()]

        cleaned_page_text = "\n".join(cleaned_lines)

        pages_text.append(cleaned_page_text)

    return pages_text