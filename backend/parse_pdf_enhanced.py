from pathlib import Path
from typing import Optional
import logging

# PDF libraries
from pypdf import PdfReader
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from unstructured.partition.pdf import partition_pdf

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