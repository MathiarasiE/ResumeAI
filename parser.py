import io
import re
from fastapi import UploadFile, HTTPException


URL_PATTERNS = {
    "github": re.compile(
        r"(?:https?://)?(?:www\.)?github\.com/([\w\-]+(?:/[\w\-.]+)?)"
        r"|github[:\s]+([\w\-]+)"
        r"|github\.com/([\w\-]+)",
        re.I
    ),
    "linkedin": re.compile(
        r"(?:https?://)?(?:www\.)?linkedin\.com/in/([\w\-]+)"
        r"|linkedin[:\s]+(?:in/)?([\w\-]+)",
        re.I
    ),
}

FULL_URL_PATTERNS = {
    "github":   re.compile(r"https?://(?:www\.)?github\.com/[\w\-]+(?:/[\w\-.]+)?", re.I),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+", re.I),
}


def extract_links(text: str) -> dict:
    result = {}
    for key, full_pat in FULL_URL_PATTERNS.items():
        m = full_pat.search(text)
        if m:
            result[key] = m.group(0)
            continue
        # Fallback: partial match — reconstruct full URL
        m = URL_PATTERNS[key].search(text)
        if m:
            username = next((g for g in m.groups() if g), None)
            if username:
                if key == "github":
                    result[key] = f"https://github.com/{username}"
                else:
                    result[key] = f"https://linkedin.com/in/{username}"
            else:
                result[key] = None
        else:
            result[key] = None
    return result


async def extract_text(file: UploadFile) -> str:
    content = await file.read()
    filename = file.filename or ""

    if filename.endswith(".pdf"):
        return _parse_pdf(content)
    elif filename.endswith(".docx"):
        return _parse_docx(content)
    elif filename.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{filename}'. Upload a PDF, DOCX, or TXT file."
        )


def _parse_pdf(content: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. Try a text-based PDF.")
        return text
    except ImportError:
        raise HTTPException(status_code=500, detail="pypdf not installed. Run: pip install pypdf")


def _parse_docx(content: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs).strip()
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from DOCX.")
        return text
    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx not installed. Run: pip install python-docx")
