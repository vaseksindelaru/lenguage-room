# KRK-9: Customization Guide

Want to rebrand KRK-9 for your own community? This guide shows you how — **no coding required**.

## 1. Changing the Logo

### Option A: Replace the default logo
1. Prepare your logo as a **PNG or JPG** (recommended size: 300×120 px).
2. Place it in the `static/` folder:
   ```bash
   cp my-logo.png static/logo.png
   ```
3. Restart the audio server:
   ```bash
   ./start.sh --stop
   ./start.sh
   ```
4. Open `http://localhost:8081` — your logo should appear.

### Option B: Use an SVG (scalable, small file size)
1. Convert your logo to SVG (use [Inkscape](https://inkscape.org) or [Adobe Illustrator](https://www.adobe.com/products/illustrator.html)).
2. Place it in `static/logo.svg`.
3. Edit `audio_player.html`, line ~135:
   ```html
   <!-- Change this line: -->
   <img id="logo" src="/static/logo.png" ...>
   <!-- To: -->
   <img id="logo" src="/static/logo.svg" ...>
   ```

### Fallback: If no logo is found
The app shows **"KRK-9"** as text (styled with CSS). You can customize this text in `audio_player.html`, line ~140:
```html
<h1 id="logo-text" ...>KRK-9</h1>
<!-- Change "KRK-9" to your app's name -->
```

## 2. Changing Colors

The app uses a **dark theme** with Discord-inspired colors. To change them:

### Main colors (in `audio_player.html`)
Edit the `<style>` section (starts at line ~7):

| Element | CSS Variable | Default Color | Description |
|---------|---------------|----------------|-------------|
| Background | `body { background: ... }` | `#1a1a2e` | Dark blue-black |
| Primary accent | `.btn-primary { background: ... }` | `#5865f2` | Discord blurple |
| Success | `.status.connected { ... }` | `#57f287` | Green |
| Warning | `.status.connecting { ... }` | `#fee75c` | Yellow |
| Error | `.status.disconnected { ... }` | `#ed4245` | Red |

**Example**: To change the primary accent to **orange**:
1. Open `audio_player.html`.
2. Search for `#5865f2` (Discord blurple).
3. Replace with your color (e.g., `#ff7b00` for orange).

### Agent colors (in `bot.py`)
Each agent has a color for their Discord embed. To change:
1. Open `bot.py`.
2. Find the `AGENTS` dict (line ~55):
   ```python
   "Alex": {"color": 0x5865F2, "emoji": "🟦", "voice": "..."},
   #          ^^^^^^^^ Change this hex code (without "0x")
   ```
3. Replace the hex code (e.g., `0xff7b00` for orange).

## 3. Changing Agent Names & Personas

### Renaming an agent
1. Open `bot.py`.
2. In the `AGENTS` dict (line ~55), change the **key** (e.g., `"Alex"` → `"Alexa"`).
3. In the `AGENT_PERSONAS` dict (line ~102), change the **key** to match.
4. Update the `audio_player.html` agent cards (lines ~136-161) to reflect the new name/emoji.

### Changing an agent's personality
Edit their **system prompt** in `AGENT_PERSONAS` (line ~102):
```python
"Alex": """You are Alex — [Your new description here]..."""
```

**Tip**: Keep prompts **short and specific** for better responses.

## 4. Adding/Removing Agents

### Adding a 5th agent ("Luna")
1. **`bot.py`**:
   - Add to `AGENTS` (line ~55):
     ```python
     "Luna": {"color": 0x9B59B6, "emoji": "🟣", "voice": "en-US-EchoNeural"}
     ```
   - Add persona to `AGENT_PERSONAS` (line ~102):
     ```python
     "Luna": """You are Luna — The Slang Expert..."""
     ```
2. **`audio_player.html`**:
   - Copy an existing `.agent-card` div (lines ~136-161).
   - Paste it after the last agent card.
   - Update `id`, `agent-emoji`, `agent-name`, `agent-voice`.
3. **Restart** the bot:
   ```bash
   ./start.sh --stop && ./start.sh
   ```

### Removing an agent
1. Remove their entry from `AGENTS` and `AGENT_PERSONAS` in `bot.py`.
2. Remove their `.agent-card` div in `audio_player.html`.
3. Restart.

## 5. Custom CSS (Advanced)

Want a **completely different look**? Add your own CSS file:
1. Create `static/custom.css` with your styles.
2. Edit `audio_player.html`, just before `</head>` (line ~130):
   ```html
   <link rel="stylesheet" href="/static/custom.css">
   ```
3. Your custom CSS will override the default styles.

## 6. Changing the Invite Button Text

To change the "Invitar amigos" button text:
1. Open `audio_player.html`.
2. Find the button (line ~482):
   ```html
   <button id="btnInvite" ...>👥 Invitar amigos</button>
   <!-- Change the text between > and </button> -->
   ```
3. Save and refresh `http://localhost:8081`.

## 7. Using a Custom Domain (for production)

If you want to deploy KRK-9 on a server with a domain:
1. Update `AUDIO_SERVER_URL` in `bot.py` (line ~42) to your domain:
   ```python
   AUDIO_SERVER_URL = "https://your-domain.com:8081/api/audio"
   ```
2. Set up **HTTPS** (required for Web Speech API). Use [Let's Encrypt](https://letsencrypt.org) or a reverse proxy (nginx, Caddy).
3. Update Discord redirect URLs in your bot settings (Discord Developer Portal).

## 8. Environment-Based Customization

You can make certain UI elements configurable via `.env`:
1. Add a variable to `.env.example`:
   ```bash
   APP_NAME=KRK-9
   LOGO_PATH=/static/logo.png
   PRIMARY_COLOR=#5865f2
   ```
2. In `audio_server.py`, read these variables and **render them into `audio_player.html`** (instead of serving it as a static file).
   - See `index_handler()` function (line ~86) — currently uses `FileResponse`.
   - Change it to `web.Response(text=html_content, content_type='text/html')`.

## Troubleshooting

### "My logo doesn't appear"
- Check the file path: `static/logo.png` (case-sensitive).
- Open browser DevTools (F12) → **Network** tab → reload. Check if the logo request returns 404.
- Ensure the audio server is running (`curl http://localhost:8081/health`).

### "Colors didn't change"
- Hard refresh the browser: `Ctrl+F5` (Windows/Linux) or `Cmd+Shift+R` (Mac).
- Clear browser cache.

### "Agent cards are misaligned"
- Check your CSS changes in `.agents-grid` (line ~23 in `audio_player.html`).
- Use browser DevTools → **Inspect Element** to debug.

---
**Need help?** Open an [issue](https://github.com/vaseksindelaru/lenguage-room/issues) or check `README_DEVS.md`.
