from news_reader_core import clean_text


def test_clean_text_removes_blacklist_lines():
    text = "This is an actual article.\nPrivacy Policy\nPhoto: Reuters\nMore content here.\n"
    cleaned = clean_text(text)

    assert "This is an actual article." in cleaned
    assert "Privacy Policy" not in cleaned
    assert "Photo: Reuters" not in cleaned
    assert "More content here." in cleaned


def test_clean_text_removes_browser_notice():
    text = "Before text. By continuing to browse this site you agree to our terms of use. After text."
    cleaned = clean_text(text)

    assert "By continuing to browse" not in cleaned.lower()
    assert "Before text." in cleaned
    assert "After text." in cleaned


def test_clean_text_ignores_short_lines_and_blank_lines():
    text = "A\n\nReal paragraph with content\nX\n"
    cleaned = clean_text(text)

    assert cleaned == "Real paragraph with content"
