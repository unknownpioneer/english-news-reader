import streamlit as st
import feedparser
import trafilatura
import requests
import re
from collections import Counter
from bs4 import BeautifulSoup


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
# EXTRACT ARTICLE TEXT
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
# KEY WORDS (FOR HIGHLIGHTING)
# =========================
def extract_keywords(text, top_n=12):
    words = re.findall(r"[a-zA-Z']+", text.lower())
    words = [w for w in words if len(w) > 4]

    freq = Counter(words)
    return [w for w, _ in freq.most_common(top_n)]


# =========================
# HIGHLIGHT FUNCTION
# =========================
def highlight_text(text, keywords):
    def replacer(match):
        word = match.group(0)
        if word.lower() in keywords:
            return f"<mark style='background-color:#ffd54f;padding:2px;border-radius:4px'>{word}</mark>"
        return word

    pattern = re.compile(r"[a-zA-Z']+")
    return pattern.sub(replacer, text)


# =========================
# UI
# =========================
st.title("📚 English News Reader (Highlight Mode)")

sources = {
    "BBC": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "NYTimes": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "CNN": "http://rss.cnn.com/rss/edition.rss"
}

selected_sources = []

st.sidebar.header("📰 Sources")

for name, url in sources.items():
    if st.sidebar.checkbox(name, value=True):
        selected_sources.append((name, url))

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
        st.markdown(f"### 🗞️ {a['title']}")
        st.caption(a["source"])

        if st.button(f"📖 Read {i}", key=f"read_{i}"):
            st.session_state.selected_article = a["link"]

        # =========================
        # ARTICLE VIEW
        # =========================
        if st.session_state.selected_article == a["link"]:

            raw_text = extract_clean_text(a["link"])

            # extract keywords for highlighting
            keywords = extract_keywords(raw_text)

            highlighted = highlight_text(raw_text, keywords)

            font_size = st.slider("📖 Text size", 14, 26, 18, key=f"font_{i}")

            st.markdown(
                f"""
                <div style="
                    font-size:{font_size}px;
                    line-height:1.8;
                    padding:16px;
                    background-color:#1e1e1e;
                    border-radius:12px;
                    color:#f5f5f5;
                    white-space:pre-wrap;
                ">
                {highlighted}
                </div>
                """,
                unsafe_allow_html=True
            )
