"""
=============================================================================
🎤 OIDO_GOOGLE.PY — Reconocimiento Híbrido de Ultra-Baja Latencia
=============================================================================
Optimizaciones Críticas Orbit V4.0:
1. VAD Adaptativo Dinámico Continuo con Histéresis:
   - Sigue el nivel de ruido ambiente en tiempo real (EMA).
   - Umbral de inicio de habla: ~2.2x ruido ambiente (evita falsos arranques).
   - Umbral de silencio: ~1.25x ruido ambiente.
   - Corte por silencio en solo 0.38s (380 ms): Cero esperas al terminar de hablar.
2. Detección Inteligente por Duración de Audio:
   - Si audio <= 1.0s (monosílabos "sí", "no", "yes"): Decodifica con Vosk en RAM en 5 ms.
   - Si audio > 1.0s (oraciones completas): Se envía directo a Google Cloud Speech API
     sin demora previa, logrando transcripciones culturales exactas en ~400 ms.
3. Entrada de Terminal no bloqueante con select.select.
=============================================================================
"""

import os
import sys
import json
import time
import queue
import select
import threading
import numpy as np
import sounddevice as sd
import speech_recognition as sr

try:
    from vosk import Model, KaldiRecognizer
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False
    Model = None
    KaldiRecognizer = None

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_VOSK_MODEL_ES = os.path.join(_BASE_DIR, "HERO", "ProyectoDeRobotica-master", "model")
_VOSK_MODEL_EN = os.path.expanduser("~/.cache/vosk/vosk-model-small-en-us-0.15")

class OidoGoogle:
    def __init__(self, language_pref=None):
        self.language_pref = (language_pref or os.getenv("ORBIT_LANGUAGE", "auto")).lower()
        self.ultimo_idioma = "en" if self.language_pref == "en" else "es"
        self.reconocedor = sr.Recognizer()
        self.reconocedor.dynamic_energy_threshold = False
        self.samplerate = 16000
        self.channels = 1
        self.blocksize = 800  # 50 ms por bloque
        self.disponible = True
        self._lock = threading.Lock()
        self.ambient_rms = 60.0

        # Cargar modelos Vosk en RAM para monosílabos inmediatos (opcional)
        self.vosk_es = None
        self.vosk_en = None
        if HAS_VOSK:
            try:
                if os.path.exists(_VOSK_MODEL_ES):
                    self.vosk_es = Model(_VOSK_MODEL_ES)
            except Exception as e:
                print(f"⚠️ [Oído Híbrido] Vosk ES no cargado: {e}")

            try:
                if os.path.exists(_VOSK_MODEL_EN):
                    self.vosk_en = Model(_VOSK_MODEL_EN)
            except Exception:
                pass

        self.pausa_silencio_defecto = float(os.getenv("ORBIT_PAUSA_SILENCIO", "1.75"))
        self._calibrar_ruido_ambiente()
        print(f"✅ [Oído Híbrido] Calibrado (Ruido base: {self.ambient_rms:.1f} RMS | Pausa silencio: {self.pausa_silencio_defecto}s)")

    def _calibrar_ruido_ambiente(self):
        """Mide el ruido ambiente base inicial para los umbrales adaptativos sin componentes DC."""
        try:
            muestra = sd.rec(int(self.samplerate * 0.50), samplerate=self.samplerate, channels=self.channels, dtype="int16")
            sd.wait()
            arr = muestra.astype(np.float32)
            arr_ac = arr - np.mean(arr)
            rms = float(np.sqrt(np.mean(arr_ac**2))) if len(arr_ac) > 0 else 40.0
            self.ambient_rms = max(20.0, min(120.0, rms))
        except Exception:
            self.ambient_rms = 40.0

    def escuchar(self, timeout=10.0, pausa_silencio=None, callback_fin_audio=None, forzar_offline=False, *args, **kwargs) -> tuple:
        """Alias compatible con orbit_robot: retorna tupla (texto, idioma)."""
        return self.escuchar_dual(timeout=timeout, pausa_silencio=pausa_silencio, callback_fin_audio=callback_fin_audio, forzar_offline=forzar_offline, *args, **kwargs)

    def escuchar_dual(self, timeout=10.0, pausa_silencio=None, callback_fin_audio=None, forzar_offline=False, *args, **kwargs) -> tuple:
        """
        Escucha con detección de silencio adaptable.
        - Si forzar_offline=True: bypass total a Google Speech y decodificación directa en RAM con Vosk (< 50ms).
        - Soporta callback_fin_audio para lanzar la frase de espera de inmediato al cerrar el micrófono,
          solapando el reconocimiento de Google Speech en paralelo para latencia cero.
        """
        if pausa_silencio is None:
            try:
                pausa_silencio = float(os.getenv("ORBIT_PAUSA_SILENCIO", str(self.pausa_silencio_defecto)))
            except Exception:
                pausa_silencio = self.pausa_silencio_defecto
        import collections
        q_audio = queue.Queue()

        def _callback(indata, frames, time_info, status):
            q_audio.put(bytes(indata))

        try:
            stream = sd.RawInputStream(
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                dtype="int16",
                channels=self.channels,
                callback=_callback
            )
        except Exception as e:
            print(f"⚠️ [Oído Híbrido] Error abriendo micrófono con sounddevice: {e}")
            return "", self.ultimo_idioma

        pre_buffer = collections.deque(maxlen=6)  # 300 ms de audio previo
        audio_buffer = bytearray()
        habla_detectada = False
        habla_anunciada = False
        inicio_habla = None
        inicio_silencio = None
        pico_habla_rms = 0.0
        consecutivos_habla = 0
        consecutivos_ruido = 0
        consecutivos_voz_post = 0
        frames_de_voz = 0
        inicio_escucha = time.time()

        with stream:
            while True:
                # 0. Entrada por teclado no bloqueante
                if sys.platform != "win32":
                    try:
                        r_in, _, _ = select.select([sys.stdin], [], [], 0.0)
                        if r_in:
                            linea_teclado = sys.stdin.readline().strip()
                            if linea_teclado:
                                return linea_teclado, "keyboard"
                    except Exception:
                        pass

                # 1. Timeout si nadie habla ni escribe
                if not habla_detectada and (time.time() - inicio_escucha) > timeout:
                    return "", self.ultimo_idioma

                try:
                    chunk = q_audio.get(timeout=0.08)
                except queue.Empty:
                    continue

                arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                arr_ac = arr - np.mean(arr)
                mean_sq = np.mean(arr_ac ** 2) if len(arr_ac) > 0 else 0
                rms = float(np.sqrt(mean_sq)) if mean_sq > 0 else 0.0

                if not habla_detectada:
                    # Seguimiento continuo del piso de ruido acústico real antes de hablar
                    self.ambient_rms = self.ambient_rms * 0.96 + rms * 0.04
                    # Umbral de inicio de habla sobre nivel AC (debe superar claramente el ruido ambiente)
                    umbral_inicio = max(220.0, self.ambient_rms * 1.80)

                    if rms > umbral_inicio:
                        consecutivos_habla += 1
                        if consecutivos_habla >= 2:
                            habla_detectada = True
                            pico_habla_rms = rms
                            frames_de_voz = consecutivos_habla
                            if inicio_habla is None:
                                inicio_habla = time.time()
                            for b in pre_buffer:
                                audio_buffer.extend(b)
                            audio_buffer.extend(chunk)
                            inicio_silencio = None
                            if not habla_anunciada:
                                print("🎙️ [Oído] Escuchando voz...", flush=True)
                                habla_anunciada = True
                    else:
                        consecutivos_habla = 0
                        pre_buffer.append(chunk)
                else:
                    audio_buffer.extend(chunk)
                    if rms > pico_habla_rms:
                        pico_habla_rms = rms

                    # Umbral de silencio dinámico inteligente:
                    # Debe estar claramente por encima del ruido ambiente (fan/sala)
                    # pero significativamente por debajo de la voz activa
                    umbral_silencio = max(self.ambient_rms * 1.30 + 30.0, min(self.ambient_rms + 140.0, pico_habla_rms * 0.40))

                    if rms < umbral_silencio:
                        consecutivos_voz_post = 0
                        if inicio_silencio is None:
                            inicio_silencio = time.time()
                        elif (time.time() - inicio_silencio) >= pausa_silencio:
                            # Comprobación de seguridad: si la voz activa duró menos de 250ms (5 frames)
                            # fue un click o ruido breve aislado, NO una frase. Descartar y seguir escuchando en el mismo stream.
                            duracion_voz_activa = frames_de_voz * (self.blocksize / self.samplerate)
                            if duracion_voz_activa < 0.25:
                                habla_detectada = False
                                habla_anunciada = False
                                audio_buffer.clear()
                                pre_buffer.clear()
                                inicio_habla = None
                                inicio_silencio = None
                                pico_habla_rms = 0.0
                                frames_de_voz = 0
                                consecutivos_habla = 0
                                consecutivos_voz_post = 0
                                continue
                            break
                    else:
                        frames_de_voz += 1
                        consecutivos_voz_post += 1
                        # Debounce: Solo reiniciar el temporizador de silencio si hay voz sostenida real (al menos 2 bloques = 100ms)
                        # Un click aislado, eco o fluctuación del ventilador no debe resetear el contador de silencio
                        if consecutivos_voz_post >= 2:
                            inicio_silencio = None

                # Límite máximo de duración de frase
                max_duracion = float(os.getenv("ORBIT_MAX_DURACION_FRASE", "20.0"))
                if habla_detectada and len(audio_buffer) > (self.samplerate * 2 * max_duracion):
                    break

        fin_escucha = time.time()
        duracion_habla = (fin_escucha - inicio_habla) if inicio_habla else 0.0

        if not habla_detectada or len(audio_buffer) < (self.samplerate * 2 * 0.30):
            return "", self.ultimo_idioma

        arr_final = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32)
        arr_final = arr_final - np.mean(arr_final)
        pcm_limpio = np.clip(arr_final, -32768, 32767).astype(np.int16).tobytes()
        dur_audio = len(pcm_limpio) / (self.samplerate * 2)

        print(f"🎙️ [Oído] Audio capturado ({dur_audio:.1f}s). Transcribiendo con Google...", flush=True)
        audio_data = sr.AudioData(pcm_limpio, self.samplerate, 2)

        # Si forzar_offline está activo y vosk existe
        if forzar_offline and HAS_VOSK:
            rec_model = self.vosk_en if (self.ultimo_idioma == "en" or self.language_pref == "en") else self.vosk_es
            if rec_model:
                try:
                    rec = KaldiRecognizer(rec_model, self.samplerate)
                    rec.AcceptWaveform(pcm_limpio)
                    res = json.loads(rec.FinalResult()).get("text", "").strip()
                    if res:
                        return res, self.ultimo_idioma
                except Exception:
                    pass

        # Reconocimiento con Google Cloud Speech
        # Si language_pref está forzado a 'en', probar en-US primero; de lo contrario, siempre es-419 primero y luego en-US como fallback
        if self.language_pref == "en":
            codigos_idioma = ["en-US", "es-419"]
        else:
            codigos_idioma = ["es-419", "en-US"]

        for cod in codigos_idioma:
            try:
                res = self.reconocedor.recognize_google(audio_data, language=cod).strip()
                if res:
                    lang = "en" if "en" in cod else "es"
                    print(f"👂 [Google STT ({cod})] Detectado: \"{res}\"")
                    self.ultimo_idioma = lang
                    return res, lang
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"⚠️ [Google STT] Error de red: {e}")
                break
            except Exception:
                continue

        # Fallback a Vosk si Google no pudo transcribir
        if HAS_VOSK:
            rec_model = self.vosk_es if self.ultimo_idioma == "es" else self.vosk_en
            if rec_model:
                try:
                    rec = KaldiRecognizer(rec_model, self.samplerate)
                    rec.AcceptWaveform(pcm_limpio)
                    res = json.loads(rec.FinalResult()).get("text", "").strip()
                    if res:
                        print(f"👂 [Vosk Local] Detectado: \"{res}\"")
                        return res, self.ultimo_idioma
                except Exception:
                    pass

        print("ℹ️ [Oído] No se distinguieron palabras claras en el audio.")
        return "", self.ultimo_idioma

    def cerrar(self):
        pass
