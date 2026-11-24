"""
Motor TTS asíncrono con edge-tts.

Reproducción cross-platform (Windows y Linux/Raspberry Pi 4):
  - Primario:  pygame.mixer  (funciona en ambos sistemas sin cambios)
  - Fallback:  ffplay        (Linux, requiere ffmpeg instalado)

Correcciones aplicadas:
  BUG-1  self.hablando era un bool accedido desde 3 hilos sin lock.
         Ahora usa threading.Event (_hablar_terminado) con propiedad.
         esperar() usa Event.wait() → sin busy-wait, sin consumo de CPU.
  BUG-2  detener() escribía el flag directamente mientras _hablar() también
         lo escribía en su finally. Ahora el Event es la única fuente
         de verdad; detener() solo llama _hablar_terminado.set().
  BUG-4  asyncio.run() puede lanzar RuntimeError si el hilo ya tiene un
         event loop activo. Sustituido por asyncio.new_event_loop().
  BUG-8  hablar() → esperar() tenía una ventana donde esperar() veía
         hablando=False antes de que el hilo arrancase. Ahora decir()
         hace _hablar_terminado.clear() ANTES de lanzar el hilo.
  ISSUE-9 ffplay no está disponible en Windows por defecto. pygame
          funciona igual en Windows y en el Pi4: código idéntico en
          ambas plataformas.
"""

import asyncio
import os
import re
import sys
import tempfile
import threading
import time

import edge_tts

# ── Backend de audio ─────────────────────────────────────────────────────────
# pygame: cross-platform (Windows, Linux, macOS, Raspberry Pi)
# ffplay: fallback solo en Linux si pygame no está disponible
try:
    import pygame
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    _BACKEND = "pygame"
except Exception as _pygame_err:
    _BACKEND = "ffplay"
    _pygame_err_msg = str(_pygame_err)


class Voz:
    def __init__(self, modelo=None, config=None, velocidad=0.85):
        self.activa = True
        self.voz = "es-AR-ElenaNeural"

        # ── Estado de reproducción sincronizado (BUG-1, BUG-2, BUG-8) ──────
        # SET   = no está hablando (estado inicial y final)
        # CLEAR = está hablando ahora mismo
        self._hablar_terminado = threading.Event()
        self._hablar_terminado.set()   # comienza sin hablar

        # Señal para interrumpir la reproducción en curso (detener())
        self._detenido = threading.Event()

        # Referencia al proceso o flag de reproducción activa
        self._proceso = None
        self._lock = threading.Lock()

        if _BACKEND == "pygame":
            print("Voz: edge-tts · Argentina · Elena  [audio: pygame [OK] cross-platform]")
        else:
            print("Voz: edge-tts · Argentina · Elena  [audio: ffplay]")
            print(f"     (pygame no disponible: {_pygame_err_msg})")

    # ── Propiedad pública — misma interfaz que antes ──────────────────────────
    @property
    def hablando(self) -> bool:
        """True mientras hay audio reproduciéndose."""
        return not self._hablar_terminado.is_set()

    # ── API pública ───────────────────────────────────────────────────────────
    def hablar(self, texto: str):
        """Alias de decir() para compatibilidad."""
        self.decir(texto)

    def decir(self, texto: str):
        """Lanza la reproducción en un hilo daemon. No bloquea."""
        if not self.activa or self.hablando:
            return
        self._detenido.clear()
        # Marcar "hablando" ANTES de lanzar el hilo (BUG-8)
        self._hablar_terminado.clear()
        hilo = threading.Thread(target=self._hablar, args=(texto,), daemon=True)
        hilo.start()

    def detener(self):
        """Interrumpe el audio en curso de inmediato."""
        self._detenido.set()
        with self._lock:
            proc = self._proceso
        if proc is not None:
            if _BACKEND == "pygame":
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
            elif hasattr(proc, "poll") and proc.poll() is None:
                proc.kill()
        with self._lock:
            self._proceso = None
        # Liberar esperar() aunque _hablar() no haya terminado (BUG-2)
        self._hablar_terminado.set()

    def esperar(self):
        """Bloquea hasta que el audio termine — sin busy-wait, sin consumo de CPU."""
        self._hablar_terminado.wait()

    # ── Métodos de conveniencia ───────────────────────────────────────────────
    @property
    def voice(self) -> bool:
        return True

    def activar(self):
        self.activa = True

    def silenciar(self):
        self.activa = False

    def cambiar_velocidad(self, valor):
        pass  # Reservado para futura implementación con rate en edge-tts

    def esta_hablando(self) -> bool:
        return self.hablando

    # ── Lógica interna ────────────────────────────────────────────────────────
    def limpiar(self, texto: str) -> str:
        """Elimina markdown y emojis que edge-tts no pronuncia bien."""
        texto = re.sub(r"\*+", "", texto)
        texto = re.sub(r"`+", "", texto)
        texto = re.sub(r"#", "", texto)
        texto = re.sub(r"\[.*?\]", "", texto)
        texto = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE00-\uFE0F]+", "", texto)
        return texto.strip()

    def _hablar(self, texto: str):
        """Hilo daemon: genera TTS y reproduce. Siempre libera el Event al salir."""
        try:
            texto = self.limpiar(texto)
            if not texto or self._detenido.is_set():
                return
            if len(texto) > 500:
                texto = texto[:500]
            self._reproducir(texto)
        except Exception as e:
            print(f"Error de voz: {e}", file=sys.stderr)
        finally:
            with self._lock:
                self._proceso = None
            # Liberar siempre, incluso en error o si detener() ya lo hizo
            self._hablar_terminado.set()

    def _reproducir(self, texto: str):
        """Genera el MP3 con edge-tts y lo reproduce con el backend configurado."""
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            # Generar audio TTS en un event loop propio (BUG-4)
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    edge_tts.Communicate(texto, self.voz).save(path)
                )
            finally:
                loop.close()

            if self._detenido.is_set():
                return

            if _BACKEND == "pygame":
                self._play_pygame(path)
            else:
                self._play_ffplay(path)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def _play_pygame(self, path: str):
        """Reproduce con pygame.mixer — funciona en Windows y Linux/Pi."""
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        with self._lock:
            self._proceso = "pygame"
        # Polling ligero con pequeño sleep para no consumir CPU
        while pygame.mixer.music.get_busy():
            if self._detenido.is_set():
                pygame.mixer.music.stop()
                break
            time.sleep(0.05)
        with self._lock:
            self._proceso = None

    def _play_ffplay(self, path: str):
        """Reproduce con ffplay — fallback en Linux si pygame no está disponible."""
        import subprocess
        proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
        )
        with self._lock:
            self._proceso = proc
        proc.wait()
        with self._lock:
            self._proceso = None
