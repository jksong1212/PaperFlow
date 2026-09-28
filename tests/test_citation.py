import pytest

from paperflow.citation import available_styles, format_references


def test_styles():
    assert "Nature" in available_styles()
    assert "European Heart Journal" in available_styles()


@pytest.mark.parametrize("style", available_styles())
def test_all_listed_styles_render(style):
    paper = {
        "id": 1,
        "filename": "example.pdf",
        "title": "Example title",
        "authors": "Jane Doe; John Smith",
        "journal": "Test Journal",
        "year": "2024",
        "volume": "1",
        "issue": "2",
        "pages": "1-3",
        "doi": "10.1234/example",
    }
    references = format_references([paper], style)
    assert len(references) == 1
    assert "Example title" in references[0]
