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