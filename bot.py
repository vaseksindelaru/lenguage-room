"""
=============================================================================
"KRK-9" — Discord Bot for KRK-9 English Practice
=============================================================================

A Discord bot that simulates a conversation room with 4 AI agents
(Alex, Maya, Jordan, Sam) to help Vaclav practice English safely.

Architecture:
- Single Discord bot that uses WEBHOOKS to post as 4 different "people"
- OpenRouter API for LLM responses (supports Claude, GPT, etc.)
- Auto-detects Vaclav's messages and applies correction rules
- Rotates topics on a schedule

=============================================================================
"""

import os
import re
import json
import random
import asyncio
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import httpx
import edge_tts
from openai import OpenAI, APIStatusError

# Audio server integration
from audio_server import init_audio_server

# State management
from state_manager import load_state, save_state, get_welcome_message, STATE_PATH, MAX_HISTORY

AUDIO_SERVER_URL = "http://localhost:8081/api/audio"

# ─── Load environment ───────────────────────────────────────────────────────
load_dotenv()

# ─── Configuration ──────────────────────────────────────────────────────────
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
VACLAV_USER_ID = int(os.getenv("VACLAV_USER_ID", "0"))

# Agent webhook names (must match webhooks created in Discord channel)
AGENTS = {
    "Alex": {"color": 0x5865F2, "emoji": "🟦", "voice": "en-US-GuyNeural"},
    "Maya": {"color": 0x57F287, "emoji": "🟩", "voice": "en-US-JennyNeural"},
    "Jordan": {"color": 0xFEE75C, "emoji": "🟧", "voice": "en-GB-RyanNeural"},
    "Sam": {"color": 0xEB459E, "emoji": "🟪", "voice": "en-US-AriaNeural"},
}

# Topics rotation with seed vocabulary
TOPICS = [
    {
        "theme": "AI & Technology",
        "seed_vocab": ["breakthrough", "bias", "reliable", "automate", "ethical concerns", "trade-off"],
        "hook": "If you could have one AI assistant that does ANYTHING for you, what would it be — and what's the one thing you'd never let AI do?"
    },
    {
        "theme": "Crypto & Markets",
        "seed_vocab": ["volatile", "rally", "correction", "bearish", "hedge", "liquidity"],
        "hook": "Would you trust a trading bot with your life savings? What's the difference between gambling and investing in crypto?"
    },
    {
        "theme": "Daily Life & Opinions",
        "seed_vocab": ["figure out", "weird", "chill", "hang out", "ended up", "run into"],
        "hook": "What's a daily habit that changed your life but seems weird to other people?"
    },
    {
        "theme": "Debate & Critical Thinking",
        "seed_vocab": ["I'd argue", "fair point", "it depends", "nuanced", "long-term", "short-term"],
        "hook": "Is it better to be honest and hurt someone's feelings, or kind and tell a white lie? What determines which to choose?"
    },
    {
        "theme": "Stories & Movies",
        "seed_vocab": ["twist", "plot", "cliffhanger", "inspiring", "relatable", "spoiler"],
        "hook": "What's a movie or series that totally changed how you see the world? No spoilers!"
    },
    {
        "theme": "Work & Productivity",
        "seed_vocab": ["procrastinate", "deadline", "burn out", "get stuff done", "overwhelming", "workflow"],
        "hook": "Are you a morning person or a night owl? Do you think society is built for one type and it's unfair to the other?"
    },
    {
        "theme": "Travel & Culture",
        "seed_vocab": ["wander off", "off the beaten path", "culture shock", "hidden gem", "local", "tourist trap"],
        "hook": "If you could teleport to any country right now, where would you go and why?"
    },
]

# ─── System Prompts ─────────────────────────────────────────────────────────
AGENT_PERSONAS = {
    "Alex": """You are Alex — The Curious One in a friendly group chat.

Your personality:
- Always ask genuine, thoughtful questions
- Casual American English with contractions and phrasal verbs ("hold on", "break that down", "what if")
- Medium pace, natural flow
- You don't lecture — you explore ideas through questions
- You're warm and make people feel comfortable sharing

Speaking style:
- "Wait, hold on — could you break that down for me?"
- "I'm curious about something..."
- "That makes sense, but what if...?"
- "Honestly though, that's a really interesting angle"

Rules:
- Keep messages SHORT (1-3 sentences). This is a chat, not an essay.
- React to what others actually said before adding your twist.
- NEVER correct grammar — that's Sam's job.
- Use B1-B2 vocabulary unless you're naturally a more advanced speaker.
- Sound like a real person texting, not a bot.""",

    "Maya": """You are Maya — The Structured Thinker in a friendly group chat.

Your personality:
- Organizes ideas and finds connections between points people make
- Clear, slightly formal but never cold
- Writes short, well-structured pieces
- Summarizes when the conversation gets scattered
- Gently offers alternative perspectives

Speaking style:
- "So if I understand correctly, you mean that..."
- "Let me summarize what we've discussed so far..."
- "There's another angle worth considering..."
- "I think there are a few layers to this..."

Rules:
- Keep messages SHORT (2-4 sentences). You can be a bit longer than others but always concise.
- React to what others actually said before offering your take.
- NEVER correct grammar — that's Sam's job.
- Your summaries are 2-3 sentences max.
- Sound like a thoughtful friend, not a professor.""",

    "Jordan": """You are Jordan — The Enthusiast in a friendly group chat.

Your personality:
- Brings energy, data, examples, and personal anecdotes
- British English informal with humor
- Uses stories to make points
- Sometimes goes on fun tangents but always comes back
- Makes people laugh or say "huh, didn't know that"

Speaking style:
- "Oh that reminds me of..."
- "Funny story actually..."
- "Here's what's wild about that..."
- "Wait wait wait — I've got a good one..."
- "That's actually genius because..."

Rules:
- Keep messages SHORT (1-3 sentences). Punchy and fun.
- React to what others actually said — show you were listening.
- NEVER correct grammar — that's Sam's job.
- Add your own flair, stories, or facts.
- Sound like the entertaining friend in the group.""",

    "Sam": """You are Sam — The Patient Tutor in a friendly group chat.

Your role is SPECIAL — you're the main English support for Vaclav, who is a Spanish
speaker learning English (intermediate level, B1-B2).

Your personality:
- Calm, warm, encouraging — NEVER condescending
- Speaks at Vacla's level of English so he can follow easily
- Detects when Vaclav hasn't participated and gently invites him in
- When Vacvac makes a mistake, you correct it GENTLY and WITHOUT changing the topic

CORRECTION FORMAT (critical):
When Vaclav makes a grammar/vocabulary mistake:
1. FIRST respond to the CONTENT (validate his point, continue the conversation)
2. THEN add the correction naturally, inline:
   "(Quick note: 'would went' → 'would have gone' — after 'would' we use 'have' + past participle. Great point though!)"
3. Never make the correction the main focus — always the content comes first.

Speaking style:
- "Vaclav, what's your take on this?"
- "Take your time. How would you say..."
- "By the way Vaclav, a quick note: we say 'agree with' instead of 'agree to' — your point was great."
- "That's a really good point, Vaclav. (Quick note: ...)"
- "Interesting — I never thought of it that way."

Rules:
- Keep messages SHORT (1-4 sentences). Longer when helping Vaclav.
- If Vaclav hasn't spoken in the last 5 messages: GENTLY invite him in.
- If Vaclav writes in Spanish: understand it, respond in English with help.
- If Vaclav says "help" or gets stuck: offer 2-3 ways he could express his idea.
- NEVER mock, rush, or embarrass Vaclav.
- Your correction tone is always: "this is a tiny thing, you're doing great, here's how..."
- Sound like a supportive friend, not a teacher grading papers.""",
}

# Master conversation coordinator prompt
COORDINATOR_PROMPT = """You are the conversation coordinator. You decide which agent should speak next
and what they should say. You have access to the full conversation history.

Available agents:
- CURIOUS: Ask questions, explore, react
- STRUCTURED: Summarize, connect dots, offer new angles
- ENTHUSIAST: Bring stories, energy, examples
- TUTOR: Support Vaclav, correct gently, keep him engaged

Your job:
1. Read the conversation history
2. Determine who speaks next (don't always go in order — vary it!)
3. Output ONLY the agent's name on the first line, then what they say

IMPORTANT: Output format:
NAME
[their message]""",

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("krk-9")

# ─── Bot setup ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─── State ──────────────────────────────────────────────────────────────────
conversation_history: List[Dict] = []
current_topic_index = 0
vaclav_message_count_in_window = 0
last_topic_change = datetime.now()
agent_webhooks: Dict[str, discord.Webhook] = {}
vaclav_voice_webhook: Optional[discord.Webhook] = None

# New state for persistence and topic control
topic_locked = True       # bots don't start topics automatically
bots_paused = False       # conversation loop paused
last_vaclav_activity = datetime.now()  # track user activity for timing

# ─── Topics file ───────────────────────────────────────────────────────────
TOPICS_FILE = os.path.join(os.path.dirname(__file__), "topics.json")

def load_topics():
    """Load topics from JSON file, or create default if not exists."""
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE) as f:
            return json.load(f)
    return TOPICS

def get_topic(day_of_week: int) -> dict:
    """Get topic based on day of week (Monday=0)."""
    topics = load_topics()
    idx = day_of_week % len(topics)
    return topics[idx]

# ─── Multi-Provider LLM Router (Cerebras → Groq → OpenRouter → Ollama) ──────
import httpx

def _init_llm_clients():
    """Initialize LLM clients for all providers in fallback order."""
    clients = []
    
    # 1. Cerebras (principal - 1M tokens/día, 30 RPM, sin tarjeta)
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    if cerebras_key:
        clients.append({
            "name": "cerebras",
            "client": OpenAI(api_key=cerebras_key, base_url="https://api.cerebras.ai/v1", max_retries=0),
            "model": "gpt-oss-120b",
            "timeout": 15,
            "type": "openai_compatible",
        })
    
    # 2. Groq (fallback rápido - LPU, 8B instant maximiza RPD)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        clients.append({
            "name": "groq",
            "client": OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1", max_retries=0),
            "model": "llama-3.1-8b-instant",
            "timeout": 15,
            "type": "openai_compatible",
        })
    
    # 3. OpenRouter (fallback diversificado - usa :free obligatorio)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        clients.append({
            "name": "openrouter",
            "client": OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1", max_retries=0),
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "timeout": 30,
            "type": "openai_compatible",
        })
    
    # 4. Ollama local (red de seguridad final - siempre disponible)
    # Usa endpoint nativo /api/chat (el /v1 compatible tiene timeouts)
    clients.append({
        "name": "ollama_local",
        "client": None,  # Usamos httpx directamente
        "model": "qwen2.5:3b",
        "timeout": 120,  # CPU-only cold start puede tardar 60s+
        "type": "ollama_native",
        "url": "http://localhost:11434/api/chat",
    })
    
    return clients


LLM_CLIENTS = _init_llm_clients()


async def _call_ollama_native(messages: list, model: str, temperature: float, max_tokens: int, timeout: int, url: str) -> str:
    """Call Ollama native /api/chat endpoint."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")


async def _warmup_ollama():
    """Pre-load Ollama model to avoid cold-start timeout on first real request."""
    ollama_provider = next((p for p in LLM_CLIENTS if p["type"] == "ollama_native"), None)
    if not ollama_provider:
        return
    try:
        logger.info("🔥 Warming up Ollama model...")
        await _call_ollama_native(
            messages=[{"role": "user", "content": "hi"}],
            model=ollama_provider["model"],
            temperature=0.7,
            max_tokens=5,
            timeout=120,
            url=ollama_provider["url"],
        )
        logger.info("✅ Ollama warmup complete")
    except Exception as e:
        logger.warning(f"⚠️ Ollama warmup failed (will retry on first real request): {e}")


async def call_openrouter(messages: list, system: str = "", temperature: float = 0.8,
                         provider_override: str = None, model_override: str = None) -> str:
    """
    Router con fallback automático: Cerebras → Groq → OpenRouter → Ollama local.
    Devuelve el texto generado o None si todo falla.

    If provider_override is set, try that provider first (with model_override if given).
    If it fails, fall back to the full router chain.
    """
    payload_messages = []
    if system:
        payload_messages.append({"role": "system", "content": system})
    payload_messages.extend(messages)

    # Build provider list: if override is set, try it first, then full chain
    providers_to_try = list(LLM_CLIENTS)  # copy
    if provider_override:
        # Map provider_override name to LLM_CLIENTS entry
        # provider names: "cerebras", "groq", "openrouter", "ollama" (or "ollama_local")
        override_name = provider_override.replace("ollama", "ollama_local") if provider_override == "ollama" else provider_override
        override_client = next((p for p in LLM_CLIENTS if p["name"] == override_name), None)
        if override_client:
            # Put override first; if model_override given, use it
            override_entry = dict(override_client)  # shallow copy
            if model_override:
                override_entry["model"] = model_override
            # Override first, then the rest of the chain (excluding duplicate)
            providers_to_try = [override_entry] + [p for p in LLM_CLIENTS if p["name"] != override_name]
            logger.info(f"🎯 LLM override: trying {provider_override}/{model_override or override_entry['model']} first")

    last_error = None
    for provider in providers_to_try:
        try:
            if provider["type"] == "ollama_native":
                # Use native Ollama endpoint
                content = await _call_ollama_native(
                    messages=payload_messages,
                    model=provider["model"],
                    temperature=temperature,
                    max_tokens=300,
                    timeout=provider.get("timeout", 120),
                    url=provider["url"],
                )
            else:
                # OpenAI-compatible providers (Cerebras, Groq, OpenRouter)
                resp = provider["client"].chat.completions.create(
                    model=provider["model"],
                    messages=payload_messages,
                    temperature=temperature,
                    max_tokens=300,
                    timeout=provider.get("timeout", 15),
                )
                content = resp.choices[0].message.content
            
            logger.info(f"✅ LLM response from {provider['name']} ({provider['model']})")
            return content
            
        except Exception as e:
            last_error = e
            # Check if it's a rate limit (429) for OpenAI-compatible providers
            if provider["type"] == "openai_compatible":
                # Try to extract status code from various exception types
                status_code = getattr(e, "status_code", None) or getattr(e, "response", None)
                if status_code and hasattr(status_code, "status_code"):
                    status_code = status_code.status_code
                if status_code == 429 or (hasattr(e, "status_code") and e.status_code == 429):
                    logger.warning(f"⚠️ {provider['name']} rate limited (429), trying next...")
                    continue
            logger.warning(f"⚠️ {provider['name']} exception: {e}")
            continue
    
    logger.error(f"❌ ALL LLM PROVIDERS FAILED. Last error: {last_error}")
    return None


# ─── Timing Helper ──────────────────────────────────────────────────────────
import random

def calculate_delay(previous_message: str, base_delay: float = 2.0) -> float:
    """Delay = base + max(reading_time, audio_time) + jitter. Range: 3–15s."""
    chars = len(previous_message)
    reading_speed_cps = 15
    reading_time = chars / reading_speed_cps
    words = len(previous_message.split())
    audio_time = words / 2.5  # ~150 wpm
    total_delay = base_delay + max(reading_time, audio_time) + random.uniform(0.5, 1.5)
    return min(max(total_delay, 3.0), 15.0)


# ─── TTS (Edge TTS) ───────────────────────────────────────────────────────────
async def generate_tts(text: str, voice: str) -> Optional[bytes]:
    """Generate TTS audio using Edge TTS (free, no API key needed). Returns MP3 bytes."""
    try:
        # Clean text for TTS (remove parenthetical corrections, emojis, etc.)
        clean_text = re.sub(r'\(Quick note:.*?\)', '', text)
        clean_text = re.sub(r'[🟦🟩🟧🟪]', '', clean_text)
        clean_text = clean_text.strip()
        
        if not clean_text:
            return None
            
        communicate = edge_tts.Communicate(clean_text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
    except Exception as e:
        logger.error(f"TTS error for voice {voice}: {e}")
        return None


async def send_agent_message(channel: discord.TextChannel, agent_name: str, text: str):
    """Send a message via webhook to appear as the agent, with TTS audio streamed to browsers."""
    webhook = agent_webhooks.get(agent_name)

    # Hot-reload voice from personas.json (falls back to AGENTS dict)
    try:
        from state_manager import load_personas
        pdata = load_personas()["agents"].get(agent_name, {})
        voice = pdata.get("voice") or AGENTS[agent_name].get("voice")
    except Exception:
        voice = AGENTS[agent_name].get("voice")
    
    # Generate TTS audio
    audio_data = None
    if voice:
        audio_data = await generate_tts(text, voice)
    
    # Send audio to browser clients (auto-play) via HTTP POST to audio server
    if audio_data:
        import base64
        b64 = base64.b64encode(audio_data).decode()
        payload = {
            "type": "audio",
            "agent": agent_name,
            "data": b64,
            "mime": "audio/mpeg"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(AUDIO_SERVER_URL, json=payload)
        except Exception as e:
            logger.warning(f"⚠️ Failed to send audio to browser: {e}")
    
    if webhook:
        try:
            # Send message to Discord (text only, no file attachment needed)
            await webhook.send(
                content=text,
                username=agent_name,
                avatar_url=get_avatar_url(agent_name),
                wait=True
            )
        except Exception as e:
            logger.error(f"❌ Webhook send failed for {agent_name}: {e}")
            # Fallback: send as embed with bot if webhook fails
            embed = discord.Embed(
                description=text,
                color=AGENTS[agent_name]["color"],
            )
            embed.set_author(name=f"{AGENTS[agent_name]['emoji']} {agent_name}")
            await channel.send(embed=embed)
    else:
        # Fallback: send as embed with bot if no webhook was found
        embed = discord.Embed(
            description=text,
            color=AGENTS[agent_name]["color"],
        )
        embed.set_author(name=f"{AGENTS[agent_name]['emoji']} {agent_name}")
        await channel.send(embed=embed)

    # Record in history
    conversation_history.append({
        "agent": agent_name,
        "author": agent_name,
        "content": text,
        "timestamp": datetime.now().isoformat(),
    })


async def generate_conversation_starter(topic: dict) -> List[Dict]:
    """Generate the opening messages for a new topic."""
    messages = [
        {
            "role": "user",
            "content": (
                f"Today's topic: {topic['theme']}\n"
                f"Vocabulary to work in naturally: {', '.join(topic['seed_vocab'])}\n"
                f"Hook/question: {topic['hook']}\n\n"
                f"Generate 3 opening messages:\n"
                f"1. ALEX introduces the topic with enthusiasm and asks the hook question\n"
                f"2. MAYA adds some context and structures the discussion\n"
                f"3. JORDAN shares a quick related thought or question\n\n"
                f"For Vaclav — keep it B1-B2 level. Natural chat tone. Short messages (1-3 sentences each).\n"
                f"Format exactly:\n"
                f"ALEX: [message]\n"
                f"MAYA: [message]\n"
                f"JORDAN: [message]"
            ),
        }
    ]

    response = await call_openrouter(messages, temperature=0.9)
    if not response:
        return [
            {"agent": "Alex", "text": f"Hey everyone! Today we're talking about {topic['theme']}. {topic['hook']}"},
            {"agent": "Maya", "text": "This should be a great discussion. I'm curious what everyone thinks."},
            {"agent": "Jordan", "text": f"Oh I've got thoughts on {topic['theme']}! Let's do this."},
        ]

    # Parse response (case-insensitive: ALEX: or Alex:)
    results = []
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        for agent_name in AGENTS:
            if line.upper().startswith(f"{agent_name}:".upper()):
                text = line.split(":", 1)[1].strip()
                results.append({"agent": agent_name, "text": text})
                break

    if not results:
        return [
            {"agent": "Alex", "text": f"Hey everyone! Today we're talking about {topic['theme']}. {topic['hook']}"},
            {"agent": "Maya", "text": "This should be a great discussion. I'm curious what everyone thinks."},
        ]

    return results[:3]


async def generate_agent_reply(conversation_context: list, agent_name: str, vaclav_recent: bool = False) -> str:
    """Generate a reply from a specific agent based on conversation context."""
    # Hot-reload persona & LLM config from personas.json
    provider_override = None
    model_override = None
    try:
        from state_manager import load_personas
        pdata = load_personas()["agents"].get(agent_name, {})
        persona = pdata.get("persona") or AGENT_PERSONAS[agent_name]
        provider_override = pdata.get("llm_provider")  # None = use default router
        model_override = pdata.get("llm_model")  # None = provider default
    except Exception:
        persona = AGENT_PERSONAS[agent_name]

    # Build conversation summary
    context_text = "\n".join(
        f"{msg.get('author', msg.get('agent', 'Unknown'))}: {msg['content']}"
        for msg in conversation_context[-10:]  # last 10 messages
    )

    extra_instruction = ""
    if agent_name == "Sam":
        if vaclav_recent:
            extra_instruction = (
                "\n⚠️ IMPORTANT: Vaclav just participated. If he made any grammar or vocabulary mistakes,\n"
                "correct him GENTLY using this format:\n"
                "1. First respond to his CONTENT (validate, continue conversation)\n"
                "2. Then add correction: '(Quick note: [mistake] → [correction] — [brief reason]. Great point though!)'\n"
                "Keep the correction secondary — content always comes first."
            )
        else:
            extra_instruction = (
                "\n⚠️ Vaclav hasn't spoken recently. GENTLY invite him into the conversation.\n"
                "Ask him a specific question related to the discussion. Make it easy for him to jump in."
            )
    else:
        if vaclav_recent:
            extra_instruction = (
                "\n⚠️ IMPORTANT: Vaclav just spoke! You MUST heavily prioritize his message.\n"
                "Directly answer any questions he asks, fulfill his requests, and respond to his points "
                "BEFORE you continue with the previous topic or your own thoughts."
            )

    prompt = f"""Recent conversation:
{context_text}

{extra_instruction}

Now it's your turn to speak, {agent_name}. 
Keep your message SHORT (1-3 sentences). React naturally and directly to the conversation.
If Vaclav just spoke, your primary goal is to address him!
Output ONLY your message text, nothing else."""

    messages = [{"role": "user", "content": prompt}]

    response = await call_openrouter(messages, system=persona, temperature=0.85,
                                     provider_override=provider_override, model_override=model_override)
    if not response:
        fallbacks = {
            "Alex": "That's really interesting! What made you think of that?",
            "Maya": "I think there's a valuable point here worth exploring further.",
            "Jordan": "Oh that's a great connection! Totally changes how I see it.",
            "Sam": "Vaclav, I'd love to hear your perspective on this — what do you think?",
        }
        return fallbacks[agent_name]

    return response.strip().strip('"')


async def generate_coordinator_decision(conversation_context: list, agent_name: str) -> str:
    """Generate agent-specific response using their persona and conversation context."""

    persona = AGENT_PERSONAS[agent_name]

    # Build conversation summary
    context_text = "\n".join(
        f"{'Vaclav' if msg['author'] == 'Vaclav' else msg['author']}: {msg['content']}"
        for msg in conversation_context[-10:]
    )

    # Calculate Vaclav participation
    vaclav_msgs = sum(1 for msg in conversation_context[-8:] if msg['author'] == 'Vaclav')
    vaclav_recent = vaclav_msgs > 0

    extra_instruction = ""
    if agent_name == "Sam":
        if vaclav_recent:
            extra_instruction = (
                "\n⚠️ VACLAV JUST SPOKE. Check his message for grammar/vocabulary errors.\n"
                "If you find errors:\n"
                "1. FIRST respond to his CONTENT (validate, continue the conversation)\n"
                "2. THEN add: '(Quick note: [wrong] → [correct] — [short reason])'\n"
                "Keep correction SHORT and secondary. Content comes first."
            )
        else:
            extra_instruction = (
                "\n⚠️ Vaclav hasn't spoken in a while. GENTLY invite him in with a friendly, easy question.\n"
                "Make him feel included, not put on the spot."
            )

    prompt = f"""Recent conversation in the chat:
{context_text}

{extra_instruction}

Now it's YOUR turn to speak, {agent_name}.
Write ONLY your message (1-3 sentences). React to what was just said before you.
This is a NATURAL CHAT — don't lecture, don't over-explain, just converse.
Output your message text ONLY."""

    messages = [{"role": "user", "content": prompt}]

    response = await call_openrouter(messages, system=persona, temperature=0.85)
    if not response:
        fallbacks = {
            "Alex": "That's really interesting actually. What made you think of that?",
            "Maya": "I think we're touching on something important here. The key point seems to be how this connects to everyday experience.",
            "Jordan": "Oh that reminds me of something — okay this is a bit random but hear me out...",
            "Sam": "Vaclav, I'd genuinely love to hear your take on this. No pressure though — what comes to mind?",
        }
        return fallbacks[agent_name]

    return response.strip().strip('"')


async def decide_next_agent() -> str:
    """Decide which agent speaks next based on conversation state."""
    recent_agents = [msg["agent"] for msg in conversation_history[-4:] if "agent" in msg]
    vaclav_recent = any(msg.get("author") == "Vaclav" for msg in conversation_history[-3:])

    # Sam should speak more if Vaclav participated or hasn't spoken
    weights = {"Alex": 25, "Maya": 20, "Jordan": 25, "Sam": 30}

    # Boost Sam if Vacvac spoke (to correct) or didn't (to invite)
    if vaclav_recent:
        weights["Sam"] += 30  # Vaclav spoke → Sam can correct + respond
    else:
        # boost Sam if too many agent-only messages
        recent_non_vaclav = [m for m in conversation_history[-5:] if m.get("author") != "Vaclav"]
        if len(recent_non_vaclav) >= 3:
            weights["Sam"] += 20

    # Avoid same agent twice in a row
    if recent_agents:
        last = recent_agents[-1]
        weights[last] = 0

    agents = list(weights.keys())
    w = [weights[a] for a in agents]
    return random.choices(agents, weights=w, k=1)[0]


def get_avatar_url(agent_name: str) -> str:
    """Return a placeholder avatar URL for each agent."""
    # Users should replace these with their own uploaded Discord avatars for the webhooks
    colors = {"Alex": "5865F2", "Maya": "57F287", "Jordan": "FEE75C", "Sam": "EB459E"}
    # Default Discord-style avatar with first letter
    letter = agent_name[0]
    color = colors.get(agent_name, "5865F2")
    return f"https://ui-avatars.com/api/?name={letter}&background={color}&color=fff&size=128&bold=true"


# ─── Conversation Loop ─────────────────────────────────────────────────────
@tasks.loop(seconds=25)
async def conversation_loop():
    """Main conversation loop — agents chat periodically."""
    global last_vaclav_activity
    
    if not CHANNEL_ID:
        return

    if bots_paused:
        return

    # topic_locked: bots only speak when user messages, !speak, or !topic
    if topic_locked:
        return

    # If Vaclav just spoke, skip this cycle to let the manual response flow
    if last_vaclav_activity and (datetime.now() - last_vaclav_activity).total_seconds() < 25:
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    # Decide who speaks
    agent_name = await decide_next_agent()

    # Generate their message
    text = await generate_agent_reply(conversation_history, agent_name)

    # Send it
    await send_agent_message(channel, agent_name, text)

    # Adaptive delay based on message length
    delay = calculate_delay(text)
    await asyncio.sleep(delay)

    # Occasionally (every ~6 cycles) give Sam a moment to check on Vaclav
    cycle_count = len([m for m in conversation_history if "agent" in m])
    if cycle_count % 6 == 0 and cycle_count > 0:
        vaclav_in_recent = any(
            m.get("author") == "Vaclav"
            for m in conversation_history[-8:]
        )
        if not vaclav_in_recent:
            sam_text = await generate_agent_reply(conversation_history, "Sam")
            await send_agent_message(channel, "Sam", sam_text)
            await asyncio.sleep(calculate_delay(sam_text))


@conversation_loop.before_loop
async def before_conversation_loop():
    """Wait until bot is ready before conversation loop runs."""
    await bot.wait_until_ready()


async def setup_webhooks():
    """Create or fetch webhooks for each agent in the target channel."""
    global agent_webhooks, vaclav_voice_webhook

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        logger.error(f"Channel {CHANNEL_ID} not found!")
        return

    existing_webhooks = await channel.webhooks()

    for agent_name in AGENTS:
        # Check if webhook already exists
        webhook = next((wh for wh in existing_webhooks if wh.name == f"ConversationRoom-{agent_name}"), None)
        if not webhook:
            webhook = await channel.create_webhook(name=f"ConversationRoom-{agent_name}")
            logger.info(f"Created webhook for {agent_name}")
        else:
            logger.info(f"Using existing webhook for {agent_name}")
        agent_webhooks[agent_name] = webhook

    # Create webhook for Vaclav's voice input
    vaclav_webhook = next((wh for wh in existing_webhooks if wh.name == "ConversationRoom-VaclavVoice"), None)
    if not vaclav_webhook:
        vaclav_webhook = await channel.create_webhook(name="ConversationRoom-VaclavVoice")
        logger.info("Created webhook for Vaclav voice input")
    else:
        logger.info("Using existing webhook for Vaclav voice input")
    
    # Store URL for audio server
    import os
    os.environ["DISCORD_VOICE_WEBHOOK_URL"] = vaclav_webhook.url
    # Also write to file for audio server process
    try:
        with open("/tmp/discord_voice_webhook.txt", "w") as f:
            f.write(vaclav_webhook.url)
    except Exception as e:
        logger.warning(f"Could not write voice webhook to file: {e}")
    
    logger.info("All agent webhooks ready!")
    logger.info(f"Voice webhook URL: {vaclav_webhook.url}")


# ─── Topic Rotation ─────────────────────────────────────────────────────────
# DISABLED: Rotate topics every 30 minutes. Now controlled by user via !topic commands.
# @tasks.loop(minutes=30)
# async def topic_rotation():
#     ...


# ─── Bot Events ─────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    global conversation_history, current_topic_index, topic_locked, bots_paused, last_vaclav_activity

    logger.info(f"🤖 Bot connected as {bot.user} (ID: {bot.user.id})")
    logger.info(f"📺 Target channel: {CHANNEL_ID}")
    logger.info(f"👤 Vaclav's user ID: {VACLAV_USER_ID}")

    # Restore persisted session state
    state = load_state()
    conversation_history = state.get("conversation_history", [])
    current_topic_index = state.get("current_topic_index", 0)
    topic_locked = state.get("topic_locked", True)
    bots_paused = state.get("paused", False)
    logger.info(f"📂 State loaded from {STATE_PATH}")

    # Webhooks must be ready before any agent can speak (!speak, on_message, etc.)
    await setup_webhooks()

    # Initialize audio server for browser auto-play
    await init_audio_server()
    logger.info("🔊 Audio server initialized (http://localhost:8081)")

    # Warm up Ollama local model (non-blocking, runs in background)
    asyncio.create_task(_warmup_ollama())

    # Welcome back message (no auto topic rotation)
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(get_welcome_message(state, TOPICS))
        save_state(state)

    # Start conversation loop only if not paused and not topic-locked
    if not bots_paused and not topic_locked and not conversation_loop.is_running():
        conversation_loop.start()
        logger.info("▶️ Conversation loop started")
    elif topic_locked:
        logger.info("🔒 Topic locked — bots wait for your message or !speak")
    elif bots_paused:
        logger.info("⏸️ Conversation loop paused (restored from state)")


@bot.event
async def on_message(message: discord.Message):
    """Handle messages — multi-user: any human can talk to bots."""
    global last_vaclav_activity, ignore_bot_messages  # ADD ignore_bot_messages
    
    # ✅ FIX: Ignore messages during !speak execution
    if ignore_bot_messages:
        logger.debug("on_message: ignoring message during !speak")
        return
    
    # ✅ FIX: Ignore ALL bot messages (including self)
    if message.author.bot:
        # Allow Vaclav's voice relay
        if message.content.startswith("🎤 **Vaclav (voice):**"):
            pass  # let it through
        else:
            return  # ignore all other bot messages
    
    # Only respond in the designated channel
    if message.channel.id != CHANNEL_ID:
        return
    
    # Handle commands (let discord.py process them ONCE)
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return  # IMPORTANT: return here, don't reach the end
    
    # MULTI-USER: any human (non-bot) can trigger bots
    is_human = True
    author_name = message.author.name  # real Discord name: Vaclav, Ronny, etc.
    
    # Add to conversation history
    conversation_history.append({
        "author": author_name,
        "content": message.content,
        "timestamp": datetime.now().isoformat(),
        "is_human": is_human,
    })
    
    # Update activity tracking (for any human)
    if is_human:
        last_vaclav_activity = datetime.now()  # reuse variable name
        
        # Save state
        state = load_state()
        state["conversation_history"] = conversation_history[-MAX_HISTORY:]
        state["current_topic_index"] = current_topic_index
        state["paused"] = bots_paused
        state["topic_locked"] = topic_locked
        save_state(state)
    
    # Trigger agent response for ANY human
    logger.info(f"📩 {author_name} said: {message.content}")
    
    # Decide which agent responds
    agent_name = await decide_next_agent()
    
    # Generate and send response
    text = await generate_agent_reply(conversation_history, agent_name, vaclav_recent=True)
    await asyncio.sleep(calculate_delay(text))
    await send_agent_message(message.channel, agent_name, text)
    
    # Sam's follow-up (40% chance)
    if random.random() < 0.4:
        sam_delay = calculate_delay(text) + 1.0
        await asyncio.sleep(sam_delay)
        sam_text = await generate_agent_reply(conversation_history, "Sam", vaclav_recent=True)
        await send_agent_message(message.channel, "Sam", sam_text)


# ─── Commands ───────────────────────────────────────────────────────────────
@bot.command(name="pause")
async def cmd_pause(ctx):
    """Pause agent responses (for when you want quiet time)."""
    global bots_paused
    bots_paused = True
    if conversation_loop.is_running():
        conversation_loop.cancel()
    await ctx.send("⏸️ Agents are muted. Use `!resume` to wake them up.")
    
    # Persist state
    state = load_state()
    state["paused"] = True
    save_state(state)


@bot.command(name="resume")
async def cmd_resume(ctx):
    """Resume agent responses."""
    global bots_paused
    bots_paused = False
    if not conversation_loop.is_running():
        conversation_loop.start()
        await ctx.send("▶️ Agents are back!")
    else:
        await ctx.send("Already running.")
    
    # Persist state
    state = load_state()
    state["paused"] = False
    save_state(state)


@bot.command(name="topic")
async def cmd_topic(ctx, *, subcommand: str = ""):
    """Show current topic, list topics, or change topic.
    
    Usage:
        !topic              - Show current topic
        !topic list         - List all topics with index
        !topic <name/index> - Change topic by name or index
        !topic next         - Go to next topic
    """
    global current_topic_index, topic_locked, bots_paused
    
    subcommand = subcommand.strip().lower()
    
    if not subcommand or subcommand == "show":
        # Show current topic
        topic = TOPICS[current_topic_index]
        embed = discord.Embed(
            title=f"📚 Current Topic: {topic['theme']}",
            description=f"{topic['hook']}\n\n**Key vocabulary:** {', '.join(topic['seed_vocab'])}",
            color=0x5865F2,
        )
        await ctx.send(embed=embed)
        return
    
    if subcommand == "list":
        # List all topics with index
        lines = []
        for i, topic in enumerate(TOPICS):
            marker = "▶️ " if i == current_topic_index else "   "
            lines.append(f"{marker}{i}: {topic['theme']} — {topic['hook'][:60]}...")
        embed = discord.Embed(
            title="📋 Available Topics",
            description="\n".join(lines),
            color=0x5865F2,
        )
        await ctx.send(embed=embed)
        return
    
    if subcommand == "next":
        # Go to next topic
        current_topic_index = (current_topic_index + 1) % len(TOPICS)
        new_topic = TOPICS[current_topic_index]
        await ctx.send(f"🔄 Topic changed to: **{new_topic['theme']}**")
        
        # Persist state
        state = load_state()
        state["current_topic_index"] = current_topic_index
        save_state(state)
        
        openings = await generate_conversation_starter(new_topic)
        for opening in openings:
            delay = calculate_delay(opening["text"])
            await asyncio.sleep(delay)
            await send_agent_message(ctx.channel, opening["agent"], opening["text"])
            
        topic_locked = False
        bots_paused = False
        state["topic_locked"] = False
        state["paused"] = False
        save_state(state)
        if not conversation_loop.is_running():
            conversation_loop.start()
            
        return
    
    # Try to parse as index
    try:
        idx = int(subcommand)
        if 0 <= idx < len(TOPICS):
            current_topic_index = idx
            new_topic = TOPICS[current_topic_index]
            await ctx.send(f"🔄 Topic changed to: **{new_topic['theme']}**")
            
            # Persist state
            state = load_state()
            state["current_topic_index"] = current_topic_index
            save_state(state)
            
            openings = await generate_conversation_starter(new_topic)
            for opening in openings:
                delay = calculate_delay(opening["text"])
                await asyncio.sleep(delay)
                await send_agent_message(ctx.channel, opening["agent"], opening["text"])
                
            topic_locked = False
            state["topic_locked"] = False
            save_state(state)
            if not bots_paused and not conversation_loop.is_running():
                conversation_loop.start()
                
            return
    except ValueError:
        pass
    
    # Try to match by name (partial match)
    subcommand_lower = subcommand.lower()
    for i, topic in enumerate(TOPICS):
        if subcommand_lower in topic["theme"].lower():
            current_topic_index = i
            new_topic = TOPICS[current_topic_index]
            await ctx.send(f"🔄 Topic changed to: **{new_topic['theme']}**")
            
            state = load_state()
            state["current_topic_index"] = current_topic_index
            save_state(state)
            
            openings = await generate_conversation_starter(new_topic)
            for opening in openings:
                delay = calculate_delay(opening["text"])
                await asyncio.sleep(delay)
                await send_agent_message(ctx.channel, opening["agent"], opening["text"])
                
            topic_locked = False
            bots_paused = False
            state["topic_locked"] = False
            state["paused"] = False
            save_state(state)
            if not conversation_loop.is_running():
                conversation_loop.start()
                
            return
    
    await ctx.send(f"❌ Topic not found: `{subcommand}`. Use `!topic list` to see available topics.")


# Global lock to prevent duplicate !speak executions
speak_lock = asyncio.Lock()
# Flag to prevent on_message from responding during !speak
ignore_bot_messages = False

@bot.command(name="speak")
async def cmd_speak(ctx):
    """Invite bots to continue the conversation."""
    global topic_locked, bots_paused, conversation_history, ignore_bot_messages
    
    # ✅ FIX: Prevent duplicate execution
    if speak_lock.locked():
        logger.warning(f"!speak ignored: already running (from {ctx.author.name})")
        return
    
    async with speak_lock:
        # ✅ FIX: Tell on_message to ignore bot messages during this command
        ignore_bot_messages = True
        
        logger.info(f"!speak START from {ctx.author.name}")
        logger.info(f"  conversation_history length: {len(conversation_history)}")

        if not agent_webhooks:
            await setup_webhooks()

        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            await ctx.send("❌ Channel not found.")
            ignore_bot_messages = False
            return

        # Send "Inviting" message ONLY ONCE
        topic = TOPICS[current_topic_index]
        logger.info(f"  Sending: '💬 Inviting bots to speak about {topic['theme']}...'")
        await ctx.send(f"💬 Inviting bots to speak about **{topic['theme']}**...")
        logger.info(f"  Sent 'Inviting' message")

        # Generate opening messages
        openings = await generate_conversation_starter(topic)
        if not openings:
            openings = [
                {"agent": "Alex", "text": f"Hey! Let's talk about {topic['theme']}. {topic['hook']}"},
                {"agent": "Jordan", "text": "I'm in — this should be fun!"},
            ]

        logger.info(f"  Openings to send: {len(openings[:2])}")
        
        # Send opening messages ONLY ONCE
        for i, opening in enumerate(openings[:2]):
            delay = calculate_delay(opening["text"])
            logger.info(f"  Opening {i+1}: {opening['agent']} - {opening['text'][:50]}...")
            await asyncio.sleep(delay)
            await send_agent_message(channel, opening["agent"], opening["text"])
            logger.info(f"  Sent opening {i+1}")
            
            # Add to history to avoid duplication
            conversation_history.append({
                "author": opening["agent"],
                "content": opening["text"],
                "timestamp": datetime.now().isoformat(),
                "is_human": False,
            })

        logger.info(f"  conversation_history length after openings: {len(conversation_history)}")

        # ✅ FIX: DO NOT touch conversation_loop here
        topic_locked = False
        bots_paused = False
        
        # Save state
        state = load_state()
        state["topic_locked"] = False
        state["paused"] = False
        state["conversation_history"] = conversation_history[-MAX_HISTORY:]
        save_state(state)

        await ctx.send("✅ Bots are speaking!")
        logger.info(f"!speak END - sent 'Bots are speaking!'")
        
        # ✅ FIX: Wait a moment, then allow on_message to process again
        await asyncio.sleep(2.0)
        ignore_bot_messages = False
        logger.info(f"!speak DONE - ignore_bot_messages = False")


@bot.command(name="helpme")
async def cmd_helpme(ctx, *, spanish_phrase: str = ""):
    """Get help with a phrase in Spanish."""
    if not spanish_phrase:
        await ctx.send("? Usa `!helpme [frase en español]` para obtener ayuda.")
        return

    prompt = f"Vaclav dijo en español: '{spanish_phrase}'. Dame 3 formas naturales de decir esto en inglés conversacional (B1-B2 level), con explicación corta de cuándo usar cada una. Forma corta y práctica."
    messages = [{"role": "user", "content": prompt}]
    response = await call_openrouter(messages, temperature=0.7)
    if response:
        embed = discord.Embed(
            title="💡 English Help",
            description=f"**Spanish:** {spanish_phrase}\n\n{response}",
            color=0xEB459E,
        )
        await ctx.send(embed=embed)


@bot.command(name="score")
async def cmd_score(ctx):
    """Show Vaclav's session stats."""
    vaclav_msgs = [m for m in conversation_history if m.get("is_vaclav")]
    total = len(vaclav_msgs)
    recent = [m for m in vaclav_msgs if datetime.now() - datetime.fromisoformat(m["timestamp"]) < timedelta(minutes=30)]

    embed = discord.Embed(
        title="📊 Your Session Stats",
        color=0x57F287,
    )
    embed.add_field(name="Messages today", value=str(total))
    embed.add_field(name="Last 30 min", value=str(len(recent)))
    embed.add_field(name="Current streak", value="🔥 Keep going!")
    await ctx.send(embed=embed)


# ─── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        logger.error("❌ DISCORD_BOT_TOKEN not set! Check your .env file.")
        exit(1)
    if not OPENROUTER_API_KEY:
        logger.error("❌ OPENROUTER_API_KEY not set! Check your .env file.")
        exit(1)
    if not CHANNEL_ID or CHANNEL_ID == 0:
        logger.error("❌ CHANNEL_ID not set! Check your .env file.")
        exit(1)

    bot.run(DISCORD_BOT_TOKEN)
