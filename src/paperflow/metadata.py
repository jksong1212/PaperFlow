from html.parser import HTMLParser

import requests


class _AbstractTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def _break(self):
        if self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")

    def handle_starttag(self, tag, attrs):
        if tag.rsplit(":", 1)[-1] in {"sec", "title", "p", "list-item", "br"}:
            self._break()

    def handle_endtag(self, tag):
        if tag.rsplit(":", 1)[-1] in {"sec", "title", "p", "list-item"}:
            self._break()

    def handle_data(self, data):
        self.parts.append(data)


def plain_abstract(value):
    """Turn a Crossref JATS abstract into readable section and paragraph text."""
    if not value:
        return ""
    if "<" not in value and "&" not in value:
        return value.strip()
    parser = _AbstractTextParser()
    parser.feed(value)
    parser.close()
    return "\n\n".join(
        line for part in "".join(parser.parts).splitlines()
        if (line := " ".join(part.split()))
    )


def crossref_by_doi(doi):
    if not doi:
        return {}
    try:
        r = requests.get("https://api.crossref.org/works/" + doi,
                         timeout=10,
                         headers={"User-Agent":"PaperFlow/0.1 (desktop research tool)"})
        r.raise_for_status()
        m = r.json()["message"]
        authors = []
        for a in m.get("author", []):
            name = " ".join(x for x in [a.get("given",""), a.get("family","")] if x)
            if name: authors.append(name)
        dates = m.get("published-print") or m.get("published-online") or m.get("issued") or {}
        parts = dates.get("date-parts", [[]])
        year = str(parts[0][0]) if parts and parts[0] else ""
        return {
            "title": (m.get("title") or [""])[0],
            "authors": "; ".join(authors),
            "journal": (m.get("container-title") or [""])[0],
            "year": year,
            "volume": m.get("volume",""),
            "issue": m.get("issue",""),
            "pages": m.get("page",""),
            "doi": m.get("DOI", doi),
            "abstract": plain_abstract(m.get("abstract", ""))
        }
    except Exception:  # noqa: BLE001 - remote metadata is optional
        return {}
