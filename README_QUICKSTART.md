# Quick Start (30 seconds)

## Option A: Local (recommended if Ollama already installed)

1. `cp .env.example .env` && edit API keys (especially `DISCORD_BOT_TOKEN`)
2. `./start.sh --local`
3. Open `http://localhost:8081` → click "Test audio"
4. Go to Discord → speak or type in practice channel
5. Next time: `./start.sh --local`

## Option B: Docker (full stack)

1. `cp .env.example .env` && edit API keys
2. `./start.sh` or `./start.sh --docker`
3. First run downloads Ollama image (~3 GB) — be patient
4. Open `http://localhost:8081` → click "Test audio"

## Commands in Discord

| Command | Action |
|---------|--------|
| `!speak` | Invite bots to talk |
| `!topic list` | See all topics |
| `!topic next` | Change topic |
| `!pause` / `!resume` | Mute/unmute bots |

## Troubleshooting

- **401 Unauthorized / LoginFailure** → Regenerate bot token in Discord Developer Portal, update `.env`
- **Audio not playing** → Click "Test audio" in browser first
- **Bots too quiet** → Use `!speak` (they don't auto-chat by default)