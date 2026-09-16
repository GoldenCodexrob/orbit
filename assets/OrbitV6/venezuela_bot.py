"""
================================================================
🇻🇪 EMBAJADOR DE VENEZUELA PARA NIÑOS - CON MICRÓFONO
================================================================
Voz: Elena (edge-tts) | Escucha: Google Speech Recognition
LLM: intercambiable Gemini (cloud) ↔ Ollama (local) vía LangChain
Wake word: "Orbit" (y variaciones: orbi, orbiz, orbis, orbital…)
================================================================
"""

import random
import re
import threading
import time
import sys
import requests

# Capa LLM intercambiable + conocimiento inyectado en el system prompt
from config import cargar_config

from voz import Voz
from escuchar import Escuchar
from internet import BusquedaWeb
from llm import ERROR_MODELO, ERROR_OLLAMA, ERROR_TIMEOUT, AgenteVenezuela
from preguntas import PREGUNTAS
from preguntas_sync import responder_offline, start_sync

# ============================================
# ⚙️ CONFIGURACIÓN
# ============================================
MODELOS_DISPONIBLES = [
    "mistral",
    "qwen2.5:7b",
    "llama3:8b",
    "phi3:mini",
    "phi3",
    "gemma:2b",
    "tinyllama",
]


# ============================================
# 🧠 CLASE PRINCIPAL
# ============================================
class Embajador:
    def __init__(self):
        self.cfg = cargar_config()
        self.sesion = requests.Session()
        self.web = BusquedaWeb()
        self.hay_internet = False
        self.ya_saludo = False  # Evita saludar más de una vez por conversación

        self.voz = Voz(velocidad=0.85)
        self.oidos = Escuchar()

        # El agente construye el modelo del proveedor configurado y arma el
        # system prompt (persona + conocimiento inyectado).
        self.agente = AgenteVenezuela(self.cfg)

        self._detectar_internet()

    @property
    def modelo(self):
        return self.cfg.modelo

    @property
    def proveedor(self):
        return self.cfg.proveedor

    def cambiar_modelo(self, nombre):
        """Cambia el modelo dentro del proveedor activo y reconstruye el agente."""
        self.cfg.modelo = nombre
        self.agente = AgenteVenezuela(self.cfg)

    def reiniciar(self):
        """Resetea estado de conversación para comenzar una nueva fresca."""
        self.ya_saludo = False
        self.agente.reiniciar_historial()

    def _detectar_internet(self):
        print("🔍 Detectando internet...")
        self.hay_internet = self.web.hay_internet()
        if self.hay_internet:
            print("✅ Internet disponible (usa Google para escucha)")
        else:
            print("⚠️ Sin internet (la escucha NO funcionará)")
        print()

    def consultar_ia(self, mensaje):
        """Delega en el agente LLM (proveedor intercambiable)."""
        return self.agente.responder(mensaje)

    def responder(self, mensaje):
        msg = mensaje.lower().strip()

        if any(p in msg for p in ["hola", "buenos", "buenas", "qué tal", "saludos"]):
            if not self.ya_saludo:
                self.ya_saludo = True
                return random.choice(
                    [
                        "¡Hola explorador! ¿Qué quieres saber de Venezuela hoy?",
                        "¡Hola aventurero! Me alegra que estés aquí. ¿Sobre qué hablamos?",
                        "¡Ey! Qué bueno verte. ¿Qué quieres descubrir hoy?",
                        "¡Hola! Listo para explorar Venezuela. ¿Por dónde empezamos?",
                    ]
                )
            # Ya saludamos: no repetimos, dejamos caer al LLM.

        if any(p in msg for p in ["chao", "adiós", "adios", "hasta luego", "bye"]):
            return random.choice(
                [
                    "¡Chao! Fue hermoso hablar contigo.",
                    "¡Hasta luego! Te espero de vuelta.",
                    "¡Chao! Vuelve cuando quieras.",
                ]
            )

        if any(p in msg for p in ["gracias"]):
            return random.choice(
                [
                    "¡De nada! Para eso estoy aquí.",
                    "¡Un placer! Aquí estoy siempre que necesites.",
                ]
            )

        # Respuesta negativa corta: "no", "no gracias", "nel", etc.
        palabras = msg.split()
        if palabras and palabras[0] in ("no", "nel", "nah", "nop") and len(palabras) <= 3:
            return random.choice(
                [
                    "¡Ok! Si tienes alguna otra pregunta, solo di 'Orbit' y aquí estaré.",
                    "¡Entendido! Cuando quieras saber algo, llámame diciendo 'Orbit'.",
                    "¡Perfecto! Recuerda que solo tienes que decir 'Orbit' para llamarme.",
                ]
            )
        
        # ── Custom questions (offline keyword match) ──────────────────
        resp_custom = responder_offline(mensaje)
        if resp_custom:
            return resp_custom

        resp_ia = self.consultar_ia(mensaje)
        if resp_ia == ERROR_OLLAMA:
            return (
                "¡Ups! Mi cerebro está descansando. Pero pregúntame sobre: "
                "¿la arepa? ¿el Salto Ángel? ¿el joropo? ¿las hallacas? "
                "¿Simón Bolívar? ¿la Navidad? ¿los llanos?"
            )
        if resp_ia == ERROR_MODELO:
            return (
                f"⚠️  El modelo '{self.cfg.modelo}' no está descargado en Ollama. "
                f"Ejecuta:  ollama pull {self.cfg.modelo}   "
                f"(o cambia LLM_MODEL en tu .env por uno que ya tengas)."
            )
        if resp_ia == ERROR_TIMEOUT:
            return random.choice([
                "Perdón, me tardé un poquito. ¿Puedes repetirme lo que dijiste?",
                "Ay, se me fue la mente por un momento. ¿Me repites eso?",
                "¡Ups! No te escuché bien. ¿Puedes decirlo de nuevo?",
            ])
        if resp_ia:
            return resp_ia

        return (
            "¡Ay! No sé sobre eso. Pero puedo contarte de: "
            "arepa, hallaca, tequeño, salto angel, bolívar, joropo, gaita, "
            "navidad, carnaval, llanos, playa. ¡Pregúntame!"
        )


# ============================================
# 🔍 WAKE WORD
# ============================================
# Detecta "Orbit" y variaciones que suelta el reconocedor de voz español.
# Ejemplos válidos: orbit, orbi, orbiz, orbis, orbital, orbita, orbith…
_WAKE_RE = re.compile(r'\borbi\w{0,4}\b', re.IGNORECASE)


def es_wake_word(texto: str) -> bool:
    """True si el texto contiene el nombre de activación (Orbit y variaciones)."""
    if not texto:
        return False
    return bool(_WAKE_RE.search(texto))


def _vigilar_interrupcion(bot, evento_interrupcion, evento_parar):
    """Thread secundario: escucha la wake word MIENTRAS el bot habla."""
    import speech_recognition as sr

    iteracion = 0
    print(f"[INT] hilo iniciado. hablando={bot.voz.hablando}", file=sys.stderr, flush=True)

    while bot.voz.hablando and not evento_parar.is_set():
        iteracion += 1
        adquirido = bot.oidos._mic_lock.acquire(blocking=False)
        print(f"[INT] iter={iteracion} lock={adquirido} hablando={bot.voz.hablando}", file=sys.stderr, flush=True)

        if not adquirido:
            time.sleep(0.05)
            continue

        try:
            with bot.oidos.microfono as fuente:
                try:
                    audio = bot.oidos.reconocedor.listen(
                        fuente, timeout=0.5, phrase_time_limit=0.5
                    )
                    try:
                        texto = bot.oidos.reconocedor.recognize_google(audio, language="es-ES")
                        print(f"[INT] STT='{texto}' wake={es_wake_word(texto)}", file=sys.stderr, flush=True)
                        if es_wake_word(texto):
                            evento_interrupcion.set()
                            bot.voz.detener()
                            break
                    except sr.UnknownValueError:
                        print("[INT] STT=no entendido", file=sys.stderr, flush=True)
                    except sr.RequestError as e:
                        print(f"[INT] STT=error red: {e}", file=sys.stderr, flush=True)
                except sr.WaitTimeoutError:
                    print("[INT] silencio", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[INT] excepcion: {e}", file=sys.stderr, flush=True)
        finally:
            bot.oidos._mic_lock.release()

    print(f"[INT] hilo terminado. iter={iteracion}", file=sys.stderr, flush=True)




# ============================================
# 🎤 MODO MANOS LIBRES CON WAKE WORD
# ============================================
def modo_manos_libres(bot):
    """Modo principal con wake word 'Orbit'.

    Estados:
        DORMIDO → espera la wake word sin timeout (escucha pasiva).
        ACTIVO  → conversación normal con timeout de 8 s.

    Interrupción en medio del habla:
        Si el usuario dice 'Orbit' mientras el bot responde, el bot se
        detiene y pregunta qué necesita.
    """
    print("\n" + "=" * 60)
    print("🎤 MODO ORBIT — Di 'ORBIT' para activar")
    print("=" * 60)

    if not bot.oidos.disponible:
        print("❌ Micrófono no disponible")
        return

    print("   • Di 'Orbit'  → Activar / interrumpir al bot")
    print("   • 'chao'      → Terminar conversación")
    print("   • 'silencio'  → Apagar voz")
    print("   • Ctrl+C     → Salir del programa")
    print("=" * 60 + "\n")

    DESPEDIDAS = [
        "¡Chao! Fue hermoso hablar contigo.",
        "¡Hasta luego! Te espero de vuelta.",
        "¡Chao! Vuelve cuando quieras.",
    ]
    SALUDOS_INICIO = [
        "¡Hola explorador! ¿Qué quieres saber de Venezuela hoy?",
        "¡Hola aventurero! Me alegra que estés aquí. ¿Empezamos?",
        "¡Ey! Qué bueno verte. ¿Qué quieres descubrir hoy?",
        "¡Hola! Listo para explorar Venezuela. ¿Por dónde empezamos?",
    ]
    FRASES_INTERRUPCION = [
        "¡Dime!",
        "¡Aquí estoy!",
        "¿Sí?",
        "¡Dime qué quieres saber!",
    ]

    dormido = True
    print("💤 Esperando que digas 'Orbit'...\n")

    while True:
        try:
            # ── DORMIDO: escucha pasiva, solo atiende la wake word ────────
            if dormido:
                texto = bot.oidos.escuchar(timeout=None, frase_max=4)

                if not texto or texto == "__TIMEOUT__":
                    continue

                if es_wake_word(texto):
                    print(f"🟢 Orbit activado: '{texto}'")
                    bot.reiniciar()
                    saludo = random.choice(SALUDOS_INICIO)
                    print(f"🤖 {saludo}\n")
                    bot.voz.hablar(saludo)
                    bot.voz.esperar()
                    bot.ya_saludo = True
                    dormido = False
                # Si no es wake word, ignorar y seguir durmiendo
                continue

            # ── ACTIVO: conversación normal (timeout 8 s) ─────────────────
            texto = bot.oidos.escuchar(timeout=8, frase_max=6)

            # 8 s de silencio → despedida y volver a dormir
            if texto == "__TIMEOUT__":
                despedida = random.choice(DESPEDIDAS)
                print(f"\n🤖 {despedida}\n")
                bot.voz.hablar(despedida)
                bot.voz.esperar()
                print("💤 Volviendo a dormir... Di 'Orbit' cuando quieras.\n")
                dormido = True
                continue

            if not texto:
                continue

            texto_lower = texto.lower().strip()

            # Wake word mientras está activo → responde al llamado directamente
            if es_wake_word(texto_lower):
                interrupcion = random.choice(FRASES_INTERRUPCION)
                print(f"\n🤖 {interrupcion}\n")
                bot.voz.hablar(interrupcion)
                bot.voz.esperar()
                continue

            # Despedida → dormir
            if texto_lower in ["chao", "adiós", "adios", "salir", "terminar", "hasta luego"]:
                despedida = random.choice(DESPEDIDAS)
                print(f"\n🤖 {despedida}\n")
                bot.voz.hablar(despedida)
                bot.voz.esperar()
                print("💤 Volviendo a dormir... Di 'Orbit' cuando quieras.\n")
                dormido = True
                continue

            if texto_lower in ["silencio", "silenciar"]:
                bot.voz.silenciar()
                print("🔇 Voz silenciada")
                continue

            if texto_lower in ["hablar", "voz", "activar"]:
                bot.voz.activar()
                print("🔊 Voz activada")
                bot.voz.hablar("¡Aquí estoy!")
                continue

            # ── Respuesta normal con vigilancia de interrupción ───────────
            print(f"\n👤 Dijiste: '{texto}'")
            t1 = time.time()
            resp = bot.responder(texto)
            t2 = time.time() - t1
            # ── Token display ────────────────────────────────────────────
            u = bot.agente.last_usage
            session_tok = bot.agente.total_in + bot.agente.total_out
            if u:
                tok_str = f" | in:{u['in']} out:{u['out']} tok:{u['total']}"
                ses_str = f" | sesion: {session_tok:,} tok"
            else:
                tok_str = ses_str = ""
            print(f"⏱️  {t2:.2f}s{tok_str}{ses_str}")
            print(f"🤖 {resp}\n")

            bot.voz.hablar(resp)

            # Lanzar hilo que escucha "Orbit" MIENTRAS el bot habla
            evento_interrupcion = threading.Event()
            evento_parar = threading.Event()
            hilo = threading.Thread(
                target=_vigilar_interrupcion,
                args=(bot, evento_interrupcion, evento_parar),
                daemon=True,
            )
            hilo.start()

            bot.voz.esperar()       # Espera a que el bot termine de hablar
            evento_parar.set()      # Signal al hilo: ya puede salir
            # join timeout > phrase_time_limit(0.5s) para que el hilo libere el mic
            hilo.join(timeout=0.7)

            if evento_interrupcion.is_set():
                # El usuario dijo 'Orbit' mientras el bot hablaba.
                # Respuesta corta (tipo Alexa) para que pueda preguntar enseguida.
                interrupcion = random.choice(FRASES_INTERRUPCION)
                print(f"\n🤖 {interrupcion}\n")
                bot.voz.hablar(interrupcion)
                bot.voz.esperar()
                # NO hay continue aqui: cae directo al escuchar() de la
                # siguiente iteracion para capturar la pregunta del usuario.

            time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n\n👋 Saliendo\n")
            return


# ============================================
# 💻 INTERFAZ PRINCIPAL
# ============================================
def main():
    print("=" * 60)
    print("🇻🇪  EMBAJADOR DE VENEZUELA PARA NIÑOS  👶")
    print("=" * 60 + "\n")

    bot = Embajador()
    start_sync()   # start background thread polling custom questions from cloud

    print(f"  IA: {bot.cfg.proveedor} · {bot.cfg.modelo}")
    print(f"  🎤 Micrófono: {'✅ Listo' if bot.oidos.disponible else '❌'}")
    print(f"  Preguntas base: {len(PREGUNTAS)}")
    print("=" * 60 + "\n")

    if not bot.oidos.disponible:
        print("❌ No se detectó micrófono. Verifica la conexión y vuelve a intentar.")
        return

    # Arranca directamente en modo manos libres con wake word.
    # Di 'Orbit' para empezar, 'chao' para terminar.
    modo_manos_libres(bot)


if __name__ == "__main__":
    main()
