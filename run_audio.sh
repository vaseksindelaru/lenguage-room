#!/bin/bash
cd /home/vaclav/discord-english-room
unset PYTHONPATH
exec venv/bin/python audio_server.py
