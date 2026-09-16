#!/usr/bin/env python3
"""
=======================================================================
  orbit_trila_bot.py
  Fused: Acoustic Trilateration + Face Tracking + Venezuela Ambassador Bot

  Flow:
    [DORMIDO]    escuchar() listens for "Orbit" on FRONT mic
                 AudioEngine tracks LEFT+RIGHT mic volumes (direction)
    [TRILATERAL] compare L/R volumes -> turn toward speaker
    [PHASE1]     camera on, search face 3s -> CENTERING / PHASE2T
    [PHASE2T]    turn 180 degrees
    [PHASE2C]    search face on opposite side 3s -> CENTERING / SWEEP
    [SWEEP]      spin 360 while camera looks for face -> CENTERING / DORMIDO
    [CENTERING]  L/R motor until face centered in frame
    [BOT]        Venezuela bot conversation (camera tracking continues)
                 goodbye/timeout -> DORMIDO

  Does NOT modify orbit_robot.py or any other existing file.
  Place this file in FINAL_AI/ alongside orbit_robot.py.
=======================================================================
"""

import sys, os, math, time, random, re, threading, json
import numpy as np
import sounddevice as sd
import cv2
import serial
import difflib
import requests

# Silence ALSA spam
_alsa_noop_ref = None
try:
    from ctypes import cdll, CFUNCTYPE, c_char_p, c_int
    _ALSA_HANDLER = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    _alsa_noop_ref = _ALSA_HANDLER(lambda *_: None)
    cdll.LoadLibrary("libasound.so.2").snd_lib_error_set_handler(_alsa_noop_ref)
except Exception:
    pass

# Venezuela bot package path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BOT_DIR    = os.path.join(_SCRIPT_DIR, "asistente_ia_venezuela")
# Add both possible locations (flat in script dir, or inside the subfolder)
if _BOT_DIR not in sys.path:
    sys.path.insert(0, _BOT_DIR)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from config          import cargar_config
from voz             import Voz
from escuchar        import Escuchar
from internet        import BusquedaWeb
from llm             import ERROR_MODELO, ERROR_OLLAMA, ERROR_TIMEOUT, AgenteVenezuela
from preguntas       import PREGUNTAS
from preguntas_sync  import responder_offline, start_sync
from media_show      import detectar_tema_media, es_afirmativo, imagen_existe, imagen_path, detectar_promo, detectar_audio_media, audio_existe, audio_path_aleatorio, detectar_respuesta_custom

# =============================================================================
# CONSTANTS
# =============================================================================
SERIAL_PORT  = "/dev/ttyUSB0"
SERIAL_BAUD  = 115200

CAM_INDEX    = 0
CAM_W, CAM_H = 320, 240
YUNET_MODEL  = os.path.join(_SCRIPT_DIR, "yunet.onnx")

# Audio (LEFT + RIGHT mics only — FRONT left free for speech_recognition)
SAMPLE_RATE  = 44100
CHUNK        = 1024
NOISE_FLOOR  = 2000   # override via config_acustica.json
SMOOTHING    = 0.4

# Face search
PHASE_1_TIMEOUT     = 6.0
PHASE_2_TIMEOUT     = 6.0
SWEEP_STEP_DEG      = 15.0
SWEEP_STEP_DELAY    = 0.7
FACE_CONFIRM_FRAMES = 3
CENTER_ZONE         = 0.15   # +/-15% of frame width = dead zone

# Turn parameters (works with existing L/R/C Arduino code — no degree commands needed)
TURN_RATE_DEG_PER_SEC = 55.0  # approx degrees/sec at VELOCIDAD_TRACKING=38
MIN_TURN_SECS         = 0.3
MOTOR_KEEPALIVE_SECS  = 0.15  # resend L/R every N secs to beat Arduino 500ms timeout

AUDIO_CACHE_DIR = os.path.join(_SCRIPT_DIR, "audio_cache")
CONFIG_FILE     = os.path.join(_SCRIPT_DIR, "config_acustica.json")

# Load config_acustica.json (optional)
_cfg = {}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE) as _f:
            _cfg = json.load(_f)
        NOISE_FLOOR = max(_cfg.get("UMBRAL", NOISE_FLOOR), 500)
        print(f"[CONFIG] NOISE_FLOOR={NOISE_FLOOR}")
    except Exception as _e:
        print(f"[CONFIG] Error: {_e}")
_CALIBRATION = {int(k): float(v) for k, v in _cfg.get("CALIBRACION", {}).items()}

# =============================================================================
# SHARED STATE
# =============================================================================
state_lock = threading.Lock()
bot_state  = {
    "talking":    False,
    "active":     False,
    "deaf_until": 0.0,
}

_media_path  = [None]   # path of image to show fullscreen, or None
_shown_media = set()    # IDs of images already offered this session; cleared on sleep
_shown_audio = set()    # IDs of audio already offered this session; cleared on sleep

# =============================================================================
# SERIAL / MOTOR CONTROL
# =============================================================================
try:
    _ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.1)
    print(f"[SERIAL] Connected on {SERIAL_PORT}")
except Exception as _e:
    print(f"[SERIAL] No serial ({_e}) -- simulation mode")
    _ser = None

_serial_lock   = threading.Lock()
_last_serial_t = 0.0

def send_motor(cmd: str):
    """Send L, R, or C. Rate-limited to 40 ms."""
    global _last_serial_t
    with _serial_lock:
        now = time.time()
        if now - _last_serial_t < 0.04:
            return
        _last_serial_t = now
        if _ser and _ser.is_open:
            _ser.write(f"{cmd}\n".encode())

def turn_timed(direction: str, degrees: float):
    """
    Turn L or R for an estimated time based on degrees.
    Resends command every MOTOR_KEEPALIVE_SECS to beat Arduino's 500ms timeout.
    """
    if degrees <= 0:
        return
    secs = max(MIN_TURN_SECS, degrees / TURN_RATE_DEG_PER_SEC)
    end  = time.time() + secs
    while time.time() < end:
        send_motor(direction)
        time.sleep(MOTOR_KEEPALIVE_SECS)
    send_motor("C")
    time.sleep(0.15)

# =============================================================================
# AUDIO ENGINE (LEFT + RIGHT mics for direction estimation)
# =============================================================================
class AudioEngine:
    """
    Tracks smoothed RMS volume on LEFT and RIGHT mics via sounddevice.
    FRONT mic is intentionally left free for speech_recognition (escuchar).
    """

    def __init__(self, idx_left: int, idx_right: int):
        self._indices = [idx_left, idx_right]
        self._cal     = [_CALIBRATION.get(idx_left, 1.0),
                         _CALIBRATION.get(idx_right, 1.0)]
        self._vols    = [0.0, 0.0]
        self._lock    = threading.Lock()
        self._running = True

    def get_volumes(self):
        with self._lock:
            return [self._vols[i] * self._cal[i] for i in range(2)]

    def direction_hint(self):
        """
        Returns (direction, degrees) based on L/R volume balance.
        direction: 'L', 'R', or None (centered / too quiet)
        degrees: estimated turn needed (used for TURN_RATE calculation)
        """
        vL, vR = self.get_volumes()
        total  = vL + vR
        if total < NOISE_FLOOR * 0.5:
            return None, 0   # too quiet
        ratio = vL / max(vR, 1.0)
        if ratio > 1.4:
            # Sound clearly from the left
            deg = min(60.0, 20.0 + (ratio - 1.4) * 20.0)
            return "L", deg
        if ratio < 0.7:
            # Sound clearly from the right
            r   = 1.0 / max(ratio, 0.01)
            deg = min(60.0, 20.0 + (r - 1.4) * 20.0)
            return "R", deg
        return None, 0   # approximately centered

    def _make_cb(self, pos):
        def _cb(indata, frames, time_info, status):
            if indata is None:
                return
            rms = float(np.sqrt(np.mean(indata[:, 0].astype(np.float32) ** 2))) * 32767.0
            with self._lock:
                self._vols[pos] = self._vols[pos] * SMOOTHING + rms * (1.0 - SMOOTHING)
        return _cb

    def _worker(self, pos, dev_idx):
        cb = self._make_cb(pos)
        try:
            rate = int(sd.query_devices(dev_idx)["default_samplerate"])
        except Exception:
            rate = SAMPLE_RATE
        channels = 1
        while self._running:
            if getattr(self, "paused", False):
                time.sleep(0.1)
                continue
            try:
                with sd.InputStream(device=dev_idx, channels=channels,
                                    samplerate=rate, dtype="float32",
                                    blocksize=CHUNK, callback=cb):
                    while self._running and not getattr(self, "paused", False):
                        time.sleep(0.05)
            except Exception:
                if not self._running:
                    break
                channels = 2 if channels == 1 else 1
                time.sleep(1.5)

    def pause(self):
        self.paused = True
        print("[AUDIO] Mic streams paused to free USB bandwidth")

    def resume(self):
        self.paused = False
        print("[AUDIO] Mic streams resumed")

    def start(self):
        for pos, idx in enumerate(self._indices):
            threading.Thread(target=self._worker, args=(pos, idx), daemon=True).start()
            time.sleep(0.1)
        print(f"[AUDIO] LEFT=[{self._indices[0]}]  RIGHT=[{self._indices[1]}]  started.")

    def stop(self):
        self._running = False


# =============================================================================
# MIC AUTO-DETECTION
# =============================================================================
def detect_microphones():
    """Returns (idx_left, idx_right, idx_front).

    C270 (webcam mic) is ALWAYS assigned as FRONT for speech recognition.
    pulse/default are used as LEFT/RIGHT ears for sounddevice direction tracking.
    This prevents ALSA crashes from sounddevice and PyAudio fighting over C270.
    """
    devices  = sd.query_devices()
    cam_mics = []
    usb_mics = []
    other    = []
    print("[AUDIO] Available input devices:")
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] < 1:
            continue
        name = dev["name"].lower()
        print(f"  [{i:2d}] {dev['name']}  ({dev['max_input_channels']}ch)")
        if any(k in name for k in ["cam", "camera", "video", "webcam", "uvc", "c270"]):
            cam_mics.append(i)
        elif any(k in name for k in ["usb", "microphone", "mic"]):
            usb_mics.append(i)
        else:
            other.append(i)

    # Full trilateration setup: 2 USB ear mics + 1 cam mic as front
    if len(usb_mics) >= 2 and len(cam_mics) >= 1:
        sel = (usb_mics[0], usb_mics[1], cam_mics[0])
    else:
        # Single-mic mode: use pulse/default/other for ears, cam for front
        # NEVER assign the cam mic as an ear — it will conflict with PyAudio
        front = cam_mics[0] if cam_mics else (other[0] if other else 0)
        ears  = [i for i in (usb_mics + other) if i != front]
        while len(ears) < 2:
            ears.append(ears[-1] if ears else front)
        sel = (ears[0], ears[1], front)

    print(f"[AUDIO] Assigned: LEFT={sel[0]}  RIGHT={sel[1]}  FRONT={sel[2]}")
    return sel


# =============================================================================
# CAMERA ENGINE (YuNet face detection)
# =============================================================================
class CameraEngine:
    """YuNet face detector. open/close on demand to save CPU."""

    def __init__(self):
        self.cap      = None
        self.is_open  = False
        self._yunet   = None
        self._confirm = 0
        self._smooth  = None
        self._alpha   = 0.3

        if os.path.exists(YUNET_MODEL) and hasattr(cv2, "FaceDetectorYN"):
            try:
                self._yunet = cv2.FaceDetectorYN.create(
                    YUNET_MODEL, "", (CAM_W, CAM_H),
                    score_threshold=0.6, nms_threshold=0.3, top_k=5,
                )
                print("[CAM] YuNet ready.")
            except Exception as e:
                print(f"[CAM] YuNet failed ({e}).")
        else:
            print("[CAM] yunet.onnx not found.")

    def open(self) -> bool:
        if self.is_open:
            return True
        for idx in [CAM_INDEX, 1, 2]:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
                cap.set(cv2.CAP_PROP_FPS, 30)
                for _ in range(5):
                    cap.read()
                self.cap      = cap
                self.is_open  = True
                self._confirm = 0
                self._smooth  = None
                if self._yunet:
                    self._yunet.setInputSize((CAM_W, CAM_H))
                print(f"[CAM] Opened (index={idx}).")
                return True
            cap.release()
        print("[CAM] Could not open camera.")
        return False

    def close(self):
        if self.cap and self.is_open:
            self.cap.release()
            self.is_open  = False
            self._confirm = 0
            self._smooth  = None
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
            print("[CAM] Closed.")

    def _smooth_box(self, box):
        if self._smooth is None:
            self._smooth = list(map(float, box))
            return box
        self._smooth = [self._alpha * b + (1 - self._alpha) * p
                        for b, p in zip(box, self._smooth)]
        return tuple(int(v) for v in self._smooth)

    def detect_face(self):
        """Returns dict {found, center_x, frame_width} or None."""
        if not self.is_open or not self.cap:
            return None
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None
        h, w = frame.shape[:2]

        if self._yunet:
            try:
                self._yunet.setInputSize((w, h))
                _, faces = self._yunet.detect(frame)
            except Exception:
                faces = None

            if faces is not None and len(faces):
                best = max(faces, key=lambda f: f[2] * f[3])
                bx, by, bw, bh = int(best[0]), int(best[1]), int(best[2]), int(best[3])
                bx, by, bw, bh = self._smooth_box((bx, by, bw, bh))
                cx = bx + bw // 2
                try:
                    disp = frame.copy()
                    cv2.rectangle(disp, (bx, by), (bx+bw, by+bh), (0, 255, 0), 2)
                    cv2.circle(disp, (cx, by + bh//2), 5, (0, 255, 0), -1)
                    cv2.line(disp, (w//2, 0), (w//2, h), (0, 0, 255), 1)
                    dz = int(w * CENTER_ZONE)
                    cv2.line(disp, (w//2-dz, 0), (w//2-dz, h), (255,128,0), 1)
                    cv2.line(disp, (w//2+dz, 0), (w//2+dz, h), (255,128,0), 1)
                    cv2.putText(disp, "LOCKED", (bx, by-8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
                    # ── Media image overlay ───────────────────────────────
                    _mp = _media_path[0]
                    if _mp and os.path.isfile(_mp):
                        _img = cv2.imread(_mp)
                        if _img is not None:
                            _mh, _mw = _img.shape[:2]
                            _scale = min(w * 0.85 / _mw, h * 0.85 / _mh)
                            _img = cv2.resize(_img, (int(_mw*_scale), int(_mh*_scale)))
                            _xo = (w - _img.shape[1]) // 2
                            _yo = (h - _img.shape[0]) // 2
                            disp[_yo:_yo+_img.shape[0], _xo:_xo+_img.shape[1]] = _img
                    cv2.imshow("Orbit", disp)
                    cv2.waitKey(1)
                except Exception:
                    pass
                return {"found": True, "center_x": cx, "frame_width": w}

        # No face
        try:
            disp = frame.copy()
            cv2.line(disp, (w//2, 0), (w//2, h), (0, 0, 255), 1)
            dz = int(w * CENTER_ZONE)
            cv2.line(disp, (w//2-dz, 0), (w//2-dz, h), (255,128,0), 1)
            cv2.line(disp, (w//2+dz, 0), (w//2+dz, h), (255,128,0), 1)
            cv2.putText(disp, "Buscando...", (8, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,128,255), 2)
            # ── Media image overlay (full screen) ────────────────────────
            _mp = _media_path[0]
            if _mp and os.path.isfile(_mp):
                _img = cv2.imread(_mp)
                if _img is not None:
                    disp = cv2.resize(_img, (w, h))
            cv2.imshow("Orbit", disp)
            cv2.waitKey(1)
        except Exception:
            pass
        return {"found": False, "frame_width": w}

    def check_face(self) -> bool:
        """True when FACE_CONFIRM_FRAMES consecutive detections."""
        res = self.detect_face()
        if res and res.get("found"):
            self._confirm += 1
            return self._confirm >= FACE_CONFIRM_FRAMES
        self._confirm = 0
        return False


# =============================================================================
# WAKE WORD
# =============================================================================
_WAKE_RE = re.compile(r'\borbi\w{0,4}\b', re.IGNORECASE)

def es_wake_word(texto: str) -> bool:
    if not texto:
        return False
    if _WAKE_RE.search(texto):
        return True
    trigger_words = ["orbit", "orb", "orbita", "porbi", 
                     "horbit", "orvi", "orby", "corbit",
                     "borbit", "morbit", "forbit", "norbit",
                     "ori", "odin", "orín",
                     "urbi", "urbit", "urbita", "urbid"]
    for w in texto.lower().split():
        if difflib.get_close_matches(w, trigger_words, n=1, cutoff=0.75):
            return True
    return False


# =============================================================================
# AUDIO CACHE
# =============================================================================
try:
    import pygame
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    _PYGAME_OK = True
    print("[AudioCache] pygame OK")
except Exception as _e:
    _PYGAME_OK = False
    print(f"[AudioCache] pygame unavailable ({_e}), using TTS fallback")

class AudioCache:
    def __init__(self, voz):
        self._voz  = voz
        self._lock = threading.Lock()

    def _path(self, key):
        return os.path.join(AUDIO_CACHE_DIR, f"{key}.mp3")

    def play(self, key: str, fallback: str = ""):
        path = self._path(key)
        if _PYGAME_OK and os.path.isfile(path):
            def _run():
                with self._lock:
                    try:
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.05)
                    except Exception:
                        pass
            threading.Thread(target=_run, daemon=True).start()
            return True
        if fallback:
            self._voz.hablar(fallback)
        return False

    def wait(self):
        if _PYGAME_OK:
            time.sleep(0.1)
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
        else:
            self._voz.esperar()

    def play_and_wait(self, key: str, fallback: str = ""):
        self.play(key, fallback)
        self.wait()

    def play_random_and_wait(self, prefix: str, count: int, fallback_list=None) -> str:
        idx = random.randrange(count)
        key = f"{prefix}_{idx}"
        fb  = fallback_list[idx] if fallback_list else ""
        self.play_and_wait(key, fb)
        return key


# =============================================================================
# EMBAJADOR (same logic as orbit_robot.py)
# =============================================================================
class Embajador:
    def __init__(self):
        self.cfg          = cargar_config()
        self.ya_saludo    = False
        self.voz          = Voz(velocidad=0.85)
        self.oidos        = Escuchar()
        self.agente       = AgenteVenezuela(self.cfg)
        self.web          = BusquedaWeb()
        print("Detectando internet...")
        self.hay_internet = self.web.hay_internet()
        print("Internet OK\n" if self.hay_internet else "Sin internet\n")

    def reiniciar(self):
        self.ya_saludo = False
        self.agente.reiniciar_historial()

    def responder(self, mensaje: str) -> str:
        msg = mensaje.lower().strip()
        if any(p in msg for p in ["hola", "buenos", "buenas", "saludos"]):
            if not self.ya_saludo:
                self.ya_saludo = True
                return random.choice([
                    "Hola explorador! Que quieres saber de Venezuela hoy?",
                    "Hola! Que quieres descubrir de Venezuela?",
                ])
        if any(p in msg for p in ["chao", "adios", "hasta luego", "bye"]):
            return random.choice([
                "Chao! Fue hermoso hablar contigo.",
                "Hasta luego! Te espero de vuelta.",
            ])
        if "gracias" in msg:
            return "De nada! Para eso estoy aqui."
        resp_custom = responder_offline(mensaje)
        if resp_custom:
            return resp_custom
        resp_ia = self.agente.responder(mensaje)
        if resp_ia in (ERROR_OLLAMA, ERROR_MODELO, ERROR_TIMEOUT):
            return "Perdon, me tarde. Puedes repetirlo?"
        return resp_ia or "Ay! No se sobre eso. Preguntame sobre Venezuela."


# =============================================================================
# INTERRUPT WATCHER
# =============================================================================
def _vigilar_interrupcion(bot, ev_int, ev_stop):
    import speech_recognition as sr
    while bot.voz.hablando and not ev_stop.is_set():
        adq = bot.oidos._mic_lock.acquire(blocking=False)
        if not adq:
            time.sleep(0.05)
            continue
        try:
            with bot.oidos.microfono as src:
                try:
                    audio = bot.oidos.reconocedor.listen(src, timeout=0.1, phrase_time_limit=1.2)
                    txt   = bot.oidos.reconocedor.recognize_google(audio, language="es-ES")
                    if es_wake_word(txt):
                        ev_int.set()
                        bot.voz.detener()
                        break
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            try:
                bot.oidos._mic_lock.release()
            except Exception:
                pass


# =============================================================================
# PHRASE BANKS
# =============================================================================
SALUDOS_INICIO = [
    "Hola explorador! Que quieres saber de Venezuela hoy?",
    "Hola! Soy Orbit. Que quieres saber de Venezuela hoy?",
    "Ey! Que bueno verte. Que quieres descubrir hoy?",
    "Hola! Soy Orbit. Que quieres saber hoy?",
]
DESPEDIDAS = [
    "¡Chao! Fue hermoso hablar contigo.",
    "¡Hasta luego! Te espero de vuelta.",
    "¡Chao! Vuelve cuando quieras.",
    "¡No olvides escanear tu cupón y disfrutar del mejor café de la ciudad!",
    "¿Ahhh, ya te vas? ¡Regresa pronto que te voy a extrañar!",
]
FRASES_INTERRUPCION = ["Dime!", "Aqui estoy!", "Si?", "Dime que quieres saber!"]


# =============================================================================
# FUSED STATE MACHINE
# =============================================================================
class OrbitFused:

    DORMIDO    = "DORMIDO"
    TRILATERAL = "TRILATERAL"
    PHASE1     = "PHASE1"
    PHASE2T    = "PHASE2T"
    PHASE2C    = "PHASE2C"
    SWEEP      = "SWEEP"
    CENTERING  = "CENTERING"
    BOT        = "BOT"

    def __init__(self, bot, audio, camera, cache):
        self.bot    = bot
        self.audio  = audio
        self.camera = camera
        self.cache  = cache

        self._state      = self.DORMIDO
        self._state_t    = time.time()
        self._running    = True
        self._turn_dir   = "R"
        self._sweep_done = 0.0
        self._sweep_last = 0.0
        self._face_continuous_time = 0.0
        threading.Thread(target=self._wake_word_thread, daemon=True).start()

    def _set(self, s):
        print(f"\n[FSM] {self._state} -> {s}")
        self._state   = s
        self._state_t = time.time()

    def _elapsed(self):
        return time.time() - self._state_t

    def _set_talking(self, v):
        with state_lock:
            bot_state["talking"] = v

    # ── Conversation ─────────────────────────────────────────────────
    def _wake_word_thread(self):
        while self._running:
            if self._state == self.DORMIDO:
                # Skip listening if deaf or talking
                with state_lock:
                    if bot_state.get("talking") or time.time() < bot_state.get("deaf_until", 0):
                        time.sleep(0.1)
                        continue
                texto = self.bot.oidos.escuchar(timeout=5, frase_max=4)
                if texto and texto != "__TIMEOUT__" and es_wake_word(texto):
                    print(f"[FSM] Wake word: '{texto}'")
                    self.camera.close() # Turn off camera immediately
                    send_motor("C")
                    self._set(self.TRILATERAL)
            else:
                time.sleep(0.1)

    def _bot_conversation_thread(self):
        bot = self.bot
        bot.reiniciar()
        self._set_talking(True)

        idx  = random.randrange(len(SALUDOS_INICIO))
        txt  = SALUDOS_INICIO[idx]
        deaf = len(txt.split()) / 2.2 + 2.1
        with state_lock:
            bot_state["deaf_until"] = time.time() + deaf

        self.cache.play_and_wait(f"saludo_{idx}", txt)
        bot.voz.esperar()
        self._set_talking(False)

        print("\n[BOT] ACTIVO -- Habla ahora\n")

        while self._running and getattr(self, "_bot_active", False):
            # Deaf window
            with state_lock:
                _talking = bot_state.get("talking", False)
                _deaf    = bot_state.get("deaf_until", 0.0)
            if _talking or time.time() < _deaf:
                time.sleep(0.05)
                continue

            texto = bot.oidos.escuchar(timeout=8, frase_max=8)

            if texto == "__TIMEOUT__":
                self._set_talking(True)
                self.cache.play_random_and_wait("despedida", 5, DESPEDIDAS)
                self._set_talking(False)
                print("[BOT] Timeout -> dormido")
                self._bot_active = False
                return

            if not texto:
                continue

            tl = texto.lower().strip()

            if es_wake_word(tl) and len(tl.split()) <= 3:
                self._set_talking(True)
                self.cache.play_random_and_wait("interrupcion", 4, FRASES_INTERRUPCION)
                self._set_talking(False)
                continue

            es_despedida = False
            var_tl = tl
            if var_tl in ["nada", "ninguna", "no", "no gracias", "nada gracias"]:
                es_despedida = True
            elif any(p in var_tl for p in ["chao", "adiós", "adios", "hasta luego", "bye", "salir", "terminar"]):
                es_despedida = True

            if es_despedida:
                self._set_talking(True)
                self.cache.play_random_and_wait("despedida", 5, DESPEDIDAS)
                self._set_talking(False)
                print("[BOT] Despedida -> dormido")
                _media_path[0] = None
                _shown_media.clear()
                self._bot_active = False
                return

            print(f"\n[BOT] Dijiste: '{texto}'")
            t0   = time.time()

            # ── Custom response intercept (before LLM) ──────────────────────
            _custom = detectar_respuesta_custom(texto)
            if _custom:
                self._set_talking(True)
                bot.voz.hablar(_custom["respuesta"])
                bot.voz.esperar()
                self._set_talking(False)
                continue
            # ─────────────────────────────────────────────────────────────────

            # ── Promo intercept (runs BEFORE LLM) ────────────────────────
            _promo = detectar_promo(texto)
            if _promo:
                _p_base = _SCRIPT_DIR
                _p_img  = os.path.join(_p_base, _promo["image"])
                _p_qr   = os.path.join(_p_base, _promo["promo_image"])
                _feh_p  = None
                import subprocess as _spp, shutil as _shh
                # Show promo image + speak
                if os.path.isfile(_p_img) and _shh.which("feh"):
                    _feh_p = _spp.Popen(
                        ["feh", "--fullscreen", "--zoom", "fill", "--no-menus", _p_img],
                        stdout=_spp.DEVNULL, stderr=_spp.DEVNULL
                    )
                self._set_talking(True)
                bot.voz.hablar(_promo["respuesta"])
                bot.voz.esperar()
                # Ask promo question
                bot.voz.hablar(_promo["promo_pregunta"])
                bot.voz.esperar()
                self._set_talking(False)
                if _feh_p:
                    _feh_p.terminate()
                # Listen for yes/no
                _r_promo = bot.oidos.escuchar(timeout=7, frase_max=6)
                if _r_promo and es_afirmativo(_r_promo):
                    # Build centered QR on black canvas, then show with feh
                    _feh_qr  = None
                    _tmp_qr  = "/tmp/orbit_qr_display.jpg"
                    if os.path.isfile(_p_qr):
                        _qr_src = cv2.imread(_p_qr)
                        if _qr_src is not None:
                            # Detect screen size via xdpyinfo, fallback 1280x720
                            try:
                                _xdpy = _spp.run(["xdpyinfo"], capture_output=True, text=True).stdout
                                import re as _re
                                _m = _re.search(r"dimensions:\s+(\d+)x(\d+)", _xdpy)
                                _SW, _SH = (int(_m.group(1)), int(_m.group(2))) if _m else (1280, 720)
                            except Exception:
                                _SW, _SH = 1280, 720
                            # Scale QR to 72% of screen, keep aspect ratio
                            _scale = min(_SW * 0.72 / _qr_src.shape[1],
                                         _SH * 0.72 / _qr_src.shape[0])
                            _qw = int(_qr_src.shape[1] * _scale)
                            _qh = int(_qr_src.shape[0] * _scale)
                            _qr_s = cv2.resize(_qr_src, (_qw, _qh))
                            # Black canvas, center QR
                            import numpy as _np
                            _canvas = _np.zeros((_SH, _SW, 3), dtype=_np.uint8)
                            _ox = (_SW - _qw) // 2
                            _oy = (_SH - _qh) // 2
                            _canvas[_oy:_oy+_qh, _ox:_ox+_qw] = _qr_s
                            cv2.imwrite(_tmp_qr, _canvas)
                        if _shh.which("feh") and os.path.isfile(_tmp_qr):
                            _feh_qr = _spp.Popen(
                                ["feh", "--fullscreen", "--zoom", "fill",
                                 "--no-menus", _tmp_qr],
                                stdout=_spp.DEVNULL, stderr=_spp.DEVNULL
                            )
                    self._set_talking(True)
                    bot.voz.hablar(_promo["promo_respuesta"])
                    bot.voz.esperar()
                    self._set_talking(False)
                    if _feh_qr:
                        _feh_qr.terminate()
                continue
            # ── End promo intercept ───────────────────────────────────────

            # --- Pensando thread ---
            llm_done = threading.Event()
            def _think_msg():
                if not llm_done.wait(2.5):
                    self._set_talking(True)
                    print("[BOT] Pensando...")
                    # Using TTS directly so we don't need a pre-recorded cache file
                    bot.voz.hablar("A ver... déjame pensar...")
                    bot.voz.esperar()
                    self._set_talking(False)
            threading.Thread(target=_think_msg, daemon=True).start()
            # -----------------------

            # ── Auto-correct common speech recognition mishearings ────────
            import re as _re
            _CORRECCIONES = [
                # "los cariño" / "los cariñas" → "los Kariña"
                (r'\blos\s+cari[ñn]o[s]?\b',       'los Kariña'),
                # "el cariño" solo en contexto de pregunta → "el Kariña"
                (r'\bel\s+cari[ñn]o\b',             'el Kariña'),
                # "pueblo cariño" → "pueblo Kariña"
                (r'\bpueblo\s+cari[ñn]o[s]?\b',     'pueblo Kariña'),
            ]
            _texto_llm = texto
            for _patron, _reemplazo in _CORRECCIONES:
                _nuevo = _re.sub(_patron, _reemplazo, _texto_llm, flags=_re.IGNORECASE)
                if _nuevo != _texto_llm:
                    print(f"[AUTO-CORRECT] '{_texto_llm}' -> '{_nuevo}'")
                    _texto_llm = _nuevo
            # ─────────────────────────────────────────────────────────────

            resp = bot.responder(_texto_llm)
            llm_done.set()  # Cancel thinking message if LLM is fast

            # Wait for thinking message to finish speaking before replying
            bot.voz.esperar()

            print(f"[BOT] {time.time()-t0:.2f}s -> {resp}\n")

            self._set_talking(True)
            bot.voz.hablar(resp)

            # ── Media offer ──────────────────────────────────────────────
            tema_media = detectar_tema_media(resp)
            if tema_media and imagen_existe(tema_media) and tema_media["id"] not in _shown_media:
                bot.voz.esperar()
                self._set_talking(False)
                # Offer to show the image (pre-recorded audio if available)
                _offer_file = os.path.join(
                    _SCRIPT_DIR,
                    f"audio_cache/media_{tema_media['id']}_offer.mp3"
                )
                self._set_talking(True)
                if os.path.isfile(_offer_file):
                    self.cache.play_and_wait(f"media_{tema_media['id']}_offer", tema_media["pregunta_show"])
                else:
                    bot.voz.hablar(tema_media["pregunta_show"])
                    bot.voz.esperar()
                self._set_talking(False)
                # Listen for yes/no
                respuesta_media = bot.oidos.escuchar(timeout=7, frase_max=6)
                if respuesta_media and es_afirmativo(respuesta_media):
                    _shown_media.add(tema_media["id"])
                    # ── Show image fullscreen via feh (safe from any thread) ──
                    import subprocess as _sp, shutil as _sh
                    _img_path = imagen_path(tema_media)
                    _feh_proc = None
                    if _sh.which("feh"):
                        _feh_proc = _sp.Popen(
                            ["feh", "--fullscreen", "--zoom", "fill", "--no-menus", _img_path],
                            stdout=_sp.DEVNULL, stderr=_sp.DEVNULL
                        )
                    # ── If entry has audio: start quietly (no pygame conflict) ──
                    import subprocess as _sp2, shutil as _sh2
                    _has_audio = bool(tema_media.get("audio_files"))
                    _afile = audio_path_aleatorio(tema_media) if _has_audio else None
                    _bg_proc  = None
                    _music_t0 = time.time()
                    _USE_FFPLAY = _sh2.which("ffplay") is not None
                    if _afile:
                        print(f"[AUDIO MEDIA] Background music: {_afile}")
                        if _USE_FFPLAY:
                            _bg_proc = _sp2.Popen(
                                ["ffplay", "-nodisp", "-loop", "0",
                                 "-volume", "20", "-loglevel", "quiet", _afile],
                                stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL
                            )
                        elif _sh2.which("mpg123"):
                            _bg_proc = _sp2.Popen(
                                ["mpg123", "-q", "--loop", "-1", "-g", "20", _afile],
                                stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL
                            )
                    # ── Speak description + follow_up ─────────────────────────
                    _base_dir = _SCRIPT_DIR
                    _desc_key = f"media_{tema_media['id']}_desc"
                    _foll_key = f"media_{tema_media['id']}_followup"
                    _desc_mp3 = os.path.join(_base_dir, f"audio_cache/{_desc_key}.mp3")
                    _foll_mp3 = os.path.join(_base_dir, f"audio_cache/{_foll_key}.mp3")
                    self._set_talking(True)
                    if os.path.isfile(_desc_mp3):
                        self.cache.play_and_wait(_desc_key, tema_media["descripcion"])
                    else:
                        bot.voz.hablar(tema_media["descripcion"])
                        bot.voz.esperar()
                    if os.path.isfile(_foll_mp3):
                        self.cache.play_and_wait(_foll_key, tema_media["follow_up"])
                    else:
                        bot.voz.hablar(tema_media["follow_up"])
                        bot.voz.esperar()
                    self._set_talking(False)
                    # ── Raise music: seek to current position, full volume ────
                    if _bg_proc:
                        _elapsed = time.time() - _music_t0
                        _bg_proc.terminate()
                        _bg_proc.wait()
                        _bg2 = None
                        if _USE_FFPLAY:
                            _bg2 = _sp2.Popen(
                                ["ffplay", "-nodisp", "-loop", "0", "-volume", "100",
                                 "-ss", f"{_elapsed:.1f}", "-loglevel", "quiet", _afile],
                                stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL
                            )
                        elif _sh2.which("mpg123"):
                            _bg2 = _sp2.Popen(
                                ["mpg123", "-q", "--loop", "-1",
                                 "-k", str(int(_elapsed * 38)), _afile],
                                stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL
                            )
                        time.sleep(20)
                        if _bg2:
                            _bg2.terminate()
                    # ── Close image ───────────────────────────────────────────
                    if _feh_proc:
                        _feh_proc.terminate()
                    time.sleep(0.1)
                    self._set_talking(True)
                    bot.voz.hablar("¿Qué más quieres saber sobre Venezuela hoy?")
                    bot.voz.esperar()
                    self._set_talking(False)
                    continue
                elif respuesta_media and len(respuesta_media.strip()) > 2:
                    # User said something different — answer it as a new question
                    resp2 = bot.responder(respuesta_media)
                    if resp2:
                        print(f"[BOT] (media redirect) -> {resp2}")
                        self._set_talking(True)
                        bot.voz.hablar(resp2)
                        bot.voz.esperar()
                        self._set_talking(False)
                        resp = resp2  # let audio offer check run on this response
                    else:
                        continue   # nothing to say, skip to next listen
            # ── End media offer ──────────────────────────────────────────

            # ── Audio offer ──────────────────────────────────────────────
            tema_audio = detectar_audio_media(resp)
            if tema_audio and audio_existe(tema_audio) and tema_audio["id"] not in _shown_audio:
                bot.voz.esperar()
                self._set_talking(False)
                self._set_talking(True)
                bot.voz.hablar(tema_audio["pregunta_show"])
                bot.voz.esperar()
                self._set_talking(False)
                respuesta_audio = bot.oidos.escuchar(timeout=7, frase_max=6)
                if respuesta_audio and es_afirmativo(respuesta_audio):
                    _shown_audio.add(tema_audio["id"])
                    _audio_file = audio_path_aleatorio(tema_audio)
                    if _audio_file:
                        import subprocess as _sp3, shutil as _sh3
                        _FFPLAY3 = _sh3.which("ffplay")
                        # ── Show image if entry has one ───────────────────────
                        _feh_a = None
                        _img_a_rel = tema_audio.get("image", "")
                        if _img_a_rel:
                            _img_a = os.path.join(
                                _SCRIPT_DIR, _img_a_rel)
                            if os.path.isfile(_img_a) and _sh3.which("feh"):
                                _feh_a = _sp3.Popen(
                                    ["feh", "--fullscreen", "--zoom", "fill",
                                     "--no-menus", _img_a],
                                    stdout=_sp3.DEVNULL, stderr=_sp3.DEVNULL
                                )
                        # ── Play verse segment if defined ─────────────────────
                        _vs = tema_audio.get("verse_start_s")
                        _ve = tema_audio.get("verse_end_s")
                        if _vs is not None and _ve is not None and _FFPLAY3:
                            _pv = _sp3.Popen(
                                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                                 "-ss", str(_vs), "-t", str(_ve - _vs),
                                 "-af", "afade=t=in:st=0:d=1.5",
                                 _audio_file],
                                stdout=_sp3.DEVNULL, stderr=_sp3.DEVNULL
                            )
                            _pv.wait()
                        # ── Ask if they want the rest ─────────────────────────
                        _promo_q = tema_audio.get(
                            "promo_pregunta", "Quieres escuchar el resto de la cancion?")
                        self._set_talking(True)
                        bot.voz.hablar(_promo_q)
                        bot.voz.esperar()
                        self._set_talking(False)
                        _r2 = bot.oidos.escuchar(timeout=7, frase_max=6)
                        if _r2 and es_afirmativo(_r2):
                            # Switch image: verso.jpg -> llanera.jpg
                            if _feh_a:
                                _feh_a.terminate()
                                _feh_a = None
                            _img_ll = os.path.join(
                                _SCRIPT_DIR,
                                "media/llanera.jpg"
                            )
                            if os.path.isfile(_img_ll) and _sh3.which("feh"):
                                _feh_a = _sp3.Popen(
                                    ["feh", "--fullscreen", "--zoom", "fill",
                                     "--no-menus", _img_ll],
                                    stdout=_sp3.DEVNULL, stderr=_sp3.DEVNULL
                                )
                            # Enthuse the user before singing
                            self._set_talking(True)
                            bot.voz.hablar("¡Canta conmigo, canta conmigo!")
                            bot.voz.esperar()
                            self._set_talking(False)
                            # Play full song from beginning
                            _full_t = tema_audio.get("full_end_s", 300)
                            if _FFPLAY3:
                                _pf = _sp3.Popen(
                                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                                     "-ss", "0", "-t", str(_full_t),
                                     "-af", "afade=t=in:st=0:d=1.5",
                                     _audio_file],
                                    stdout=_sp3.DEVNULL, stderr=_sp3.DEVNULL
                                )
                                _pf.wait()
                            # After full song, ask follow-up
                            self._set_talking(True)
                            bot.voz.hablar("¿Qué más quieres saber sobre Venezuela hoy?")
                            bot.voz.esperar()
                            self._set_talking(False)
                        else:
                            _no_resp = tema_audio.get(
                                "promo_no_resp",
                                "Perfecto, que otra cosa quieres saber sobre Venezuela hoy?")
                            # Close image first so user sees the cycle ended
                            if _feh_a:
                                _feh_a.terminate()
                                _feh_a = None
                            self._set_talking(True)
                            bot.voz.hablar(_no_resp)
                            bot.voz.esperar()
                            self._set_talking(False)
                        # ── Hide image (if still open from yes branch) ────────
                        if _feh_a:
                            _feh_a.terminate()
                    continue
                elif respuesta_audio and len(respuesta_audio.strip()) > 2:
                    resp2 = bot.responder(respuesta_audio)
                    if resp2:
                        self._set_talking(True)
                        bot.voz.hablar(resp2)
                        bot.voz.esperar()
                        self._set_talking(False)
                    continue
            # ── End audio offer ───────────────────────────────────────────


            ev_int  = threading.Event()
            ev_stop = threading.Event()
            hilo = threading.Thread(target=_vigilar_interrupcion,
                                    args=(bot, ev_int, ev_stop), daemon=True)
            hilo.start()
            bot.voz.esperar()
            ev_stop.set()
            hilo.join(timeout=0.5)
            self._set_talking(False)

            if ev_int.is_set():
                self._set_talking(True)
                self.cache.play_random_and_wait("interrupcion", 4, FRASES_INTERRUPCION)
                self._set_talking(False)

            time.sleep(0.05)

    def _run_bot(self):
        self._bot_active = True
        threading.Thread(target=self._bot_conversation_thread, daemon=True).start()
        
        while self._running and self._bot_active:
            if self.camera.is_open:
                res = self.camera.detect_face()
                if res and res.get("found"):
                    fw     = res["frame_width"]
                    offset = res["center_x"] - fw // 2
                    dead   = int(fw * CENTER_ZONE)
                    if abs(offset) > dead:
                        ratio = (abs(offset) - dead) / (fw / 2.0 - dead)
                        speed = int(35 + max(0.0, min(1.0, ratio)) * 30)
                        send_motor(f"R{speed}" if offset > 0 else f"L{speed}")
                    else:
                        send_motor("C")
                else:
                    send_motor("C")
            else:
                send_motor("C")
            time.sleep(0.03)

    # ── Main loop ────────────────────────────────────────────────────
    def run(self):
        print("\n" + "="*60)
        print("  ORBIT TRILA BOT -- Trilateration + Face + Venezuela")
        print("  Di 'ORBIT' para activar")
        print("="*60 + "\n")

        while self._running:
            try:
                s = self._state

                if s == self.DORMIDO:
                    # Camera active always in DORMIDO to track faces
                    if not self.camera.is_open:
                        self.camera.open()
                    res = self.camera.detect_face()
                    if res and res.get("found"):
                        if time.time() < getattr(self, "_face_ignore_until", 0.0):
                            self._face_continuous_time = 0.0
                        elif self._face_continuous_time == 0.0:
                            self._face_continuous_time = time.time()
                        elif time.time() - self._face_continuous_time >= 4.0:
                            print("[FSM] Face seen for 4s -> Wake up!")
                            send_motor("C")
                            self._face_continuous_time = 0.0
                            self._set(self.BOT)
                            continue
                            
                        fw     = res["frame_width"]
                        offset = res["center_x"] - fw // 2
                        dead   = int(fw * CENTER_ZONE)
                        if abs(offset) > dead:
                            ratio = (abs(offset) - dead) / (fw / 2.0 - dead)
                            speed = int(35 + max(0.0, min(1.0, ratio)) * 30)
                            send_motor(f"R{speed}" if offset > 0 else f"L{speed}")
                        else:
                            send_motor("C")
                    else:
                        self._face_continuous_time = 0.0
                        send_motor("C")

                elif s == self.TRILATERAL:
                    self.camera.close()  # Ensure camera is off during trilateration
                    direction, degrees = self.audio.direction_hint()
                    if direction and degrees > 0:
                        print(f"[FSM] Turning {direction} ~{degrees:.0f}deg")
                        turn_timed(direction, degrees)
                        self._turn_dir = direction
                    else:
                        print("[FSM] No direction hint -- no turn")
                        self._turn_dir = "R"
                    self._set(self.PHASE1)

                elif s == self.PHASE1:
                    if self._elapsed() < 0.1:
                        if not self.camera.open():
                            self._set(self.DORMIDO); continue
                        print(f"[FSM] Phase1: searching face {PHASE_1_TIMEOUT}s...")
                    if self.camera.check_face():
                        print("[FSM] Face confirmed Phase1")
                        self._set(self.CENTERING)
                    elif self._elapsed() >= PHASE_1_TIMEOUT:
                        print("[FSM] No face -> Phase2 (180)")
                        self.camera.close()
                        self._set(self.PHASE2T)

                elif s == self.PHASE2T:
                    self.camera.close()
                    flip = "R" if self._turn_dir == "L" else "L"
                    print(f"[FSM] Turning 180 {flip}")
                    turn_timed(flip, 180.0)
                    self._set(self.PHASE2C)

                elif s == self.PHASE2C:
                    if self._elapsed() < 0.1:
                        if not self.camera.open():
                            self._set(self.DORMIDO); continue
                        print(f"[FSM] Phase2: searching face {PHASE_2_TIMEOUT}s...")
                    if self.camera.check_face():
                        print("[FSM] Face confirmed Phase2")
                        self._set(self.CENTERING)
                    elif self._elapsed() >= PHASE_2_TIMEOUT:
                        print("[FSM] No face -> Sweep 360")
                        self._sweep_done = 0.0
                        self._sweep_last = time.time()
                        self._set(self.SWEEP)

                elif s == self.SWEEP:
                    if not self.camera.is_open:
                        if not self.camera.open():
                            self._set(self.DORMIDO); continue
                        print("[FSM] Sweep 360...")
                    if self.camera.check_face():
                        send_motor("C")
                        print("[FSM] Face found in sweep")
                        self._set(self.CENTERING)
                    else:
                        now = time.time()
                        if now - self._sweep_last >= SWEEP_STEP_DELAY:
                            if self._sweep_done < 360.0:
                                step = min(SWEEP_STEP_DEG, 360.0 - self._sweep_done)
                                turn_timed("R", step)
                                self._sweep_done += step
                                self._sweep_last  = now
                                print(f"[FSM] Sweep {self._sweep_done:.0f}/360")
                            else:
                                print("[FSM] Full sweep, no face -> DORMIDO")
                                self.camera.close()
                                self._set(self.DORMIDO)

                elif s == self.CENTERING:
                    if self._elapsed() < 0.1:
                        print("[FSM] Centering face...")
                    res = self.camera.detect_face()
                    if res and res.get("found"):
                        if time.time() < getattr(self, "_face_ignore_until", 0.0):
                            self._face_continuous_time = 0.0
                        elif self._face_continuous_time == 0.0:
                            self._face_continuous_time = time.time()
                        elif time.time() - self._face_continuous_time >= 4.0:
                            print("[FSM] Face seen for 4s -> Wake up!")
                            send_motor("C")
                            self._face_continuous_time = 0.0
                            self._set(self.BOT)
                            continue
                            
                        fw     = res["frame_width"]
                        offset = res["center_x"] - fw // 2
                        dead   = int(fw * CENTER_ZONE)
                        if abs(offset) <= dead:
                            send_motor("C")
                            print("[FSM] Centered -> starting bot")
                            self._set(self.BOT)
                        else:
                            ratio = (abs(offset) - dead) / (fw / 2.0 - dead)
                            speed = int(35 + max(0.0, min(1.0, ratio)) * 30)
                            send_motor(f"R{speed}" if offset > 0 else f"L{speed}")
                    else:
                        send_motor("C")
                        if self._elapsed() > 3.0:
                            print("[FSM] Lost face in centering -> DORMIDO")
                            self.camera.close()
                            self._set(self.DORMIDO)

                elif s == self.BOT:
                    if hasattr(self.audio, 'pause'): self.audio.pause()
                    self._run_bot()
                    if hasattr(self.audio, 'resume'): self.audio.resume()
                    self._face_ignore_until = time.time() + 12.0
                    self._set(self.DORMIDO)

                time.sleep(0.04)

            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                print(f"[FSM] Error in {self._state}: {e}")
                traceback.print_exc()
                time.sleep(0.5)

        send_motor("C")
        self.camera.close()
        self.audio.stop()
        if _ser and _ser.is_open:
            _ser.close()
        print("\nOrbit apagado.")

    def stop(self):
        self._running = False


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("="*60)
    print("  ORBIT TRILA BOT")
    print("  Trilateration + Face Tracking + Venezuela Bot")
    print("="*60 + "\n")

    idx_left, idx_right, _front = detect_microphones()
    audio  = AudioEngine(idx_left, idx_right)
    camera = CameraEngine()

    print("Inicializando bot Venezuela...")
    bot   = Embajador()
    cache = AudioCache(bot.voz)

    start_sync()
    print(f"  IA: {bot.cfg.proveedor} . {bot.cfg.modelo}")
    print(f"  Microfono: {'OK' if bot.oidos.disponible else 'No disponible'}")
    print(f"  Preguntas base: {len(PREGUNTAS)}")
    print("="*60 + "\n")

    if not bot.oidos.disponible:
        print("Sin microfono -- saliendo.")
        return

    audio.start()



    time.sleep(0.5)

    import signal
    sm = OrbitFused(bot, audio, camera, cache)

    def _sig(sig, frame):
        print("\nSenial de terminacion.")
        sm.stop()

    signal.signal(signal.SIGINT,  _sig)
    signal.signal(signal.SIGTERM, _sig)

    sm.run()


if __name__ == "__main__":
    main()
