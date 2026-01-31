import tempfile
from typing import List

import pytesseract
from pdf2image import convert_from_bytes


def ocr_pdf_to_pages(pdf_bytes: bytes, lang: str = "fra") -> List[str]:
    """
    Convertit un PDF image en texte OCR, page par page.
    """
    images = convert_from_bytes(pdf_bytes, dpi=300)
    pages_text = []

    for img in images:
        text = pytesseract.image_to_string(img, lang=lang)
        pages_text.append(text)

    return pages_text
