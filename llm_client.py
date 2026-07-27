"""LLM client router for news briefing — zero discord dependency."""
import os
import logging
from openai import OpenAI, APIStatusError

logger = logging.getLogger("krk-9")

LLM_CLIENTS = []


def _init_llm_clients():
    """Initialize LLM clients for all providers in fallback order."""
    clients = []

    # 1. Cerebras
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    if cerebras_key:
        clients.append({
            "name": "cerebras",
            "client": OpenAI(api_key=cerebras_key, base_url="https://api.cerebras.ai/v1", max_retries=0),
            "model": "gpt-oss-120b",
            "timeout": 15,
            "type": "openai_compatible",
        })

    # 2. Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        clients.append({
            "name": "groq",
            "client": OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1", max_retries=0),
            "model": "llama-3.1-8b-instant",
            "timeout": 15,
            "type": "openai_compatible",
        })

    # 3. OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        clients.append({
            "name": "openrouter",
            "client": OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1", max_retries=0),
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "timeout": 30,
            "type": "openai_compatible",
        })

    # 4. Ollama local (native endpoint)
    clients.append({
        "name": "ollama_local",
        "client": None,
        "model": "qwen2.5:3b",
        "timeout": 120,
        "type": "ollama_native",
        "url": "http://localhost:11434/api/chat",
    })

    return clients


LLM_CLIENTS = _init_llm_clients()


async def _call_ollama_native(messages, model, temperature, max_tokens, timeout, url):
    """Call Ollama native /api/chat endpoint."""
    import httpx
    prompt = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "user")
    if not prompt:
        return ""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


async def call_openrouter(messages, system="", temperature=0.8,
                          provider_override=None, model_override=None, max_tokens=300) -> str:
    """Router con fallback automático: Cerebras → Groq → OpenRouter → Ollama local.

    Si provider_override se establece, intenta ese proveedor primero.
    Devuelve el texto generado o None si todo falla.
    """
    import httpx
    payload_messages = []
    if system:
        payload_messages.append({"role": "system", "content": system})
    payload_messages.extend(messages)

    # Build provider list: if override is set, try it first
    providers_to_try = list(LLM_CLIENTS)
    if provider_override:
        override_name = provider_override.replace("ollama", "ollama_local") if provider_override == "ollama" else provider_override
        override_client = next((p for p in LLM_CLIENTS if p["name"] == override_name), None)
        if override_client:
            override_entry = dict(override_client)
            if model_override:
                override_entry["model"] = model_override
            providers_to_try = [override_entry] + [p for p in LLM_CLIENTS if p["name"] != override_name]
            logger.info(f"🎯 LLM override: trying {provider_override}/{model_override or override_entry['model']} first")

    last_error = None
    for provider in providers_to_try:
        try:
            if provider["type"] == "ollama_native":
                content = await _call_ollama_native(
                    messages=payload_messages,
                    model=provider["model"],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=provider.get("timeout", 120),
                    url=provider["url"],
                )
            else:
                resp = provider["client"].chat.completions.create(
                    model=provider["model"],
                    messages=payload_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=provider.get("timeout", 15),
                )
                content = resp.choices[0].message.content

            logger.info(f"✅ LLM response from {provider['name']} ({provider['model']})")
            return content

        except Exception as e:
            last_error = e
            if provider["type"] == "openai_compatible":
                status_code = getattr(e, "status_code", None)
                if status_code == 429:
                    logger.warning(f"⚠️ {provider['name']} rate limited (429), trying next...")
                    continue
            logger.warning(f"⚠️ {provider['name']} exception: {e}")
            continue

    logger.error(f"❌ ALL LLM PROVIDERS FAILED. Last error: {last_error}")
    return None