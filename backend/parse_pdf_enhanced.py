from collections import defaultdict
from pathlib import Path
from typing import Optional
import logging

# PDF libraries
from pypdf import PdfReader
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from unstructured.partition.pdf import partition_pdf

from parse_pdf import extract_text_from_pdf

# Configure logger for this module
logger = logging.getLogger("ingest")
logger.setLevel(logging.DEBUG)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Format logs nicely
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# Avoid double handlers if reload happens
if not logger.handlers:
    logger.addHandler(console_handler)

def detect_pdf_type(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        num_pages = len(reader.pages)

        if num_pages == 0:
            logger.warning(f"{pdf_path.name}: PDF has no pages - defaulting to scanned")
            return "scanned"

        pages_to_check = min(3, num_pages)
        min_chars = 100

        total_extracted_chars = 0

        for i in range(pages_to_check):
            page = reader.pages[i]
            extracted = page.extract_text() or ""
            total_extracted_chars += len(extracted)

            logger.debug(f"{pdf_path.name}: Page {i+1} extracted {len(extracted)} chars")

        avg_chars_per_page = total_extracted_chars / pages_to_check

        logger.info(f"{pdf_path.name}: Avg extracted chars per checked page = {avg_chars_per_page:.1f}")

        if avg_chars_per_page < min_chars:
            return "scanned"
        else:
            return "text-based"
        
    except Exception as e:
        logger.error(f"Failed to ingest PDF {pdf_path.name}: {e}")
        return "scanned"

# this function extracts text from a PDF using Unstructured, grouped by page
def extract_with_unstructured(pdf_path: Path) -> list[str]:
    elements = partition_pdf(
        filename=str(pdf_path),
        strategy="hi_res",
        infer_table_structure=True,
    )

    pages_dict: dict[int, list[str]] = defaultdict(list)

    for el in elements:
        page_num = getattr(el, "page_number", 1) or 1
        pages_dict[page_num].append(str(el))
    
    if not pages_dict:
        logger.warning(f"No elements returned by Unstructured for {pdf_path.name}")
        return []

    max_page = max(pages_dict.keys())
    pages: list[str] = []

    for page in range(1, max_page + 1):
        page_elems = pages_dict.get(page, [])
        page_text = "\n".join(page_elems).strip()
        pages.append(page_text)

        logger.debug(
            f"{pdf_path.name}: Unstructured page {page} has"
            f" {len(page_elems)} elements, {len(page_text)} chars"
        )

    logger.info(
        f"Unstructured extraction complete for {pdf_path.name}"
        f" ({len(pages)} pages of text)"
    )

    return pages

# this function reads the actual image of the page and returns a list of strings with each one representing a page
def extract_with_ocr(pdf_path: Path) -> list[str]:
    images = convert_from_path(pdf_path, dpi=300)
    str_list = []

    for img in images:
        img_str: str = pytesseract.image_to_string(img)
        img_str = img_str.strip()
        str_list.append(img_str)
    
    return str_list

# this function extracts tables from the pdf
def extract_tables_from_page(pdf_path: Path, page_num: int) -> list[str]:
    tables_as_strings = []

    with pdfplumber.open(pdf_path) as pdf:
        if page_num < 0 or page_num >= len(pdf.pages):
            raise ValueError(f"Page number {page_num} out of range.")

        page = pdf.pages[page_num]
        tables = page.extract_tables() or []

        for table in tables:
            formatted_rows = [" | ".join(cell if cell is not None else "" for cell in row) for row in table]

            table_str = "\n".join(formatted_rows)
            tables_as_strings.append(table_str)
    
    return tables_as_strings

def extract_text_from_pdf_enhanced(pdf_path: Path) -> list[str]:
    pdf_type = detect_pdf_type(pdf_path)
    
    if pdf_type == "scanned":
        return extract_with_ocr(pdf_path)
    
    try:
        return extract_with_unstructured(pdf_path)
    except Exception as e:
        logging.warning(f"Unstructured failed: {e}, falling back to pypdf")
    
    return extract_text_from_pdf(pdf_path)

