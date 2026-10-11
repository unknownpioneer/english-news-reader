import re

UNNECESSARY_LINE_PATTERNS = [
    r"^published(?:\s+on|\s+at)?\s+.*$",
    r"^updated(?:\s+on|\s+at)?\s+.*$",
    r"^last updated(?:\s+on|\s+at)?\s+.*$",
    r"^posted\s+.*$",
    r"^\d+\s*(?:min|mins|minute|minutes)\s+read$",
    r"^reading time\s*:\s*.*$",
    r"^estimated reading time\s*:\s*.*$",
    r"^listen to this article.*$",
    r"^follow us on.*$",
    r"^share this.*$",
    r"^read more.*$",
]


def clean_text(text):
    if not text:
        return ""

    text = re.sub(
        r"By continuing to browse.*?browser\.",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    lines = text.split("\n")
    blacklist = [
        "privacy policy",
        "terms of use",
        "cookie settings",
        "use of cookies",
        "subscribe",
        "newsletter",
        "share this",
        "related articles",
        "contributed to this story",
        "WATCH:",
    ]

    cleaned = []
    for line in lines:
        line = line.strip()
        if len(line) < 3:
            continue

        line_lower = line.lower()

        if any(item in line_lower for item in blacklist):
            continue

        if any(re.match(pattern, line, flags=re.IGNORECASE) for pattern in UNNECESSARY_LINE_PATTERNS):
            continue

        if re.search(r"\.\s*/(xinhua|cgtn|reuters|ap|afp|vcg)\s*$", line, re.IGNORECASE):
            continue

        if line_lower.startswith(("photo:", "image:", "credit:")):
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def extract_clean_text(url):
    import requests
    from bs4 import BeautifulSoup
    import trafilatura

    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text.strip()) > 200:
                return text

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower() and "application/xhtml+xml" not in content_type.lower():
            return None

        response.encoding = response.apparent_encoding or "utf-8"
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text("\n")
        return text.strip() or None

    except requests.RequestException:
        return None
    except Exception:
        return None
