"""
Enhanced Resume & Document Extraction Engine.
Supports:
- PDF (.pdf) with vector text extraction + Tesseract OCR fallback for scanned pages
- Modern Word (.docx) via python-docx (unpacking OpenXML)
- Legacy Word (.doc) via win32com Word automation (Windows) + pure-Python OLE2 text recovery fallback (Linux/Docker)
- Plain Text (.txt, .md, .csv)
- Rich Text Format (.rtf)
- OpenDocument Text (.odt) via zip XML extraction
- Configurable max file size (default 10 MB, no minimum barrier)
- Format sniffing via magic bytes to prevent misnamed extension crashes
"""
import io
import os
import re
import tempfile
import zipfile
from typing import Tuple, Optional
import xml.etree.ElementTree as ET

# PyMuPDF for high-speed PDF parsing
try:
    import fitz
except ImportError:
    fitz = None

# python-docx for modern OpenXML Word documents
try:
    from docx import Document
except ImportError:
    Document = None

# pytesseract for OCR fallback on scanned PDFs
try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

# win32com for native Windows Word extraction
try:
    import win32com.client as win32
except ImportError:
    win32 = None

DEFAULT_MAX_FILE_SIZE_MB = 10.0


def detect_file_format(file_bytes: bytes, filename: str) -> str:
    """Detect file format using magic bytes first, falling back to extension."""
    ext = os.path.splitext(filename.lower())[1]

    # Magic byte inspections
    if file_bytes.startswith(b"%PDF-"):
        return "pdf"
    if file_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "doc"
    if file_bytes.startswith(b"PK\x03\x04"):
        # Could be .docx or .odt
        if ext == ".odt":
            return "odt"
        return "docx"
    if file_bytes.startswith(b"{\\rtf"):
        return "rtf"

    # Fallback to extension
    if ext in [".pdf"]:
        return "pdf"
    if ext in [".docx"]:
        return "docx"
    if ext in [".doc"]:
        return "doc"
    if ext in [".txt", ".text", ".md", ".markdown", ".csv"]:
        return "txt"
    if ext in [".rtf"]:
        return "rtf"
    if ext in [".odt"]:
        return "odt"

    return "unknown"


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF with automatic OCR fallback if pages are scanned images."""
    if not fitz:
        raise ValueError("PyMuPDF (fitz) is not installed.")

    text_parts = []
    scanned_pages = []

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc[page_num]
            txt = page.get_text()
            if txt and len(txt.strip()) > 30:
                text_parts.append(txt.strip())
            else:
                # Potential scanned/image page
                scanned_pages.append(page)

        # If digital text extraction yielded almost nothing and we have pages, attempt OCR fallback
        total_extracted = "\n\n".join(text_parts).strip()
        if len(total_extracted) < 100 and scanned_pages and pytesseract and Image:
            for page in scanned_pages:
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text.strip():
                    text_parts.append(ocr_text.strip())
            total_extracted = "\n\n".join(text_parts).strip()

        doc.close()
        return total_extracted
    except Exception as e:
        raise ValueError(f"Error parsing PDF document: {str(e)}")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text and tables from modern .docx files."""
    if not Document:
        raise ValueError("python-docx is not installed.")

    try:
        doc = Document(io.BytesIO(file_bytes))
        parts = [para.text for para in doc.paragraphs if para.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts).strip()
    except Exception as e:
        raise ValueError(f"Error parsing DOCX document: {str(e)}")


def extract_ole2_stream_text(file_bytes: bytes) -> str:
    """Cross-platform pure-Python text recovery from binary OLE2 Compound File (.doc)."""
    # Extract UTF-16LE strings (primary for Word documents)
    utf16_matches = re.findall(b"(?:[\x20-\x7e]\x00){4,}", file_bytes)
    utf16_text = [m.decode("utf-16le", errors="ignore").strip() for m in utf16_matches]

    # Extract ASCII strings
    ascii_matches = re.findall(b"[\x20-\x7e\n\r\t]{5,}", file_bytes)
    ascii_text = [m.decode("latin1", errors="ignore").strip() for m in ascii_matches]

    # Choose the representation with richer readable content
    utf16_len = sum(len(x) for x in utf16_text)
    ascii_len = sum(len(x) for x in ascii_text)
    primary = utf16_text if utf16_len >= ascii_len else ascii_text

    cleaned_lines = []
    for line in primary:
        # Strip OLE formatting noise
        line = re.sub(r'HYPERLINK\s+"[^"]*"\s*\\h', '', line).strip()
        if len(line) >= 2 and not line.startswith("Normal.") and not line.startswith("Heading"):
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def extract_text_from_doc(file_bytes: bytes) -> str:
    """Extract text from legacy .doc via fast pure-Python OLE2 text recovery with Word COM fallback."""
    # Attempt 1: Fast pure-Python OLE2 stream recovery (Instant, non-blocking, cross-platform)
    extracted = extract_ole2_stream_text(file_bytes)
    if extracted and len(extracted) > 50:
        return extracted

    # Attempt 2: Word COM Automation on Windows if OLE stream recovery was insufficient
    if win32 is not None:
        temp_doc_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp:
                tmp.write(file_bytes)
                temp_doc_path = tmp.name

            word = win32.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False
            doc = word.Documents.Open(os.path.abspath(temp_doc_path), ReadOnly=True)
            text = doc.Content.Text
            doc.Close(False)
            word.Quit()
            if text and len(text.strip()) > 30:
                return text.strip()
        except Exception:
            pass
        finally:
            if temp_doc_path and os.path.exists(temp_doc_path):
                try:
                    os.remove(temp_doc_path)
                except Exception:
                    pass

    if extracted and len(extracted) > 10:
        return extracted

    raise ValueError("Could not extract readable text from legacy .doc file. Please re-save as .docx or .pdf.")


def extract_text_from_rtf(file_bytes: bytes) -> str:
    """Extract text from RTF content."""
    text_content = file_bytes.decode("latin1", errors="ignore")
    # Remove RTF control sequences
    clean = re.sub(r"\\[a-zA-Z0-9]+(-?\d+)?\s?", " ", text_content)
    clean = re.sub(r"[{}]", " ", clean)
    lines = [l.strip() for l in clean.splitlines() if l.strip()]
    return "\n".join(lines).strip()


def extract_text_from_odt(file_bytes: bytes) -> str:
    """Extract text from OpenDocument Text (.odt) zip XML."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            content_xml = z.read("content.xml")
            tree = ET.fromstring(content_xml)
            paragraphs = []
            for elem in tree.iter():
                if elem.tag.endswith("p") or elem.tag.endswith("h"):
                    text = "".join(elem.itertext()).strip()
                    if text:
                        paragraphs.append(text)
            return "\n".join(paragraphs).strip()
    except Exception as e:
        raise ValueError(f"Error parsing ODT file: {str(e)}")


def extract_resume_text(uploaded_file, max_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB) -> Tuple[str, str]:
    """
    Unified entry point for resume text extraction.
    Validates file size, determines true format via magic bytes, extracts text,
    and returns (extracted_text, detected_format).
    """
    if uploaded_file is None:
        raise ValueError("No file uploaded.")

    content = uploaded_file.getvalue()
    size_mb = len(content) / (1024 * 1024)

    # 1. Size Validation
    if len(content) == 0:
        raise ValueError("The uploaded file is empty (0 bytes). Please upload a valid document.")
    if size_mb > max_size_mb:
        raise ValueError(f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of {max_size_mb:.1f} MB.")

    # 2. Format Sniffing
    detected_fmt = detect_file_format(content, uploaded_file.name)

    # 3. Extraction Dispatch
    if detected_fmt == "pdf":
        text = extract_text_from_pdf(content)
    elif detected_fmt == "docx":
        text = extract_text_from_docx(content)
    elif detected_fmt == "doc":
        text = extract_text_from_doc(content)
    elif detected_fmt == "rtf":
        text = extract_text_from_rtf(content)
    elif detected_fmt == "odt":
        text = extract_text_from_odt(content)
    elif detected_fmt == "txt":
        text = content.decode("utf-8", errors="ignore").strip()
    else:
        raise ValueError(
            f"Unsupported format detected for '{uploaded_file.name}'. "
            "Supported formats: PDF (.pdf), Word (.docx, .doc), Plain Text (.txt, .md), RTF (.rtf), OpenDocument (.odt)."
        )

    # 4. Result Validation
    if not text or len(text.strip()) < 20:
        raise ValueError(
            "Extraction completed but insufficient text was found. "
            "If this is a scanned document, please ensure it has legible text or provide a digital copy."
        )

    return text.strip(), detected_fmt.upper()
