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

# looks at the first page to find the header and footer and then removes it from every next page
def remove_repeated_headers_footers(pages_text: list[str], header_lines: int = 2, footer_lines: int = 2):
    if not pages_text:
        return pages_text
    
    first_page_lines = pages_text[0].splitlines()

    header_candidate = first_page_lines[:header_lines]

    footer_candidate = first_page_lines[-footer_lines:] if footer_lines > 0 else []

    cleaned_pages: list[str] = []

    for page_idx, page_text in enumerate(pages_text):
        lines = page_text.splitlines()

        if header_candidate and lines[:header_lines] == header_candidate:
            lines = lines[header_lines:]
        
        if footer_candidate and lines[-footer_candidate:] == footer_candidate:
            lines = lines[:footer_lines]
        
        cleaned_pages.append("\n".join(lines))

        print(f"[DEBUG] Cleaned page {page_idx+1}: {len(lines)} lines")
    
    return cleaned_pages