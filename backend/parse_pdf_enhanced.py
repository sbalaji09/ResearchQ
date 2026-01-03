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

from exceptions import *
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

# extract tables from all pages of a PDF
def extract_all_tables(pdf_path: Path) -> dict[int, list[str]]:
    tables_by_page: dict[int, list[str]] = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables() or []
                if tables:
                    formatted_tables = []
                    for table in tables:
                        rows = [" | ".join(cell if cell else "" for cell in row) for row in table]
                        formatted_tables.append("\n".join(rows))
                    tables_by_page[page_num] = formatted_tables
    except Exception as e:
        logger.warning(f"Table extraction failed: {e}")
    
    return tables_by_page

# appends extracted tables to the end of each page's text
def merge_tables_into_pages(pages_text: list[str], tables_by_page: dict[int, list[str]]) -> list[str]:
    merged_pages = []
    
    for page_num, page_text in enumerate(pages_text):
        if page_num in tables_by_page:
            tables_section = "\n\n[TABLES]\n" + "\n\n".join(tables_by_page[page_num])
            merged_pages.append(page_text + tables_section)
        else:
            merged_pages.append(page_text)
    
    return merged_pages

# FAST extraction - uses pypdf first (much faster than unstructured)
def extract_text_from_pdf_fast(pdf_path: Path) -> list[str]:
    """
    Fast PDF text extraction optimized for speed.

    Optimizations:
    - Tries pypdf first without type detection (saves ~100ms)
    - Only falls back to OCR if pypdf extraction is empty/fails
    - Minimal logging
    """
    pages_text = []

    # Try pypdf first - works for most research papers
    try:
        pages_text = extract_text_from_pdf(pdf_path)
        pages_text = validate_extracted_text(pages_text, pdf_path)
        return pages_text
    except NoTextExtractedError:
        # PDF is likely scanned, try OCR
        pass
    except Exception:
        # pypdf failed for other reasons, try OCR
        pass

    # Fallback to OCR for scanned PDFs
    try:
        pages_text = extract_with_ocr(pdf_path)
        pages_text = validate_extracted_text(pages_text, pdf_path)
        return pages_text
    except Exception as e:
        raise PDFParsingError(
            f"Could not extract text from {pdf_path.name}",
            pdf_path.name
        )


# extract text from PDF with multiple fallback strategies (original - slower but more robust)
def extract_text_from_pdf_enhanced(pdf_path: Path) -> list[str]:
    pdf_type = detect_pdf_type(pdf_path)
    pages_text = []
    errors = []

    if pdf_type == "text-based":
        try:
            pages_text = extract_with_unstructured(pdf_path)
            pages_text = validate_extracted_text(pages_text, pdf_path)
            logger.info(f"{pdf_path.name}: Successfully extracted with Unstructured")
        except Exception as e:
            errors.append(f"Unstructued: {e}")
            logger.warning(f"Unstructured failed for {pdf_path.name}: {e}")
            pages_text = []

    if not pages_text and pdf_type == "text-based":
        try:
            pages_text = extract_text_from_pdf(pdf_path)
            pages_text = validate_extracted_text(pages_text, pdf_path)
            logger.info(f"{pdf_path.name}: Successfully extracted with pypdf")
        except Exception as e:
            errors.append(f"pypdf: {e}")
            logger.warning(f"pypdf failed for {pdf_path.name}: {e}")
            pages_text = []

    if not pages_text:
        try:
            logger.info(f"{pdf_path.name}: Attempting OCR extraction...")
            pages_text = extract_with_ocr(pdf_path)
            pages_text = validate_extracted_text(pages_text, pdf_path)
            logger.info(f"{pdf_path.name}: Successfully extracted with OCR")
        except Exception as e:
            errors.append(f"OCR: {e}")
            logger.error(f"OCR failed for {pdf_path.name}: {e}")

    if not pages_text:
        error_details = "; ".join(errors)
        raise PDFParsingError(
            f"All extraction methods failed for {pdf_path.name}. Errors: {error_details}",
            pdf_path.name
        )

    try:
        tables_by_page = extract_all_tables(pdf_path)
        if tables_by_page:
            logger.info(f"Found tables on {len(tables_by_page)} pages, merging...")
            pages_text = merge_tables_into_pages(pages_text, tables_by_page)
    except Exception as e:
        logger.warning(f"Table extraction failed (non-critical): {e}")

    return pages_text

# validates extracted text quality
def validate_extracted_text(pages_text: list[str], pdf_path: Path, min_chars_per_page: int = 50) -> list[str]:
    if not pages_text:
        raise NoTextExtractedError(pdf_path.name)
    
    total_chars = sum(len(page) for page in pages_text)
    non_empty_pages = sum(1 for page in pages_text if len(page.strip()) > min_chars_per_page)

    if total_chars < 100:
        raise NoTextExtractedError(pdf_path.name)

    if non_empty_pages == 0:
        raise NoTextExtractedError(pdf_path.name)

    empty_pages = len(pages_text) - non_empty_pages
    if empty_pages > len(pages_text) * 0.5:
        logger.warning(
            f"{pdf_path.name}: {empty_pages}/{len(pages_text)} pages have little / no text"
        )
    
    return pages_text