import streamlit as st
import feedparser
import trafilatura
import requests
import re
from bs4 import BeautifulSoup


# =========================
# SESSION STATE
# =========================
if "selected_article" not in st.session_state:
    st.session_state.selected_article = None

if "selected_word" not in st.session_state:
    st.session_state.selected_word = ""


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
    return "\n".join([l for l in lines if len(l.strip()) > 2])


# =========================
# TRANSLATION (EN → IT / ZH)
# =========================
def translate_word(word, lang="it"):
    try:
        langpair = {
            "it": "en|it",
            "zh": "en|zh",
            "en": "it|en"
        }.get(lang, "en|it")

        url = f"https://api.mymemory.translated.net/get?q={word}&langpair={langpair}"
        res = requests.get(url).json()

        return res["responseData"]["translatedText"]

    except:
        return "Translation failed"


# =========================
# UI
# =========================
st.title("📚 Multi-Source English Reader (BBC + Inside Story)")

sources = {
    "🇬🇧BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "🇦🇺Inside Story (Australia)": "https://insidestory.org.au/feed/",
    "🇮🇹Republicca": "https://www.repubblica.it/rss/homepage/rss2.0.xml",
    "🇬🇧The Guardian": "https://www.theguardian.com/world/rss",
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
            text = clean_text(raw_text)

            st.subheader("📄 Article")

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

            # =========================
            # WORD SELECTION + TRANSLATION
            # =========================
            st.subheader("🖱️ Word Translator")

            target_lang = st.selectbox(
                "Translate to:",
                ["Italian 🇮🇹", "Chinese 🇨🇳", "English ↔ Italian"]
            )

            lang_map = {
                "Italian 🇮🇹": "it",
                "Chinese 🇨🇳": "zh",
                "English ↔ Italian": "en"
            }

            selected_word = st.text_input("Enter a word from the article")

            if selected_word:
                st.session_state.selected_word = selected_word.lower()

            if st.session_state.selected_word:
                word = st.session_state.selected_word
                lang = lang_map[target_lang]

                st.info(f"Word: {word}")

                translation = translate_word(word, lang)
                st.success(f"Translation: {translation}")
