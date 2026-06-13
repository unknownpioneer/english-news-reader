import streamlit as st
import feedparser
import trafilatura
import requests
import re
from bs4 import BeautifulSoup


# =========================
# ARTICLE FETCHING (RSS)
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

def clean_article_text(text):
    # split into lines
    lines = text.split("\n")

    cleaned_lines = []

    for line in lines:
        line_lower = line.lower()

        # ❌ filter out metadata / noise
        if (
            "published" in line_lower or
            "updated" in line_lower or
            "ago" in line_lower or
            "share" in line_lower or
            "follow us" in line_lower or
            "sign up" in line_lower
        ):
            continue

        # remove empty junk
        if len(line.strip()) < 3:
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
# =========================
# TEXT EXTRACTION (ROBUST)
# =========================
def extract_clean_text(url):
    try:
        # ---------- METHOD 1: Trafilatura (BEST) ----------
        downloaded = trafilatura.fetch_url(url)

        if downloaded:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False
            )

            if text and len(text.strip()) > 200:
                return text

        # ---------- METHOD 2: FALLBACK ----------
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=15).text

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")

        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n".join(line for line in lines if line)

        if len(cleaned) > 200:
            return cleaned

        return "⚠️ Could not extract readable article text."

    except Exception as e:
        return f"⚠️ Error extracting article:\n{str(e)}"


# =========================
# STREAMLIT UI
# =========================
st.title("📚 Multi-Source English News Reader (Fixed)")

st.sidebar.header("📰 Sources")

sources = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Inside Story": "https://insidestory.org.au/feed/"
}

selected_sources = []

for name in sources:
    if st.sidebar.checkbox(name, value=True):
        selected_sources.append((name, sources[name]))

limit = st.sidebar.slider("Articles per source", 1, 10, 5)


# =========================
# SESSION STATE (IMPORTANT FIX)
# =========================
if "selected_article" not in st.session_state:
    st.session_state.selected_article = None


# =========================
# LOAD ARTICLES
# =========================
if st.button("📥 Fetch Articles"):
    all_articles = []

    with st.spinner("Fetching from sources..."):
        for name, url in selected_sources:
            articles = get_articles_from_rss(url, name, limit)
            all_articles.extend(articles)

    st.session_state.all_articles = all_articles
    st.success(f"Loaded {len(all_articles)} articles")


# =========================
# DISPLAY ARTICLES
# =========================
if "all_articles" in st.session_state:

    all_articles = st.session_state.all_articles

    # Filter
    source_filter = st.selectbox(
        "Filter by source",
        ["All"] + list(set(a["source"] for a in all_articles))
    )

    if source_filter != "All":
        all_articles = [a for a in all_articles if a["source"] == source_filter]

    # Show list
    for i, article in enumerate(all_articles):
        st.markdown(f"### 🗞️ {article['title']}")
        st.caption(f"Source: {article['source']}")

        if st.button(f"📖 Read Article {i}", key=f"btn_{i}"):
            st.session_state.selected_article = article["link"]

        # If selected → show content
        if st.session_state.selected_article == article["link"]:
           with st.spinner("Extracting article..."):
                raw_text = extract_clean_text(article["link"])
                text = clean_article_text(raw_text)

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
              {text}
              </div>
              """,
              unsafe_allow_html=True
          )
            
