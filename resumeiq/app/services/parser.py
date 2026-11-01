import os
import io
import re
from typing import Dict, Any, Tuple
import pdfplumber
import docx

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {'.pdf', '.docx'}

class ParserError(Exception):
    """Custom exception for resume file parsing errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def validate_file(filename: str, file_bytes: bytes) -> None:
    """
    Validates file extension and size.
    Raises ParserError if invalid.
    """
    if not filename:
        raise ParserError("No file uploaded or filename missing.", 400)
    
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise ParserError(f"Unsupported file type '{ext}'. Allowed types: PDF, DOCX.", 400)
    
    if len(file_bytes) == 0:
        raise ParserError("Uploaded file is empty (0 bytes).", 400)
        
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ParserError("File exceeds the maximum allowed size of 5 MB.", 400)

def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, int]:
    """
    Extracts text and page count from PDF bytes using pdfplumber.
    Detects scanned/image-only PDFs.
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)
            if page_count == 0:
                raise ParserError("PDF document has 0 pages.", 400)
            
            extracted_pages = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    extracted_pages.append(text)
            
            full_text = "\n\n".join(extracted_pages).strip()
            
            # Scanned PDF check: page count > 0 but extracted text is empty or virtually non-existent
            if not full_text or len(full_text.split()) < 15:
                raise ParserError(
                    "Scanned or image-only PDF detected. Please upload a machine-readable text PDF or Word document.",
                    400
                )
            
            return full_text, page_count
    except ParserError:
        raise
    except Exception as e:
        raise ParserError(f"Failed to process PDF: {str(e)}", 400)

def extract_text_from_docx(file_bytes: bytes) -> Tuple[str, int]:
    """
    Extracts text and paragraph count from DOCX bytes using python-docx.
    """
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
                    
        full_text = "\n".join(paragraphs).strip()
        
        if not full_text or len(full_text.split()) < 15:
            raise ParserError("Word document contains insufficient or empty text.", 400)
            
        # Approximate page count (approx 400 words per page)
        words = len(full_text.split())
        est_pages = max(1, round(words / 400))
        return full_text, est_pages
    except ParserError:
        raise
    except Exception as e:
        raise ParserError(f"Failed to process DOCX file: {str(e)}", 400)

def parse_resume(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    Main parser entrypoint. Validates file, extracts text and metadata.
    Handles non-English text guardrails and minimal content length.
    """
    validate_file(filename, file_bytes)
    
    _, ext = os.path.splitext(filename.lower())
    if ext == '.pdf':
        text, pages = extract_text_from_pdf(file_bytes)
    elif ext == '.docx':
        text, pages = extract_text_from_docx(file_bytes)
    else:
        raise ParserError(f"Unsupported format: {ext}", 400)
        
    # Edge-case checks: Very short resumes
    word_count = len(text.split())
    if word_count < 30:
        raise ParserError("The document is too short to be an informative resume (under 30 words).", 400)
        
    # Non-English check (heuristic: English ASCII/Latin ratio check)
    latin_chars = len(re.findall(r'[a-zA-Z0-9\s.,;:()/\-–—]', text))
    if len(text) > 0 and (latin_chars / len(text)) < 0.60:
        raise ParserError("Resume text appears to be primarily in an unsupported non-Latin/non-English language.", 400)
        
    return {
        "text": text,
        "filename": filename,
        "extension": ext,
        "file_size": len(file_bytes),
        "word_count": word_count,
        "page_count": pages
    }

