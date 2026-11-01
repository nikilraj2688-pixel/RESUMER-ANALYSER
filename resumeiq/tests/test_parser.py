import os
import pytest
from resumeiq.app.services.parser import parse_resume, ParserError

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def test_parse_docx_success():
    path = os.path.join(FIXTURES_DIR, "sample_swe.docx")
    with open(path, "rb") as f:
        bytes_data = f.read()
    res = parse_resume("sample_swe.docx", bytes_data)
    assert res["extension"] == ".docx"
    assert "Alex Johnson" in res["text"]
    assert "FastAPI" in res["text"]
    assert res["word_count"] > 50

def test_parse_pdf_success():
    path = os.path.join(FIXTURES_DIR, "sample_ds.pdf")
    with open(path, "rb") as f:
        bytes_data = f.read()
    res = parse_resume("sample_ds.pdf", bytes_data)
    assert res["extension"] == ".pdf"
    assert "Maya Patel" in res["text"]
    assert "PyTorch" in res["text"]
    assert res["page_count"] >= 1

def test_parse_invalid_extension():
    with pytest.raises(ParserError) as exc_info:
        parse_resume("test.exe", b"binary content here")
    assert "Unsupported file type" in str(exc_info.value)

def test_parse_empty_file():
    with pytest.raises(ParserError) as exc_info:
        parse_resume("empty.pdf", b"")
    assert "empty" in str(exc_info.value)

