import html
import logging
import re

import feedparser
import streamlit as st

from news_reader_core import clean_text, extract_clean_text


# =========================
# SESSION STATE
# =========================
def ensure_session_state():
    defaults = {
        "selected_article": None,
        "articles": [],
        "saved_articles": {},
        "reader_mode": True,
        "focus_mode": False,
        "font_size": 18,
        "line_spacing": 1.75,
        "theme": "Dark",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


ensure_session_state()


# =========================
# HELPERS
# =========================
def safe_article_id(link):
    return re.sub(r"[^A-Za-z0-9_]", "_", link or "article")


@st.cache_data(ttl=3600)
def get_article_preview(url):
    try:
        raw_text = extract_clean_text(url)
        text = clean_text(raw_text) if raw_text else ""
        if not text:
            return "Preview unavailable for this story."
        preview = " ".join(text.split())
        return preview[:200] + ("..." if len(preview) > 200 else "")
    except Exception:
        logging.exception("Failed to generate preview for %s", url)
        return "Preview unavailable for this story."


def get_article_index(link, article_list):
    for idx, article in enumerate(article_list):
        if article["link"] == link:
            return idx
    return -1


def save_article(article):
    saved = st.session_state.saved_articles
    saved[article["link"]] = {
        "title": article["title"],
        "source": article["source"],
        "link": article["link"],
    }
    st.session_state.saved_articles = saved


def unsave_article(link):
    saved = st.session_state.saved_articles
    saved.pop(link, None)
    st.session_state.saved_articles = saved


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
                "source": source_name,
            })

        return articles

    except Exception:
        logging.exception("Failed to fetch RSS from %s", source_name)
        return []


# =========================
# APP SETTINGS
# =========================
st.set_page_config(page_title="Multi-Source Reader", layout="wide")

st.title("📚 Multi-Source Reader")

sources = {
    "🇬🇧BBC News": {"url": "https://feeds.bbci.co.uk/news/rss.xml", "default": True},
    "🇬🇧The Guardian": {"url": "https://www.theguardian.com/world/rss", "default": True},
    "🇺🇸The National Public Radio": {"url": "https://feeds.npr.org/1001/rss.xml", "default": True},
    "🇺🇸Newsletter": {"url": "https://www.newsweek.com/rss", "default": True},
    "🇺🇸the CNBC": {"url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "default": True},
    "🇦🇺Inside Story (Australia)": {"url": "https://insidestory.org.au/feed/", "default": True},
    "🇨🇳The CGTN (World)": {"url": "https://www.cgtn.com/subscribe/rss/section/world.xml", "default": True},
    "🇨🇳The CGTN (Politics)": {"url": "https://www.cgtn.com/subscribe/rss/section/politics.xml", "default": True},
    "🇨🇳The CGTN (China)": {"url": "https://www.cgtn.com/subscribe/rss/section/china.xml", "default": False},
    "🇮🇹La Repubblica (Italy)": {"url": "https://www.repubblica.it/rss/homepage/rss2.0.xml", "default": False},
}

# Sidebar controls
st.sidebar.header("📰 Sources")
selected_sources = []
for name, data in sources.items():
    if st.sidebar.checkbox(name, value=data["default"], key=f"source_{name}"):
        selected_sources.append((name, data["url"]))

st.sidebar.markdown("---")
st.sidebar.subheader("Reading")
st.session_state.reader_mode = st.sidebar.checkbox("Reader mode", value=st.session_state.reader_mode)
st.session_state.focus_mode = st.sidebar.checkbox("Focus mode", value=st.session_state.focus_mode)
st.session_state.theme = st.sidebar.selectbox("Theme", ["Dark", "Light"], index=["Dark", "Light"].index(st.session_state.theme))
st.session_state.font_size = st.sidebar.slider("Font size", 14, 28, st.session_state.font_size)
st.session_state.line_spacing = st.sidebar.slider("Line spacing", 1.2, 2.2, st.session_state.line_spacing, step=0.1)
limit = st.sidebar.slider("Articles per source", 1, 10, 5)

# Updated saved list in sidebar
if st.session_state.saved_articles:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Saved")
    for article in st.session_state.saved_articles.values():
        st.sidebar.caption(f"• {article['source']}: {article['title']}")


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
# ARTICLE LIST / READER
# =========================
if "articles" in st.session_state and st.session_state.articles:
    articles = st.session_state.articles

    source_filter = st.selectbox(
        "Filter by source",
        ["All"] + sorted({a["source"] for a in articles}),
    )
    if source_filter != "All":
        articles = [a for a in articles if a["source"] == source_filter]

    if st.session_state.selected_article is not None:
        current_index = get_article_index(st.session_state.selected_article, articles)
    else:
        current_index = -1

    if st.session_state.reader_mode and st.session_state.selected_article is not None:
        article = next((a for a in articles if a["link"] == st.session_state.selected_article), None)
        if article is not None:
            st.markdown("---")
            st.markdown(f"## 🗞️ {article['title']}")
            st.caption(f"{article['source']}")

            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_a:
                if st.button("← Previous", key="prev_article_reader") and current_index > 0:
                    st.session_state.selected_article = articles[current_index - 1]["link"]
            with col_b:
                link_url = article["link"]
                st.link_button("Open original", link_url)
            with col_c:
                if st.button("Next →", key="next_article_reader") and current_index < len(articles) - 1:
                    st.session_state.selected_article = articles[current_index + 1]["link"]

            if article["link"] in st.session_state.saved_articles:
                if st.button("★ Saved", key=f"save_{safe_article_id(article['link'])}"):
                    unsave_article(article["link"])
            else:
                if st.button("☆ Save article", key=f"save_{safe_article_id(article['link'])}"):
                    save_article(article)

            raw_text = extract_clean_text(article["link"])
            text = clean_text(raw_text) if raw_text else ""
            if not text:
                st.info("No readable article text could be extracted for this article.")
            else:
                bg_col = "#111111" if st.session_state.theme == "Dark" else "#f5f5f5"
                fg_col = "#f5f5f5" if st.session_state.theme == "Dark" else "#111111"
                escaped_text = html.escape(text)
                st.markdown(
                    f"""
                    <div style=
                        "max-width: 1000px;
                        margin: 0 auto;
                        padding: 24px 28px;
                        background-color: {bg_col};
                        border-radius: 14px;
                        color: {fg_col};
                        font-size: {st.session_state.font_size}px;
                        line-height: {st.session_state.line_spacing};
                        white-space: pre-wrap;
                        border: 1px solid rgba(255,255,255,0.08);"
                    >
                        {escaped_text}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.warning("Selected article could not be found in the current list.")

    else:
        st.subheader("Latest stories")
        for i, a in enumerate(articles):
            preview = get_article_preview(a["link"])
            article_id = safe_article_id(a["link"])
            saved = a["link"] in st.session_state.saved_articles

            with st.container(border=True):
                st.markdown(f"### 🗞️ {a['title']}")
                st.caption(f"{a['source']}")
                st.caption(f"{preview}")

                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    if st.button("Read", key=f"read_{article_id}"):
                        st.session_state.selected_article = a["link"]
                with col2:
                    if saved:
                        if st.button("★ Saved", key=f"save_{article_id}"):
                            unsave_article(a["link"])
                    else:
                        if st.button("☆ Save", key=f"save_{article_id}"):
                            save_article(a)
                with col3:
                    st.link_button("Open", a["link"])

                if st.session_state.focus_mode and i == 0:
                    st.caption("Focus mode is on — reading details are shown at the top of the article view.")

else:
    st.info("No articles loaded yet. Choose at least one source and click ‘Fetch Articles’." )
