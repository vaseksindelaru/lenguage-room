#!/bin/bash
# English Practice Bot - Quick Start Script
# Usage:
#   ./start.sh              # Local (default, recommended)
#   ./start.sh --docker     # Full Docker stack
#   ./start.sh --stop       # Stop local services

set -e

# CRITICAL: Unset PYTHONPATH to avoid contamination from host/Hermes environments
# This ensures the venv is properly isolated
unset PYTHONPATH

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-local}"
VENV_PYTHON="${SCRIPT_DIR}/venv/bin/python"
PID_DIR="${SCRIPT_DIR}/.pids"
mkdir -p "$PID_DIR" ~/.english-bot

print_success() {
    echo ""
    echo "✅ English Practice Bot running!"
    echo "🌐 Audio UI: http://localhost:8081"
    echo "💬 Discord: join your practice channel"
    echo ""
    echo "🎤 In the browser: click 'Test audio' → allow mic → hold 🎤 to speak"
    echo "💬 In Discord: type or use !speak to invite bots"
}

check_env() {
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            echo "⚠️  Created .env from .env.example"
            echo "   Please edit .env with your API keys before continuing!"
            exit 1
        else
            echo "❌ No .env.example found. Please create .env manually."
            exit 1
        fi
    fi
}

is_audio_healthy() {
    curl -sf http://localhost:8081/health > /dev/null 2>&1
}

is_ollama_up() {
    curl -sf http://localhost:11434/api/tags > /dev/null 2>&1
}

is_bot_running() {
    pgrep -f "${SCRIPT_DIR}/venv/bin/python bot.py" > /dev/null 2>&1
}

port_in_use() {
    ss -tln 2>/dev/null | grep -q ":$1 " || netstat -tln 2>/dev/null | grep -q ":$1 "
}

stop_local() {
    echo "🛑 Stopping local services..."
    if [ -f "${PID_DIR}/bot.pid" ]; then
        kill "$(cat "${PID_DIR}/bot.pid")" 2>/dev/null || true
        rm -f "${PID_DIR}/bot.pid"
    fi
    pkill -f "${SCRIPT_DIR}/venv/bin/python bot.py" 2>/dev/null || true
    if [ -f "${PID_DIR}/audio.pid" ]; then
        kill "$(cat "${PID_DIR}/audio.pid")" 2>/dev/null || true
        rm -f "${PID_DIR}/audio.pid"
    fi
    pkill -f "${SCRIPT_DIR}/venv/bin/python audio_server.py" 2>/dev/null || true
    echo "✅ Local bot and audio server stopped"
    echo "   (Ollama left running — stop manually if needed: pkill ollama)"
}

start_local() {
    echo "🚀 Starting English Practice Bot (local mode)..."
    check_env

    if [ ! -x "$VENV_PYTHON" ]; then
        echo "📦 Creating venv..."
        python3 -m venv venv
        "$VENV_PYTHON" -m pip install -q -r requirements.txt
    fi

    if ! is_ollama_up; then
        echo "🦙 Starting Ollama..."
        if command -v ollama &>/dev/null; then
            ollama serve > "${PID_DIR}/ollama.log" 2>&1 &
            echo $! > "${PID_DIR}/ollama.pid"
            sleep 2
        else
            echo "⚠️  Ollama not running. Install from https://ollama.com"
        fi
    else
        echo "✅ Ollama: running"
    fi

    if ! is_audio_healthy; then
        echo "🔊 Starting audio server..."
        "$VENV_PYTHON" audio_server.py > "${PID_DIR}/audio.log" 2>&1 &
        echo $! > "${PID_DIR}/audio.pid"
        sleep 2
    else
        echo "✅ Audio server: healthy"
    fi

    if is_bot_running; then
        echo "✅ Bot: already running — restart with: ./start.sh --stop && ./start.sh"
    else
        echo "🤖 Starting Discord bot..."
        : > "${PID_DIR}/bot.log"
        "$VENV_PYTHON" bot.py >> "${PID_DIR}/bot.log" 2>&1 &
        echo $! > "${PID_DIR}/bot.pid"
        sleep 5
        if grep -q "LoginFailure\|401 Unauthorized" "${PID_DIR}/bot.log" 2>/dev/null; then
            echo "❌ Bot failed: invalid DISCORD_BOT_TOKEN"
            echo "   → Discord Developer Portal → Bot → Reset Token → update .env"
            tail -5 "${PID_DIR}/bot.log"
            exit 1
        fi
        if ! is_bot_running; then
            echo "❌ Bot crashed on startup:"
            tail -15 "${PID_DIR}/bot.log"
            exit 1
        fi
        if ! grep -q "connected to Gateway" "${PID_DIR}/bot.log" 2>/dev/null; then
            echo "⚠️  Bot starting... check: tail -f .pids/bot.log"
        else
            echo "✅ Bot: connected to Discord"
        fi
    fi

    if is_audio_healthy; then
        print_success
        echo "🛑 To stop: ./start.sh --stop"
        echo "📝 Logs: tail -f .pids/bot.log"
    else
        echo "⚠️  Audio server not responding. Check: tail -f .pids/audio.log"
        exit 1
    fi
}

start_docker() {
    echo "🚀 Starting English Practice Bot (docker mode)..."

    if docker compose version &>/dev/null; then
        COMPOSE="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE="docker-compose"
    else
        echo "❌ Docker Compose not found. Use: ./start.sh --local"
        exit 1
    fi

    check_env

    if is_bot_running || port_in_use 8081; then
        echo "⚠️  Port 8081 in use (local audio server running)."
        echo "   Stop local first: ./start.sh --stop"
        echo "   Or use local mode: ./start.sh --local"
        exit 1
    fi

    echo "🐳 Starting services with $COMPOSE..."
    $COMPOSE up -d --build

    echo "⏳ Waiting for services..."
    for i in 1 2 3 4 5 6; do
        sleep 5
        if is_audio_healthy; then break; fi
    done

    if is_audio_healthy; then
        echo "✅ Audio server: healthy"
        print_success
    else
        echo "⚠️  Audio server not ready. Check: $COMPOSE logs -f"
        exit 1
    fi
    echo "🛑 To stop: $COMPOSE down"
    echo "📝 Logs: $COMPOSE logs -f"
}

case "$MODE" in
    --local|-l|local) start_local ;;
    --docker|-d|docker) start_docker ;;
    --stop|-s|stop) stop_local ;;
    *)
        echo "Usage: ./start.sh [--local|--docker|--stop]"
        exit 1
        ;;
esac
