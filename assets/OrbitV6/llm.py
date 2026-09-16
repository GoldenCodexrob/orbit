"""
Capa de proveedor LLM intercambiable (Gemini cloud ↔ Ollama local) sobre LangChain.

Piezas:
- _construir_kwargs(cfg): traduce la config común a los kwargs específicos del
  proveedor (Ollama usa num_predict/num_ctx/repeat_penalty; Gemini usa
  max_output_tokens). Pura, sin dependencias de LangChain.
- crear_modelo(cfg): factory que devuelve un BaseChatModel. Importa el paquete
  del proveedor de forma PEREZOSA, así no hace falta tener instalados Gemini y
  Ollama a la vez.
- AgenteVenezuela: envuelve modelo + system prompt + tools y expone
  responder(texto). Soporta tool calling (bind_tools) y deja un seam para
  multimodal (ver _contenido).

Correcciones:
  ISSUE-6  historial[-8:] podía empezar en un mensaje "assistant", enviando
           al modelo un historial con el primer turno sin contexto del usuario.
           _historial_reciente() ahora garantiza que el slice siempre empiece
           en un turno "human" y contenga pares completos.
"""
import asyncio
import concurrent.futures
import re
import sys

# Señales de error (strings centinela que venezuela_bot.py traduce a mensajes).
ERROR_OLLAMA = "ERROR_OLLAMA"   # el servidor de Ollama no responde
ERROR_MODELO = "ERROR_MODELO"   # el modelo configurado no está descargado
ERROR_TIMEOUT = "ERROR_TIMEOUT" # la llamada tardó más de 25s (rate limit / red lenta)


def _construir_kwargs(cfg) -> dict:
    """Traduce la config común a los kwargs del proveedor concreto."""
    if cfg.proveedor == "ollama":
        kwargs = {
            "model": cfg.modelo,
            "base_url": cfg.base_url,
            "temperature": cfg.temperatura,
            "num_predict": cfg.max_tokens,
            "num_ctx": cfg.num_ctx,
            "top_p": cfg.top_p,
            "repeat_penalty": cfg.repeat_penalty,
        }
        # reasoning=False desactiva el "thinking" (modelos como gemma/qwen3/r1
        # volcarían su respuesta al campo thinking y dejarían content vacío).
        # None = no enviar el flag (algunos modelos antiguos no lo soportan).
        if cfg.reasoning is not None:
            kwargs["reasoning"] = cfg.reasoning
        return kwargs
    if cfg.proveedor == "google_genai":
        kwargs = {
            "model": cfg.modelo,
            "google_api_key": cfg.google_api_key,
            "max_output_tokens": cfg.max_tokens,
        }
        # Disable internal "thinking" on Gemini 3.x models (thinking_budget=0).
        # Without this, gemini-3.6-flash spends 80+ seconds thinking before
        # responding — way too slow for a conversational bot.
        kwargs["model_kwargs"] = {
            "generation_config": {"thinking_config": {"thinking_budget": 0}}
        }
        return kwargs
    raise ValueError(f"Proveedor LLM no soportado: {cfg.proveedor!r}")


def crear_modelo(cfg):
    """Devuelve un BaseChatModel de LangChain según el proveedor configurado."""
    kwargs = _construir_kwargs(cfg)
    if cfg.proveedor == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(**kwargs)
    if cfg.proveedor == "google_genai":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(**kwargs)
    raise ValueError(f"Proveedor LLM no soportado: {cfg.proveedor!r}")


def _postprocesar(texto: str) -> str:
    """Limpia la respuesta del modelo y garantiza oraciones completas.

    - Elimina markdown (negrita, cursiva).
    - Limita a 4 oraciones como máximo.
    - Si el texto quedó cortado (no termina en .!?), retrocede a la
      última oración completa para no dejar fragmentos como 'fue un.'.
    - Si no hay ninguna oración completa, añade un punto al final.
    """
    if not texto:
        return texto
    # Quitar markdown
    texto = re.sub(r'\*\*([^*]+)\*\*', r'\1', texto)
    texto = re.sub(r'\*([^*]+)\*', r'\1', texto)
    texto = texto.strip()

    # Dividir en oraciones (split después de .!?)
    orac = re.split(r'(?<=[.!?])\s+', texto)

    # Tomar máximo 4 oraciones completas (las que terminan en .!?)
    completas = [o for o in orac if o and o[-1] in '.!?']
    incompletas = [o for o in orac if o and o[-1] not in '.!?']

    if len(orac) > 4:
        # De las primeras 4, quedarse solo con las completas
        candidatos = orac[:4]
        completas_sel = [o for o in candidatos if o[-1] in '.!?']
        if completas_sel:
            return ' '.join(completas_sel)
        # Ninguna completa en las primeras 4 → tomar el texto y añadir punto
        texto = ' '.join(candidatos)
    else:
        texto = ' '.join(orac)

    # Si el texto termina en fragmento incompleto, recortar al último punto
    if texto and texto[-1] not in '.!?':
        ultimo_punto = max(
            texto.rfind('.'), texto.rfind('!'), texto.rfind('?')
        )
        if ultimo_punto > len(texto) // 3:  # al menos 1/3 del texto
            texto = texto[:ultimo_punto + 1]
        else:
            texto = texto.rstrip(', ') + '.'

    return texto



class AgenteVenezuela:
    """Agente conversacional sobre un BaseChatModel intercambiable."""

    def __init__(self, cfg, tools=None, modelo=None, system_prompt_texto=None):
        from prompt import system_prompt

        self.cfg = cfg
        self.tools = list(tools or [])
        self.system_prompt = system_prompt_texto or system_prompt()
        # modelo inyectable (desacopla de LangChain en pruebas / extensiones).
        self.modelo = modelo if modelo is not None else crear_modelo(cfg)
        self.runnable = (
            self.modelo.bind_tools(self.tools) if self.tools else self.modelo
        )
        self._tools_por_nombre = {
            getattr(t, "name", None): t for t in self.tools
        }
        # Historial de la conversación actual (pares human/assistant).
        self.historial: list = []
        # ── Contadores de tokens de la sesión ─────────────────────────────────
        self.last_usage: dict = {}        # tokens de la última llamada
        self.total_in: int = 0            # tokens de entrada acumulados
        self.total_out: int = 0           # tokens de salida acumulados

    def reiniciar_historial(self):
        """Borra el historial para comenzar una conversación fresca."""
        self.historial = []

    def _contenido(self, texto: str):
        """Seam multimodal.

        Hoy devuelve texto plano. Para audio nativo (futuro), construir aquí una
        lista de bloques, p. ej.:
            [{"type": "text", "text": texto},
             {"type": "media", "mime_type": "audio/ogg", "data": <bytes>}]
        Directo para Gemini; el camino Ollama necesitaría STT hasta que soporte
        audio. NO se implementa todavía.
        """
        return texto

    def _historial_reciente(self, n: int = 8) -> list:
        """Devuelve los últimos n mensajes del historial garantizando que:
        - Siempre empieza en un turno "human" (nunca en "assistant").
        - Contiene pares completos para no desorientar al modelo (ISSUE-6).

        Args:
            n: máximo de mensajes a incluir (default 8 = 4 intercambios).
        """
        if not self.historial:
            return []
        # Tomar el slice inicial
        reciente = self.historial[-n:]
        # Si arranca en "assistant", quitar ese mensaje huérfano
        if reciente and reciente[0][0] != "human":
            reciente = reciente[1:]
        return reciente

    def responder(self, texto: str, max_iteraciones: int = 4) -> str:
        """Pregunta al modelo incluyendo el historial completo de la conversación.

        Aplica un timeout de 15 s sobre la llamada al LLM: si Gemini o Ollama
        tardan demasiado (rate-limit, red lenta), devuelve un mensaje amigable
        en lugar de congelarse indefinidamente.
        """
        # Añadir el turno del usuario al historial.
        self.historial.append(("human", self._contenido(texto)))

        mensajes = [("system", self.system_prompt)] + self._historial_reciente(8)

        try:
            # ── Llamada al LLM con timeout de 15 segundos ────────────────
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.runnable.invoke, mensajes)
                try:
                    ai = future.result(timeout=90)
                except concurrent.futures.TimeoutError:
                    self.historial.pop()  # Retirar turno fallido
                    print("[LLM] Timeout de 90s alcanzado", file=sys.stderr)
                    return ERROR_TIMEOUT

            # Loop de tools: inerte si no hay tools registradas.
            iteraciones = 0
            while getattr(ai, "tool_calls", None) and iteraciones < max_iteraciones:
                from langchain_core.messages import ToolMessage

                mensajes.append(ai)
                for tc in ai.tool_calls:
                    herramienta = self._tools_por_nombre.get(tc["name"])
                    resultado = herramienta.invoke(tc["args"]) if herramienta else ""
                    mensajes.append(
                        ToolMessage(content=str(resultado), tool_call_id=tc["id"])
                    )
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.runnable.invoke, mensajes)
                    try:
                        ai = future.result(timeout=90)
                    except concurrent.futures.TimeoutError:
                        break
                iteraciones += 1

            respuesta = _postprocesar(self._texto_de(ai))
            # ── Registrar uso de tokens (Gemini siempre lo incluye) ──────────
            usage = getattr(ai, "usage_metadata", None) or {}
            self.last_usage = {
                "in":    usage.get("input_tokens",  0),
                "out":   usage.get("output_tokens", 0),
                "total": usage.get("total_tokens",  0),
            }
            self.total_in  += self.last_usage["in"]
            self.total_out += self.last_usage["out"]
            if respuesta:
                self.historial.append(("assistant", respuesta))
            return respuesta
        except Exception as e:
            self.historial.pop()
            return self._manejar_error(e)

    @staticmethod
    def _texto_de(ai) -> str:
        """Extrae el texto de un AIMessage (string o lista de bloques).
        Funciona con modelos normales y con modelos de pensamiento (Gemini 3.x).
        """
        import re as _re
        contenido = getattr(ai, "content", ai)
        if isinstance(contenido, list):
            partes = []
            for b in contenido:
                if isinstance(b, dict):
                    # Preferir bloque de tipo "text"; ignorar tipo "thinking"
                    if b.get("type") == "thinking":
                        continue
                    texto_bloque = b.get("text") or b.get("content") or ""
                    partes.append(str(texto_bloque))
                else:
                    partes.append(str(b))
            resultado = "".join(partes).strip()
            # Si quedó vacío (el modelo puso todo en thinking), usar str completo
            if not resultado:
                resultado = str(contenido)
            return resultado
        texto = contenido if isinstance(contenido, str) else str(contenido)
        # Quitar etiquetas <thinking>...</thinking> si el modelo las incluye en texto
        texto = _re.sub(r'<thinking>.*?</thinking>', '', texto, flags=_re.DOTALL)
        return texto.strip()

    def _manejar_error(self, e):
        """Traduce excepciones a señales; nunca rompe el CLI, pero no calla."""
        firma = (type(e).__name__ + " " + str(e)).lower()
        if self.cfg.proveedor == "ollama" and any(
            t in firma for t in ("connection", "refused", "connecterror", "max retries")
        ):
            return ERROR_OLLAMA
        if any(t in firma for t in ("not found", "404", "try pulling", "no such model")):
            return ERROR_MODELO
        # Error inesperado: no reventamos el CLI, pero lo avisamos por stderr
        # para no esconder fallos de configuración.
        print(f"⚠️  [LLM] {type(e).__name__}: {e}", file=sys.stderr)
        return None