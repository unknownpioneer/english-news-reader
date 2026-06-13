import streamlit as st
import feedparser
import trafilatura
import requests
import re
from collections import Counter
from bs4 import BeautifulSoup


# =========================
# SESSION STATE INIT
# =========================
if "selected_article" not in st.session_state:
    st.session_state.selected_article = None

if "saved_words" not in st.session_state:
    st.session_state.saved_words = set()


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

        # fallback
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")

        text = soup.get_text("\n")
        return text

    except Exception as e:
        return f"⚠️ Error: {e}"


# =========================
# CLEAN TEXT
# =========================
def clean_text(text):
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        l = line.lower()

        if any(x in l for x in ["published", "updated", "ago", "subscribe", "share"]):
            continue

        if len(line.strip()) < 3:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


# =========================
# KEY VOCABULARY
# =========================
def extract_keywords(text, top_n=12):
    words = re.findall(r"[a-zA-Z']+", text.lower())
    words = [w for w in words if len(w) > 4]

    freq = Counter(words)
    return freq.most_common(top_n)


# =========================
# TRANSLATION
# =========================
def translate_word(word):
    try:
        url = f"https://api.mymemory.translated.net/get?q={word}&langpair=en|zh"
        res = requests.get(url).json()
        return res["responseData"]["translatedText"]
    except:
        return "Translation error"


# =========================
# QUIZ GENERATOR
# =========================
def generate_quiz(text, n=3):
    sentences = [s.strip() for s in text.split(".") if len(s.split()) > 8]

    if len(sentences) == 0:
        return []

    import random
    picks = random.sample(sentences, min(n, len(sentences)))

    return [
        {
            "question": f"What does this mean?\n\n{p}?",
            "answer": p
        }
        for p in picks
    ]


# =========================
# UI
# =========================
st.title("📚 English News Learning App")

sources = {
    "BBC": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Inside Story": "https://insidestory.org.au/feed/"
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

            raw = extract_clean_text(a["link"])
            text = clean_text(raw)

            st.subheader("📄 Article")

            font_size = st.slider("Text size", 14, 26, 18, key=f"font_{i}")

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
            # KEY VOCABULARY
            # =========================
            st.subheader("🔑 Key Vocabulary")

            keywords = extract_keywords(text)

            for word, freq in keywords:
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"{word} ({freq})")

                with col2:
                    if st.button("➕ Save", key=f"save_{word}_{i}"):
                        st.session_state.saved_words.add(word)

            # =========================
            # SAVED WORDS
            # =========================
            st.subheader("💾 Saved Words")
            st.write(list(st.session_state.saved_words))

            # =========================
            # TRANSLATION
            # =========================
            st.subheader("🌍 Translate Words")

            for word, _ in keywords:
                if st.button(f"{word}", key=f"tr_{word}_{i}"):
                    translation = translate_word(word)
                    st.info(f"{word} → {translation}")

            # =========================
            # QUIZ
            # =========================
            st.subheader("🧠 Quiz")

            quiz = generate_quiz(text)

            for j, q in enumerate(quiz):
                st.write(q["question"])

                if st.button(f"Show answer {j}", key=f"quiz_{i}_{j}"):
                    st.success(q["answer"])
