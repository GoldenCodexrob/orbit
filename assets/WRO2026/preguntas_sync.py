"""
preguntas_sync.py  —  Orbit live question sync
-----------------------------------------------
Polls JSONBin every 30 seconds and updates PREGUNTAS_CUSTOM in memory.
The robot answers custom questions offline using keyword matching,
and picks up new questions from the web app without restarting.

Setup:
  pip install requests   (usually already installed)
  Replace this file in asistente_ia_venezuela/ on the robot.

Integration in venezuela_bot.py:
  from preguntas_sync import responder_offline, start_sync

  start_sync()   # call once at startup

  # Before LLM call:
  respuesta = responder_offline(texto_del_usuario)
  if respuesta:
      hablar(respuesta)
  else:
      # normal LLM call ...
"""

import json
import threading
import time
import os

import requests  # pip install requests

# ── Config ────────────────────────────────────────────────────────────────────
JSONBIN_BIN_ID  = "6a861dafda38895dfef8caf8"
JSONBIN_KEY     = "$2a$10$3gfM9M2cDfXmdEl2mXo6COmqhMwgM5QbZ5MK4cUw2PHevDP4JtOBi"
POLL_INTERVAL   = 30          # seconds between cloud checks
CACHE_FILE      = os.path.join(os.path.dirname(__file__), "preguntas_cache.json")
JSONBIN_READ_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"

# ── State (thread-safe via lock) ──────────────────────────────────────────────
_lock             = threading.Lock()
PREGUNTAS_CUSTOM  = []   # updated live by background thread
_sync_started     = False


# ── Offline keyword responder ─────────────────────────────────────────────────
def responder_offline(texto: str) -> str | None:
    """
    Check if any custom question keyword matches the user's text.
    Returns the stored answer if found, else None.
    Call this BEFORE the LLM / internet call.
    """
    texto_lower = texto.lower()
    with _lock:
        snapshot = list(PREGUNTAS_CUSTOM)
    for qa in snapshot:
        for keyword in qa.get("keywords", []):
            if keyword.lower() in texto_lower:
                return qa["respuesta"]
    return None


def bloque_conocimiento_custom() -> str:
    """Render custom questions into the system prompt block."""
    with _lock:
        snapshot = list(PREGUNTAS_CUSTOM)
    if not snapshot:
        return ""
    lineas = ["\nPreguntas adicionales personalizadas:"]
    for i, qa in enumerate(snapshot, 1):
        lineas.append(f"{i}. Si preguntan \u00ab{qa['pregunta']}\u00bb \u2192 {qa['respuesta']}")
    return "\n".join(lineas)


# ── Local cache helpers ───────────────────────────────────────────────────────
def _save_cache(data: list):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_cache() -> list:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ── Cloud poll ────────────────────────────────────────────────────────────────
def _fetch_from_cloud() -> list | None:
    """Fetch questions from JSONBin. Returns list or None on error."""
    try:
        r = requests.get(
            JSONBIN_READ_URL,
            headers={"X-Master-Key": JSONBIN_KEY},
            timeout=10
        )
        if not r.ok:
            return None
        data = r.json().get("record", [])
        if not isinstance(data, list):
            return None
        # Filter out the init placeholder
        return [q for q in data if not q.get("_init")]
    except Exception:
        return None


def _sync_loop():
    """Background thread: polls cloud, updates PREGUNTAS_CUSTOM, saves cache."""
    global PREGUNTAS_CUSTOM
    while True:
        data = _fetch_from_cloud()
        if data is not None:
            with _lock:
                PREGUNTAS_CUSTOM = data
            _save_cache(data)
            if data:
                print(f"[preguntas_sync] {len(data)} question(s) loaded from cloud.")
        time.sleep(POLL_INTERVAL)


# ── Startup ───────────────────────────────────────────────────────────────────
def start_sync():
    """
    Call once at startup (e.g. in venezuela_bot.py).
    Loads cache immediately, then starts background polling thread.
    """
    global PREGUNTAS_CUSTOM, _sync_started
    if _sync_started:
        return
    _sync_started = True

    # Load cache immediately so offline answers work right away
    cached = _load_cache()
    with _lock:
        PREGUNTAS_CUSTOM = cached
    if cached:
        print(f"[preguntas_sync] Loaded {len(cached)} question(s) from cache.")

    # Start background thread
    t = threading.Thread(target=_sync_loop, daemon=True)
    t.start()
    print(f"[preguntas_sync] Sync started — polling every {POLL_INTERVAL}s.")
