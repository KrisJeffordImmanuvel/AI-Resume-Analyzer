import pytest

from parsing import (
    MAX_UPLOAD_BYTES,
    ParseError,
    clean_jd_text,
    extract_jd_file_text,
    extract_resume_text,
    normalize_text,
)
from tests.helpers import make_blank_pdf, make_docx, make_pdf


def test_pdf_resume_text_is_extracted():
    text = extract_resume_text("cv.pdf", make_pdf(["Jane Doe", "Built APIs with Python and Docker"]))
    assert "Jane Doe" in text
    assert "Python and Docker" in text


def test_docx_resume_includes_paragraphs_and_tables():
    data = make_docx(["Jane Doe", "Backend engineer"], table=[["Skills", "Python, SQL"]])
    text = extract_resume_text("cv.docx", data)
    assert "Backend engineer" in text
    assert "Skills | Python, SQL" in text


@pytest.mark.parametrize(
    "data",
    [
        "Café résumé – Python".encode(),
        "Café résumé – Python".encode("utf-8-sig"),
        "Café résumé – Python".encode("utf-16"),
        "Café résumé – Python".encode("cp1252"),
    ],
    ids=["utf-8", "utf-8-bom", "utf-16", "windows-1252"],
)
def test_txt_resume_decodes_common_windows_encodings(data):
    assert extract_resume_text("cv.txt", data) == "Café résumé – Python"


def test_extension_check_is_case_insensitive():
    assert "Python" in extract_resume_text("CV.TXT", b"Python")


def test_old_doc_format_is_rejected_with_advice():
    with pytest.raises(ParseError) as err:
        extract_resume_text("cv.doc", b"whatever")
    assert err.value.status == 415
    assert ".docx" in err.value.message


@pytest.mark.parametrize("name", ["cv.png", "cv.rtf", "cv"])
def test_unsupported_resume_types_are_rejected(name):
    with pytest.raises(ParseError) as err:
        extract_resume_text(name, b"data")
    assert err.value.status == 415


def test_scanned_or_blank_pdf_gives_clear_error():
    with pytest.raises(ParseError) as err:
        extract_resume_text("cv.pdf", make_blank_pdf())
    assert err.value.status == 422
    assert "scanned" in err.value.message


def test_corrupt_pdf_gives_clear_error():
    with pytest.raises(ParseError) as err:
        extract_resume_text("cv.pdf", b"not really a pdf")
    assert err.value.status == 422


def test_corrupt_docx_gives_clear_error():
    with pytest.raises(ParseError):
        extract_resume_text("cv.docx", b"not really a docx")


def test_empty_file_is_rejected():
    with pytest.raises(ParseError):
        extract_resume_text("cv.txt", b"")


def test_oversized_file_is_rejected():
    with pytest.raises(ParseError) as err:
        extract_resume_text("cv.txt", b"a" * (MAX_UPLOAD_BYTES + 1))
    assert err.value.status == 413


@pytest.mark.parametrize("name", ["jd.pdf", "jd.docx", "jd.md"])
def test_job_description_files_must_be_txt(name):
    with pytest.raises(ParseError) as err:
        extract_jd_file_text(name, b"Python")
    assert err.value.status == 415


def test_job_description_txt_and_paste_are_accepted():
    assert extract_jd_file_text("jd.txt", b"Need Python") == "Need Python"
    assert clean_jd_text("  Need\r\nPython  ") == "Need\nPython"


def test_blank_pasted_job_description_is_rejected():
    with pytest.raises(ParseError):
        clean_jd_text("   \n  ")


def test_normalize_collapses_spaces_but_keeps_lines():
    assert normalize_text("a \t b\r\n\r\n\r\n\r\nc d") == "a b\n\nc d"
