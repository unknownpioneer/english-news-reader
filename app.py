import streamlit as st
import feedparser
import trafilatura
import requests
from bs4 import BeautifulSoup
import re

# =========================
# SESSION STATE
# =========================
if "selected_article" not in st.session_state:
    st.session_state.selected_article = None


# =========================
# RSS FETCH
# =========================
def get_articles_from_rss(rss_url, source_name, limit=5):
    feed = feedparser.parse(rss_url)
    articles = []

    for entry in feed.entries[:limit]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "source": source_name
        })

    return articles


# =========================
# ARTICLE EXTRACTION
# =========================
def extract_clean_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)

        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text) > 200:
                return text

        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")

        return soup.get_text("\n")

    except Exception as e:
        return f"⚠️ Error: {e}"


# =========================
# SIMPLE CLEANING
# =========================
def clean_text(text):
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
        "contributed to this story"
    ]

    cleaned = []

    for line in lines:
        line = line.strip()

        if len(line) < 3:
            continue

        line_lower = line.lower()

        if any(item in line_lower for item in blacklist):
            continue

        # Remove image captions
        if re.search(
            r"\.\s*/(xinhua|cgtn|reuters|ap|afp|vcg)\s*$",
            line,
            re.IGNORECASE
        ):
            continue

        if line_lower.startswith(("photo:", "image:", "credit:")):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)
    # Additional regex cleaning
    patterns = [
        r"By continuing to browse.*?browser\.",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    return text


# =========================
# UI
# =========================
st.title("📚 Multi-Source Reader")

sources = {
    "🇬🇧BBC News": {
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "default": True
    },
    "🇬🇧The Guardian": {
        "url": "https://www.theguardian.com/world/rss",
        "default": True
    },
    "🇺🇸The National Public Radio":{
        "url": "https://feeds.npr.org/1001/rss.xml",
        "default": True
    },
    "🇺🇸Newsletter": {
        "url": "https://www.newsweek.com/rss",
        "default": True
    },
    "the CNBC": {
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "default": True
    },
    "🇦🇺Inside Story (Australia)": {
        "url": "https://insidestory.org.au/feed/",
        "default": True
    },
    "🇨🇳The CGTN (World)": {
        "url": "https://www.cgtn.com/subscribe/rss/section/world.xml",
        "default": True
    },
    "🇨🇳The CGTN (Politics)": {
        "url": "https://www.cgtn.com/subscribe/rss/section/politics.xml",
        "default": True
    },
    "🇨🇳The CGTN (China)": {
        "url": "https://www.cgtn.com/subscribe/rss/section/china.xml",
        "default": False
    },
    "🇮🇹La Repubblica (Italy)": {
        "url": "https://www.repubblica.it/rss/homepage/rss2.0.xml",
        "default": False   # 👈 disabled by default (as requested)
    },
}

selected_sources = []

st.sidebar.header("📰 Sources")

for name, data in sources.items():
    if st.sidebar.checkbox(name, value=data["default"]):
        selected_sources.append((name, data["url"]))

limit = st.sidebar.slider("Articles per source", 1, 10, 5)


# =========================
# FETCH ARTICLES
# =========================
if st.button("📥 Fetch Articles"):
    all_articles = []

    for name, url in selected_sources:
        all_articles += get_articles_from_rss(url, name, limit)

    st.session_state.articles = all_articles
    st.success(f"Loaded {len(all_articles)} articles")


# =========================
# DISPLAY ARTICLES
# =========================
if "articles" in st.session_state:

    articles = st.session_state.articles

    source_filter = st.selectbox(
        "Filter by source",
        ["All"] + list(set(a["source"] for a in articles))
    )

    if source_filter != "All":
        articles = [a for a in articles if a["source"] == source_filter]

    for i, a in enumerate(articles):

        # ✅ REVERTED: use RSS title only
        st.markdown(f"### 🗞️ {a['title']}")
        st.caption(a["source"])

        if st.button(f"📖 Read {i}", key=f"read_{i}"):
            st.session_state.selected_article = a["link"]

        # =========================
        # ARTICLE VIEW
        # =========================
        if st.session_state.selected_article == a["link"]:

            raw_text = extract_clean_text(a["link"])
            text = clean_text(raw_text)

            st.subheader("📄 Article")

            font_size = st.slider("📖 Text size", 14, 26, 18, key=f"font_{i}")

            st.markdown(
                f"""
                <div style="
                    font-size:{font_size}px;
                    line-height:1.8;
                    padding:12px;
                    background-color:#1e1e1e;
                    border-radius:10px;
                    color:#f5f5f5;
                    white-space:pre-wrap;
                ">
                    {text}
                </div>
                """,
                unsafe_allow_html=True
            )
