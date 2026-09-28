import re, webbrowser
from collections import Counter
import fitz

AI_URLS = {
    "ChatGPT": "https://chatgpt.com/",
    "Claude": "https://claude.ai/",
    "Gemini": "https://gemini.google.com/",
}
STOP = {"the","and","for","with","from","this","that","what","why","how","paper",
        "study","does","are","was","were","논문","관련","대해","무엇","어떻게","정리"}

def _pdf_text(path, max_chars=100000):
    try:
        doc=fitz.open(path); out=[]; n=0
        for i,page in enumerate(doc):
            t=page.get_text("text").strip()
            if t:
                s=f"\n--- Page {i+1} ---\n{t}"; out.append(s); n+=len(s)
            if n>=max_chars: break
        doc.close()
        return "".join(out)[:max_chars]
    except Exception as e:
        return f"[PDF extraction failed: {e}]"

def _excerpt(text, question, max_chars=16000):
    keys=[w for w,_ in Counter(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[가-힣]{2,}",
        question.lower())).most_common(15) if w not in STOP]
    blocks=re.split(r"\n\s*\n|(?=--- Page \d+ ---)", text)
    ranked=sorted([(sum(b.lower().count(k) for k in keys)+(0.2 if i<5 else 0),i,b)
                   for i,b in enumerate(blocks)], key=lambda x:(-x[0],x[1]))
    picked=[]; total=0
    for score,i,b in ranked:
        if score<=0 and picked: continue
        b=b.strip()
        if not b: continue
        b=b[:max_chars-total]; picked.append((i,b)); total+=len(b)
        if total>=max_chars: break
    return "\n\n".join(b for _,b in sorted(picked))

def build_prompt(p, question, metadata=True, abstract=True, pdf=True, notes=False):
    x=["You are helping me analyze a scientific paper.",
       "Use only the supplied paper context for factual claims about this paper. "
       "Distinguish the paper's claims from your interpretation. If context is insufficient, say so.",
       f"\nQUESTION:\n{question.strip()}"]
    if metadata:
        x += ["\nPAPER METADATA:",
              f"Title: {p['title']}", f"Authors: {p['authors']}",
              f"Journal: {p['journal']}", f"Year: {p['year']}", f"DOI: {p['doi']}"]
    if abstract and p["abstract"]: x += ["\nABSTRACT:", p["abstract"]]
    if notes and p["notes"]: x += ["\nMY NOTES:", p["notes"]]
    if pdf:
        ex=_excerpt(_pdf_text(p["filepath"]), question)
        if ex: x += ["\nRELEVANT LOCAL PDF EXCERPTS:", ex]
    x += ["\nAnswer concisely first, then give supporting details. Cite page markers when available."]
    return "\n".join(x)

def open_ai(provider):
    if provider in AI_URLS: webbrowser.open(AI_URLS[provider])
