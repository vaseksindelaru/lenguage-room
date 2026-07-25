# Graph Report - .  (2026-07-25)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 272 nodes · 557 edges · 16 communities (15 shown, 1 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 38 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f7818bd5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- audio_server.py
- state_manager.py
- save_state
- bot.py
- send_agent_message
- install-krk9.sh
- load_personas
- call_openrouter
- start.sh
- on_casete_help
- generate_tts
- setup_wizard.py
- news_config.py
- cmd_speak
- get_topic
- run_audio.sh

## God Nodes (most connected - your core abstractions)
1. `load_state()` - 44 edges
2. `start_audio_server()` - 35 edges
3. `save_state()` - 26 edges
4. `send_agent_message()` - 16 edges
5. `call_openrouter()` - 14 edges
6. `on_message()` - 12 edges
7. `generate_briefing()` - 12 edges
8. `load_personas()` - 11 edges
9. `main()` - 10 edges
10. `register_news_routes()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `start_audio_server()` --indirect_call--> `news_config_get_handler()`  [INFERRED]
  audio_server.py → news_gui_routes.py
- `start_audio_server()` --indirect_call--> `news_config_post_handler()`  [INFERRED]
  audio_server.py → news_gui_routes.py
- `start_audio_server()` --indirect_call--> `news_config_reset_handler()`  [INFERRED]
  audio_server.py → news_gui_routes.py
- `start_audio_server()` --indirect_call--> `news_config_validate_handler()`  [INFERRED]
  audio_server.py → news_gui_routes.py
- `start_audio_server()` --indirect_call--> `news_gui_handler()`  [INFERRED]
  audio_server.py → news_gui_routes.py

## Import Cycles
- None detected.

## Communities (16 total, 1 thin omitted)

### Community 0 - "audio_server.py"
Cohesion: 0.05
Nodes (63): active_agents_get_handler(), active_agents_post_handler(), assistant_chat_handler(), broadcast_audio(), broadcast_audio_http(), chat_handler(), _detect_llm_providers(), health_handler() (+55 more)

### Community 1 - "state_manager.py"
Cohesion: 0.07
Nodes (43): Any, cmd_session(), cmd_sessions(), Lista las sesiones guardadas del usuario., Subcomandos: new, resume, save., append_session_message(), create_user_session(), _deep_merge() (+35 more)

### Community 2 - "save_state"
Cohesion: 0.08
Nodes (38): cmd_pause(), cmd_preferences(), cmd_resume(), Pause agent responses (for when you want quiet time)., Resume agent responses., !preferences [add|remove|clear|list] <words...>, Valida la config. Lanza ValueError si algo está mal., validate_news_config() (+30 more)

### Community 3 - "bot.py"
Cohesion: 0.15
Nodes (16): init_audio_server(), Called by bot.py - server runs externally, just verify it's up., before_conversation_loop(), _call_ollama_native(), cmd_score(), _init_llm_clients(), on_ready(), ============================================================================= "K (+8 more)

### Community 4 - "send_agent_message"
Cohesion: 0.16
Nodes (14): extract_notable_words(), generate_tts(), get_avatar_url(), on_message(), Handle messages — multi-user: any human can talk to bots., Extrae palabras notables: ≥4 letras, solo alfabéticas, no stopwords EN., Generate TTS audio. Delegado a tts_providers para soportar Edge + ElevenLabs., Send a message via webhook to appear as the agent, with TTS audio streamed to br (+6 more)

### Community 5 - "install-krk9.sh"
Cohesion: 0.42
Nodes (11): clone_repo(), install_deps(), main(), print_error(), print_header(), print_step(), print_success(), setup_env() (+3 more)

### Community 6 - "load_personas"
Cohesion: 0.18
Nodes (12): calculate_delay(), cmd_video(), conversation_loop(), decide_next_agent(), generate_agent_reply(), Fetch YouTube video transcript and discuss with bots. !video <URL>, Delay = base + max(reading_time, audio_time) + jitter. Range: 3–15s., Generate a reply from a specific agent based on conversation context. (+4 more)

### Community 7 - "call_openrouter"
Cohesion: 0.18
Nodes (12): call_openrouter(), cmd_helpme(), cmd_topic(), generate_conversation_starter(), generate_coordinator_decision(), generate_topic_suggestions(), !topic [list|next|suggest|refresh|pick <texto>|index], Genera 5 temas sugeridos basados en intereses del user. Cacheado por hash. (+4 more)

### Community 8 - "start.sh"
Cohesion: 0.42
Nodes (10): check_env(), is_audio_healthy(), is_bot_running(), is_ollama_up(), port_in_use(), print_success(), start.sh script, start_docker() (+2 more)

### Community 9 - "on_casete_help"
Cohesion: 0.20
Nodes (10): cmd_casete(), extract_target_word(), maybe_invoke_casete(), on_casete_help(), Pide a Casete que sople una palabra. !casete <word>, Extrae la palabra objetivo de un mensaje tipo 'cómo se dice <word>'.          He, Trunca la respuesta de Casete a ~20 tokens sin partir palabras., Responde a la petición de vocabulario de un jugador.          Regla de oro: la p (+2 more)

### Community 10 - "generate_tts"
Cohesion: 0.33
Nodes (8): _clean_text(), generate_tts(), _generate_tts_edge(), _generate_tts_elevenlabs(), TTS providers for KRK-9. Soporta dos providers:   - edge   : edge_tts (Microsoft, Dispatch según el tipo de voice.          Args:         text: texto a sintetizar, Edge TTS (código actual, sin cambios funcionales)., ElevenLabs TTS via REST API. Fallback automático a Edge si falla.

### Community 11 - "setup_wizard.py"
Cohesion: 0.52
Nodes (6): ask_input(), ask_yes_no(), check_dependency(), main(), print_header(), print_step()

### Community 12 - "news_config.py"
Cohesion: 0.33
Nodes (5): get_news_config(), News Room GUI: configuration editor and management endpoints., Devuelve la config de noticias del usuario (o defaults)., Guarda la config en memoria (persistencia via save_state externa)., save_news_config()

### Community 13 - "cmd_speak"
Cohesion: 0.50
Nodes (4): cmd_speak(), Invite bots to continue the conversation., Create or fetch webhooks for each agent in the target channel., setup_webhooks()

### Community 14 - "get_topic"
Cohesion: 0.50
Nodes (4): get_topic(), load_topics(), Load topics from JSON file, or create default if not exists., Get topic based on day of week (Monday=0).

## Knowledge Gaps
- **1 isolated node(s):** `run_audio.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_state()` connect `audio_server.py` to `state_manager.py`, `save_state`, `bot.py`, `send_agent_message`, `load_personas`, `call_openrouter`, `on_casete_help`, `cmd_speak`?**
  _High betweenness centrality (0.169) - this node is a cross-community bridge._
- **Why does `save_state()` connect `save_state` to `audio_server.py`, `state_manager.py`, `bot.py`, `send_agent_message`, `call_openrouter`, `cmd_speak`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `generate_tts()` connect `generate_tts` to `audio_server.py`, `bot.py`, `send_agent_message`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `start_audio_server()` (e.g. with `active_agents_get_handler()` and `active_agents_post_handler()`) actually correct?**
  _`start_audio_server()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `run_audio.sh script` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `audio_server.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0506558118498417 - nodes in this community are weakly interconnected._
- **Should `state_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06659619450317125 - nodes in this community are weakly interconnected._