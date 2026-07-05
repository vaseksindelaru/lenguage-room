# English Practice Bot 🎧

Discord bot for English conversation practice with **4 AI agents**, **TTS audio**, and **speech recognition**.

## Features

- **4 AI Agents** with distinct personalities:
  - 🟦 **Alex** - The Curious One (asks questions)
  - 🟩 **Maya** - The Structured Thinker (organizes ideas)
  - 🟧 **Jordan** - The Enthusiast (brings stories/energy)
  - 🟪 **Sam** - The Patient Tutor (corrects grammar gently)

- **Multi-LLM Router** with automatic fallback:
  1. **Cerebras** (llama-3.3-70b) - 1M tokens/day free
  2. **Groq** (llama-3.1-8b-instant) - LPU ultra-fast
  3. **OpenRouter** (meta-llama/llama-3.3-70b:free) - diversified
  4. **Ollama local** (qwen2.5:3b) - offline fallback

- **Audio Pipeline**:
  - **TTS**: Edge-TTS (free, no API key) → WebSocket to browser
  - **STT**: Web Speech API (native browser) → Discord webhook

- **Auto topic rotation** every 30 minutes
- **Gentle grammar corrections** by Sam

## Quick Start

### Local Development
```bash
# 1. Clone and setup
git clone https://github.com/yourusername/discord-english-practice-bot.git
cd discord-english-practice-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Start Ollama (local LLM fallback)
ollama serve &
ollama pull qwen2.5:3b

# 5. Start audio server
python audio_server.py

# 6. Start bot
python bot.py

# 7. Open http://localhost:8081 in browser for audio + mic
```

### Docker (Production)
```bash
# 1. Create .env with your secrets
cp .env.example .env
# Edit .env

# 2. Start all services
docker-compose up -d

# 3. Open http://localhost:8081 in browser
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_BOT_TOKEN` | Discord bot token | ✅ |
| `OPENROUTER_API_KEY` | OpenRouter API key | ✅ |
| `CEREBRAS_API_KEY` | Cerebras API key (free) | ✅ |
| `GROQ_API_KEY` | Groq API key (free) | ✅ |
| `CHANNEL_ID` | Discord channel ID | ✅ |
| `VACLAV_USER_ID` | Your Discord user ID | ✅ |
| `OPENROUTER_MODEL` | Model to use via OpenRouter | ⭕ |

## How to Use

1. **Open** `http://localhost:8081` in Chrome/Edge
2. **Click "Test audio"** to unlock AudioContext
3. **Go to Discord** → your practice channel
4. **Hold 🎤 "Mantén para hablar"** and speak English
5. **Release** → transcription posts to Discord
5. **Agents respond** with text + audio (plays in browser)
6. **Sam** gently corrects grammar: *"(Quick note: 'would went' → 'would have gone'...)"*

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│ Audio Server │────▶│   Discord   │
│  (STT/TTS)  │◀───│ (WebSocket)  │     │  (Webhook)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   Discord   │
                    │     Bot     │
                    │  (LLM Router)│
                    └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌─────────┐  ┌─────────┐  ┌─────────┐
         │ Cerebras│  │  Groq   │  │OpenRouter│
         └─────────┘  └─────────┘  └─────────┘
              │            │            │
              └────────────┼────────────┘
                           ▼
                    ┌─────────────┐
                    │  Ollama     │
                    │  (local)    │
                    └─────────────┘
```

## Cost: $0/month

All services used have generous free tiers:
- **Cerebras**: 1M tokens/day free
- **Groq**: ~14K requests/day free
- **OpenRouter**: 50-1000 req/day free
- **Ollama**: Runs locally (electricity only)
- **Edge-TTS**: Free (Microsoft Edge service)

## License

MIT