import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document


# ---------- Article extraction ----------
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


def extract_clean_text(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    doc = Document(response.text)
    html = doc.summary()

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")

    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)

    return cleaned


# ---------- UI ----------
st.title("📚 Multi-Source English News Reader")

st.sidebar.header("📰 News Sources")

# Predefined sources (you can edit/add more)
sources = {
    "NYTimes World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "CNN Top Stories": "http://rss.cnn.com/rss/edition.rss",
    "Inside Story": "https://insidestory.org.au/feed/"
}

selected_sources = []

for name in sources:
    if st.sidebar.checkbox(name, value=True):
        selected_sources.append((name, sources[name]))

limit = st.sidebar.slider("Articles per source", 1, 10, 5)


# ---------- Load articles ----------
if st.button("Fetch Articles"):
    all_articles = []

    with st.spinner("Fetching from multiple sources..."):
        for name, url in selected_sources:
            articles = get_articles_from_rss(url, name, limit)
            all_articles.extend(articles)

    st.success(f"Loaded {len(all_articles)} articles")

    # ---------- Filter by source ----------
    source_filter = st.selectbox(
        "Filter by source",
        ["All"] + list(set(a["source"] for a in all_articles))
    )

    if source_filter != "All":
        all_articles = [a for a in all_articles if a["source"] == source_filter]

    # ---------- Display articles ----------
    for i, article in enumerate(all_articles):
        st.markdown(f"### 🗞️ {article['title']}")
        st.caption(f"Source: {article['source']}")

        if st.button(f"Read Article {i}", key=i):
            with st.spinner("Extracting content..."):
                text = extract_clean_text(article["link"])

            st.text_area(
                "Article Content",
                text[:4000],
                height=400,
                key=f"text_{i}"
            )

            st.download_button(
                "Download Article",
                text,
                file_name=article["title"][:40] + ".txt",
                key=f"download_{i}"
            )

        st.divider()