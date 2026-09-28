POPULAR_STYLES={"APA 7th":"apa","Vancouver":"vancouver","Nature":"nature","IEEE":"ieee","AMA":"american-medical-association","Cell":"cell","Science":"science","The Lancet":"the-lancet","European Heart Journal":"european-heart-journal","Circulation":"circulation"}

def available_styles(): return list(POPULAR_STYLES)

def _authors(raw):
    out=[]
    for n in [x.strip() for x in (raw or "").split(";") if x.strip()]:
        b=n.split(); out.append({"literal":n} if len(b)<2 else {"given":" ".join(b[:-1]),"family":b[-1]})
    return out

def _item(p):
    d={"id":str(p["id"]),"type":"article-journal","title":p["title"] or p["filename"]}
    if p["authors"]: d["author"]=_authors(p["authors"])
    if p["journal"]: d["container-title"]=p["journal"]
    if p["volume"]: d["volume"]=str(p["volume"])
    if p["issue"]: d["issue"]=str(p["issue"])
    if p["pages"]: d["page"]=str(p["pages"])
    if p["doi"]: d["DOI"]=p["doi"]
    try:
        if p["year"]: d["issued"]={"date-parts":[[int(str(p["year"])[:4])]]}
    except ValueError: pass
    return d

def format_references(papers,display_style):
    from citeproc import Citation,CitationItem,CitationStylesBibliography,CitationStylesStyle,formatter
    from citeproc.source.json import CiteProcJSON
    from citeproc_styles import get_style_filepath
    source=CiteProcJSON([_item(p) for p in papers])
    style=CitationStylesStyle(get_style_filepath(POPULAR_STYLES[display_style]),validate=False)
    bib=CitationStylesBibliography(style,source,formatter.plain)
    for p in papers: bib.register(Citation([CitationItem(str(p["id"]))]))
    return ["".join(map(str,e)) for e in bib.bibliography()]
