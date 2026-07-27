"""News Room: briefing matutino por usuario (RSS + LLM resumen).

Supports 6 summarize styles, conversational follow-ups, and like/interest tracking.
"""
import hashlib
import logging
import os
from datetime import datetime
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("news_room")
_google_ai_creds_cache: Dict = {}


# ─── Style-specific prompt templates ──────────────────────────────────────────
# Each returns (system_prompt, format_instruction) so they can be composed.

def _style_markdown_sections(target_lang: str) -> Tuple[str, str]:
    return (
        f"You are the news briefing agent for KRK-9. "
        f"Generate a structured morning briefing in {target_lang}. "
        f"Be efficient and warm in tone.",
        "Use EXACTLY this markdown structure:\n"
        "## 📰 Top News\n(for each story: **bold title** — source, one sentence on why it matters)\n"
        "## ✅ Suggested Tasks\n(3 actionable checkboxes based on the news)\n"
        "## 🗣️ Vocabulary\n(5 new English words/expressions from the articles, with brief definitions)\n"
        "## 💬 Discussion Questions\n(3 open-ended questions for practice)\n"
    )

def _style_numbered_list(target_lang: str) -> Tuple[str, str]:
    return (
        f"You are the news briefing agent for KRK-9. "
        f"Generate a numbered briefing in {target_lang}. "
        f"Be crisp and informative.",
        "Format as a numbered list (1., 2., 3., etc.). "
        "For each item write: the number, the title in bold, the source in parentheses, "
        "then a short paragraph (2-3 sentences) explaining what happened and why it matters. "
        "No sections, no headers — just the numbered list."
    )

def _style_bullet_points(target_lang: str) -> Tuple[str, str]:
    return (
        f"You are the news briefing agent for KRK-9. "
        f"Generate a scannable bullet-point briefing in {target_lang}. "
        f"Be telegraphic — maximum 1 line per item.",
        "Format as bullet points using •. Each bullet: "
        "**Title** (Source) — one short phrase about why it matters. "
        "Keep each bullet to ONE LINE. No paragraphs, no sections. "
        "End with 3 vocabulary bullets marked with 🗣️."
    )

def _style_conversational(target_lang: str) -> Tuple[str, str]:
    return (
        f"You are KRK-9, a friendly AI news companion. "
        f"You're chatting with your user about today's news in {target_lang}. "
        f"Be natural, warm, and conversational — like a friend reading the news aloud over coffee. "
        f"Use casual language, reactions ('wow', 'interesting!', 'check this out'), "
        f"and invite the user to ask follow-up questions.",
        "Write as a natural chat conversation — NOT as a formatted briefing. "
        "Start with a greeting ('Hey! Let me tell you what's happening today...'). "
        "Cover each news item naturally, weaving them together. "
        "After each major item, add something like 'Want me to dig deeper into this?' or "
        "'I can tell you more about this one if you're curious'. "
        "End with: 'Anything catch your eye? Just ask me for details on any of these!'"
    )

def _style_detailed(target_lang: str) -> Tuple[str, str]:
    return (
        f"You are the news briefing agent for KRK-9. "
        f"Generate an in-depth, analytical briefing in {target_lang}. "
        f"Provide context, background, and implications for each story.",
        "For each news item, write 2-3 paragraphs:\n"
        "1. What happened (the facts)\n"
        "2. Why it matters (context and implications)\n"
        "3. What to watch next (potential developments)\n"
        "Use ### headers for each story. Be thorough but readable."
    )

def _style_quick_summary(target_lang: str) -> Tuple[str, str]:
    return (
        f"You are the news briefing agent for KRK-9. "
        f"Generate an ultra-concise TL;DR in {target_lang}. Maximum 5 sentences total.",
        "Write a TL;DR of ALL the news in 3-5 sentences total. "
        "Cover only the most important stories. No formatting, no headers, no lists — "
        "just a brief paragraph you could read in 15 seconds."
    )

STYLE_BUILDERS = {
    "markdown_sections": _style_markdown_sections,
    "numbered_list": _style_numbered_list,
    "bullet_points": _style_bullet_points,
    "conversational": _style_conversational,
    "detailed": _style_detailed,
    "quick_summary": _style_quick_summary,
}


# ─── LLM Providers ───────────────────────────────────────────────────────────

def _get_google_ai_key() -> str:
    """Returns the Google AI Studio API key from credentials config, then env/.env."""
    creds = _google_ai_creds_cache.get("credentials", {})
    key = creds.get("google_ai_studio_key", "")
    if key:
        return key
    return os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")


async def _call_google_ai(prompt: str, system: str = "", temperature: float = 0.6, max_tokens: int = 2000) -> str | None:
    """Calls Google AI Studio API via httpx direct REST call. Returns text or None."""
    import httpx
    api_key = _get_google_ai_key()
    if not api_key:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        messages_content = []
        if system:
            messages_content.append({"role": "user", "parts": [{"text": system + "\n\n" + prompt}]})
        else:
            messages_content.append({"role": "user", "parts": [{"text": prompt}]})
        payload = {"contents": messages_content}
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"]
        return None
    except Exception as e:
        logger.error(f"❌ Google AI Studio briefing falló: {e}")
        return None


# ─── RSS Fetching ─────────────────────────────────────────────────────────────

async def fetch_rss_items(sources: List[Dict], max_per_source: int = 5) -> List[Dict]:
    """Descarga items de fuentes RSS habilitadas."""
    import feedparser
    items = []
    for src in sources:
        if not src.get("enabled", True) or src.get("type") != "rss":
            continue
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:max_per_source]:
                items.append({
                    "title": entry.get("title", "(sin título)"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:400],
                    "source": src.get("name", src["id"]),
                })
            logger.info(f"📰 {src['name']}: {min(len(feed.entries), max_per_source)} items")
        except Exception as e:
            logger.warning(f"⚠️ RSS {src.get('name')} falló: {e}")
    return items


# ─── Prompt Building ─────────────────────────────────────────────────────────

def build_briefing_prompt(
    items: List[Dict],
    max_items: int,
    agent_cfg: Dict = None,
    summarize_style: str = "markdown_sections",
    user_interests: List[str] = None,
) -> Tuple[str, str]:
    """Build (system_prompt, user_prompt) for briefing generation.

    Returns a tuple so callers can pass system and user content separately
    to the LLM provider.
    """
    if agent_cfg is None:
        agent_cfg = {}

    target_lang = agent_cfg.get("target_language", "es")
    style_builder = STYLE_BUILDERS.get(summarize_style, _style_markdown_sections)
    system_base, format_instruction = style_builder(target_lang)

    # Inject user interests if available
    interests_note = ""
    if user_interests:
        topics_str = ", ".join(user_interests[:15])
        interests_note = (
            f"\n\nThe user has shown interest in these topics: {topics_str}. "
            f"Prioritize similar news when choosing which items to highlight."
        )

    system_prompt = f"{system_base}{interests_note}\n\n{format_instruction}"

    # Build the news items as user content
    lines = [
        f"{i+1}. [{it['source']}] {it['title']}\n   {it['summary'][:200]}\n   {it['link']}"
        for i, it in enumerate(items[:max_items])
    ]
    user_prompt = "Today's news:\n" + "\n\n".join(lines)

    return system_prompt, user_prompt


# ─── LLM Call Helper ─────────────────────────────────────────────────────────

async def _call_llm(
    system_prompt: str,
    user_prompt: str,
    agent_cfg: Dict,
    llm_provider: str = "openrouter",
    llm_model: str = None,
) -> Optional[str]:
    """Call the configured LLM with fallback. Returns text or None."""
    from news_config import LLM_DEFAULT_MODEL

    temperature = agent_cfg.get("temperature", 0.6)
    max_tokens = agent_cfg.get("max_tokens", 2000)
    if llm_model is None:
        llm_model = agent_cfg.get("llm_model", LLM_DEFAULT_MODEL.get(llm_provider, ""))

    # Cache Google AI Studio credentials
    global _google_ai_creds_cache

    providers_to_try = []
    if llm_provider == "google_ai_studio":
        providers_to_try = ["google_ai_studio", "openrouter"]
    else:
        providers_to_try = ["openrouter", "google_ai_studio"]

    for provider in providers_to_try:
        try:
            if provider == "google_ai_studio":
                body = await _call_google_ai(
                    user_prompt, system=system_prompt,
                    temperature=temperature, max_tokens=max_tokens,
                )
            else:
                from llm_client import call_openrouter
                body = await call_openrouter(
                    [{"role": "user", "content": user_prompt}],
                    system=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    provider_override="" if provider != "openrouter" else None,
                    model_override=llm_model,
                )
            if body is not None:
                return body
        except Exception as e:
            logger.warning(f"⚠️ {provider} LLM falló: {e}")

    logger.error("❌ Ambos LLM fallaron")
    return None


# ─── Briefing Generation ─────────────────────────────────────────────────────

async def generate_briefing(uid: str) -> str:
    """Generate a news briefing using the configured LLM provider and summarize_style."""
    from state_manager import load_state, save_state, get_news_config

    state = load_state()
    cfg = get_news_config(state, uid)
    sources = cfg.get("sources", [])
    max_items = cfg.get("output", {}).get("max_briefing_items", 6)
    agent_cfg = cfg.get("agent", {})

    # Cache Google AI Studio credentials for _get_google_ai_key()
    global _google_ai_creds_cache
    _google_ai_creds_cache = cfg.get("credentials", {})

    # Read summarize_style from config
    summarize_style = agent_cfg.get("summarize_style", "markdown_sections")

    # Load user interests for prompt injection
    user = state.get("users", {}).get(uid, {})
    interests_data = user.get("news_interests", {})
    # Extract top topics from liked articles
    topic_counts = interests_data.get("topic_counts", {})
    user_interests = sorted(topic_counts.keys(), key=lambda k: topic_counts[k], reverse=True)[:10] if topic_counts else []

    # Collect news items
    items = await fetch_rss_items(sources, 5)
    llm_provider = agent_cfg.get("llm_provider", "openrouter")
    llm_model = agent_cfg.get("llm_model", None)

    if not items:
        md = f"# ☕ Briefing {datetime.now():%Y-%m-%d}\n\n⚠️ No se pudieron descargar noticias hoy."
    else:
        system_prompt, user_prompt = build_briefing_prompt(
            items, max_items, agent_cfg,
            summarize_style=summarize_style,
            user_interests=user_interests,
        )

        body = await _call_llm(system_prompt, user_prompt, agent_cfg, llm_provider, llm_model)

        if body is None:
            body = "(LLM no disponible — lista cruda)\n" + "\n".join(
                f"- {i['title']} ({i['source']})" for i in items
            )

        md = (
            f"---\ntype: krk9-news-briefing\ndate: \"{datetime.now():%Y-%m-%d}\"\n"
            f"user: \"{uid}\"\nstyle: \"{summarize_style}\"\n---\n\n"
            f"# ☕ Morning Briefing — {datetime.now():%Y-%m-%d}\n\n{body}\n"
        )

    # Save briefing + article data to state
    user_state = state.setdefault("users", {}).setdefault(uid, {})
    user_state.setdefault("news_history", []).insert(0, {
        "date": datetime.now().isoformat(),
        "markdown": md,
    })
    user_state["news_history"] = user_state["news_history"][:30]

    # Store articles alongside conversation context for follow-up questions
    articles_data = [
        {"index": i, "title": it["title"], "link": it["link"],
         "summary": it["summary"], "source": it["source"]}
        for i, it in enumerate(items[:max_items])
    ]
    user_state["news_conversation"] = {
        "last_briefing": {
            "date": datetime.now().isoformat(),
            "style": summarize_style,
            "markdown": md,
            "articles": articles_data,
        },
        "history": [],  # Reset conversation history on new briefing
    }

    # Mark today as run
    for r in user_state.get("rooms", []):
        if r.get("type") == "news":
            r.setdefault("config", {})["last_run_date"] = f"{datetime.now():%Y-%m-%d}"
    save_state(state)
    logger.info(f"📰 Briefing generado para {uid} ({len(md)} chars, style={summarize_style})")
    return md


# ─── Conversational Follow-up ────────────────────────────────────────────────

async def chat_followup(uid: str, message: str) -> Dict:
    """Handle a follow-up question about the latest briefing.

    Loads the last briefing context, finds relevant articles,
    and uses the LLM to answer with more detail.

    Returns {"reply": str, "sources": [{"title", "link"}]}
    """
    from state_manager import load_state, save_state, get_news_config

    state = load_state()
    cfg = get_news_config(state, uid)
    agent_cfg = cfg.get("agent", {})

    # Cache Google AI Studio credentials
    global _google_ai_creds_cache
    _google_ai_creds_cache = cfg.get("credentials", {})

    user = state.get("users", {}).get(uid, {})
    conversation = user.get("news_conversation", {})
    last_briefing = conversation.get("last_briefing", {})

    if not last_briefing:
        return {"reply": "No hay un briefing reciente. Genera uno primero con el botón 📰 Generate Briefing.", "sources": []}

    articles = last_briefing.get("articles", [])
    history = conversation.get("history", [])

    target_lang = agent_cfg.get("target_language", "es")

    # Build context for the LLM
    articles_context = "\n".join(
        f"{a['index']+1}. [{a['source']}] {a['title']}\n   {a['summary'][:300]}\n   Link: {a['link']}"
        for a in articles
    )

    # Include recent conversation history (cap at 10 turns)
    history_context = ""
    if history:
        recent = history[-10:]
        history_lines = [f"{h['role'].upper()}: {h['content']}" for h in recent]
        history_context = "\n\nConversation so far:\n" + "\n".join(history_lines)

    system_prompt = (
        f"You are KRK-9, a friendly AI news companion. The user is asking follow-up "
        f"questions about today's news briefing. Answer in {target_lang}.\n\n"
        f"You have access to the following news articles from the last briefing:\n"
        f"{articles_context}\n\n"
        f"Rules:\n"
        f"- If the user asks about a specific article, provide more details from its summary\n"
        f"- If they say 'give me details' or 'tell me more', identify which article(s) they mean\n"
        f"- Be conversational and helpful\n"
        f"- If you don't have enough information, say so and provide the article link\n"
        f"- Keep responses focused and relevant"
    )

    user_prompt = f"{history_context}\n\nUSER: {message}"

    llm_provider = agent_cfg.get("llm_provider", "openrouter")
    llm_model = agent_cfg.get("llm_model", None)

    reply = await _call_llm(system_prompt, user_prompt, agent_cfg, llm_provider, llm_model)

    if reply is None:
        reply = "Lo siento, no pude procesar tu pregunta. Intenta de nuevo."

    # Find which articles might be referenced (simple keyword matching)
    referenced_sources = []
    msg_lower = message.lower()
    for a in articles:
        title_words = set(a["title"].lower().split())
        # Check if any significant word from the article title appears in the message
        if any(w in msg_lower for w in title_words if len(w) > 4):
            referenced_sources.append({"title": a["title"], "link": a["link"]})

    # If user says generic "details", "more", "first", "second" etc
    if not referenced_sources:
        ordinals = {"first": 0, "1": 0, "second": 1, "2": 1, "third": 2, "3": 2,
                     "fourth": 3, "4": 3, "fifth": 4, "5": 4, "sixth": 5, "6": 5,
                     "primero": 0, "primera": 0, "segundo": 1, "segunda": 1,
                     "tercero": 2, "tercera": 2, "cuarto": 3, "cuarta": 3}
        for word, idx in ordinals.items():
            if word in msg_lower and idx < len(articles):
                referenced_sources.append({"title": articles[idx]["title"], "link": articles[idx]["link"]})
                break

    # Append to conversation history
    conversation.setdefault("history", []).append({
        "role": "user", "content": message, "ts": datetime.now().isoformat()
    })
    conversation["history"].append({
        "role": "assistant", "content": reply, "ts": datetime.now().isoformat()
    })
    # Cap history at 20 turns
    conversation["history"] = conversation["history"][-20:]

    user["news_conversation"] = conversation
    save_state(state)

    return {"reply": reply, "sources": referenced_sources}


# ─── Like / Interest Tracking ────────────────────────────────────────────────

def _extract_keywords(title: str) -> List[str]:
    """Extract meaningful keywords from an article title for interest tracking."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
        "of", "and", "or", "but", "with", "by", "from", "as", "it", "its", "this",
        "that", "how", "what", "why", "when", "who", "which", "new", "says", "said",
        "will", "can", "could", "would", "should", "has", "have", "had", "not", "no",
        "be", "been", "do", "does", "did", "just", "more", "than", "into", "about",
        "up", "out", "over", "after", "before", "between", "under", "also", "may",
    }
    words = title.lower().split()
    # Keep words that are meaningful (>3 chars, not stop words)
    return [w.strip(".,!?:;()[]\"'") for w in words
            if len(w) > 3 and w.lower().strip(".,!?:;()[]\"'") not in stop_words]


def record_like(uid: str, article_index: int = None, article_url: str = None) -> Dict:
    """Record that a user liked a news article.

    Returns {"ok": bool, "liked_topics": [str], "article_title": str}
    """
    from state_manager import load_state, save_state

    state = load_state()
    user = state.get("users", {}).get(uid, {})
    conversation = user.get("news_conversation", {})
    last_briefing = conversation.get("last_briefing", {})
    articles = last_briefing.get("articles", [])

    if not articles:
        return {"ok": False, "error": "No briefing articles available", "liked_topics": []}

    # Find the article
    article = None
    if article_index is not None and 0 <= article_index < len(articles):
        article = articles[article_index]
    elif article_url:
        article = next((a for a in articles if a.get("link") == article_url), None)

    if not article:
        return {"ok": False, "error": "Article not found", "liked_topics": []}

    # Initialize interests structure
    interests = user.setdefault("news_interests", {
        "liked_articles": [],
        "topic_counts": {},
    })

    # Add to liked articles (avoid duplicates by link)
    liked_links = {a.get("link") for a in interests.get("liked_articles", [])}
    if article["link"] not in liked_links:
        interests.setdefault("liked_articles", []).append({
            "title": article["title"],
            "link": article["link"],
            "source": article["source"],
            "ts": datetime.now().isoformat(),
        })
        # Keep only last 50
        interests["liked_articles"] = interests["liked_articles"][-50:]

    # Update topic counts
    keywords = _extract_keywords(article["title"])
    topic_counts = interests.setdefault("topic_counts", {})
    for kw in keywords:
        topic_counts[kw] = topic_counts.get(kw, 0) + 1

    user["news_interests"] = interests
    save_state(state)

    # Return top topics
    top_topics = sorted(topic_counts.keys(), key=lambda k: topic_counts[k], reverse=True)[:10]
    return {"ok": True, "liked_topics": top_topics, "article_title": article["title"]}


def get_user_interests(uid: str) -> Dict:
    """Get the user's news interest profile.

    Returns {"liked_count": int, "top_topics": [str], "recent_likes": [{title, source, ts}]}
    """
    from state_manager import load_state

    state = load_state()
    user = state.get("users", {}).get(uid, {})
    interests = user.get("news_interests", {})
    liked = interests.get("liked_articles", [])
    topic_counts = interests.get("topic_counts", {})
    top_topics = sorted(topic_counts.keys(), key=lambda k: topic_counts[k], reverse=True)[:10]

    return {
        "liked_count": len(liked),
        "top_topics": top_topics,
        "recent_likes": [
            {"title": a["title"], "source": a.get("source", ""), "ts": a.get("ts", "")}
            for a in liked[-5:]
        ],
    }


if __name__ == "__main__":
    import asyncio, sys
    uid = sys.argv[1] if len(sys.argv) > 1 else "legacy_vaclav"
    print(asyncio.run(generate_briefing(uid))[:1500])