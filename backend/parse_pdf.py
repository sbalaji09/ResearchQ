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

# removes repeated headers and footers from pages
# detects headers/footers by finding lines that appear on most pages (with optional page number variation)
def remove_repeated_headers_footers(pages_text: list[str], header_lines: int = 2, footer_lines: int = 2):
    import re

    if not pages_text or len(pages_text) < 2:
        return pages_text

    # this function normalizes the lines by removing page numbers and extra whitespace to compare lines across pages
    def normalize_line(line: str) -> str:
        # removes page nubmers
        normalized = re.sub(r'^\d+$', '', line.strip())

        # removes other numbers at the end of lines
        normalized = re.sub(r'\s+\d+\s*$', '', normalized)
        return normalized.strip()

    # checks if a line looks like a header or a standalone page number
    def is_likely_header_or_page_number(line: str) -> bool:
        stripped = line.strip()
        if re.match(r'^\d+$', stripped):
            return True
        return False

    # analyze pages 2+ to find the common header
    header_patterns: dict[str, int] = {}

    for page_text in pages_text[1:]:
        lines = page_text.splitlines()
        for line in lines[:header_lines]:
            normalized = normalize_line(line)
            if normalized:
                header_patterns[normalized] = header_patterns.get(normalized, 0) + 1

    # a pattern is considered to be a header if it appears on most pages
    num_pages_to_check = len(pages_text) - 1
    threshold = num_pages_to_check * 0.5

    common_headers = {pattern for pattern, count in header_patterns.items() if count >= threshold}

    cleaned_pages: list[str] = []

    for page_idx, page_text in enumerate(pages_text):
        lines = page_text.splitlines()

        # remove the headers for the pages
        if page_idx > 0:
            lines_to_remove = 0
            for i, line in enumerate(lines[:header_lines + 1]):
                normalized = normalize_line(line)
                # remove the line if it matches a common header
                if normalized in common_headers or is_likely_header_or_page_number(line):
                    lines_to_remove = i + 1
                else:
                    break
            lines = lines[lines_to_remove:]

        cleaned_pages.append("\n".join(lines))
        print(f"[DEBUG] Cleaned page {page_idx+1}: {len(lines)} lines")

    return cleaned_pages

def main():
    pdf_path = Path("test_papers/research_paper.pdf")

    if not pdf_path.exists():
        raise FileNotFoundError(f"Could not find {pdf_path}. Make sure the PDF is in the same folder")
    
    pages_text = extract_text_from_pdf(pdf_path)

    pages_text_no_hf = remove_repeated_headers_footers(pages_text)

    full_text = "\n\n=== PAGE BREAK ===\n\n".join(pages_text_no_hf)

    print("\n--- Preview of extracted text (first 1000 characters) ---\n")
    print(full_text[:1000])
    print("\n--- End of preview ---\n")

    output_path = Path("paper_extracted.txt")
    output_path.write_text(full_text, encoding="utf-8")
    print(f"Saved full extracted text to {output_path.resolve()}")

if __name__ == "__main__":
    main()