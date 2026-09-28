import requests

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
            "abstract": m.get("abstract","") or ""
        }
    except Exception:
        return {}
