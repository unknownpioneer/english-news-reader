import streamlit as st
import feedparser
import trafilatura
import requests
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
# TITLE + BODY SPLIT (NEW)
# =========================
def extract_title_and_body(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    junk_keywords = ["bbc", "share", "image", "listen", "watch", "subscribe"]

    title = "Article"

    for line in lines:
        if not any(j in line.lower() for j in junk_keywords):
            title = line
            break

    body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    return title, body


# =========================
# SIMPLE CLEANING
# =========================
def clean_text(text):
    lines = text.split("\n")
    return "\n".join([l for l in lines if len(l.strip()) > 2])


# =========================
# UI
# =========================
st.title("📚 Multi-Source Reader")

sources = {
    "🇬🇧BBC News": {
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "default": True
    },
    "🇬🇧The Guardian":
    {
        "url": "https://www.theguardian.com/world/rss",
        "default": True
    },
    "🇦🇺Inside Story (Australia)": {
        "url": "https://insidestory.org.au/feed/",
        "default": True   # 👈 IMPORTANT: unchecked by default
    },
    "🇮🇹Repubblica": {
        "url": "https://www.repubblica.it/rss/homepage/rss2.0.xml",
        "default": False
    }
    
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

            # ✨ NEW: title + body split
            article_title, article_body = extract_title_and_body(text)

            st.subheader("📄 Article")

            font_size = st.slider("📖 Text size", 14, 26, 18, key=f"font_{i}")

            # 📰 BIG TITLE
            st.markdown(
                f"""
                <div style="
                    font-size:30px;
                    font-weight:700;
                    margin-bottom:12px;
                    line-height:1.3;
                    color:#ffffff;
                ">
                    {article_title}
                </div>
                """,
                unsafe_allow_html=True
            )

            # 📖 BODY TEXT
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
                    {article_body}
                </div>
                """,
                unsafe_allow_html=True
            )
