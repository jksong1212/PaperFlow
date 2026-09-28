from paperflow.metadata import crossref_by_doi, plain_abstract

JATS_ABSTRACT = """
<jats:sec xml:lang="en">
  <jats:title>Background</jats:title>
  <jats:p>Estimation of oxygen <jats:italic>supply</jats:italic> &amp; demand.</jats:p>
</jats:sec>
<jats:sec xml:lang="en">
  <jats:title>Conclusions</jats:title>
  <jats:p>Carotid tonometry provides valid noninvasive SEVR values.</jats:p>
</jats:sec>
"""


def test_jats_abstract_preserves_sections_and_paragraphs():
    assert plain_abstract(JATS_ABSTRACT) == (
        "Background\n\n"
        "Estimation of oxygen supply & demand.\n\n"
        "Conclusions\n\n"
        "Carotid tonometry provides valid noninvasive SEVR values."
    )


def test_crossref_metadata_stores_plain_abstract(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"title": ["Sample"], "abstract": JATS_ABSTRACT}}

    monkeypatch.setattr("paperflow.metadata.requests.get", lambda *args, **kwargs: Response())
    result = crossref_by_doi("10.1234/sample")
    assert result["abstract"].startswith("Background\n\nEstimation")
    assert "<jats:" not in result["abstract"]
