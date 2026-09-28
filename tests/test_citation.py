from paperflow.citation import available_styles

def test_styles():
    assert "Nature" in available_styles()
    assert "European Heart Journal" in available_styles()
