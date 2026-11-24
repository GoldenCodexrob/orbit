"""
=============================================================================
🎙️ HABLAR_CON_ORBIT.PY — Modo Conversacional Bilingüe Ultra-Rápido (Orbit V4.0)
=============================================================================
- Reconocimiento Dual en RAM con Vosk (Inglés y Español en tiempo real).
- Detección automática del idioma del usuario en cada turno.
- Conmutación bilingüe con la voz neuronal de Orbit (ElevenLabs Turbo v2.5):
  * Voz Unificada (Inglés y Español) -> Voice ID: htFfPSZGJwjBv1CL0aMD
- Reacción vocal instantánea (< 100 ms) sin silencios ni llamadas bloqueantes.
- Sin dobles reacciones ni tartamudeos en nombres venezolanos (Lecheria, arepas, hallacas).
=============================================================================
"""

import time
import sys
import os
import random
import re
import threading
import subprocess
import requests

from voz_elevenlabs import VozElevenLabs
from oido_vosk import OidoVosk
from rag_conocimiento import BaseConocimiento
from cerebro_v4 import CerebroV4
import historial_orbit
import web_historial

# Iniciar servidor web de monitoreo en segundo plano
def _iniciar_servidor_web_bg():
    try:
        import http.server
        server_address = ("0.0.0.0", 8080)
        httpd = http.server.ThreadingHTTPServer(server_address, web_historial.OrbitHTTPRequestHandler)
        httpd.serve_forever()
    except Exception:
        pass

threading.Thread(target=_iniciar_servidor_web_bg, daemon=True).start()

print("\n" + "="*68)
print("🤖 INICIANDO CONVERSACIÓN CON ORBIT V4.0 (BILINGÜE ULTRA-RÁPIDO)")
print("="*68)
ip_local = web_historial.obtener_ip_local()
print(f"📊 Dashboard Web en Vivo: http://localhost:8080  |  http://{ip_local}:8080")
print("Inicializando motores...")

voz = VozElevenLabs()

stt_engine = os.getenv("STT_ENGINE", "google").strip().lower()
if stt_engine == "google":
    try:
        from oido_google import OidoGoogle
        oido = OidoGoogle()
    except Exception as err:
        print(f"⚠️ [Oído Google no disponible: {err}]. Usando OidoVosk...")
        from oido_vosk import OidoVosk
        oido = OidoVosk()
else:
    from oido_vosk import OidoVosk
    oido = OidoVosk()

rag = BaseConocimiento()
cerebro = CerebroV4(db=rag)

# Pre-calentamiento asíncrono para eliminar el arranque en frío (Cold Start de 8s)
def _precalentar_conexiones():
    try:
        if hasattr(cerebro, "_llamar_gemini") and cerebro.gemini_api_key:
            cerebro._llamar_gemini([{"role": "user", "content": "ping"}])
    except Exception:
        pass
    try:
        requests.head("https://api.elevenlabs.io", timeout=3)
    except Exception:
        pass

threading.Thread(target=_precalentar_conexiones, daemon=True).start()

idioma_inicial = os.getenv("ORBIT_LANGUAGE", "auto").lower()
is_english = (idioma_inicial == "en" or (idioma_inicial == "auto" and oido.ultimo_idioma == "en"))

SALUDOS_INICIALES_ES = [
    "¡Hola! Soy Orbit, tu robot embajador cultural. ¡Estoy súper emocionado de recorrer juntos nuestras tradiciones y comidas típicas! ¿Por dónde empezamos hoy?",
    "¡Epa, qué alegría saludarte! Me llamo Orbit. ¡Me apasiona compartir las historias y leyendas más increíbles de Venezuela y Puerto Rico! ¿Qué te gustaría descubrir?",
    "¡Hola, qué gran gusto conocerte! Soy Orbit. ¡Conozco las maravillas culturales y los lugares más bellos de nuestra tierra! ¿Sobre qué quieres charlar hoy?"
]

SALUDOS_INICIALES_EN = [
    "Hello! I'm Orbit, your cultural ambassador robot. I'm super excited to explore our rich traditions and delicious cuisine together! Where shall we begin today?",
    "Hey there, wonderful to see you! My name is Orbit. I love sharing fascinating stories and culture from Venezuela and Puerto Rico! What would you like to discover today?",
    "Hello! So great to meet you, I'm Orbit! I know the most incredible cultural wonders of our lands. What would you like to chat about today?"
]

if is_english:
    saludo_inicial = random.choice(SALUDOS_INICIALES_EN)
else:
    saludo_inicial = random.choice(SALUDOS_INICIALES_ES)

print(f"\n🤖 Orbit: {saludo_inicial}\n")
cerebro.agregar_historial("assistant", saludo_inicial)
voz.hablar(saludo_inicial, idioma="en" if is_english else "es")
while voz.hablando:
    time.sleep(0.05)
time.sleep(0.35)  # Pausa limpia para que el altavoz libere el canal antes de abrir el micrófono

print("-" * 68)
print("🎙️ MODO CONVERSACIONAL AUTOMÁTICO ACTIVO / AUTO-LISTENING ACTIVE:")
print(" [🎤] Orbit escucha continuamente por el micrófono sin tocar ENTER.")
print(" [⌨️] O escribe tu mensaje y presiona ENTER si prefieres usar teclado.")
print(" [🚪] Di o escribe 'salir' / 'exit' / 'bye' para terminar.")
print(f" [🌐] Dashboard Historial en Vivo: http://localhost:8080")
print("-" * 68 + "\n")

# Reacciones pre-cacheadas contextuales generadas con las voces ElevenLabs respectivas
REACCIONES_EN_PREGUNTA = [
    ("audio_cache_reacciones/reaccion_en_1.mp3", "Oh, that is such a great question!"),
    ("audio_cache_reacciones/reaccion_en_2.mp3", "I am so excited you asked about that!"),
    ("audio_cache_reacciones/reaccion_en_3.mp3", "Oh, that is one of my absolute favorite topics!"),
    ("audio_cache_reacciones/reaccion_en_4.mp3", "Sure thing! Let me tell you something fascinating."),
    ("audio_cache_reacciones/reaccion_en_5.mp3", "Wow, what an awesome topic to explore today!"),
    ("audio_cache_reacciones/reaccion_en_6.mp3", "Oh, that is a fantastic one, let me tell you!"),
    ("audio_cache_reacciones/reaccion_en_7.mp3", "I love your curiosity! Listen to this:"),
    ("audio_cache_reacciones/reaccion_en_8.mp3", "You got it! Here is the scoop:"),
    ("audio_cache_reacciones/reaccion_en_9.mp3", "Right on! Let me break that down for you."),
    ("audio_cache_reacciones/reaccion_en_10.mp3", "That's a really cool thing to ask, check this out:"),
    ("audio_cache_reacciones/reaccion_en_11.mp3", "Oh, absolutely! You're going to love this detail."),
    ("audio_cache_reacciones/reaccion_en_12.mp3", "Great topic to bring up! Here is what's special:"),
    ("audio_cache_reacciones/reaccion_en_13.mp3", "Love that curiosity! Here is the fascinating story:"),
    ("audio_cache_reacciones/reaccion_en_14.mp3", "Awesome question! Let me share this with you:"),
    ("audio_cache_reacciones/reaccion_en_15.mp3", "Here we go! Let me explain this right away."),
    ("audio_cache_reacciones/reaccion_en_16.mp3", "Wonderful question! Listen to this great fact:")
]

REACCIONES_ES_PREGUNTA = [
    ("audio_cache_reacciones/reaccion_es_1.mp3", "¡Oye, qué buena pregunta me haces!"),
    ("audio_cache_reacciones/reaccion_es_2.mp3", "¡Ay, ese es uno de mis temas favoritos!"),
    ("audio_cache_reacciones/reaccion_es_3.mp3", "¡Qué alegría que me preguntes sobre eso!"),
    ("audio_cache_reacciones/reaccion_es_4.mp3", "¡Claro que sí! Déjame contarte algo fascinante."),
    ("audio_cache_reacciones/reaccion_es_5.mp3", "¡Uff, qué temazo para compartir hoy!"),
    ("audio_cache_reacciones/reaccion_es_6.mp3", "¡Esa está buenísima, ya te cuento!"),
    ("audio_cache_reacciones/reaccion_es_7.mp3", "¡Qué gran curiosidad tienes, escucha esto!"),
    ("audio_cache_reacciones/reaccion_es_8.mp3", "¡Me encanta esa pregunta, fíjate en esto!"),
    ("audio_cache_reacciones/reaccion_es_9.mp3", "¡De una! Te lo explico con todo detalle."),
    ("audio_cache_reacciones/reaccion_es_10.mp3", "¡Excelente duda! Te va a encantar lo que sé."),
    ("audio_cache_reacciones/reaccion_es_11.mp3", "¡Por supuesto! Mira qué dato tan interesante."),
    ("audio_cache_reacciones/reaccion_es_12.mp3", "¡Qué buen punto trajiste a la mesa! Oye esto:"),
    ("audio_cache_reacciones/reaccion_es_13.mp3", "¡Qué nota que quieras saber de eso! Déjame decirte:"),
    ("audio_cache_reacciones/reaccion_es_14.mp3", "¡Eso me encanta! Te lo cuento al instante."),
    ("audio_cache_reacciones/reaccion_es_15.mp3", "¡Justo lo que me gusta explicar! Atento a esto:"),
    ("audio_cache_reacciones/reaccion_es_16.mp3", "¡Qué maravilla de pregunta! Aquí tienes la respuesta:")
]

REACCIONES_ES_SI = [
    ("audio_cache_reacciones/reaccion_es_si_1.mp3", "¡Buenísimo!"),
    ("audio_cache_reacciones/reaccion_es_si_2.mp3", "¡Excelente elección!"),
    ("audio_cache_reacciones/reaccion_es_si_3.mp3", "¡Qué bien, me alegra mucho!"),
    ("audio_cache_reacciones/reaccion_es_si_4.mp3", "¡A mí también me encantaría!")
]

REACCIONES_ES_NO = [
    ("audio_cache_reacciones/reaccion_es_no_1.mp3", "¡Te entiendo perfectamente!"),
    ("audio_cache_reacciones/reaccion_es_no_2.mp3", "¡Tranquilo, para gustos los colores!"),
    ("audio_cache_reacciones/reaccion_es_no_3.mp3", "¡Cero rollo, no pasa nada!"),
    ("audio_cache_reacciones/reaccion_es_no_4.mp3", "¡Totalmente comprensible!")
]

REACCIONES_EN_YES = [
    ("audio_cache_reacciones/reaccion_en_yes_1.mp3", "Awesome! I love that!"),
    ("audio_cache_reacciones/reaccion_en_yes_2.mp3", "Great choice, that sounds exciting!"),
    ("audio_cache_reacciones/reaccion_en_yes_3.mp3", "I would absolutely love that too!")
]

REACCIONES_EN_NO = [
    ("audio_cache_reacciones/reaccion_en_no_1.mp3", "Totally fair, I completely understand!"),
    ("audio_cache_reacciones/reaccion_en_no_2.mp3", "No problem at all, I hear you!"),
    ("audio_cache_reacciones/reaccion_en_no_3.mp3", "No worries at all, that makes total sense!")
]

UMBRAL_FRASE_LARGA = float(os.getenv("ORBIT_UMBRAL_FRASE_LARGA", "8.0"))

def _ejecutar_accion_especial(accion: str, idioma: str):
    """
    Ejecuta acciones multimedia interactivas (Alma Llanera / Cupón QR Deleite).
    """
    if not accion:
        return

    if accion == "reproducir_alma":
        alma_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "alma.mp3")
        lir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "almalir.png")
        if os.path.exists(lir_path):
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", lir_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        if os.path.exists(alma_path):
            print("\n🎶 [Reproduciendo Alma Llanera / Playing Alma Llanera] (clip 28s) 🇻🇪...")
            cmd_alma = ["afplay", "-t", "28", alma_path] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", alma_path]
            try:
                proc_alma = subprocess.Popen(cmd_alma, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    proc_alma.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc_alma.terminate()
                    try:
                        proc_alma.wait(timeout=1)
                    except Exception:
                        proc_alma.kill()
            except Exception as e:
                print(f"⚠️ Error al reproducir audio: {e}")
            time.sleep(0.35)

        post_alma = (
            "Long live the joropo and long live Venezuela! Did you enjoy Alma Llanera? What else would you like to explore today?"
            if idioma == "en" else
            "¡Qué viva el joropo y qué viva Venezuela! ¿Te gustó Alma Llanera? ¿Qué más te gustaría saber de Venezuela o Puerto Rico?"
        )
        print(f"\n🤖 Orbit: {post_alma}\n")
        cerebro.agregar_historial("assistant", post_alma)
        voz.hablar(post_alma, idioma=idioma)
        while voz.hablando:
            time.sleep(0.05)
        time.sleep(0.35)

    elif accion == "reproducir_viejo_san_juan":
        audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "en_mi_viejo_san_juan.mp3")
        lir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "viejosanjuanlir.png")
        if os.path.exists(lir_path):
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", lir_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        if os.path.exists(audio_path):
            print("\n🎶 [Reproduciendo En mi Viejo San Juan] (clip 28s) 🇵🇷...")
            cmd = ["afplay", "-t", "28", audio_path] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", audio_path]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except Exception:
                        proc.kill()
            except Exception as e:
                print(f"⚠️ Error al reproducir audio: {e}")
            time.sleep(0.35)

        post_sj = (
            "What an emotional masterpiece! En mi Viejo San Juan is truly the heartfelt soul of Puerto Rico. What else would you like to explore?"
            if idioma == "en" else
            "¡Qué joya tan emocionante! 'En mi Viejo San Juan' es el verdadero himno del corazón boricua. ¿Qué más te gustaría descubrir?"
        )
        print(f"\n🤖 Orbit: {post_sj}\n")
        cerebro.agregar_historial("assistant", post_sj)
        voz.hablar(post_sj, idioma=idioma)
        while voz.hablando:
            time.sleep(0.05)
        time.sleep(0.35)

    elif accion == "reproducir_caballo_viejo":
        audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "caballo_viejo.mp3")
        lir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "caballoviejolir.png")
        if os.path.exists(lir_path):
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", lir_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        if os.path.exists(audio_path):
            print("\n🎶 [Reproduciendo Caballo Viejo de Simón Díaz] (clip 28s) 🇻🇪...")
            cmd = ["afplay", "-t", "28", audio_path] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", audio_path]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except Exception:
                        proc.kill()
            except Exception as e:
                print(f"⚠️ Error al reproducir audio: {e}")
            time.sleep(0.35)

        post_cv = (
            "That was Caballo Viejo by Simón Díaz! Did you feel the magic of the Venezuelan Llanos?"
            if idioma == "en" else
            "¡Ese fue Caballo Viejo del gran tío Simón Díaz! ¿Sentiste la magia y el sentimiento de los Llanos venezolanos?"
        )
        print(f"\n🤖 Orbit: {post_cv}\n")
        cerebro.agregar_historial("assistant", post_cv)
        voz.hablar(post_cv, idioma=idioma)
        while voz.hablando:
            time.sleep(0.05)
        time.sleep(0.35)

    elif accion == "reproducir_verde_luz":
        audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "verde_luz.mp3")
        lir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "verdeluzlir.png")
        if os.path.exists(lir_path):
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", lir_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        if os.path.exists(audio_path):
            print("\n🎶 [Reproduciendo Verde Luz de Antonio Cabán Vale] (clip 28s) 🇵🇷...")
            cmd = ["afplay", "-t", "28", audio_path] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", audio_path]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except Exception:
                        proc.kill()
            except Exception as e:
                print(f"⚠️ Error al reproducir audio: {e}")
            time.sleep(0.35)

        post_vl = (
            "Verde Luz touches the deepest roots of Puerto Rico! Would you like to know more about Puerto Rican culture?"
            if idioma == "en" else
            "¡Verde Luz llega directo al corazón de Puerto Rico! ¿Te gustaría conocer más sobre las bellezas y la música de la isla?"
        )
        print(f"\n🤖 Orbit: {post_vl}\n")
        cerebro.agregar_historial("assistant", post_vl)
        voz.hablar(post_vl, idioma=idioma)
        while voz.hablando:
            time.sleep(0.05)
        time.sleep(0.35)

    elif accion in ["mostrar_lecheria", "mostrar_san_juan", "mostrar_convention_center", "mostrar_wro"]:
        img_map = {
            "mostrar_lecheria": "lecheria.jpg",
            "mostrar_san_juan": "san_juan.jpg",
            "mostrar_convention_center": "convention_center.jpg",
            "mostrar_wro": "wro.jpg"
        }
        img_file = img_map.get(accion)
        if img_file:
            img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", img_file)
            if os.path.exists(img_path):
                try:
                    if sys.platform == "darwin":
                        subprocess.Popen(["open", img_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

    elif accion == "mostrar_qr_deleite":
        qr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "qr_deleite.png")
        if os.path.exists(qr_path):
            import shutil
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", qr_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif shutil.which("feh"):
                    subprocess.Popen(["feh", "--fullscreen", "--zoom", "fill", "--no-menus", qr_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        print("\n🎟️ [CÓDIGO DE DESCUENTO DELEITE]: ORBIT5 (5% OFF en caja)\n")

    elif accion == "mostrar_karina":
        karina_audio = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "karina.mp3")
        karina_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "karina.jpg")
        if os.path.exists(karina_img):
            import shutil
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", karina_img], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif shutil.which("feh"):
                    subprocess.Popen(["feh", "--fullscreen", "--zoom", "fill", "--no-menus", karina_img], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        if os.path.exists(karina_audio):
            print("\n🎶 [Reproduciendo Mare-Mare tradicional de los Kari'ña] 🇻🇪...")
            cmd_k = ["afplay", karina_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", karina_audio]
            try:
                proc_k = subprocess.Popen(cmd_k, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc_k.wait()
            except Exception as e:
                print(f"⚠️ Error al reproducir audio: {e}")
            time.sleep(0.35)

while True:
    try:
        info_reaccion = {
            "proc": None,
            "texto": "",
            "activa": False,
            "hilo": None,
            "cancelar": False,
            "espera_seg": 0.0
        }

        def _reproducir_con_demora(reac_file, espera):
            time.sleep(espera)
            if not info_reaccion.get("cancelar", False):
                cmd = ["afplay", reac_file] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", reac_file]
                info_reaccion["proc"] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def _al_apagar_microfono(idioma, duracion=0.0):
            # En frases largas (>= 8s), esperar entre 900 y 1100 ms (0.9 a 1.1s) para una pausa natural
            info_reaccion["activa"] = True
            info_reaccion["cancelar"] = False
            reacciones = REACCIONES_EN_PREGUNTA if idioma == "en" else REACCIONES_ES_PREGUNTA
            reac_file, reac_texto = random.choice(reacciones)
            info_reaccion["texto"] = reac_texto

            if os.path.exists(reac_file):
                pausa_min = float(os.getenv("ORBIT_PAUSA_LARGA_MIN", "0.90"))
                pausa_max = float(os.getenv("ORBIT_PAUSA_LARGA_MAX", "1.10"))
                espera = random.uniform(pausa_min, pausa_max)
                info_reaccion["espera_seg"] = espera
                t = threading.Thread(target=_reproducir_con_demora, args=(reac_file, espera), daemon=True)
                info_reaccion["hilo"] = t
                t.start()

        print("🎤 [Escuchando micrófono / Listening...] Habla en Español o Inglés...")
        texto_usuario, idioma_usuario = oido.escuchar_dual(timeout=10.0, callback_fin_audio=_al_apagar_microfono)

        if not texto_usuario:
            info_reaccion["cancelar"] = True
            if info_reaccion["proc"] and info_reaccion["proc"].poll() is None:
                try:
                    info_reaccion["proc"].terminate()
                except Exception:
                    pass
            despedidas_inactividad_es = [
                "¡Parece que te fuiste! Bueno, ¡hasta luego! Aquí estaré cuando quieras seguir charlando.",
                "¿Te fuiste? ¡Bueno, cuídate mucho y hasta la próxima aventura!",
                "No escucho a nadie por aquí. Me voy a descansar un ratito. ¡Hasta luego!"
            ]
            despedidas_inactividad_en = [
                "Looks like you stepped away! Well, goodbye! I'll be right here whenever you want to chat again.",
                "Did you leave? Well, take good care and see you on our next adventure!",
                "I don't hear anyone around. I'll take a little power rest. See you later!"
            ]
            lang_fin = oido.ultimo_idioma
            desp_inactividad = random.choice(despedidas_inactividad_en if lang_fin == "en" else despedidas_inactividad_es)
            print(f"\n⏱️ [Inactividad de 10s]: No se detectó voz.")
            print(f"🤖 Orbit: {desp_inactividad}\n")
            voz.hablar(desp_inactividad, idioma=lang_fin)
            while voz.hablando:
                time.sleep(0.05)
            print("💤 [Orbit desactivado por inactividad. ¡Hasta pronto!]")
            break

        if idioma_usuario == "keyboard":
            idioma_usuario = voz.detectar_idioma(texto_usuario)
            flag = "⌨️ " + ("🇺🇸 EN" if idioma_usuario == "en" else "🇻🇪 ES")
            print(f"📝 [{flag}] Entrada texto: \"{texto_usuario}\"")
        else:
            flag = "🎙️ " + ("🇺🇸 EN" if idioma_usuario == "en" else "🇻🇪 ES")
            print(f"👂 [{flag}] Escuchado: \"{texto_usuario}\"")

        min_texto = texto_usuario.lower().strip()

        # Detección inteligente de despedida (no confundir con preguntas que usen verbos como 'salir')
        palabras_split = min_texto.split()
        n_palabras = len(palabras_split)

        # 1. Comandos directos de consola (máximo 3 palabras, ej: 'q', 'exit', 'quit', 'salir', 'quiero salir')
        es_comando_cierre = (
            min_texto in ["q", "exit", "quit", "salir", "salir orbit", "quiero salir"] or
            (n_palabras <= 3 and any(w in palabras_split for w in ["exit", "quit"]))
        )

        # 2. Despedidas naturales (admite frases de despedida con agradecimiento de hasta 14 palabras, sin preguntas)
        es_despedida_natural = False
        patrones_despedida = [
            r"\b(chao|adios|adiós|bye|goodbye)\b",
            r"\b(hasta luego|nos vemos|hasta pronto|hasta la proxima|hasta la próxima)\b",
            r"\b(me tengo que ir|debo irme|ya me voy)\b"
        ]
        tiene_palabra_despedida = any(re.search(pat, min_texto) for pat in patrones_despedida)

        if tiene_palabra_despedida and n_palabras <= 14:
            # Si contiene patrones explícitos de pregunta, NO es despedida
            patrones_pregunta = [
                r"\b(qu[eé]\s+(es|son|hacer|opinas|piensas|tal|cosas|significa|ano|año|dia|día|lugar|puedo|hora|paso|pasó))\b",
                r"\b(c[oó]mo\b)",
                r"\b(d[oó]nde\b)",
                r"\b(cu[aá]ndo\b)",
                r"\b(qui[eé]n\b)",
                r"\b(por\s*qu[eé]\b)",
                r"\b(cu[aá]l\b)",
                r"\b(puedo\b)",
                r"\b(sabes\b)",
                r"\b(conoces\b)",
                r"\b(dime\b)",
                r"\b(cu[eé]ntame\b)",
                r"\b(expl[ií]came\b)",
                r"\b(what\b|where\b|how\b|when\b|who\b|why\b|which\b|can you\b|tell me\b)"
            ]
            if not any(re.search(pat, min_texto) for pat in patrones_pregunta):
                es_despedida_natural = True

        es_despedida = es_comando_cierre or es_despedida_natural
        if es_despedida:
            info_reaccion["cancelar"] = True
            if info_reaccion["proc"] and info_reaccion["proc"].poll() is None:
                try:
                    info_reaccion["proc"].terminate()
                except Exception:
                    pass
            despedidas_es = [
                "¡Nos vemos pronto en Puerto Rico!",
                "¡Chao pescao! Me encantó conversar contigo. ¡Que tengas un día súper genial y vuelve pronto!",
                "¡Oye, pero por qué te vas tan pronto! Bueno, ¡fue un verdadero gustazo compartir hoy! ¡Cuídate mucho y hasta la próxima!",
                "¡Hasta luego, mi pana! Me voy a recargar las baterías con una gran sonrisa después de esta buena charla. ¡Nos vemos en la próxima aventura!"
            ]
            despedidas_en = [
                "See you soon in Puerto Rico!",
                "Catch you later, alligator! I had so much fun chatting with you. Have a super awesome day and come back soon!",
                "Hey, why are you leaving so soon! Well, it was an absolute pleasure hanging out today! Take care and see you next time!",
                "Goodbye, my friend! I'm going to recharge my batteries with a big smile after this awesome conversation. See you on the next adventure!"
            ]
            lang_fin = oido.ultimo_idioma
            despedida = random.choice(despedidas_en if lang_fin == "en" else despedidas_es)
            print(f"\n🤖 Orbit: {despedida}\n")
            voz.hablar(despedida, idioma=lang_fin)
            while voz.hablando:
                time.sleep(0.05)
            break

        t0 = time.time()

        # 0. VERIFICAR SI LA ENTRADA ES INCOHERENTE, RUIDO O LE FALTAN LETRAS
        es_incoherente, aclaracion = cerebro.verificar_incoherencia(texto_usuario, idioma=idioma_usuario)
        if es_incoherente:
            info_reaccion["cancelar"] = True
            if info_reaccion["proc"] and info_reaccion["proc"].poll() is None:
                try:
                    info_reaccion["proc"].terminate()
                except Exception:
                    pass
            historial_orbit.registrar_interaccion(
                pregunta=texto_usuario,
                respuesta=aclaracion,
                reaccion="",
                latencia_ms=int((time.time() - t0) * 1000),
                idioma=idioma_usuario,
                origen="teclado" if idioma_usuario == "keyboard" else "voz",
                tipo_entrada="incoherente",
                tema="incoherente"
            )
            print(f"\n🤖 Orbit: \"{aclaracion}\"\n")
            voz.hablar(aclaracion, idioma=idioma_usuario)
            while voz.hablando:
                time.sleep(0.05)
            print("-" * 68)
            continue

        # Solo saludos o chistes cortos (oraciones directas de <= 4 palabras)
        patrones_saludo_chiste = [
            r'\b(hola|hello|buenos d[ií]as|buenas tardes|buenas noches)\b',
            r'\b(chiste|joke|gracioso|funny)\b',
            r'\b(qui[eé]n eres|who are you|c[oó]mo est[aá]s|how are you)\b'
        ]
        es_saludo_o_chiste = (
            len(texto_usuario.split()) <= 4 and
            any(re.search(pat, min_texto) for pat in patrones_saludo_chiste)
        )

        if es_saludo_o_chiste:
            info_reaccion["cancelar"] = True
            if info_reaccion["proc"] and info_reaccion["proc"].poll() is None:
                try:
                    info_reaccion["proc"].terminate()
                except Exception:
                    pass
            time.sleep(random.uniform(0.50, 0.65))
            respuesta = cerebro.responder(texto_usuario, idioma=idioma_usuario)
            latencia_ms = int((time.time() - t0) * 1000)
            historial_orbit.registrar_interaccion(
                pregunta=texto_usuario,
                respuesta=respuesta,
                reaccion="",
                latencia_ms=latencia_ms,
                idioma=idioma_usuario,
                origen="teclado" if idioma_usuario == "keyboard" else "voz",
                tipo_entrada="saludo_chiste",
                tema=cerebro.tema_actual or "general"
            )
            print(f"\n⚡ [Tiempo de primera reacción]: {latencia_ms} ms")
            print(f"🤖 Orbit: {respuesta}\n")
            voz.hablar(respuesta, idioma=idioma_usuario)
            while voz.hablando:
                time.sleep(0.05)
            accion = getattr(cerebro, "accion_pendiente", None)
            if accion:
                cerebro.accion_pendiente = None
                _ejecutar_accion_especial(accion, idioma_usuario)
        else:
            # 1. EN PARALELO, ARRANCAR INMEDIATAMENTE LA GENERACIÓN CONTEXTUAL Y SÍNTESIS
            contenedor = {"listo": False, "texto": "", "audio_path": None}

            def _generar_fondo():
                texto_cuerpo = cerebro.responder(texto_usuario, es_continuacion=True, idioma=idioma_usuario)
                texto_cuerpo = cerebro.limpiar_reaccion_inicial(texto_cuerpo)
                contenedor["texto"] = texto_cuerpo
                try:
                    contenedor["audio_path"] = voz.sintetizar_a_archivo(texto_cuerpo, idioma=idioma_usuario)
                except Exception as err:
                    print(f"\n⚠️ Error en síntesis: {err}")
                contenedor["listo"] = True

            hilo_gen = threading.Thread(target=_generar_fondo, daemon=True)
            hilo_gen.start()

            proc_reaccion = None
            reac_texto = ""
            tipo_entrada = cerebro.clasificar_tipo_entrada(texto_usuario)

            # 2. GESTIÓN DEL FALLBACK / FRASE DE ESPERA
            if info_reaccion["activa"] and (info_reaccion["proc"] or info_reaccion["hilo"]):
                # CASO >= 8s: Esperar a que concluya la pausa natural de 900-1100 ms si aún estaba corriendo
                if info_reaccion["hilo"]:
                    info_reaccion["hilo"].join()
                proc_reaccion = info_reaccion["proc"]
                reac_texto = info_reaccion["texto"]
                latencia_ms = int(info_reaccion.get("espera_seg", 1.0) * 1000)
                print(f"\n⚡ [Tiempo de primera reacción]: {latencia_ms} ms (pausa natural de 900-1100 ms tras frase >= {UMBRAL_FRASE_LARGA:.0f}s)")
                print(f"🤖 Orbit: \"{reac_texto}\" ...", end="", flush=True)
            else:
                # CASO < 8s: Pausa de 500 ms exactamente como antes, luego disparar fallback
                time.sleep(random.uniform(0.48, 0.55))

                if idioma_usuario == "en":
                    if tipo_entrada == "afirmativo":
                        reacciones = REACCIONES_EN_YES
                    elif tipo_entrada == "negativo":
                        reacciones = REACCIONES_EN_NO
                    else:
                        reacciones = REACCIONES_EN_PREGUNTA
                else:
                    if tipo_entrada == "afirmativo":
                        reacciones = REACCIONES_ES_SI
                    elif tipo_entrada == "negativo":
                        reacciones = REACCIONES_ES_NO
                    else:
                        reacciones = REACCIONES_ES_PREGUNTA

                reac_file, reac_texto = random.choice(reacciones)
                latencia_ms = int((time.time() - t0) * 1000)
                print(f"\n⚡ [Tiempo de primera reacción]: {latencia_ms} ms")
                print(f"🤖 Orbit: \"{reac_texto}\" ...", end="", flush=True)

                if os.path.exists(reac_file):
                    cmd = ["afplay", reac_file] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", reac_file]
                    proc_reaccion = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Esperar a que la frase de espera termine de reproducirse
            if proc_reaccion:
                proc_reaccion.wait()

            # Esperar a que la síntesis de fondo esté lista
            hilo_gen.join()

            print(f"\n    \"{contenedor['texto']}\"\n")

            # Registrar interacción completa en el historial persistente
            historial_orbit.registrar_interaccion(
                pregunta=texto_usuario,
                respuesta=contenedor.get("texto", ""),
                reaccion=reac_texto,
                latencia_ms=latencia_ms,
                idioma=idioma_usuario,
                origen="teclado" if idioma_usuario == "keyboard" else "voz",
                tipo_entrada=tipo_entrada,
                tema=cerebro.tema_actual or "general"
            )

            # 3. REPRODUCIR LA RESPUESTA PRINCIPAL SIN RETARDO
            if contenedor["audio_path"] and os.path.exists(contenedor["audio_path"]):
                cmd_story = ["afplay", contenedor["audio_path"]] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", contenedor["audio_path"]]
                proc_story = subprocess.Popen(cmd_story, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc_story.wait()
                time.sleep(0.35)  # Pausa limpia para que el altavoz libere el canal antes de abrir el micrófono

            accion = getattr(cerebro, "accion_pendiente", None)
            if accion:
                cerebro.accion_pendiente = None
                _ejecutar_accion_especial(accion, idioma_usuario)

        print("-" * 68)

    except (KeyboardInterrupt, EOFError):
        print("\n\n👋 Sesión finalizada.")
        break

oido.cerrar()
print("Sistema cerrado correctamente.\n")
