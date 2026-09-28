import re
from pathlib import Path

import pymupdf

DOI_RE = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)

def extract_pdf(path):
    p = Path(path)
    title = authors = text = ""
    try:
        doc = pymupdf.open(path)
        meta = doc.metadata or {}
        title = (meta.get("title") or "").strip()
        authors = (meta.get("author") or "").strip()
        # First pages are enough for DOI/initial metadata in the MVP.
        text = "\n".join(page.get_text("text") for page in list(doc)[:3])
        doc.close()
    except Exception:  # noqa: BLE001 - keep filename fallback for unreadable PDFs
        text = ""
    doi = ""
    m = DOI_RE.search(text)
    if m:
        doi = m.group(0).rstrip(".,;)]}")
    if not title or len(title) < 5:
        title = p.stem.replace("_"," ").replace("-"," ")
    return {
        "filepath": str(p.resolve()),
        "filename": p.name,
        "title": title,
        "authors": authors,
        "journal": "", "year": "", "volume": "", "issue": "", "pages": "",
        "doi": doi, "abstract": ""
    }
