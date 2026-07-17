#!/bin/bash
# auto-sync.sh — Sincroniza el vault con Git
# Uso: hermes ejecuta este script periódicamente desde cron

VAULT="$HOME/Documents/Obsidian-Vault"
cd "$VAULT" || exit 1

# Pull cambios del remoto (si existe)
if git remote get-url origin &>/dev/null; then
    git pull --rebase origin main 2>/dev/null || git pull --rebase origin master 2>/dev/null
fi

# Stage + commit + push si hay cambios
if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -m "auto-sync: $(date '+%Y-%m-%d %H:%M')"
    if git remote get-url origin &>/dev/null; then
        git push origin main 2>/dev/null || git push origin master 2>/dev/null
    fi
    echo "✓ Vault sincronizado: $(date)"
else
    echo "✓ Vault sin cambios: $(date)"
fi
