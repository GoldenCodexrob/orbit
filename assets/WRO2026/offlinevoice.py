#!/usr/bin/env python3
"""
=============================================================================
🎙️ OFFLINEVOICE.PY — Motor de Síntesis Offline con Kokoro TTS (am_echo)
=============================================================================
Motor de voz neural 100% local y offline para Orbit (WRO 2026).
- Modelo: Kokoro TTS (82M)
- Voz predeterminada: am_echo (Male · American English)
- Idioma: Inglés ('a' para American English)
- Operación: 100% Offline (sin conexión a internet)
=============================================================================
"""

import os
import sys

# Forzar modo 100% offline para HuggingFace y Transformers
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import time
import threading
import subprocess
import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Buscar la voz am_echo.pt en Voice, voice o directorio actual
_CANDIDATOS_VOZ = [
    os.path.join(_BASE_DIR, "Voice", "am_echo.pt"),
    os.path.join(_BASE_DIR, "voice", "am_echo.pt"),
    os.path.join(_BASE_DIR, "am_echo.pt"),
    os.path.join(_BASE_DIR, "Voice", "af_bella.pt"),
    os.path.join(_BASE_DIR, "voice", "af_bella.pt"),
    os.path.join(_BASE_DIR, "af_bella.pt"),
]
_VOICE_FILE = next((p for p in _CANDIDATOS_VOZ if os.path.exists(p)), "am_echo")
_VOICE_TARGET = _VOICE_FILE


class OfflineVoice:
    """Clase envolvente compatible con la API de voz de Orbit (hablar, decir, esperar, detener)."""

    def __init__(self, lang_code: str = 'a', voice: str = None):
        self.lang_code = lang_code
        self.voice = voice or _VOICE_TARGET
        self._hablar_terminado = threading.Event()
        self._hablar_terminado.set()
        self._detenido = threading.Event()
        self._lock = threading.Lock()
        self._proc_actual = None

        # Resolver ruta exacta del archivo .pt para carga 100% offline sin red
        ruta_pt = None
        if isinstance(self.voice, str):
            if os.path.exists(self.voice):
                ruta_pt = self.voice
            else:
                for candidata in [
                    os.path.join(_BASE_DIR, "Voice", f"{self.voice}.pt"),
                    os.path.join(_BASE_DIR, "voice", f"{self.voice}.pt"),
                    os.path.join(_BASE_DIR, f"{self.voice}.pt"),
                    _VOICE_TARGET
                ]:
                    if os.path.exists(candidata):
                        ruta_pt = candidata
                        break

        # Precargar tensor de voz localmente en RAM
        self.voice_tensor = None
        if ruta_pt and os.path.exists(ruta_pt):
            try:
                self.voice_tensor = torch.load(ruta_pt, weights_only=True)
            except Exception:
                try:
                    self.voice_tensor = torch.load(ruta_pt)
                except Exception:
                    self.voice_tensor = None

        nombre_voz = os.path.basename(str(ruta_pt or self.voice)).replace(".pt", "")
        print(f"🔊 [Voz Kokoro TTS] Modelo Local Activado ({nombre_voz} | Male · American English | 100% Offline)")
        start = time.time()
        self.pipeline = KPipeline(lang_code=self.lang_code, repo_id='hexgrad/Kokoro-82M')
        print(f"✓ [Kokoro Offline] Modelo listo en {time.time() - start:.2f}s")

    @property
    def hablando(self) -> bool:
        return not self._hablar_terminado.is_set()

    def sintetizar_a_archivo(self, texto: str, output_path: str = None) -> str:
        """Sintetiza texto y devuelve la ruta del archivo WAV generado (24kHz)."""
        if not texto or not texto.strip():
            return None

        if not output_path:
            output_path = os.path.join(_BASE_DIR, f"speech_kokoro_{int(time.time()*1000)}.wav")

        voz_activa = self.voice_tensor if self.voice_tensor is not None else self.voice
        segments = []
        for gs, ps, audio in self.pipeline(texto.strip(), voice=voz_activa):
            segments.append(audio)

        if segments:
            audio_concat = np.concatenate(segments)
            sf.write(output_path, audio_concat, 24000)
            return output_path
        return None

    def decir(self, texto: str, idioma: str = None):
        """Reproduce el texto de forma asíncrona sin bloquear el hilo principal."""
        if not texto or not texto.strip():
            return
        if self.hablando:
            self.detener()
            time.sleep(0.05)

        self._detenido.clear()
        self._hablar_terminado.clear()
        hilo = threading.Thread(target=self._reproducir, args=(texto.strip(),), daemon=True)
        hilo.start()

    def hablar(self, texto: str, idioma: str = None):
        self.decir(texto, idioma=idioma)

    def esperar(self, timeout: float = None):
        """Espera a que termine de reproducirse el audio actual."""
        time.sleep(0.06)
        self._hablar_terminado.wait(timeout=timeout)

    def detener(self):
        """Detiene de inmediato cualquier audio que se esté reproduciendo."""
        self._detenido.set()
        with self._lock:
            if self._proc_actual and hasattr(self._proc_actual, "poll") and self._proc_actual.poll() is None:
                try:
                    self._proc_actual.terminate()
                except Exception:
                    pass
                self._proc_actual = None
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        self._hablar_terminado.set()

    def _reproducir(self, texto: str):
        wav_path = None
        try:
            wav_path = self.sintetizar_a_archivo(texto)
            if not wav_path or not os.path.exists(wav_path) or self._detenido.is_set():
                return

            if sys.platform == "darwin":
                with self._lock:
                    self._proc_actual = subprocess.Popen(["afplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                while self._proc_actual and self._proc_actual.poll() is None:
                    if self._detenido.is_set():
                        self._proc_actual.terminate()
                        break
                    time.sleep(0.04)
            else:
                try:
                    import pygame
                    if not pygame.mixer.get_init():
                        pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
                    pygame.mixer.music.load(wav_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        if self._detenido.is_set():
                            pygame.mixer.music.stop()
                            break
                        time.sleep(0.04)
                except Exception:
                    subprocess.run(["aplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"❌ Error al reproducir audio Kokoro: {e}", file=sys.stderr)
        finally:
            self._hablar_terminado.set()
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass


def loop_conversacional():
    """Bucle interactivo por consola para pruebas directas."""
    print("=" * 50)
    print("Cargando modelo Kokoro...")
    start = time.time()
    pipeline = KPipeline(lang_code='a')
    load_time = time.time() - start
    print(f"✓ Modelo cargado en {load_time:.2f}s")
    print(f"✓ Voz configurada: {os.path.basename(str(_VOICE_TARGET))}")
    print("=" * 50)

    counter = 1

    while True:
        try:
            print(f"\n[{counter}] Escribe tu texto (o 'salir' para terminar):")
            text = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta luego!")
            break

        if text.lower() in ['salir', 'exit', 'quit']:
            print("\n¡Hasta luego!")
            break

        if not text:
            continue

        output_file = f"speech_{counter}.wav"

        print(f"Generando audio...", end=" ", flush=True)
        start_gen = time.time()

        segments = []
        for gs, ps, audio in pipeline(text, voice=_VOICE_TARGET):
            segments.append(audio)

        if segments:
            audio = np.concatenate(segments)
            sf.write(output_file, audio, 24000)

            elapsed = time.time() - start_gen
            duration = len(audio) / 24000

            print(f"✓ {elapsed:.2f}s | Audio: {duration:.2f}s | Archivo: {output_file}")

            # Reproducir automáticamente si el sistema tiene reproductor disponible
            try:
                if sys.platform == "darwin":
                    subprocess.run(["afplay", output_file])
                elif subprocess.run(["which", "aplay"], stdout=subprocess.DEVNULL).returncode == 0:
                    subprocess.run(["aplay", output_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        counter += 1


if __name__ == "__main__":
    loop_conversacional()
