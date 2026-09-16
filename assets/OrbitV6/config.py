"""
Configuración central cargada desde entorno (.env).

El cambio de proveedor (Gemini cloud ↔ Ollama local) se hace con UNA variable:
LLM_PROVIDER. Ver .env.example para todas las opciones.

Correcciones:
  ISSUE-11  La sintaxis `bool | None` requiere Python 3.10+.
            El Pi4 con Raspberry Pi OS Bullseye viene con Python 3.9.
            Sustituido por Optional[bool] de typing (compatible ≥ 3.7).
"""

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv es opcional; sin él se usan solo os.environ
    pass


@dataclass
class ConfigLLM:
    proveedor: str          # "ollama" | "google_genai"
    modelo: str             # "mistral" | "gemini-2.5-flash" | ...
    temperatura: float
    max_tokens: int
    top_p: float
    # Específicos de Ollama
    base_url: str
    num_ctx: int
    repeat_penalty: float
    reasoning: Optional[bool]   # False = desactiva "thinking"; None = no enviar el flag
    # Específicos de Google
    google_api_key: Optional[str]


def _parse_reasoning(valor: str) -> Optional[bool]:
    """'true'/'false' -> bool; 'none'/'' -> None (no enviar el flag a Ollama)."""
    v = (valor or "").strip().lower()
    if v in ("true", "1", "yes", "si", "sí"):
        return True
    if v in ("false", "0", "no"):
        return False
    return None


def cargar_config() -> ConfigLLM:
    """Construye ConfigLLM leyendo variables de entorno con defaults sensatos."""
    proveedor = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    modelo_default = (
        "gemini-2.5-flash" if proveedor == "google_genai" else "phi3:mini"
    )

    return ConfigLLM(
        proveedor=proveedor,
        modelo=os.getenv("LLM_MODEL", modelo_default),
        temperatura=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "200")),
        top_p=float(os.getenv("LLM_TOP_P", "0.9")),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "2048")),
        repeat_penalty=float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.15")),
        reasoning=_parse_reasoning(os.getenv("OLLAMA_REASONING", "false")),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
