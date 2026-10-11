import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
import re
import html
import logging

from news_reader_core import clean_text, extract_clean_text

# =========================
# SESSION STATE
# =========================
if "selected_article" not in st.session_state:
    st.session_state.selected_article = None

if "articles" not in st.session_state:
    st.session_state.articles = []


# =========================
# RSS FETCH
# =========================
@st.cache_data(ttl=900)
def get_articles_from_rss(rss_url, source_name, limit=5):
    try:
        feed = feedparser.parse(rss_url)

        if getattr(feed, "bozo", False) and getattr(feed, "bozo_exception", None):
            logging.warning("RSS parse warning for %s: %s", source_name, feed.bozo_exception)

        entries = getattr(feed, "entries", []) or []
        articles = []
        seen_links = set()

        for entry in entries[:limit]:
            title = str(getattr(entry, "title", "") or "").strip()
            link = str(getattr(entry, "link", "") or "").strip()

            if not title or not link:
                continue

            normalized_link = link.lower()
            if normalized_link in seen_links:
                continue

            seen_links.add(normalized_link)
            articles.append({
                "title": title,
                "link": link,
                "source": source_name
            })

        return articles

    except Exception:
        logging.exception("Failed to fetch RSS from %s", source_name)
        return []


@st.cache_data(ttl=3600)
def cached_extract_clean_text(url):
    return extract_clean_text(url)


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
    "🇺🇸The National Public Radio": {
        "url": "https://feeds.npr.org/1001/rss.xml",
        "default": True
    },
    "🇺🇸Newsletter": {
        "url": "https://www.newsweek.com/rss",
        "default": True
    },
    "🇺🇸the CNBC": {
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
        "default": False
    },
}

selected_sources = []

st.sidebar.header("📰 Sources")

for name, data in sources.items():
    if st.sidebar.checkbox(name, value=data["default"], key=f"source_{name}"):
        selected_sources.append((name, data["url"]))

limit = st.sidebar.slider("Articles per source", 1, 10, 5)


# =========================
# FETCH ARTICLES
# =========================
if st.button("📥 Fetch Articles"):
    all_articles = []

    for name, url in selected_sources:
        all_articles.extend(get_articles_from_rss(url, name, limit))

    st.session_state.articles = all_articles
    st.session_state.selected_article = None
    st.success(f"Loaded {len(all_articles)} articles")


# =========================
# DISPLAY ARTICLES
# =========================
if "articles" in st.session_state:
    articles = st.session_state.articles

    source_filter = st.selectbox(
        "Filter by source",
        ["All"] + sorted({a["source"] for a in articles})
    )

    if source_filter != "All":
        articles = [a for a in articles if a["source"] == source_filter]

    for i, a in enumerate(articles):
        article_id = re.sub(r"[^A-Za-z0-9_]", "_", a["link"])

        st.markdown(f"### 🗞️ {a['title']}")
        st.caption(a["source"])

        if st.button(f"📖 Read {i}", key=f"read_{article_id}"):
            st.session_state.selected_article = a["link"]

        if st.session_state.selected_article == a["link"]:
            raw_text = cached_extract_clean_text(a["link"])
            text = clean_text(raw_text) if raw_text else ""

            st.subheader("📄 Article")

            if not text:
                st.info("No readable article text could be extracted for this article.")
            else:
                font_size = st.slider("📖 Text size", 14, 26, 18, key=f"font_{article_id}")
                escaped_text = html.escape(text)
                st.markdown(
                    f"""
                    <div style=
                        "font-size:{font_size}px;
                        line-height:1.8;
                        padding:12px;
                        background-color:#1e1e1e;
                        border-radius:10px;
                        color:#f5f5f5;
                        white-space:pre-wrap;"
                    >
                        {escaped_text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
