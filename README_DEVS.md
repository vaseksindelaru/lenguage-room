# KRK-9: English Practice Room — Developer Guide

## Architecture Overview

KRK-9 is a multi-agent Discord bot that simulates a conversation room with 4 AI personas. It uses:
- **Discord.py** for the bot interface
- **WebSocket + HTTP** for real-time audio streaming to browsers
- **Multi-LLM Router** (Cerebras → Groq → OpenRouter → Ollama) for responses
- **Edge-TTS** for text-to-speech
- **Web Speech API** for browser-based speech recognition

## Project Structure

```
krk-9/
├── bot.py                 # Main Discord bot + agent logic
├── audio_server.py        # WebSocket/HTTP server for browser audio
├── audio_player.html     # Browser UI (audio player + voice input)
├── state_manager.py      # Persistence (conversation history, settings)
├── requirements.txt       # Python dependencies
├── docker-compose.yml    # Docker setup (optional)
├── start.sh              # Local dev startup script
├── install-krk9.sh      # One-click installer for end users
├── setup_wizard.py      # Interactive configuration wizard
├── static/              # User-customizable assets (logo, CSS)
│   └── logo.png        # App logo (optional, falls back to text)
├── .env.example         # Environment template
├── README_USERS.md      # End-user documentation
├── README_DEVS.md       # This file
└── CUSTOMIZATION.md     # Branding & customization guide
```

## Key Components

### 1. **Discord Bot (`bot.py`)**
- Listens for messages in a specific channel (`CHANNEL_ID`)
- Uses **webhooks** to post as 4 different "agents" (Alex, Maya, Jordan, Sam)
- Routes LLM requests through a **fallback chain**: Cerebras → Groq → OpenRouter → Ollama
- **Sam** is the tutor agent: gently corrects grammar for the user (Vaclav)

#### Adding a New Agent:
1. Add agent config to `AGENTS` dict (line ~55):
   ```python
   "NewAgent": {"color": 0xHEXCODE, "emoji": "🟩", "voice": "en-US-VoiceNeural"}
   ```
2. Add persona to `AGENT_PERSONAS` dict (line ~102):
   ```python
   "NewAgent": """You are NewAgent — [personality description]..."""
   ```
3. Update `TOPICS` rotation if needed.

### 2. **Audio Server (`audio_server.py`)**
- **WebSocket** (`/ws`): Streams TTS audio to browsers in real-time
- **HTTP endpoints**:
  - `/api/audio` (POST): Bot sends audio to browsers
  - `/api/voice` (POST): Browser sends recognized speech to Discord
  - `/api/invite` (GET): Generates Discord invite link
  - `/health` (GET): Health check
  - `/static/` (GET): Serves user assets (logo, custom CSS)

#### Adding a New API Endpoint:
```python
async def new_endpoint_handler(request):
    # Your logic here
    return web.json_response({"status": "ok"})

# In start_audio_server():
app.router.add_get('/api/new-endpoint', new_endpoint_handler)
```

### 3. **Browser UI (`audio_player.html`)**
- Displays agent status (speaking indicator)
- **Voice input**: Uses Web Speech API (requires HTTPS or localhost)
- **Audio playback**: Receives base64 audio via WebSocket, plays with Web Audio API
- **Invite button**: Calls `/api/invite` to generate Discord invite

#### Customizing the UI:
- **Logo**: Place your logo at `static/logo.png` (or update `<img src>` in HTML)
- **Colors**: Edit CSS variables in `<style>` section
- **Agent cards**: Modify `.agent-card` divs (lines ~136-161)

## Environment Configuration (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Discord bot token | *Required* |
| `CHANNEL_ID` | Discord channel ID for bot | *Required* |
| `GUILD_ID` | Discord guild (server) ID | *Required* |
| `VACLAV_USER_ID` | Your Discord user ID (for tutor corrections) | `0` |
| `OLLAMA_URL` | Ollama local endpoint | `http://localhost:11434` |
| `CEREBRAS_API_KEY` | Cerebras API key (free tier) | Optional |
| `GROQ_API_KEY` | Groq API key (free tier) | Optional |
| `OPENROUTER_API_KEY` | OpenRouter API key (`:free` models) | Optional |
| `DISCORD_VOICE_WEBHOOK_URL` | Webhook for voice messages | Optional |

## LLM Provider Fallback Chain

The bot tries providers in this order (defined in `_init_llm_clients()`):
1. **Cerebras** (`gpt-oss-120b`) — 1M tokens/day free
2. **Groq** (`llama-3.1-8b-instant`) — Fast, free
3. **OpenRouter** (`meta-llama/llama-3.3-70b-instruct:free`) — Free tier
4. **Ollama** (`qwen2.5:3b`) — Local fallback (always available)

To modify:
- Edit `_init_llm_clients()` in `bot.py` (line ~270)
- Update `.env` with your API keys

## Development Workflow

### 1. Local Setup
```bash
# Clone repo
git clone https://github.com/vaseksindelaru/lenguage-room.git krk9
cd krk9

# Create venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Discord bot token, channel ID, etc.

# Start Ollama (if using local LLM)
ollama serve
ollama pull qwen2.5:3b

# Run bot + audio server
./start.sh
```

### 2. Docker Setup (Alternative)
```bash
# Build and start all services
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down
```

### 3. Testing
- **Bot**: Type in Discord channel → agents should respond
- **Audio**: Open `http://localhost:8081` → click "Test audio"
- **Voice**: Click "Hold to speak" → allow mic → speak → check Discord for message

### 4. Debugging
- **Bot logs**: `.pids/bot.log`
- **Audio server logs**: `.pids/audio.log`
- **Ollama logs**: `.pids/ollama.log`

## Contributing

### Pull Request Process
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- **Python**: Follow PEP 8 (use `black` formatter)
- **JavaScript**: Use 2-space indentation
- **Commit messages**: Use conventional commits (e.g., `feat:`, `fix:`, `docs:`)

### Adding a Feature (Example)
**Goal**: Add a 5th agent ("Luna") that specializes in slang and informal English.

1. **`bot.py`**:
   - Add to `AGENTS` dict:
     ```python
     "Luna": {"color": 0x9B59B6, "emoji": "🟣", "voice": "en-US-EchoNeural"}
     ```
   - Add persona to `AGENT_PERSONAS`:
     ```python
     "Luna": """You are Luna — The Slang Expert..."""
     ```
2. **`audio_player.html`**:
   - Add agent card div (copy existing card, update ID/name/emoji)
3. **Test**: Run bot, type in Discord → Luna should respond.

## Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic_core'"
- **Cause**: `PYTHONPATH` contamination from host environment
- **Fix**: `start.sh` already has `unset PYTHONPATH`. If running manually, execute:
  ```bash
  unset PYTHONPATH
  venv/bin/python bot.py
  ```

### "Audio server not responding"
- Check if port 8081 is free: `ss -tln | grep 8081`
- Check logs: `tail -f .pids/audio.log`
- Restart: `./start.sh --stop && ./start.sh`

### "Discord bot not responding"
- Verify bot token in `.env`
- Check bot logs: `tail -f .pids/bot.log`
- Ensure bot has **Message Content Intent** enabled in Discord Developer Portal

## Future Roadmap
- [ ] **Multi-user support**: Bots respond to any human in channel (not just Vaclav)
- [ ] **Voice channels**: Detect users in voice chat, greet them
- [ ] **Roger integration**: Merge with [Roger project](https://github.com/arturcloe2084-eng/roger_willkommen) for enhanced capabilities
- [ ] **Mobile app**: React Native or Flutter frontend
- [ ] **More LLM providers**: Claude, GPT-4, local LLaMA variants

## License
**MIT License** — Free for personal and commercial use. No attribution required, but appreciated.

---
**Questions?** Open an [issue](https://github.com/vaseksindelaru/lenguage-room/issues) or join our Discord (invite in `README_USERS.md`).
