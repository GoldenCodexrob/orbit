"""
=============================================================================
🤖 ORBIT_SIN_MOTOR.PY — Robot Autónomo Inteligente (MODO ESCRITORIO / SIN MOTORES)
=============================================================================
WRO 2026 — Future Innovators Senior
Versión 100% de escritorio y mesa sin tracción física ni conexión a la MegaPi:
- Sin motores ni ruedas: No requiere puerto serial / MegaPi ni realiza movimientos de chasis.
- Expresiones faciales y seguimiento ocular activo en pantalla a 60 FPS.
- Cerebro Cognitivo (Gemini/RAG), Voz Neuronal / Offline y Oído STT.
- Interfaz interactiva de Aprendizaje Kari'ña y Karaoke en pantalla completa.
=============================================================================
"""

import os
import sys
import json
# Desactivar extensiones problemáticas de XRandR en SDL2 bajo RealVNC / Xvnc
# Previene el crash 'X Error: BadRRCrtc (invalid Crtc parameter)'
os.environ["SDL_VIDEO_X11_XRANDR"] = "0"
os.environ["SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR"] = "0"
os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

import time
import random
import threading
import subprocess
import argparse
import cv2
import numpy as np
import math
import re
import unicodedata

# Cargar variables de entorno
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
_PARENT_DIR = os.path.dirname(_BASE_DIR)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

# Intentar importar motor de visión alargada (dual-cam stitched)
try:
    from vision_alargada import CamStreamThread, construir_vision_alargada, cargar_calibracion
    TIENE_VISION_ALARGADA = True
except Exception as _e_va:
    print(f"⚠️ [Visión] Advertencia: No se pudo importar vision_alargada ({_e_va}). Se usará modo monocámara.")
    TIENE_VISION_ALARGADA = False

_DIR_REACCIONES = os.path.join(_BASE_DIR, "audio_cache_reacciones")

# Reacciones inmediatas pre-cacheadas para eliminar silencios incómodos
REACCIONES_EN_PREGUNTA = [
    ("reaccion_en_1.mp3", "Oh, that is such a great question!"),
    ("reaccion_en_2.mp3", "I am so excited you asked about that!"),
    ("reaccion_en_3.mp3", "Oh, that is one of my absolute favorite topics!"),
    ("reaccion_en_4.mp3", "Sure thing! Let me tell you something fascinating."),
    ("reaccion_en_5.mp3", "Wow, what an awesome topic to explore today!"),
    ("reaccion_en_6.mp3", "Oh, that is a fantastic one, let me tell you!"),
    ("reaccion_en_7.mp3", "I love your curiosity! Listen to this:"),
    ("reaccion_en_8.mp3", "You got it! Here is the scoop:"),
    ("reaccion_en_9.mp3", "Right on! Let me break that down for you."),
    ("reaccion_en_10.mp3", "That's a really cool thing to ask, check this out:"),
    ("reaccion_en_11.mp3", "Oh, absolutely! You're going to love this detail."),
    ("reaccion_en_12.mp3", "Great topic to bring up! Here is what's special:"),
    ("reaccion_en_13.mp3", "Love that curiosity! Here is the fascinating story:"),
    ("reaccion_en_14.mp3", "Awesome question! Let me share this with you:"),
    ("reaccion_en_15.mp3", "Here we go! Let me explain this right away."),
    ("reaccion_en_16.mp3", "Wonderful question! Listen to this great fact:")
]

# Frases puente offline sintetizadas con la misma voz Kokoro am_echo (100% idéntica a la voz que habla)
KOKORO_REACCIONES_EN = [
    ("kokoro_reaccion_en_1.wav", "Oh, that is such a great question!"),
    ("kokoro_reaccion_en_2.wav", "I am so excited you asked about that!"),
    ("kokoro_reaccion_en_3.wav", "Oh, that is one of my favorite topics!"),
    ("kokoro_reaccion_en_4.wav", "Sure thing, let me tell you something fascinating!"),
    ("kokoro_reaccion_en_5.wav", "Wow, what an awesome topic to explore!"),
    ("kokoro_reaccion_en_6.wav", "That's a really cool thing to ask, check this out:"),
    ("kokoro_reaccion_en_7.wav", "I love your curiosity, listen to this!"),
    ("kokoro_reaccion_en_8.wav", "Great topic to bring up, here is what is special:"),
    ("kokoro_reaccion_en_9.wav", "Here we go, let me explain this right away!"),
    ("kokoro_reaccion_en_10.wav", "Wonderful question! Listen to this great fact:")
]

REACCIONES_ES_PREGUNTA = [
    ("reaccion_es_1.mp3", "¡Oye, qué buena pregunta me haces!"),
    ("reaccion_es_2.mp3", "¡Ay, ese es uno de mis temas favoritos!"),
    ("reaccion_es_3.mp3", "¡Qué alegría que me preguntes sobre eso!"),
    ("reaccion_es_4.mp3", "¡Claro que sí! Déjame contarte algo fascinante."),
    ("reaccion_es_5.mp3", "¡Uff, qué temazo para compartir hoy!"),
    ("reaccion_es_6.mp3", "¡Esa está buenísima, ya te cuento!"),
    ("reaccion_es_7.mp3", "¡Qué gran curiosidad tienes, escucha esto!"),
    ("reaccion_es_8.mp3", "¡Me encanta esa pregunta, fíjate en esto!"),
    ("reaccion_es_9.mp3", "¡De una! Te lo explico con todo detalle."),
    ("reaccion_es_10.mp3", "¡Excelente duda! Te va a encantar lo que sé."),
    ("reaccion_es_11.mp3", "¡Por supuesto! Mira qué dato tan interesante."),
    ("reaccion_es_12.mp3", "¡Qué buen punto trajiste a la mesa! Oye esto:"),
    ("reaccion_es_13.mp3", "¡Qué nota que quieras saber de eso! Déjame decirte:"),
    ("reaccion_es_14.mp3", "¡Eso me encanta! Te lo cuento al instante."),
    ("reaccion_es_15.mp3", "¡Justo lo que me gusta explicar! Atento a esto:"),
    ("reaccion_es_16.mp3", "¡Qué maravilla de pregunta! Aquí tienes la respuesta:")
]

class DummyMovimiento:
    """Controlador de movimiento nulo para ejecución en modo sin motores (escritorio)."""
    def __init__(self, *args, **kwargs):
        self.activo = False
        self.simulado = True

    def mover(self, *args, **kwargs):
        pass

    def detener(self, *args, **kwargs):
        pass

    def girar_angulo(self, *args, **kwargs):
        return True

    def cerrar(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        def _noop(*args, **kwargs):
            return None
        return _noop
try:
    from cerebro_v4 import CerebroV4 as CerebroOrbitV4
except ImportError:
    from cerebro_v4 import CerebroOrbitV4
from voz_elevenlabs import VozElevenLabs
try:
    from rag_conocimiento import BaseConocimiento as RAGConocimiento
except ImportError:
    from rag_conocimiento import RAGConocimiento
import historial_orbit
from historial_orbit import registrar_evento_qr
from robot_face import OrbitFaceBackground

# Intentar importar motores de oído
try:
    from oido_google import OidoGoogle as OidoMotor
    _OIDO_TIPO = "Google"
except Exception:
    try:
        from oido_vosk import OidoVosk as OidoMotor
        _OIDO_TIPO = "Vosk"
    except Exception:
        OidoMotor = None
        _OIDO_TIPO = "Ninguno"

# =============================================================================
# 🎟️ CATÁLOGO DE PATROCINADORES Y EXPERIENCIAS TURÍSTICAS (WRO 2026)
# =============================================================================
CATALOGO_SPONSORS_QR = {
    "deleite": {"file": "qr_deleite.png", "code": "ORBIT5", "label": "Deleite Automercado (Lechería, VZ)", "desc": "5% OFF EN AUTOMERCADO"},
    "casita_blanca": {"file": "qr_casita_blanca.png", "code": "ORBIT-CASITA", "label": "La Casita Blanca (Santurce, PR)", "desc": "PIÑA COLADA GRATIS"},
    "casita": {"file": "qr_casita_blanca.png", "code": "ORBIT-CASITA", "label": "La Casita Blanca (Santurce, PR)", "desc": "PIÑA COLADA GRATIS"},
    "chocobar": {"file": "qr_chocobar_cortes.png", "code": "ORBIT-CHURROS", "label": "Chocobar Cortés (San Juan, PR)", "desc": "CHURROS CON CHOCOLATE GRATIS"},
    "hacienda": {"file": "qr_hacienda_munoz.png", "code": "ORBIT-HACIENDA", "label": "Hacienda Muñoz (San Lorenzo, PR)", "desc": "TOUR CAFETALERO 2x1 & CAFÉ GRATIS"},
    "toroverde": {"file": "qr_toroverde.png", "code": "ORBIT-TORO", "label": "ToroVerde Adventure Park (Orocovis, PR)", "desc": "PASE AVENTURA 2x1 EN TIROLESAS"},
    "toro_verde": {"file": "qr_toroverde.png", "code": "ORBIT-TORO", "label": "ToroVerde Adventure Park (Orocovis, PR)", "desc": "PASE AVENTURA 2x1 EN TIROLESAS"},
    "paramo": {"file": "qr_paramo_cafe.png", "code": "ORBIT-PARAMO", "label": "Páramo Café (Caracas, VZ)", "desc": "MOKACCINO DE CORTESÍA GRATIS"},
    "cacao": {"file": "qr_cacao_de_origen.png", "code": "ORBIT-CACAO", "label": "Cacao de Origen (Caracas, VZ)", "desc": "CATA GUIADA DE CACAO CRIOLLO GRATIS"},
    "canaima": {"file": "qr_canaima.png", "code": "ORBIT-CANAIMA", "label": "Campamento Canaima (Canaima, VZ)", "desc": "EXCURSIÓN SALTO ÁNGEL 2x1"},
    "source": {"file": "qr_source_code.png", "code": "ORBIT-SOURCE", "label": "Orbit Web Platform & Código Fuente", "desc": "EXPLORADOR INTERACTIVO Y ARQUITECTURA"},
    "source_code": {"file": "qr_source_code.png", "code": "ORBIT-SOURCE", "label": "Orbit Web Platform & Código Fuente", "desc": "EXPLORADOR INTERACTIVO Y ARQUITECTURA"},
    "codigo_fuente": {"file": "qr_source_code.png", "code": "ORBIT-SOURCE", "label": "Orbit Web Platform & Código Fuente", "desc": "EXPLORADOR INTERACTIVO Y ARQUITECTURA"}
}

# =============================================================================
# ⚙️ CONFIGURACIÓN DE VISIÓN Y MOVIMIENTO
# =============================================================================
CAM_WIDTH = 320
CAM_HEIGHT = 240
CAM_FPS = 30
CENTER_ZONE_FRACTION = 0.22   # Zona central neutra (muerta) para centrado
VELOCIDAD_GIRO_SEGUIMIENTO_MIN = 85
VELOCIDAD_GIRO_SEGUIMIENTO_MAX = 135
VELOCIDAD_BUSQUEDA_ANGULO = 120

TIEMPO_INACTIVIDAD_BUSQUEDA = 15.0  # Segundos antes de "mirar alrededor"
ANGULO_BUSQUEDA_MIN = 75.0          # Grados mínimos de giro
ANGULO_BUSQUEDA_MAX = 150.0         # Grados máximos de giro
FRAMES_CONFIRMACION_CARA = 3        # Tramas consecutivas para confirmar cara

# =============================================================================
# 👁️ MOTOR DE VISIÓN DUAL ALARGADA Y RASTREO FACIAL (YuNet ONNX / Haar Fallback)
# =============================================================================
class MotorVision:
    def __init__(self, indice_camara=0, invertir_ojos=False, usar_alargada=True, cam_cabeza=None, cam_torso=None):
        self.indice_camara = indice_camara
        self.invertir_ojos = invertir_ojos
        self.usar_alargada = usar_alargada
        self.cam_cabeza_override = cam_cabeza
        self.cam_torso_override = cam_torso

        self.modo_dual = False
        self.stream_cabeza = None
        self.stream_torso = None
        self.cap = None  # Fallback a cámara individual
        self.cfg_alargada = None

        self.frame_width = CAM_WIDTH
        self.frame_height = CAM_HEIGHT
        self.detector_yunet = None
        self.detector_haar = None
        self._lock = threading.Lock()
        self._smooth_x = None
        self._smooth_y = None
        self._smooth_w = None
        self._alpha = 0.38
        self.perdidas_consecutivas = 0
        self.ultimo_rostro = None
        self.contador_confirmacion = 0
        self.ultimo_norm_x = 0.0
        self.ultimo_norm_y = 0.0
        self.ultimo_encontrado = False
        self._ultimo_tiempo_trama = 0.0
        self._ultima_trama_cache = None
        
        self._iniciar_detector()
        self._iniciar_detector_aruco()

    def _iniciar_detector_aruco(self):
        """Inicializa el detector ArUco para reconocimiento de la Base de Carga (DICT_7X7_50 ID 0)."""
        self.aruco_dict = None
        self.aruco_detector = None
        self._aruco_params = None
        try:
            if hasattr(cv2, "aruco"):
                self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_7X7_50)
                if hasattr(cv2.aruco, "DetectorParameters"):
                    params = cv2.aruco.DetectorParameters()
                elif hasattr(cv2.aruco, "DetectorParameters_create"):
                    params = cv2.aruco.DetectorParameters_create()
                else:
                    params = None

                if params is not None:
                    try:
                        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
                    except Exception:
                        pass

                if hasattr(cv2.aruco, "ArucoDetector"):
                    self.aruco_detector = cv2.aruco.ArucoDetector(self.aruco_dict, params)
                else:
                    self._aruco_params = params
                print("🎯 [Visión] Detector ArUco DICT_7X7_50 inicializado (Base de Carga).")
        except Exception as e:
            print(f"⚠️ [Visión] Error inicializando detector ArUco: {e}")

    def detectar_aruco(self, frame=None, target_id=0):
        """
        Escanea el frame en busca del marcador ArUco de la Base de Carga (DICT_7X7_50 ID 0).
        Retorna: (encontrado, id_detectado, centro_x, centro_y, esquinas, frame_anotado)
        """
        with self._lock:
            cuadro = frame
            if cuadro is None:
                if self.modo_dual and self.stream_cabeza and self.stream_torso:
                    ret_c, fc = self.stream_cabeza.read()
                    ret_t, ft = self.stream_torso.read()
                    if ret_c and ret_t and fc is not None and ft is not None:
                        cuadro, _ = construir_vision_alargada(
                            fc, ft,
                            overlap_px=self.cfg_alargada.get("overlap_px", 195) if self.cfg_alargada else 195,
                            offset_x=self.cfg_alargada.get("offset_x_px", 2) if self.cfg_alargada else 2,
                            modo=self.cfg_alargada.get("modo_blend", "linea") if self.cfg_alargada else "linea"
                        )
                elif self.cap and self.cap.isOpened():
                    ret, raw = self.cap.read()
                    if ret and raw is not None:
                        cuadro = raw

            if cuadro is None:
                return False, None, 0, 0, None, None

            if not hasattr(cv2, "aruco") or self.aruco_dict is None:
                return False, None, 0, 0, None, cuadro

            gray = cv2.cvtColor(cuadro, cv2.COLOR_BGR2GRAY)
            try:
                if self.aruco_detector is not None:
                    corners, ids, _ = self.aruco_detector.detectMarkers(gray)
                elif hasattr(cv2.aruco, "detectMarkers"):
                    corners, ids, _ = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self._aruco_params)
                else:
                    return False, None, 0, 0, None, cuadro

                if ids is not None and len(ids) > 0:
                    ids_flat = ids.flatten().tolist()
                    for idx, m_id in enumerate(ids_flat):
                        if target_id is None or m_id == target_id:
                            c = corners[idx][0]
                            cx = int(np.mean(c[:, 0]))
                            cy = int(np.mean(c[:, 1]))

                            # Dibujar polígono verde y etiqueta en el frame
                            pts = c.reshape((-1, 1, 2)).astype(np.int32)
                            cv2.polylines(cuadro, [pts], isClosed=True, color=(0, 255, 0), thickness=3)
                            cv2.circle(cuadro, (cx, cy), 6, (0, 255, 0), -1)
                            cv2.putText(
                                cuadro, f"BASE DE CARGA [ID:{m_id}]",
                                (int(c[0][0]), max(25, int(c[0][1]) - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA
                            )
                            return True, m_id, cx, cy, c, cuadro
            except Exception:
                pass

            return False, None, 0, 0, None, cuadro

    def _iniciar_detector(self):
        # 1. Intentar cargar modelo YuNet ONNX
        ruta_yunet = os.path.join(_BASE_DIR, "yunet.onnx")
        if not os.path.exists(ruta_yunet):
            r_alt = os.path.join(os.path.dirname(_BASE_DIR), "yunet.onnx")
            if os.path.exists(r_alt):
                ruta_yunet = r_alt

        if os.path.exists(ruta_yunet) and hasattr(cv2, "FaceDetectorYN"):
            try:
                self.detector_yunet = cv2.FaceDetectorYN.create(
                    ruta_yunet, "", (CAM_WIDTH, CAM_HEIGHT),
                    score_threshold=0.6, nms_threshold=0.3, top_k=5
                )
                print("👁️ [Visión] Detector YuNet ONNX cargado exitosamente.")
                return
            except Exception as e:
                print(f"⚠️ [Visión] YuNet falló ({e}). Usando fallback.")

        # 2. Fallback a Haar Cascade de OpenCV
        try:
            ruta_haar = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.detector_haar = cv2.CascadeClassifier(ruta_haar)
            print("👁️ [Visión] Detector Haar Cascade cargado como fallback.")
        except Exception as e:
            print(f"⚠️ [Visión] Error cargando Haar Cascade: {e}")

    def abrir_camara(self):
        """
        Inicializa las cámaras del robot.
        Intenta primero el Sistema de Visión Alargada Dual (Cabeza + Torso) con calibración guardada.
        Si alguna cámara falla o no está disponible, realiza fallback transparente a cámara individual.
        """
        with self._lock:
            # 1. Intentar inicializar Visión Alargada Dual
            if self.usar_alargada and TIENE_VISION_ALARGADA:
                try:
                    cfg = cargar_calibracion()
                    if self.cam_cabeza_override is not None:
                        cfg["cam_cabeza_idx"] = self.cam_cabeza_override
                    if self.cam_torso_override is not None:
                        cfg["cam_torso_idx"] = self.cam_torso_override

                    idx_cabeza = cfg.get("cam_cabeza_idx", 1)
                    idx_torso = cfg.get("cam_torso_idx", 0)

                    print("\n" + "=" * 68)
                    print("🚀 [Visión Dual] INICIALIZANDO SISTEMA DE VISIÓN ALARGADA ORBIT")
                    print("=" * 68)
                    print(f"  • Cámara Cabeza: /dev/video{idx_cabeza} (Rot: {cfg.get('rot_cabeza')}°, Ángulo: {cfg.get('angulo_cabeza', 0.0):+.1f}°, Zoom: {cfg.get('scale_cabeza', 1.0):.2f}x)")
                    print(f"  • Cámara Torso:  /dev/video{idx_torso} (Rot: {cfg.get('rot_torso')}°, Ángulo: {cfg.get('angulo_torso', 0.0):+.1f}°, Zoom: {cfg.get('scale_torso', 1.0):.2f}x)")
                    print(f"  • Solapamiento:  {cfg.get('overlap_px', 195)} px | Offset X: {cfg.get('offset_x_px', 2)} px | Blend: {cfg.get('modo_blend', 'linea').upper()}")
                    print("=" * 68)

                    self.stream_cabeza = CamStreamThread(
                        src=idx_cabeza,
                        name="Cabeza",
                        width=cfg.get("width", 640),
                        height=cfg.get("height", 480),
                        fps=cfg.get("fps", 30),
                        rotation_deg=cfg.get("rot_cabeza", 0),
                        fine_angle=cfg.get("angulo_cabeza", 0.0),
                        scale=cfg.get("scale_cabeza", 1.0),
                        flip_h=cfg.get("flip_cabeza", False)
                    )

                    self.stream_torso = CamStreamThread(
                        src=idx_torso,
                        name="Torso",
                        width=cfg.get("width", 640),
                        height=cfg.get("height", 480),
                        fps=cfg.get("fps", 30),
                        rotation_deg=cfg.get("rot_torso", 0),
                        fine_angle=cfg.get("angulo_torso", 0.0),
                        scale=cfg.get("scale_torso", 1.0),
                        flip_h=cfg.get("flip_torso", False)
                    )

                    ok_c = self.stream_cabeza.start()
                    ok_t = self.stream_torso.start()

                    if ok_c and ok_t:
                        # Esperar a que ambas cámaras entreguen sus primeras tramas
                        t_esp = time.time()
                        listas = False
                        while time.time() - t_esp < 2.0:
                            ret_c, fc = self.stream_cabeza.read()
                            ret_t, ft = self.stream_torso.read()
                            if ret_c and ret_t and fc is not None and ft is not None:
                                listas = True
                                test_pan, _ = construir_vision_alargada(
                                    fc, ft,
                                    overlap_px=cfg.get("overlap_px", 195),
                                    offset_x=cfg.get("offset_x_px", 2),
                                    modo=cfg.get("modo_blend", "linea")
                                )
                                h_pan, w_pan = test_pan.shape[:2]
                                self.frame_width = w_pan
                                self.frame_height = h_pan
                                if self.detector_yunet:
                                    self.detector_yunet.setInputSize((w_pan, h_pan))
                                break
                            time.sleep(0.04)

                        if listas:
                            self.modo_dual = True
                            self.cfg_alargada = cfg
                            print(f"✅ [Visión Dual] Panorama Vertical Operativo ({self.frame_width} x {self.frame_height} px) con éxito.\n")
                            return True
                        else:
                            print("⚠️ [Visión Dual] Tiempo agotado esperando tramas iniciales de ambas cámaras.")
                    else:
                        print("⚠️ [Visión Dual] No se pudieron abrir ambas cámaras en paralelo.")
                except Exception as _e_dual:
                    print(f"⚠️ [Visión Dual] Error inicializando visión alargada: {_e_dual}")

                # Limpieza en caso de fallo
                if self.stream_cabeza:
                    self.stream_cabeza.stop()
                    self.stream_cabeza = None
                if self.stream_torso:
                    self.stream_torso.stop()
                    self.stream_torso = None
                self.modo_dual = False

            # 2. Fallback a cámara individual estándar
            print("📹 [Visión] Iniciando captura en modo Monocámara Fallback...")
            for idx in [self.indice_camara, 0, 1, 2]:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, CAM_FPS)
                    for _ in range(3):
                        cap.read()
                    self.cap = cap
                    self.frame_width = CAM_WIDTH
                    self.frame_height = CAM_HEIGHT
                    if self.detector_yunet:
                        self.detector_yunet.setInputSize((CAM_WIDTH, CAM_HEIGHT))
                    print(f"📹 [Cámara Fallback] Abierta correctamente en índice {idx} ({CAM_WIDTH}x{CAM_HEIGHT}).")
                    return True
                cap.release()

            print("❌ [Cámara] No se pudo abrir ninguna cámara en el sistema.")
            return False

    def procesar_trama(self):
        """
        Lee una trama (alargada dual o monocámara) y detecta rostros de forma segura con thread-lock y caché.
        Retorna: (encontrado, cx, frame_ancho, frame_dibujado)
        """
        with self._lock:
            ahora = time.time()
            if ahora - self._ultimo_tiempo_trama < 0.022 and self._ultima_trama_cache is not None:
                return self._ultima_trama_cache

            frame = None
            y_union = None

            # 1. Obtener cuadro de visión alargada dual
            if self.modo_dual and self.stream_cabeza and self.stream_torso:
                ret_c, frame_c = self.stream_cabeza.read()
                ret_t, frame_t = self.stream_torso.read()
                if ret_c and ret_t and frame_c is not None and frame_t is not None:
                    overlap = self.cfg_alargada.get("overlap_px", 195)
                    offset_x = self.cfg_alargada.get("offset_x_px", 2)
                    modo_blend = self.cfg_alargada.get("modo_blend", "linea")
                    frame, y_union = construir_vision_alargada(
                        frame_c, frame_t,
                        overlap_px=overlap,
                        offset_x=offset_x,
                        modo=modo_blend
                    )

            # 2. Fallback a cámara individual si no hay frame dual
            if frame is None and self.cap and self.cap.isOpened():
                ret, raw = self.cap.read()
                if ret and raw is not None:
                    frame = raw

            if frame is None:
                return False, 0, self.frame_width, None

            h, w = frame.shape[:2]
            self.frame_width = w
            self.frame_height = h
            centro_x = w // 2
            centro_y = h // 2
            zona_muerta = int(w * CENTER_ZONE_FRACTION)
            linea_izq = centro_x - zona_muerta // 2
            linea_der = centro_x + zona_muerta // 2

            cara_encontrada = False
            cara_cx = 0
            cara_cy = 0

            # Líneas guía de centrado
            cv2.line(frame, (linea_izq, 0), (linea_izq, h), (255, 120, 0), 1)
            cv2.line(frame, (linea_der, 0), (linea_der, h), (255, 120, 0), 1)

            # Etiqueta de seam si estamos en modo dual
            if self.modo_dual and y_union is not None:
                if self.cfg_alargada.get("modo_blend") != "linea":
                    cv2.line(frame, (0, y_union), (w, y_union), (0, 200, 255), 1, cv2.LINE_4)
                cv2.putText(frame, "SEAM", (15, y_union - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 200, 255), 1, cv2.LINE_AA)

            # Detección con YuNet
            if self.detector_yunet:
                self.detector_yunet.setInputSize((w, h))
                _, caras = self.detector_yunet.detect(frame)
                if caras is not None and len(caras) > 0:
                    mejor = max(caras, key=lambda c: c[2] * c[3])
                    bx, by, bw, bh = int(mejor[0]), int(mejor[1]), int(mejor[2]), int(mejor[3])
                    cara_cx = bx + bw // 2
                    cara_cy = by + bh // 2
                    cara_encontrada = True
                    
                    if self._smooth_x is None:
                        self._smooth_x = float(cara_cx)
                        self._smooth_y = float(cara_cy)
                        self._smooth_w = float(bw)
                    else:
                        self._smooth_x = self._alpha * cara_cx + (1.0 - self._alpha) * self._smooth_x
                        self._smooth_y = self._alpha * cara_cy + (1.0 - self._alpha) * self._smooth_y
                        self._smooth_w = self._alpha * bw + (1.0 - self._alpha) * self._smooth_w

                    cara_cx = int(self._smooth_x)
                    cara_cy = int(self._smooth_y)

                    color = (0, 255, 0) if (linea_izq <= cara_cx <= linea_der) else (0, 165, 255)
                    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), color, 2)
                    cv2.circle(frame, (cara_cx, cara_cy), 4, color, -1)
                    etiqueta = "ORBIT LOCKED" if color == (0, 255, 0) else "SEGUIMIENTO"
                    cv2.putText(frame, etiqueta,
                                (bx, max(20, by - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Fallback con Haar
            elif self.detector_haar:
                gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                caras = self.detector_haar.detectMultiScale(gris, scaleFactor=1.2, minNeighbors=4, minSize=(40, 40))
                if len(caras) > 0:
                    mejor = max(caras, key=lambda c: c[2] * c[3])
                    bx, by, bw, bh = mejor
                    cara_cx = bx + bw // 2
                    cara_cy = by + bh // 2
                    cara_encontrada = True

                    if self._smooth_x is None:
                        self._smooth_x = float(cara_cx)
                        self._smooth_y = float(cara_cy)
                    else:
                        self._smooth_x = self._alpha * cara_cx + (1.0 - self._alpha) * self._smooth_x
                        self._smooth_y = self._alpha * cara_cy + (1.0 - self._alpha) * self._smooth_y

                    cara_cx = int(self._smooth_x)
                    cara_cy = int(self._smooth_y)

                    color = (0, 255, 0) if (linea_izq <= cara_cx <= linea_der) else (0, 165, 255)
                    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), color, 2)
                    cv2.circle(frame, (cara_cx, cara_cy), 4, color, -1)

            if cara_encontrada:
                self.contador_confirmacion += 1
                self.ultimo_encontrado = True
                self.perdidas_consecutivas = 0
                # Coordenadas normalizadas [-1.0, 1.0]
                # X: negativo = izquierda, positivo = derecha
                # Y: positivo = arriba, negativo = abajo
                self.ultimo_norm_x = float(np.clip((cara_cx - (w / 2.0)) / (w / 2.0), -1.0, 1.0))
                self.ultimo_norm_y = float(np.clip(- (cara_cy - (h / 2.0)) / (h / 2.0), -1.0, 1.0))
            else:
                self.perdidas_consecutivas += 1
                if self.perdidas_consecutivas > 4:
                    self.contador_confirmacion = 0
                    self.ultimo_encontrado = False
                    self._smooth_x = None
                    self._smooth_y = None

            self._ultimo_tiempo_trama = ahora
            self._ultima_trama_cache = (cara_encontrada, cara_cx, w, frame)
            return self._ultima_trama_cache

    def obtener_coordenadas_mirada(self):
        """
        Calcula coordenadas 2D de seguimiento ocular directo desde la cámara:
        Retorna: (encontrado, target_ojo_x, target_ojo_y)
        """
        self.procesar_trama()
        if not self.ultimo_encontrado:
            return False, 0.0, 0.0

        # Rango amplio, expresivo y fluido dentro de la esclerótica
        # Eje X: invertido por defecto (-self.ultimo_norm_x) para que coincida con la
        # perspectiva del interlocutor frente a la pantalla (si te mueves a tu derecha, Orbit mira hacia ti).
        signo_x = 1.0 if self.invertir_ojos else -1.0
        target_x = float(np.clip(signo_x * self.ultimo_norm_x * 1.10, -0.95, 0.95))
        # Eje Y: no invertido (+Y arriba, -Y abajo)
        target_y = float(np.clip(self.ultimo_norm_y * 1.10, -0.90, 0.90))
        return True, target_x, target_y

    def cara_confirmada(self):
        return self.contador_confirmacion >= FRAMES_CONFIRMACION_CARA

    def cerrar(self):
        with self._lock:
            if self.stream_cabeza:
                try:
                    self.stream_cabeza.stop()
                except Exception:
                    pass
                self.stream_cabeza = None
            if self.stream_torso:
                try:
                    self.stream_torso.stop()
                except Exception:
                    pass
                self.stream_torso = None
            if self.cap and self.cap.isOpened():
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


# =============================================================================
# 🌐 DETECCIÓN DE CONECTIVIDAD A INTERNET
# =============================================================================
def hay_conexion_internet(host="8.8.8.8", port=53, timeout=1.2) -> bool:
    """Verifica si el sistema dispone de conexión a internet real mediante DNS/Socket."""
    try:
        import socket
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


# =============================================================================
# 🤖 ORQUESTADOR DE FLUJO COMPLETO (ORBIT V4.0)
# =============================================================================
class OrbitFullRobot:
    def __init__(self, puerto_serial=None, indice_camara=0, modo_simulado=False,
                 mostrar_video=False, pantalla_completa=False, forzar_offline=False,
                 invertir_ojos=False, usar_alargada=True, cam_cabeza=None, cam_torso=None):
        print("\n" + "=" * 68)
        print("🤖 INICIALIZANDO ROBOT AUTÓNOMO ORBIT V4.0")
        print("=" * 68)

        self.mostrar_video = mostrar_video
        self.modo_simulado = modo_simulado
        self.pantalla_completa = pantalla_completa
        self.invertir_ojos = invertir_ojos
        self.silencios_consecutivos = 0
        self.ejecutando = True

        # Determinar estado de conexión
        online = False if forzar_offline else hay_conexion_internet()
        self.modo_offline = not online
        if self.modo_offline:
            print("🌐 [Orbit Full] MODO 100% OFFLINE ACTIVADO (Sin internet o --offline).")
            print("🇺🇸 [Orbit Full] Idioma fijado estrictamente en Inglés (Kokoro TTS am_echo + RAG Cultural In-Memory).")
        else:
            print("🌐 [Orbit Full] Conexión a Internet verificada: Modo Online Activado.")

        # 0. Motor Facial en Proceso Independiente (MultiProcessing a 60 FPS)
        self.cara = OrbitFaceBackground(fullscreen=self.pantalla_completa)
        self.cara.start()

        # 1. Modo Sin Motores (Escritorio / Sin MegaPi ni Ruedas)
        self.movimiento = DummyMovimiento()
        print("🛑 [Orbit Sin Motor] Ruedas y motores DESACTIVADOS. Operando en modo estático de escritorio.")

        # 2. Visión Computarizada (Visión Alargada Dual o Monocámara Fallback)
        self.vision = MotorVision(
            indice_camara=indice_camara,
            invertir_ojos=self.invertir_ojos,
            usar_alargada=usar_alargada,
            cam_cabeza=cam_cabeza,
            cam_torso=cam_torso
        )
        self.vision.abrir_camara()

        # 2.1 Estado de Base de Carga / Acople Automático
        self.base_carga_detectada = False
        self.base_carga_info = None

        # 3. Motor de Voz (Kokoro TTS am_echo si offline, ElevenLabs si online)
        self.voz = None
        if self.modo_offline:
            try:
                from offlinevoice import OfflineVoice
                self.voz = OfflineVoice(lang_code='a', voice='am_echo')
            except Exception as e:
                print(f"⚠️ [Orbit Full] Error cargando Kokoro TTS: {e}")
        else:
            try:
                self.voz = VozElevenLabs()
            except Exception as e:
                print(f"⚠️ [Orbit Full] Falló ElevenLabs ({e}), activando voz local Kokoro TTS...")
                from offlinevoice import OfflineVoice
                self.voz = OfflineVoice(lang_code='a', voice='am_echo')

        # 4. Oído / Reconocimiento de Voz (Bilingüe con prioridad nativa en Español)
        self.oido = OidoMotor() if OidoMotor else None
        if self.oido:
            self.oido.ultimo_idioma = "es"

        # 5. Cerebro Cognitivo y Base Cultural
        self.cerebro = CerebroOrbitV4()
        self.rag = RAGConocimiento()

        # Estados del Flujo
        self.ESTADO_BUSQUEDA = "BUSQUEDA"
        self.ESTADO_SALUDO = "SALUDO"
        self.ESTADO_CONVERSANDO = "CONVERSANDO"
        self.estado_actual = self.ESTADO_BUSQUEDA

        # Control de seguimiento ocular 2D continuo con cámara
        self.seguir_ojos_activo = True
        self.hilo_mirada = None

        # Temporizadores de Inactividad
        self.tiempo_ultimo_rostro = time.time()
        self.tiempo_ultima_interaccion = time.time()
        self.conversacion_activa = False

        # 6. Servidor Web Local y Gestor de Centro de Comando / Aprende con Orbit
        self.proceso_dashboard = None
        self.proceso_aprender = None
        self.puerto_dashboard = 8080
        try:
            import web_historial
            web_historial.iniciar_servidor_segundo_plano(puerto=self.puerto_dashboard)
        except Exception as err_web:
            print(f"⚠️ [Orbit Full] No se pudo inicializar servidor web de historial: {err_web}")

        # Saludos de Bienvenida (Cortos, carismáticos y receptivos)
        if self.modo_offline:
            self.SALUDOS = [
                "Hello! Explorer, what would you like to know today?"
            ]
        else:
            self.SALUDOS = [
                "¡Hola! Explorador, ¿qué quieres saber hoy?"
            ]

    def _lanzar_reaccion_puente(self, idioma="es"):
        """Reproduce de inmediato una frase puente de espera pre-cacheada para eliminar silencios."""
        if self.modo_offline or idioma == "en":
            kokoro_dir = os.path.join(_DIR_REACCIONES, "kokoro_am_echo")
            if os.path.exists(kokoro_dir):
                archivo, texto = random.choice(KOKORO_REACCIONES_EN)
                ruta = os.path.join(kokoro_dir, archivo)
            else:
                archivo, texto = random.choice(REACCIONES_EN_PREGUNTA)
                ruta = os.path.join(_DIR_REACCIONES, archivo)
        else:
            archivo, texto = random.choice(REACCIONES_ES_PREGUNTA)
            ruta = os.path.join(_DIR_REACCIONES, archivo)

        if os.path.exists(ruta):
            print(f"⚡ [Orbit] Reacción inmediata (Voz am_echo): \"{texto}\"" if (self.modo_offline or idioma == "en") else f"⚡ [Orbit] Reacción inmediata: \"{texto}\"")
            if sys.platform == "darwin":
                try:
                    return subprocess.Popen(["afplay", ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            else:
                try:
                    import pygame
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    s = pygame.mixer.Sound(ruta)
                    s.play()
                    return s
                except Exception:
                    try:
                        return subprocess.Popen(["aplay", ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
        return None

    def iniciar(self):
        print("🚀 [Orbit] Sistema listo. Esperando detección de rostros...")
        print(f"⏱️ [Orbit] Temporizador de inactividad: {TIEMPO_INACTIVIDAD_BUSQUEDA:.0f}s para mirar alrededor.")
        
        # Iniciar hilo de seguimiento ocular 2D continuo con cámara
        self.seguir_ojos_activo = True
        self.hilo_mirada = threading.Thread(target=self._bucle_seguimiento_ojos, daemon=True, name="OrbitGazeTrack")
        self.hilo_mirada.start()
        print("👀 [Orbit Full] Seguimiento visual 2D activo (ojos sincronizados con la cámara).")

        try:
            while self.ejecutando:
                if self.estado_actual == self.ESTADO_BUSQUEDA:
                    self._ciclo_busqueda()
                elif self.estado_actual == self.ESTADO_SALUDO:
                    self._ciclo_saludo()
                elif self.estado_actual == self.ESTADO_CONVERSANDO:
                    self._ciclo_conversacion()
                
                time.sleep(0.01)

        except (KeyboardInterrupt, SystemExit):
            print("\n🛑 [Orbit Sin Motor] Interrupción recibida (Ctrl+C). Deteniendo sistemas...")
            self.ejecutando = False
        finally:
            self.apagar()

    def _bucle_seguimiento_ojos(self):
        """
        Hilo continuo de alta frecuencia que traduce en tiempo real las coordenadas
        (X, Y) de la cara detectada por la cámara hacia el objetivo de mirada de Orbit.
        """
        while self.ejecutando:
            if not self.seguir_ojos_activo:
                time.sleep(0.03)
                continue

            try:
                encontrado, target_x, target_y = self.vision.obtener_coordenadas_mirada()
                if encontrado:
                    self.tiempo_ultimo_rostro = time.time()
                    # Mover ojos en 2D siguiendo a la persona con suavidad
                    self.cara.mirar_a(target_x, target_y)
                else:
                    # Si no detecta rostro tras 1.6s, retornar suavemente al centro
                    if time.time() - self.tiempo_ultimo_rostro > 1.6:
                        self.cara.mirar_a(0.0, 0.0)
            except Exception:
                pass

            time.sleep(0.033)  # ~30 FPS de actualización

    # ── 1. CICLO DE BÚSQUEDA Y SEGUIMIENTO FACIAL (MODO SIN MOTORES) ────────────
    def _ciclo_busqueda(self):
        encontrado, cx, w, frame = self.vision.procesar_trama()
        ahora = time.time()

        centro_x = w // 2
        zona_muerta = int(w * CENTER_ZONE_FRACTION)
        lim_izq = centro_x - zona_muerta // 2
        lim_der = centro_x + zona_muerta // 2

        if encontrado:
            self.tiempo_ultimo_rostro = ahora
            self.tiempo_ultima_interaccion = ahora

            # Si la cara se mantiene centrada y confirmada -> Pasar a Saludo
            if self.vision.cara_confirmada() and (lim_izq <= cx <= lim_der):
                print("🎯 [Orbit Sin Motor] ¡Cara confirmada y centrada! Procediendo a saludar...")
                self.estado_actual = self.ESTADO_SALUDO
                return
        else:
            # REGLA DE 15 SEGUNDOS DE INACTIVIDAD: MIRAR ALREDEDOR CON LOS OJOS
            tiempo_sin_ver = ahora - self.tiempo_ultimo_rostro
            if tiempo_sin_ver >= TIEMPO_INACTIVIDAD_BUSQUEDA:
                print(f"\n⏱️ [Orbit Sin Motor] {TIEMPO_INACTIVIDAD_BUSQUEDA:.0f}s sin detectar interacción. Mirando alrededor...")
                self._mirar_alrededor()
                self.tiempo_ultimo_rostro = time.time()
                self.tiempo_ultima_interaccion = time.time()

        # Opcional: mostrar ventana gráfica
        if self.mostrar_video and frame is not None:
            cv2.imshow("Orbit Vision V4.0 (Sin Motor)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.ejecutando = False

    def _mirar_alrededor(self):
        """
        Explora con la mirada hacia los lados para buscar personas (modo sin motores).
        """
        print("👀 [Orbit Sin Motor] Explorando el entorno con la mirada...")
        self.seguir_ojos_activo = False
        self.cara.cambiar_expresion("sorprendido")
        signo_ojos = 1.0 if self.invertir_ojos else -1.0

        # Mirar hacia un lado
        self.cara.mirar_a(-0.75 * signo_ojos, 0.15)
        self.cara.pestaniar()
        time.sleep(1.0)
        encontrado, _, _, _ = self.vision.procesar_trama()
        if not encontrado:
            # Mirar hacia el otro lado
            self.cara.mirar_a(0.75 * signo_ojos, -0.10)
            self.cara.pestaniar()
            time.sleep(1.0)
            encontrado, _, _, _ = self.vision.procesar_trama()

        if encontrado:
            print("🎯 [Orbit Sin Motor] ¡Persona avistada durante la exploración visual!")
            self.cara.cambiar_expresion("feliz")
            self.cara.pestaniar()
            self.tiempo_ultimo_rostro = time.time()
        else:
            self.cara.cambiar_expresion("normal")
            self.cara.mirar_a(0.0, 0.0)
        self.seguir_ojos_activo = True

    def _limpiar_saludo_redundante(self, texto: str) -> str:
        """Elimina '¡Hola!', 'Hola aventurero', etc., ya que Orbit ya se presentó en el saludo inicial."""
        if not texto:
            return ""
        t = texto.strip()
        patron = (
            r'^(¡?\s*(hola|epa|buenas(\s+tardes|\s+días|\s+noches)?|saludos|hello|hi|hey)'
            r'[\s,!\.:]*(amigo|amiga|aventurero|aventurera|explorador|viajero|compañero)?[\s,!\.:]*)+'
        )
        t = re.sub(patron, '', t, flags=re.IGNORECASE).strip()
        t = re.sub(r'^[,\.:;\s]+', '', t).strip()
        if t and t[0].islower():
            t = t[0].upper() + t[1:]
        return t or texto

    def _esperar_voz(self, timeout=None):
        """Espera a que termine de reproducirse el audio de forma segura."""
        if hasattr(self.voz, "esperar") and callable(self.voz.esperar):
            try:
                self.voz.esperar(timeout=timeout)
                return
            except TypeError:
                self.voz.esperar()
                return
        if hasattr(self.voz, "_hablar_terminado"):
            time.sleep(0.06)
            self.voz._hablar_terminado.wait(timeout=timeout)
        elif hasattr(self.voz, "hablando"):
            while getattr(self.voz, "hablando", False):
                time.sleep(0.04)

    # ── 2. CICLO DE SALUDO ───────────────────────────────────────────────────
    def _ciclo_saludo(self):
        self.movimiento.detener()
        if self.oido:
            self.oido.ultimo_idioma = "es"
        saludo = random.choice(self.SALUDOS)
        print(f"\n🤖 Orbit saluda: \"{saludo}\"")
        
        # Expresión alegre y pestañeo al saludar; ojos siguen al interlocutor
        self.seguir_ojos_activo = True
        self.cara.cambiar_expresion("feliz")
        self.cara.pestaniar()

        # Hablar mediante el motor de voz configurado (Kokoro offline o ElevenLabs online)
        if self.voz:
            self.voz.hablar(saludo)
            self._esperar_voz()
            time.sleep(0.4)
        
        self.cara.cambiar_expresion("normal")
        self.conversacion_activa = True
        self.silencios_consecutivos = 0
        self.tiempo_ultima_interaccion = time.time()
        self.estado_actual = self.ESTADO_CONVERSANDO

    # ── 3. CICLO DE CONVERSACIÓN BILINGÜE ────────────────────────────────────
    def _ciclo_conversacion(self):
        prompt_escucha = "Say your question or type in console ('exit' to quit):" if self.modo_offline else "Di tu pregunta o escribe en consola ('salir' para terminar):"
        print(f"\n🎤 [Orbit Escuchando...] {prompt_escucha}")
        
        texto_usuario = ""
        idioma = "en" if self.modo_offline else "es"

        # Expresión de escucha atenta y seguimiento visual directo en 2D
        self.seguir_ojos_activo = True
        self.cara.cambiar_expresion("escuchando")

        try:
            # Escucha con timeout de 12 segundos y pausa ágil de 0.75s (configurable por .env)
            pausa_vad = float(os.getenv("ORBIT_PAUSA_SILENCIO", "0.75"))
            if self.oido and getattr(self.oido, "disponible", True):
                res = None
                try:
                    if hasattr(self.oido, "escuchar_dual") and callable(self.oido.escuchar_dual):
                        res = self.oido.escuchar_dual(timeout=12.0, pausa_silencio=pausa_vad, forzar_offline=self.modo_offline)
                    elif hasattr(self.oido, "escuchar") and callable(self.oido.escuchar):
                        res = self.oido.escuchar(timeout=12.0, pausa_silencio=pausa_vad, forzar_offline=self.modo_offline)
                    else:
                        res = ("", "en" if self.modo_offline else "es")
                except Exception as err_escucha:
                    print(f"⚠️ [Orbit Full] Error en captura de micrófono: {err_escucha}")
                    res = ("", "en" if self.modo_offline else "es")

                if isinstance(res, (tuple, list)):
                    texto_usuario = (res[0] or "").strip() if len(res) > 0 else ""
                    idioma = res[1] if len(res) > 1 else ("en" if self.modo_offline else "es")
                elif isinstance(res, str):
                    texto_usuario = (res or "").strip()
                    idioma = "en" if self.modo_offline else "es"
                else:
                    texto_usuario = ""
                    idioma = "en" if self.modo_offline else "es"

                if idioma == "keyboard":
                    idioma = "en" if (self.modo_offline or any(w in texto_usuario.lower() for w in ["what", "who", "where", "how", "why"])) else "es"
            else:
                # Entrada de teclado si no hay micrófono
                try:
                    prompt_input = "\n👤 You (EN): " if self.modo_offline else "\n👤 Tú: "
                    texto_usuario = input(prompt_input).strip()
                    idioma = "en" if (self.modo_offline or any(w in texto_usuario.lower() for w in ["what", "who", "where", "how"])) else "es"
                except EOFError:
                    texto_usuario = "exit" if self.modo_offline else "salir"
        finally:
            self.movimiento.detener()

        texto_usuario = (texto_usuario or "").strip()
        if texto_usuario and texto_usuario != "__TIMEOUT__":
            # Clasificación inteligente de idioma en tiempo real (Español vs Inglés)
            t_low = texto_usuario.lower()
            tiene_caracteres_es = any(c in t_low for c in "áéíóúñ¿¡")
            patrones_en = [
                r"\b(open|close|command|center|fleet|i\s+love\s+you|love\s+you)\b",
                r"\b(what|who|where|how|why|when|which|whose)\b",
                r"\b(tell\s+me|can\s+you|could\s+you|would\s+you|show\s+me|give\s+me|help\s+me)\b",
                r"\b(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening)\b",
                r"\b(thank\s+you|thanks|please|yes|yeah|yep|sure|okay|cool)\b",
                r"\b(eat|food|restaurant|beach|island|culture|history|music|song|weather)\b"
            ]
            palabras_es_claras = {
                "donde", "dónde", "puedo", "comer", "que", "qué", "quien", "quién", "como", "cómo",
                "hola", "buenos", "dias", "tardes", "noches", "por", "favor", "gracias", "de",
                "la", "el", "los", "las", "un", "una", "en", "para", "con", "del", "al", "comida",
                "cultural", "quiero", "sabes", "dime", "cuéntame", "cuentame", "centro", "comando",
                "cerrar", "cierra", "volver"
            }
            tokens_in = set(re.findall(r"\b\w+\b", t_low))
            puntos_es = len(tokens_in.intersection(palabras_es_claras)) + (3 if tiene_caracteres_es else 0)
            puntos_en = sum(1 for p in patrones_en if re.search(p, t_low))
            if puntos_en > puntos_es:
                idioma = "en"
            elif puntos_es > puntos_en:
                idioma = "es"
            elif hasattr(self.cerebro, "detectar_idioma"):
                idioma = self.cerebro.detectar_idioma(texto_usuario, idioma_previo="es")
            else:
                idioma = "es"

            if self.oido:
                self.oido.ultimo_idioma = idioma

        # Caso de Silencio / Timeout en escucha
        if not texto_usuario or texto_usuario == "__TIMEOUT__":
            tiempo_sin_hablar = time.time() - self.tiempo_ultima_interaccion
            if tiempo_sin_hablar >= 20.0:
                print("⏱️ [Orbit Full] Inactividad prolongada (20s sin interacción). Finalizando conversación...")
                self.seguir_ojos_activo = False
                self.cara.cambiar_expresion("triste")
                self.cara.mirar_a(0.0, -0.35)
                despedida = "I don't hear anyone around. I'll take a quick rest. See you soon!" if idioma == "en" else "No escucho a nadie por aquí. Me voy a descansar un ratito. ¡Hasta luego!"
                print(f"🤖 Orbit: \"{despedida}\"")
                if self.voz:
                    self.voz.hablar(despedida)
                    self._esperar_voz()
                self._finalizar_conversacion()
                self.seguir_ojos_activo = True
            else:
                # Mantenerse escuchando atentamente sin interrumpir al usuario
                self.cara.cambiar_expresion("escuchando")
            return

        # Caso de Despedida explícita
        if any(w in texto_usuario.lower() for w in ["chao", "adiós", "adios", "bye", "salir", "exit", "quit", "hasta luego", "nos vemos"]):
            self.seguir_ojos_activo = True
            self.cara.cambiar_expresion("feliz")
            self.cara.pestaniar()
            despedida = "It was wonderful talking with you! Have an amazing day. See you soon!" if (self.modo_offline or idioma == "en") else "¡Fue un gran placer compartir contigo! Que tengas un día maravilloso. ¡Hasta pronto!"
            print(f"🤖 Orbit: \"{despedida}\"")
            if self.voz:
                self.voz.hablar(despedida)
                self._esperar_voz()
            self._finalizar_conversacion()
            return

        print(f"👤 Usuario [{idioma}]: \"{texto_usuario}\"")

        # Caso de Comando Especial: "Centro de Comando" (Dashboard Web Local del Robot)
        texto_lower = texto_usuario.lower()
        texto_limpio = re.sub(r'[^\w\s]', '', texto_lower)
        frases_comando = [
            "centro de comando", "centro de mandos", "centro de mando",
            "abrir centro de comando", "abre centro de comando", "abrir centro de mando",
            "ver centro de comando", "mostrar centro de comando", "panel de control",
            "abrir dashboard", "mostrar dashboard", "command center", "fleet command"
        ]
        if any(f in texto_limpio for f in frases_comando) or (
            ("centro" in texto_limpio or "command" in texto_limpio) and ("comando" in texto_limpio or "mando" in texto_limpio or "center" in texto_limpio)
        ):
            print(f"\n🎯 [Orbit Full] ¡Comando detectado: '{texto_usuario}' -> Activando Centro de Comando!")
            self.movimiento.detener()
            self.cara.cambiar_expresion("feliz")
            self.cara.pestaniar()

            anuncio = "Abriendo centro de comando de Orbit. Aquí puedes ver mis datos actuales." if (not self.modo_offline and idioma != "en") else "Opening Orbit Fleet Command Center. Here you can see my current data."
            print(f"🤖 Orbit: \"{anuncio}\"")
            if self.voz:
                self.voz.hablar(anuncio, idioma=idioma)
                self._esperar_voz()
                time.sleep(0.3)

            # Registrar interacción en historial
            try:
                historial_orbit.registrar_interaccion(
                    pregunta=texto_usuario,
                    respuesta=anuncio,
                    reaccion="⚡ Abriendo Centro de Comando",
                    latencia_ms=100,
                    idioma=idioma,
                    origen="voz",
                    tipo_entrada="comando",
                    tema="sistema"
                )
            except Exception:
                pass

            # Desplegar dashboard y quedar a la espera auditiva de 'cerrar'
            self._abrir_centro_comando()
            self._esperar_comando_cerrar(idioma=idioma)
            return

        # Caso de Comando Especial: "Aprender Kari'ña" / "Aprende con Orbit" / "Duolingo"
        texto_norm_cmd = "".join(c for c in unicodedata.normalize("NFD", texto_lower) if unicodedata.category(c) != "Mn")
        patrones_cmd_aprender = [
            r'\b(aprender|aprende|aprendamos|estudiar|practicar)\b.*?\b(karina|carina|carino)\b',
            r'\b(ensename|ensenar|clase|leccion|lecciones)\b.*?\b(karina|carina|carino)\b',
            r'\b(modo\s+)?(karina|carina|carino)\b.*?\b(aprender|aprendizaje|estudiar|duolingo)\b',
            r'\bmodo\s+(karina|carina|carino)\b',
            r'\b(quiero|deseo|me\s+gustaria|ensename\s+a|como)\s+hablar\s+(en\s+)?(karina|carina|carino)\b',
            r'\b(duolingo|duolingorbit|aprende\s+con\s+orbit)\b',
            r'\b(learn|study|practice|teach\s+me)\b.*?\b(karina|indigenous)\b',
            r'\b(open\s+duolingo|duolingo\s+mode|learn\s+with\s+orbit)\b'
        ]
        if any(re.search(pat, texto_norm_cmd) for pat in patrones_cmd_aprender):
            print(f"\n🎯 [Orbit Full] ¡Comando detectado: '{texto_usuario}' -> Activando Modo Aprende con Orbit (Kari'ña)!")
            self.movimiento.detener()
            self.cara.cambiar_expresion("feliz")
            self.cara.pestaniar()

            anuncio = (
                "How wonderful to learn our ancestral roots! Opening Learn with Orbit to practice the Kari'ña language."
                if (self.modo_offline or idioma == "en") else
                "¡Qué gran entusiasmo por nuestras raíces ancestrales! Abriendo Aprende con Orbit para practicar la lengua Kari'ña."
            )
            print(f"🤖 Orbit: \"{anuncio}\"")

            # 🚀 Abrir Chromium en paralelo MIENTRAS Orbit habla el anuncio para que esté listo al terminar
            print("🚀 [Orbit Full] Pre-abriendo interfaz Aprende con Orbit en paralelo mientras habla...")
            self._abrir_modo_aprender_karina(idioma=idioma)

            if self.voz:
                self.voz.hablar(anuncio, idioma=idioma)
                self._esperar_voz()
                time.sleep(0.3)

            try:
                historial_orbit.registrar_interaccion(
                    pregunta=texto_usuario,
                    respuesta=anuncio,
                    reaccion="📚 Abriendo Aprender Kari'ña",
                    latencia_ms=100,
                    idioma=idioma,
                    origen="voz",
                    tipo_entrada="comando",
                    tema="educacion"
                )
            except Exception:
                pass

            self._esperar_comando_cerrar_karina(idioma=idioma)
            return

        # Caso de Comando Especial: "Carga" / "Base de Carga" (Giro 360° y Detección ArUco ID 0)
        frases_carga = [
            "carga", "cargar", "a cargar", "ve a cargar", "ir a cargar",
            "base de carga", "estacion de carga", "estación de carga",
            "buscar carga", "busca la carga", "buscar base", "busca la base",
            "encontrar carga", "dock", "docking", "charge", "charging",
            "go charge", "find dock", "charging station"
        ]
        tokens_carga = set(re.findall(r"\b\w+\b", texto_limpio))
        es_comando_carga = any(f in texto_limpio for f in frases_carga) or (
            "carga" in tokens_carga or "cargar" in tokens_carga or "dock" in tokens_carga or "docking" in tokens_carga
        )

        if es_comando_carga:
            print(f"\n🔋 [Orbit Full] ¡Comando de carga detectado: '{texto_usuario}'!")
            self._ejecutar_busqueda_base_carga(idioma=idioma)
            return

        # Generar respuesta cognitiva cultural
        
        # 1. ⚡ REACCIÓN PUENTE INMEDIATA ON-DEMAND:
        # Se disparará ÚNICAMENTE si Cerebro no tiene un atajo directo en RAM y necesita consultar al LLM
        proc_reaccion = None

        def _notificar_espera_llm():
            nonlocal proc_reaccion
            if proc_reaccion is None:
                proc_reaccion = self._lanzar_reaccion_puente(idioma=idioma)

        # 2. 🧠 EXPRESIÓN PENSANDO INTERACTIVA:
        # - Mirada reflexiva hacia arriba-derecha
        # - Pupila dilatada cognitivamente
        self.seguir_ojos_activo = False
        print("🤔 [Orbit Full] Pensando la respuesta...")
        self.cara.cambiar_expresion("pensando")
        self.cara.mirar_a(0.50, 0.65)

        # Buscar contexto RAG y respuesta cognitiva (local si offline, nube si online)
        try:
            contexto_rag = self.rag.buscar(texto_usuario, k=2)
        except Exception:
            contexto_rag = ""

        respuesta = self.cerebro.responder(
            texto_usuario,
            idioma=idioma,
            es_continuacion=True,
            forzar_local=self.modo_offline,
            callback_inicio_llm=_notificar_espera_llm
        )
        # Eliminar saludos redundantes de inicio ("¡Hola!", "Hola aventurero", etc.) ya que Orbit ya se presentó
        respuesta = self._limpiar_saludo_redundante(respuesta)
        
        # Esperar a que la frase de reacción inmediata termine de hablar completamente antes de dar la respuesta
        if proc_reaccion:
            try:
                if isinstance(proc_reaccion, subprocess.Popen):
                    proc_reaccion.wait(timeout=8.0)
                elif hasattr(proc_reaccion, "wait"):
                    proc_reaccion.wait(timeout=8.0)
                else:
                    try:
                        import pygame
                        while pygame.mixer.get_busy():
                            time.sleep(0.05)
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(0.12)  # Pausa natural para separar la reacción de la respuesta y liberar CoreAudio

        # 3. 💡 MOMENTO "¡YA SÉ LA RESPUESTA!" (DILATACIÓN DE PUPILA + SNAP DE ATENCIÓN):
        # - Los ojos se enganchan instantáneamente al usuario
        # - Pupila se dilata con entusiasmo (1.30x)
        # - Expresión alegre y pestañeo vivo
        print("💡 [Orbit Sin Motor] ¡Ya sé la respuesta! Orbit dilata pupilas y conecta con el usuario.")
        self.seguir_ojos_activo = True
        self.cara.cambiar_expresion("feliz")
        self.cara.dilatar_pupilas(1.30)
        time.sleep(0.18)
        self.cara.pestaniar()

        # 4. 🎬 ACTIVACIÓN ANTICIPADA DE VISOR EN OJOS (Deleite / QR Deleite se muestran MIENTRAS habla)
        accion = getattr(self.cerebro, "accion_pendiente", None)
        activo_visor_mientras_habla = False

        if accion == "mostrar_deleite":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "deleite.jpg")
            if not os.path.isfile(ruta_img):
                ruta_img = os.path.join(_base, "media", "deleite_fondo.jpg")
            if not os.path.isfile(ruta_img):
                ruta_img = os.path.join(_base, "media", "deleite_logo.png")
            if os.path.isfile(ruta_img):
                print("\n👁️ [Orbit Full] Visor multimedia en ojos: proyectando imagen de Deleite Automercado MIENTRAS habla...")
                self.cara.mostrar_imagen(ruta_img)
                activo_visor_mientras_habla = True
                self.cerebro.accion_pendiente = None

        elif accion == "mostrar_qr_deleite":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_qr = os.path.join(_base, "media", "qr_deleite.png")
            if not os.path.isfile(ruta_qr):
                ruta_qr = os.path.join(_base, "media", "deleite_qr.jpg")
            if not os.path.isfile(ruta_qr):
                ruta_qr = os.path.join(_base, "media", "deleite_qr.png")
            if os.path.isfile(ruta_qr):
                print("\n🎟️ [Orbit Full] Visor multimedia en ojos: proyectando código QR de descuento Deleite MIENTRAS habla...")
                self.cara.mostrar_imagen(ruta_qr)
                print("=" * 64)
                print("🎟️  CÓDIGO DE DESCUENTO DELEITE AUTOMERCADO: ORBIT5 (5% OFF)")
                print("    ¡Escanea el código QR en los ojos de Orbit o menciona 'ORBIT5' en caja!")
                print("=" * 64 + "\n")
                activo_visor_mientras_habla = True
                self.cerebro.accion_pendiente = None
                try:
                    total_qr = registrar_evento_qr(sponsor_id="deleite", qr_code="ORBIT5", robot_id="orbit_1")
                    print(f"📊 [Orbit B2B] QR Deleite registrado en BD local/cloud. Total acumulado: {total_qr} escaneos.\n")
                except Exception as _e_qr:
                    print(f"⚠️ [Orbit B2B] Error registrando métrica QR: {_e_qr}\n")

        elif accion == "mostrar_casita_blanca":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "casita_blanca.jpg")
            if not os.path.isfile(ruta_img):
                ruta_img = os.path.join(_base, "media", "casita_blanca.png")
            if os.path.isfile(ruta_img):
                print("\n👁️ [Orbit Full] Visor multimedia en ojos: proyectando foto de La Casita Blanca (Santurce, PR) MIENTRAS habla...")
                self.cara.mostrar_imagen(ruta_img)
                activo_visor_mientras_habla = True
                self.cerebro.accion_pendiente = None

        elif accion == "mostrar_qr_casita_blanca":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_qr = os.path.join(_base, "media", "qr_casita_blanca.png")
            if not os.path.isfile(ruta_qr):
                ruta_qr = os.path.join(_base, "media", "casita_blanca_qr.png")
            if os.path.isfile(ruta_qr):
                print("\n🎟️ [Orbit Full] Visor multimedia en ojos: proyectando código QR de La Casita Blanca MIENTRAS habla...")
                self.cara.mostrar_imagen(ruta_qr)
                print("=" * 64)
                print("🎟️  CÓDIGO DE DESCUENTO LA CASITA BLANCA (SANTURCE, PR): ORBIT5 (5% OFF)")
                print("    ¡Escanea el código QR en los ojos de Orbit o menciona 'ORBIT5' en caja!")
                print("=" * 64 + "\n")
                activo_visor_mientras_habla = True
                self.cerebro.accion_pendiente = None
                try:
                    total_qr = registrar_evento_qr(sponsor_id="casita_blanca", qr_code="ORBIT5", robot_id="orbit_1")
                    print(f"📊 [Orbit B2B] QR Casita Blanca registrado en BD local/cloud. Total acumulado: {total_qr} escaneos.\n")
                except Exception as _e_qr:
                    print(f"⚠️ [Orbit B2B] Error registrando métrica QR: {_e_qr}\n")

        elif accion and accion.startswith("mostrar_qr_"):
            sp_key = accion.replace("mostrar_qr_", "").strip().lower()
            cfg = CATALOGO_SPONSORS_QR.get(sp_key)
            if not cfg:
                for k in CATALOGO_SPONSORS_QR:
                    if k in sp_key or sp_key in k:
                        cfg = CATALOGO_SPONSORS_QR[k]
                        sp_key = k
                        break
            if cfg:
                _base = os.path.dirname(os.path.abspath(__file__))
                ruta_qr = os.path.join(_base, "media", cfg["file"])
                if os.path.isfile(ruta_qr):
                    print(f"\n🎟️ [Orbit Full] Visor multimedia en ojos: proyectando código QR de {cfg['label']} MIENTRAS habla...")
                    self.cara.mostrar_imagen(ruta_qr)
                    print("=" * 64)
                    print(f"🎟️  PROMO OFICIAL {cfg['label'].upper()}: {cfg['desc']} (Código {cfg['code']})")
                    print("    ¡Escanea el código QR en los ojos de Orbit!")
                    print("=" * 64 + "\n")
                    activo_visor_mientras_habla = True
                    self.cerebro.accion_pendiente = None
                    try:
                        total_qr = registrar_evento_qr(sponsor_id=sp_key, qr_code=cfg["code"], robot_id="orbit_1")
                        print(f"📊 [Orbit B2B] QR {cfg['label']} registrado en BD local/cloud. Total acumulado: {total_qr} escaneos.\n")
                    except Exception as _e_qr:
                        print(f"⚠️ [Orbit B2B] Error registrando métrica QR: {_e_qr}\n")

        # Si la acción pendiente es abrir modo aprender Kari'ña, pre-abrir Chromium en paralelo mientras habla
        if getattr(self.cerebro, "accion_pendiente", None) == "abrir_aprender_karina":
            print("🚀 [Orbit Full] Pre-abriendo interfaz Aprende con Orbit en paralelo mientras habla...")
            self._abrir_modo_aprender_karina(idioma=idioma)

        # 5. 🎙️ ORBIT COMIENZA A HABLAR SIN DEMORAS
        # (Los ojos se mantienen mostrando la imagen o siguiendo a la persona activamente mientras habla)
        print(f"🤖 Orbit: \"{respuesta}\"\n")
        if not activo_visor_mientras_habla:
            self.cara.dilatar_pupilas(1.05)
        if self.voz:
            self.voz.hablar(respuesta, idioma=idioma)
            self._esperar_voz()

        # Si el visor estuvo activo mientras hablaba, contraer ojos INMEDIATAMENTE al terminar la pregunta
        if activo_visor_mientras_habla:
            time.sleep(0.3)
            print("👁️ [Orbit Full] Pregunta completada. Ocultando visor de ojos y regresando a mirada natural...")
            self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

        # 6. 🎬 EJECUCIÓN DE ACCIONES MULTIMEDIA POSTERIORES (Visor de Ojos Kari'ña / Alma Llanera)
        else:
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            accion_post = getattr(self.cerebro, "accion_pendiente", None)
            if accion_post:
                self.cerebro.accion_pendiente = None
                self._ejecutar_accion_especial(accion_post, idioma)
        
        # Registrar interacción en historial
        historial_orbit.registrar_interaccion(
            pregunta=texto_usuario,
            respuesta=respuesta,
            reaccion="",
            latencia_ms=200,
            idioma=idioma,
            origen="voz"
        )
        
        self.tiempo_ultima_interaccion = time.time()

    def _ejecutar_accion_especial(self, accion: str, idioma: str):
        """
        Ejecuta acciones multimedia interactivas (Transición cinematográfica de ojos Kari'ña, Alma Llanera, etc.).
        """
        if not accion:
            return

        if accion == "mostrar_karina":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "karina.jpg")
            ruta_audio = os.path.join(_base, "media", "karina.mp3")

            print("\n👁️ [Orbit Full] Transición cinematográfica de ojos: agrandando visor multimedia...")
            self.cara.mostrar_imagen(ruta_img)
            time.sleep(0.4)

            if os.path.isfile(ruta_audio):
                print("🎶 [Orbit Full] Reproduciendo danza y canto sagrado Mare-Mare de los Kari'ña 🇻🇪...")
                cmd_audio = ["afplay", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", ruta_audio]
                try:
                    proc_audio = subprocess.Popen(cmd_audio, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    proc_audio.wait()
                except Exception as e:
                    print(f"⚠️ Error al reproducir audio: {e}")
            else:
                time.sleep(10.0)

            time.sleep(0.6)
            print("👁️ [Orbit Full] Finalizando visor. Contrayendo ojos y regresando a modo mirada...")
            self.cara.ocultar_imagen()
            time.sleep(0.7)
            self.cara.pestaniar()

            # Pregunta de cierre obligatoria al terminar la música y ocultar el visor
            pregunta_cierre = (
                "Would you like to know more about the Kari'ña or about Venezuela?"
                if idioma == "en" else
                "¿Quieres saber algo más sobre los Kari'ña o sobre Venezuela?"
            )
            print(f"🤖 Orbit: \"{pregunta_cierre}\"\n")
            if self.voz:
                self.voz.hablar(pregunta_cierre)
                self._esperar_voz()

        elif accion == "abrir_aprender_karina":
            self._abrir_modo_aprender_karina(idioma=idioma)
            self._esperar_comando_cerrar_karina(idioma=idioma)
            return

        elif accion == "mostrar_deleite":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "deleite.jpg")
            if not os.path.isfile(ruta_img):
                ruta_img = os.path.join(_base, "media", "deleite_fondo.jpg")
            if not os.path.isfile(ruta_img):
                ruta_img = os.path.join(_base, "media", "deleite_logo.png")
            if os.path.isfile(ruta_img):
                print("\n👁️ [Orbit Full] Visor multimedia: mostrando imagen de Deleite Automercado en los ojos...")
                self.cara.mostrar_imagen(ruta_img)
                time.sleep(3.8)
                print("👁️ [Orbit Full] Finalizando visor. Contrayendo ojos y regresando a modo mirada...")
                self.cara.ocultar_imagen()
                time.sleep(0.5)
                self.cara.pestaniar()

        elif accion == "mostrar_qr_deleite":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_qr = os.path.join(_base, "media", "qr_deleite.png")
            if not os.path.isfile(ruta_qr):
                ruta_qr = os.path.join(_base, "media", "deleite_qr.jpg")
            if not os.path.isfile(ruta_qr):
                ruta_qr = os.path.join(_base, "media", "deleite_qr.png")
            if os.path.isfile(ruta_qr):
                print("\n🎟️ [Orbit Full] Visor multimedia: proyectando código QR de descuento Deleite en ojos...")
                self.cara.mostrar_imagen(ruta_qr)
                print("=" * 64)
                print("🎟️  CÓDIGO DE DESCUENTO DELEITE AUTOMERCADO: ORBIT5 (5% OFF)")
                print("    ¡Escanea el código QR en los ojos de Orbit o menciona 'ORBIT5' en caja!")
                print("=" * 64 + "\n")
                try:
                    total_qr = registrar_evento_qr(sponsor_id="deleite", qr_code="ORBIT5", robot_id="orbit_1")
                    print(f"📊 [Orbit B2B] QR Deleite registrado en BD local/cloud. Total acumulado: {total_qr} escaneos.\n")
                except Exception as _e_qr:
                    print(f"⚠️ [Orbit B2B] Error registrando métrica QR: {_e_qr}\n")
                time.sleep(2.0)
                print("👁️ [Orbit Full] Ocultando visor QR. Contrayendo ojos a modo normal...")
                self.cara.ocultar_imagen()
                time.sleep(0.4)
                self.cara.pestaniar()

        elif accion == "mostrar_casita_blanca":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "casita_blanca.jpg")
            if not os.path.isfile(ruta_img):
                ruta_img = os.path.join(_base, "media", "casita_blanca.png")
            if os.path.isfile(ruta_img):
                print("\n👁️ [Orbit Full] Visor multimedia: mostrando foto de La Casita Blanca en los ojos...")
                self.cara.mostrar_imagen(ruta_img)
                time.sleep(3.5)
                print("👁️ [Orbit Full] Finalizando visor. Contrayendo ojos y regresando a modo mirada...")
                self.cara.ocultar_imagen()
                time.sleep(0.4)
                self.cara.pestaniar()

        elif accion == "mostrar_qr_casita_blanca":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_qr = os.path.join(_base, "media", "qr_casita_blanca.png")
            if not os.path.isfile(ruta_qr):
                ruta_qr = os.path.join(_base, "media", "casita_blanca_qr.png")
            if os.path.isfile(ruta_qr):
                print("\n🎟️ [Orbit Full] Visor multimedia: proyectando código QR de La Casita Blanca en ojos...")
                self.cara.mostrar_imagen(ruta_qr)
                print("=" * 64)
                print("🎟️  CÓDIGO DE DESCUENTO LA CASITA BLANCA (SANTURCE, PR): ORBIT5 (5% OFF)")
                print("    ¡Escanea el código QR en los ojos de Orbit o menciona 'ORBIT5' en caja!")
                print("=" * 64 + "\n")
                try:
                    total_qr = registrar_evento_qr(sponsor_id="casita_blanca", qr_code="ORBIT5", robot_id="orbit_1")
                    print(f"📊 [Orbit B2B] QR Casita Blanca registrado en BD local/cloud. Total acumulado: {total_qr} escaneos.\n")
                except Exception as _e_qr:
                    print(f"⚠️ [Orbit B2B] Error registrando métrica QR: {_e_qr}\n")

        elif accion and accion.startswith("mostrar_qr_"):
            sp_key = accion.replace("mostrar_qr_", "").strip().lower()
            cfg = CATALOGO_SPONSORS_QR.get(sp_key)
            if not cfg:
                for k in CATALOGO_SPONSORS_QR:
                    if k in sp_key or sp_key in k:
                        cfg = CATALOGO_SPONSORS_QR[k]
                        sp_key = k
                        break
            if cfg:
                _base = os.path.dirname(os.path.abspath(__file__))
                ruta_qr = os.path.join(_base, "media", cfg["file"])
                if os.path.isfile(ruta_qr):
                    print(f"\n🎟️ [Orbit Full] Visor multimedia en ojos: proyectando código QR de {cfg['label']} MIENTRAS habla...")
                    self.cara.mostrar_imagen(ruta_qr)
                    print("=" * 64)
                    print(f"🎟️  PROMO OFICIAL {cfg['label'].upper()}: {cfg['desc']} (Código {cfg['code']})")
                    print("    ¡Escanea el código QR en los ojos de Orbit!")
                    print("=" * 64 + "\n")
                    activo_visor_mientras_habla = True
                    self.cerebro.accion_pendiente = None
                    try:
                        total_qr = registrar_evento_qr(sponsor_id=sp_key, qr_code=cfg["code"], robot_id="orbit_1")
                        print(f"📊 [Orbit B2B] QR {cfg['label']} registrado en BD local/cloud. Total acumulado: {total_qr} escaneos.\n")
                    except Exception as _e_qr:
                        print(f"⚠️ [Orbit B2B] Error registrando métrica QR: {_e_qr}\n")
                time.sleep(2.0)
                print("👁️ [Orbit Full] Ocultando visor QR. Contrayendo ojos a modo normal...")
                self.cara.ocultar_imagen()
                time.sleep(0.4)
                self.cara.pestaniar()

        elif accion == "mostrar_lecheria":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "lecheria.jpg")
            if os.path.isfile(ruta_img):
                print("\n🏖️ [Orbit Full] Visor multimedia: mostrando foto del Morro de Lechería en los ojos...")
                self.cara.mostrar_imagen(ruta_img)
                time.sleep(3.5)
                print("👁️ [Orbit Full] Finalizando visor. Contrayendo ojos y regresando a modo mirada...")
                self.cara.ocultar_imagen()
                time.sleep(0.4)
                self.cara.pestaniar()

        elif accion == "mostrar_san_juan":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "san_juan.jpg")
            if os.path.isfile(ruta_img):
                print("\n🏰 [Orbit Full] Visor multimedia: mostrando foto del Viejo San Juan y El Morro en los ojos...")
                self.cara.mostrar_imagen(ruta_img)
                time.sleep(3.5)
                print("👁️ [Orbit Full] Finalizando visor. Contrayendo ojos y regresando a modo mirada...")
                self.cara.ocultar_imagen()
                time.sleep(0.4)
                self.cara.pestaniar()

        elif accion == "mostrar_convention_center":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "convention_center.jpg")
            if os.path.isfile(ruta_img):
                print("\n🏛️ [Orbit Full] Visor multimedia: mostrando Centro de Convenciones de Puerto Rico en los ojos...")
                self.cara.mostrar_imagen(ruta_img)
                time.sleep(3.5)
                print("👁️ [Orbit Full] Finalizando visor. Contrayendo ojos y regresando a modo mirada...")
                self.cara.ocultar_imagen()
                time.sleep(0.4)
                self.cara.pestaniar()

        elif accion == "mostrar_wro":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_img = os.path.join(_base, "media", "wro.jpg")
            if os.path.isfile(ruta_img):
                print("\n🤖 [Orbit Full] Visor multimedia: mostrando imagen oficial de la WRO en los ojos...")
                self.cara.mostrar_imagen(ruta_img)
                time.sleep(3.5)
                print("👁️ [Orbit Full] Finalizando visor. Contrayendo ojos y regresando a modo mirada...")
                self.cara.ocultar_imagen()
                time.sleep(0.4)
                self.cara.pestaniar()

        elif accion == "reproducir_alma":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_alma = os.path.join(_base, "media", "alma.mp3")
            ruta_lir = os.path.join(_base, "media", "almalir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de Alma Llanera (almalir.png) en el visor...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_alma):
                print("\n🎶 [Orbit Full] Reproduciendo Alma Llanera (clip 28s) 🇻🇪...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd_alma = ["afplay", "-t", "28", ruta_alma] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_alma]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_alma = (
                "Long live the joropo and long live Venezuela! Did you enjoy Alma Llanera? What else would you like to explore today?"
                if idioma == "en" else
                "¡Qué viva el joropo y qué viva Venezuela! ¿Te gustó Alma Llanera? ¿Qué más te gustaría saber de Venezuela o Puerto Rico?"
            )
            print(f"🤖 Orbit: \"{post_alma}\"\n")
            if self.voz:
                self.voz.hablar(post_alma)
                self._esperar_voz()

        elif accion == "reproducir_viejo_san_juan":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_audio = os.path.join(_base, "media", "en_mi_viejo_san_juan.mp3")
            ruta_lir = os.path.join(_base, "media", "viejosanjuanlir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de En mi Viejo San Juan (viejosanjuanlir.png)...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_audio):
                print("\n🎶 [Orbit Full] Reproduciendo En mi Viejo San Juan (clip 28s) 🇵🇷...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd = ["afplay", "-t", "28", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_audio]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_sj = (
                "What an emotional masterpiece! En mi Viejo San Juan is truly the heartfelt soul of Puerto Rico. What else would you like to explore?"
                if idioma == "en" else
                "¡Qué joya tan emocionante! 'En mi Viejo San Juan' es el verdadero himno del corazón boricua. ¿Qué más te gustaría descubrir?"
            )
            print(f"🤖 Orbit: \"{post_sj}\"\n")
            if self.voz:
                self.voz.hablar(post_sj)
                self._esperar_voz()

        elif accion == "reproducir_caballo_viejo":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_audio = os.path.join(_base, "media", "caballo_viejo.mp3")
            ruta_lir = os.path.join(_base, "media", "caballoviejolir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de Caballo Viejo (caballoviejolir.png)...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_audio):
                print("\n🎶 [Orbit Full] Reproduciendo Caballo Viejo de Simón Díaz (clip 28s) 🇻🇪...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd = ["afplay", "-t", "28", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_audio]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_cv = (
                "That was Caballo Viejo by the great Simón Díaz! Did you feel the magic of the Venezuelan Llanos?"
                if idioma == "en" else
                "¡Ese fue Caballo Viejo del gran tío Simón Díaz! ¿Sentiste la magia y el sentimiento de los Llanos venezolanos?"
            )
            print(f"🤖 Orbit: \"{post_cv}\"\n")
            if self.voz:
                self.voz.hablar(post_cv)
                self._esperar_voz()

        elif accion == "reproducir_verde_luz":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_audio = os.path.join(_base, "media", "verde_luz.mp3")
            ruta_lir = os.path.join(_base, "media", "verdeluzlir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de Verde Luz (verdeluzlir.png)...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_audio):
                print("\n🎶 [Orbit Full] Reproduciendo Verde Luz de Antonio Cabán Vale (clip 28s) 🇵🇷...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd = ["afplay", "-t", "28", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_audio]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_vl = (
                "Verde Luz touches the deepest roots of Puerto Rico! Would you like to know more about Puerto Rican culture?"
                if idioma == "en" else
                "¡Verde Luz llega directo al corazón de Puerto Rico! ¿Te gustaría conocer más sobre las bellezas y la música de la isla?"
            )
            print(f"🤖 Orbit: \"{post_vl}\"\n")
            if self.voz:
                self.voz.hablar(post_vl)
                self._esperar_voz()

        elif accion == "reproducir_venezuela":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_audio = os.path.join(_base, "media", "venezuela.mp3")
            ruta_lir = os.path.join(_base, "media", "venezuelalir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de Venezuela (venezuelalir.png)...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_audio):
                print("\n🎶 [Orbit Full] Reproduciendo 'Venezuela' de Herrero y Armenteros (clip 28s) 🇻🇪...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd = ["afplay", "-t", "28", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_audio]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_vz = (
                "What an inspiring masterpiece! 'Venezuela' is truly the heartfelt soul of the nation. What else would you like to explore?"
                if idioma == "en" else
                "¡Qué tema tan conmovedor! 'Venezuela' es una de las canciones patrióticas más hermosas del mundo. ¿De qué otro tema te gustaría hablar hoy?"
            )
            print(f"🤖 Orbit: \"{post_vz}\"\n")
            if self.voz:
                self.voz.hablar(post_vz)
                self._esperar_voz()

        elif accion == "reproducir_rawayana":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_audio = os.path.join(_base, "media", "rawayana.mp3")
            ruta_lir = os.path.join(_base, "media", "rawayanalir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de High - Rawayana (rawayanalir.png)...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_audio):
                print("\n🎶 [Orbit Full] Reproduciendo 'High' de Rawayana ft. Apache (clip 28s) 🇻🇪...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd = ["afplay", "-t", "28", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_audio]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_rw = (
                "That was High by Rawayana featuring Apache! Pure tropical Venezuelan reggae groove. Did you like the rhythm?"
                if idioma == "en" else
                "¡Esa fue 'High' de Rawayana con Apache! Puro sabor y buena vibra caribeña venezolana. ¿Te gustó el ritmo?"
            )
            print(f"🤖 Orbit: \"{post_rw}\"\n")
            if self.voz:
                self.voz.hablar(post_rw)
                self._esperar_voz()

        elif accion == "reproducir_pr_pop":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_audio = os.path.join(_base, "media", "pr_pop.mp3")
            ruta_lir = os.path.join(_base, "media", "prpoplir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de Tití Me Preguntó (prpoplir.png)...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_audio):
                print("\n🎶 [Orbit Full] Reproduciendo 'Tití Me Preguntó' de Bad Bunny (clip 28s) 🇵🇷...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd = ["afplay", "-t", "28", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_audio]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_pop = (
                "That was Tití Me Preguntó by Bad Bunny, the global superstar representing Puerto Rico's modern pop culture! What else would you like to hear?"
                if idioma == "en" else
                "¡Ese fue 'Tití Me Preguntó' de Bad Bunny, el fenómeno mundial que representa la cultura pop moderna de Puerto Rico! ¿Qué otra canción te gustaría escuchar?"
            )
            print(f"🤖 Orbit: \"{post_pop}\"\n")
            if self.voz:
                self.voz.hablar(post_pop)
                self._esperar_voz()

        elif accion == "reproducir_preciosa":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_audio = os.path.join(_base, "media", "preciosa.mp3")
            ruta_lir = os.path.join(_base, "media", "preciosalir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de Preciosa (preciosalir.png)...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_audio):
                print("\n🎶 [Orbit Full] Reproduciendo 'Preciosa' de Rafael Hernández / Marc Anthony (clip 28s) 🇵🇷...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd = ["afplay", "-t", "28", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_audio]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_prec = (
                "What an emotional tribute! 'Preciosa' is the deepest anthem of Puerto Rican pride and identity. What else would you like to discover?"
                if idioma == "en" else
                "¡Qué homenaje tan emocionante! 'Preciosa' de Rafael Hernández es el mayor himno de devoción y amor a Puerto Rico. ¿Qué más te gustaría saber?"
            )
            print(f"🤖 Orbit: \"{post_prec}\"\n")
            if self.voz:
                self.voz.hablar(post_prec)
                self._esperar_voz()

        elif accion == "reproducir_world":
            _base = os.path.dirname(os.path.abspath(__file__))
            ruta_audio = os.path.join(_base, "media", "world.mp3")
            ruta_lir = os.path.join(_base, "media", "worldlir.png")
            if os.path.isfile(ruta_lir):
                print("📜 [Orbit Full] Proyectando letra de We Will Rock You (worldlir.png)...")
                self.cara.mostrar_imagen(ruta_lir)
            if os.path.isfile(ruta_audio):
                print("\n🎶 [Orbit Full] Reproduciendo 'We Will Rock You' de Queen (clip 28s) 🌍...")
                self.cara.cambiar_expresion("feliz")
                self.cara.dilatar_pupilas(1.15)
                cmd = ["afplay", "-t", "28", ruta_audio] if sys.platform == "darwin" else ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-t", "28", ruta_audio]
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
            if os.path.isfile(ruta_lir):
                self.cara.ocultar_imagen()
            time.sleep(0.4)
            self.cara.cambiar_expresion("normal")
            self.cara.dilatar_pupilas(1.0)
            self.cara.pestaniar()

            post_wld = (
                "That was We Will Rock You by Queen! An iconic world anthem known in every corner of the Earth. What else would you like to explore?"
                if idioma == "en" else
                "¡Ese fue 'We Will Rock You' de Queen, un clásico del mundo que hace vibrar a personas de todos los países! ¿Te gustaría seguir explorando?"
            )
            print(f"🤖 Orbit: \"{post_wld}\"\n")
            if self.voz:
                self.voz.hablar(post_wld)
                self._esperar_voz()

    # ── CENTRO DE COMANDO & DASHBOARD WEB LOCAL ──────────────────────────────
    def _abrir_centro_comando(self):
        """Abre la interfaz web local del Centro de Comando / Dashboard en Chromium."""
        url = f"http://localhost:{self.puerto_dashboard}?t={int(time.time())}"
        print(f"\n🚀 [Centro de Comando] Desplegando dashboard local en: {url}")
        
        self.movimiento.detener()

        # Asegurar servidor web activo en segundo plano
        try:
            import web_historial
            web_historial.iniciar_servidor_segundo_plano(puerto=self.puerto_dashboard)
        except Exception:
            pass

        # Flags optimizados para Raspberry Pi y pantalla de Orbit
        flags = [
            f"--app={url}",
            "--start-maximized",
            "--force-device-scale-factor=1.20",  # Escala la interfaz para mayor legibilidad
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--disable-features=Translate",
            "--password-store=basic",         # Bypass clave / GNOME Keyring
            "--use-mock-keychain",            # Evita popups de contraseñas
            "--disable-save-password-bubble"
        ]

        comandos = [
            ["chromium-browser"] + flags,
            ["chromium"] + flags,
            ["google-chrome"] + flags,
            ["chromium-browser", url],
            ["chromium", url],
            ["google-chrome", url],
            ["xdg-open", url]
        ]

        if sys.platform == "darwin":
            comandos.insert(0, ["open", "-a", "Google Chrome", "--args"] + flags)
            comandos.insert(1, ["open", url])

        for cmd in comandos:
            try:
                self.proceso_dashboard = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                print(f"🖥️ [Centro de Comando] Navegador iniciado ({cmd[0]}).")
                return
            except (FileNotFoundError, PermissionError):
                continue
            except Exception:
                pass

        try:
            import webbrowser
            webbrowser.open(url)
            print(f"🖥️ [Centro de Comando] Abierto con navegador estándar del sistema.")
        except Exception as e:
            print(f"⚠️ [Centro de Comando] Error abriendo navegador: {e}")

    def _esperar_comando_cerrar(self, idioma="es"):
        """
        Mantiene en pantalla el Centro de Comando y escucha atentamente hasta
        que el usuario pronuncie 'cerrar' / 'close' (o 'cierra', 'volver a los ojos', etc.).
        """
        prompt_info = "👂 Orbit is listening. Say 'close' to return to eyes." if idioma == "en" else "👂 Orbit está auditivamente esperando. Di 'cerrar' para volver a los ojos."
        print("=" * 68)
        print("🖥️ [CENTRO DE COMANDO ORBIT ACTIVO]")
        print(prompt_info)
        print("=" * 68)

        self.cara.cambiar_expresion("escuchando")
        
        while self.ejecutando:
            # 1. Si el usuario cerró la ventana manualmente con el mouse o atajo
            if self.proceso_dashboard and self.proceso_dashboard.poll() is not None:
                print("ℹ️ [Centro de Comando] Ventana cerrada por el usuario.")
                break

            # 2. Escucha activa de voz con pausa corta optimizada para comando
            texto_voz = ""
            try:
                if self.oido and getattr(self.oido, "disponible", True):
                    if hasattr(self.oido, "escuchar_dual") and callable(self.oido.escuchar_dual):
                        res = self.oido.escuchar_dual(timeout=4.5, pausa_silencio=0.70, forzar_offline=self.modo_offline, lang=idioma)
                    elif hasattr(self.oido, "escuchar") and callable(self.oido.escuchar):
                        res = self.oido.escuchar(timeout=4.5, pausa_silencio=0.70, forzar_offline=self.modo_offline, lang=idioma)
                    else:
                        res = ("", idioma)

                    if isinstance(res, (tuple, list)):
                        texto_voz = (res[0] or "").strip()
                    elif isinstance(res, str):
                        texto_voz = (res or "").strip()
                else:
                    # Modo entrada por consola si no hay micrófono
                    try:
                        prompt_cerrar = "⌨️ Say 'close' (or type 'close' in console): " if idioma == "en" else "⌨️ Di 'cerrar' (o escribe 'cerrar' en consola): "
                        print(prompt_cerrar)
                        texto_voz = input("👤 Tú: ").strip()
                    except EOFError:
                        texto_voz = "close" if idioma == "en" else "cerrar"
                    except KeyboardInterrupt:
                        print("\n🛑 [Centro de Comando] Ctrl+C recibido. Cerrando silenciosamente...")
                        self.ejecutando = False
                        self._cerrar_centro_comando(idioma=idioma, decir_despedida=False)
                        return
            except (KeyboardInterrupt, SystemExit):
                print("\n🛑 [Centro de Comando] Ctrl+C recibido. Cerrando silenciosamente...")
                self.ejecutando = False
                self._cerrar_centro_comando(idioma=idioma, decir_despedida=False)
                return
            except Exception as e:
                time.sleep(0.3)
                continue

            texto_voz = (texto_voz or "").lower().strip()
            if not texto_voz or texto_voz == "__TIMEOUT__":
                continue

            print(f"🗣️ [Orbit escuchó]: \"{texto_voz}\"")

            # Detectar comando de cierre seguro sin falsos positivos en comentarios largos
            tokens_cerrar = texto_voz.split()
            es_frase_larga = len(tokens_cerrar) > 5 or len(texto_voz) > 30

            patrones_comando_cierre = [
                r'\b(cerrar|cierra|ci[eé]rral[oa]|cerrando|cerrado)\b',
                r'\b(volver|regresar)\s*(a\s+los\s+ojos|a\s+la\s+pantalla|a\s+la\s+cara)?\b',
                r'\b(salir|exit|close|quit)\b',
                r'^(listo|ok\s+listo)$'
            ]
            
            # Aliases fonéticos de 'cerrar' aislados (ej. "sara", "gerald", "cera", "sea") SOLO si la frase es corta (<= 3 palabras)
            patrones_foneticos_cortos = [
                r'^(sara|sarah|gerald|cheryl|cherar|cera|serra|sea)$',
                r'^(cerrar|cierra|close|volver)\s+(sara|sarah|pantalla|ojos)?$'
            ]

            comando_confirmado = False
            if es_frase_larga:
                # Si el usuario está conversando o comentando datos del dashboard en voz alta,
                # solo cerrar si da una orden explícita dirigida al comando o al dashboard
                if re.search(r'\b(cerrar|cierra|close|exit|salir)\s+(el\s+)?(centro\s+de\s+comando|dashboard|navegador|pantalla|ventana)\b', texto_voz):
                    comando_confirmado = True
                elif texto_voz.startswith(("cerrar", "cierra", "close", "salir")):
                    comando_confirmado = True
            else:
                if any(re.search(pat, texto_voz) for pat in patrones_comando_cierre):
                    comando_confirmado = True
                elif any(re.search(pat, texto_voz) for pat in patrones_foneticos_cortos):
                    comando_confirmado = True

            if comando_confirmado:
                print("🎯 [Centro de Comando] ¡Comando 'cerrar' confirmado!")
                break

        if not self.ejecutando:
            self._cerrar_centro_comando(idioma=idioma, decir_despedida=False)
            return

        # Cerrar el navegador y regresar a los ojos
        self._cerrar_centro_comando(idioma=idioma, decir_despedida=True)

    def _cerrar_centro_comando(self, idioma="es", decir_despedida=True):
        """Cierra el proceso del navegador y devuelve el foco a los ojos de Orbit."""
        print("🔒 [Centro de Comando] Cerrando navegador y retornando a la cara de Orbit...")
        if self.proceso_dashboard:
            try:
                self.proceso_dashboard.terminate()
                self.proceso_dashboard.wait(timeout=1.2)
            except Exception:
                try:
                    self.proceso_dashboard.kill()
                except Exception:
                    pass
            self.proceso_dashboard = None

        # Asegurar cierre de pestañas en Linux/Raspberry Pi
        if sys.platform.startswith("linux"):
            try:
                subprocess.run(["pkill", "-f", "chromium.*8080"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                subprocess.run(["pkill", "-f", "chromium-browser.*8080"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                # Si wmctrl está disponible en X11, traer ventana de cara al frente
                subprocess.run(["wmctrl", "-a", "Orbit Face"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        elif sys.platform == "darwin":
            try:
                script = 'tell application "Google Chrome" to close (every window whose title contains "ORBIT" or title contains "Fleet" or title contains "localhost:8080")'
                subprocess.run(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        # Respuesta amable solo si NO es apagado forzado por Ctrl+C
        if decir_despedida and self.ejecutando:
            mensaje_cierre = "Command center closed. Ready to explore!" if (self.modo_offline or idioma == "en") else "Centro de comando cerrado. ¡Listo para seguir explorando!"
            print(f"🤖 Orbit: \"{mensaje_cierre}\"")
            self.cara.cambiar_expresion("feliz")
            self.cara.pestaniar()
            if self.voz:
                self.voz.hablar(mensaje_cierre, idioma=idioma)
                self._esperar_voz()
                time.sleep(0.3)

            self.cara.cambiar_expresion("normal")
            self.cara.mirar_a(0.0, 0.0)
            self.seguir_ojos_activo = True
            self.tiempo_ultima_interaccion = time.time()

    # ── MODO APRENDE CON ORBIT (KARI'ÑA / DUOLINGO) ──────────────────────────
    def _obtener_ruta_aprende_con_orbit(self):
        """Busca el archivo aprende-con-orbit.html en las rutas estándar del proyecto."""
        _base_actual = os.path.dirname(os.path.abspath(__file__))
        candidatos = [
            os.path.normpath(os.path.join(os.path.dirname(_base_actual), "ORBIT_International", "Interfaz De Orbit", "aprender", "aprende-con-orbit.html")),
            os.path.normpath(os.path.join(_base_actual, "..", "ORBIT_International", "Interfaz De Orbit", "aprender", "aprende-con-orbit.html")),
            "/home/nala/Documents/WRO-2026/ORBIT_International/Interfaz De Orbit/aprender/aprende-con-orbit.html",
            "/home/nala/Desktop/WRO-2026/ORBIT_International/Interfaz De Orbit/aprender/aprende-con-orbit.html",
            os.path.expanduser("~/Documents/WRO-2026/ORBIT_International/Interfaz De Orbit/aprender/aprende-con-orbit.html"),
            os.path.expanduser("~/Desktop/WRO-2026/ORBIT_International/Interfaz De Orbit/aprender/aprende-con-orbit.html"),
        ]
        for c in candidatos:
            if os.path.isfile(c):
                return c
        return None

    def _abrir_modo_aprender_karina(self, idioma="es"):
        """Abre la interfaz interactiva de aprendizaje Kari'ña (Duolingorbit) en Chromium."""
        if getattr(self, "proceso_aprender", None) and self.proceso_aprender.poll() is None:
            print("🖥️ [Aprende con Orbit] El navegador ya está en ejecución en pantalla.")
            return

        try:
            import web_historial
            web_historial.iniciar_servidor_segundo_plano(puerto=self.puerto_dashboard)
        except Exception:
            pass

        ruta_html = self._obtener_ruta_aprende_con_orbit()
        
        # Preferir URL local HTTP para cero restricciones de audio y sesión
        url = f"http://localhost:{self.puerto_dashboard}/aprender/aprende-con-orbit.html?lang=karina&t={int(time.time())}"
        print(f"\n🚀 [Aprende con Orbit] Desplegando interfaz de Kari'ña en: {url}")
        self.movimiento.detener()

        flags = [
            "--kiosk",
            "--start-fullscreen",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--disable-features=Translate",
            "--password-store=basic",
            "--use-mock-keychain",
            "--disable-save-password-bubble",
            "--autoplay-policy=no-user-gesture-required",
            "--allow-file-access-from-files",
            "--noerrdialogs",
            "--disable-pinch",
            "--overscroll-history-navigation=0",
            "--window-position=0,0",
            "--window-size=1024,600",
            "--user-data-dir=/tmp/orbit_chromium_kiosk",
            "--check-for-update-interval=31536000",
            "--hide-scrollbars"
        ]

        env = os.environ.copy()
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"

        comandos = [
            ["chromium-browser"] + flags + ["--app=" + url],
            ["chromium"] + flags + ["--app=" + url],
            ["chromium-browser"] + flags + [url],
            ["chromium"] + flags + [url],
            ["google-chrome"] + flags + ["--app=" + url],
            ["chromium-browser", "--kiosk", "--window-size=1024,600", "--window-position=0,0", "--user-data-dir=/tmp/orbit_chromium_kiosk", url],
            ["chromium", "--kiosk", "--window-size=1024,600", "--window-position=0,0", "--user-data-dir=/tmp/orbit_chromium_kiosk", url],
            ["xdg-open", url]
        ]

        if sys.platform == "darwin":
            comandos.insert(0, ["open", "-a", "Google Chrome", "--args", "--kiosk", url])
            comandos.insert(1, ["open", url])
            if ruta_html:
                comandos.append(["open", f"file://{ruta_html}?lang=karina"])

        for cmd in comandos:
            try:
                self.proceso_aprender = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    start_new_session=True
                )
                print(f"🖥️ [Aprende con Orbit] Navegador iniciado ({cmd[0]}).")
                return
            except (FileNotFoundError, PermissionError):
                continue
            except Exception:
                pass

        try:
            import webbrowser
            webbrowser.open(url)
            print(f"🖥️ [Aprende con Orbit] Abierto con navegador estándar del sistema.")
        except Exception as e:
            print(f"⚠️ [Aprende con Orbit] Error abriendo navegador: {e}")

    def _esperar_comando_cerrar_karina(self, idioma="es"):
        """
        Mantiene en pantalla la interfaz de aprendizaje y escucha atentamente hasta
        que el usuario pronuncie 'muchas gracias por enseñarme' o 'cerrar modo karina'.
        """
        prompt_info = (
            "👂 Orbit is listening. Say 'thank you for teaching me' or 'close karina' to return to eyes."
            if idioma == "en" else
            "👂 Orbit está auditivamente esperando. Di 'muchas gracias por enseñarme' o 'cerrar modo karina' para volver a los ojos."
        )
        print("=" * 68)
        print("📚 [MODO APRENDER KARI'ÑA ACTIVO]")
        print(prompt_info)
        print("=" * 68)

        self.cara.cambiar_expresion("escuchando")
        
        while self.ejecutando:
            # 1. Si el usuario cerró la ventana manualmente con el mouse o atajo
            if self.proceso_aprender and self.proceso_aprender.poll() is not None:
                print("ℹ️ [Aprende con Orbit] Ventana cerrada por el usuario.")
                break

            # 2. Escucha activa de voz con pausa corta optimizada para comando
            texto_voz = ""
            try:
                if self.oido and getattr(self.oido, "disponible", True):
                    if hasattr(self.oido, "escuchar_dual") and callable(self.oido.escuchar_dual):
                        res = self.oido.escuchar_dual(timeout=4.5, pausa_silencio=0.70, forzar_offline=self.modo_offline, lang=idioma)
                    elif hasattr(self.oido, "escuchar") and callable(self.oido.escuchar):
                        res = self.oido.escuchar(timeout=4.5, pausa_silencio=0.70, forzar_offline=self.modo_offline, lang=idioma)
                    else:
                        res = ("", idioma)

                    if isinstance(res, (tuple, list)):
                        texto_voz = (res[0] or "").strip()
                    elif isinstance(res, str):
                        texto_voz = (res or "").strip()
                else:
                    try:
                        prompt_cerrar = (
                            "⌨️ Say 'thank you for teaching me' or 'close' (or type in console): "
                            if idioma == "en" else
                            "⌨️ Di 'muchas gracias por enseñarme' o 'cerrar modo karina' (o escribe en consola): "
                        )
                        print(prompt_cerrar)
                        texto_voz = input("👤 Tú: ").strip()
                    except EOFError:
                        texto_voz = "close" if idioma == "en" else "cerrar"
                    except KeyboardInterrupt:
                        print("\n🛑 [Aprende con Orbit] Ctrl+C recibido. Apagando silenciosamente...")
                        self.ejecutando = False
                        self._cerrar_modo_aprender_karina(idioma=idioma, decir_despedida=False)
                        return
            except (KeyboardInterrupt, SystemExit):
                print("\n🛑 [Aprende con Orbit] Ctrl+C recibido. Apagando silenciosamente...")
                self.ejecutando = False
                self._cerrar_modo_aprender_karina(idioma=idioma, decir_despedida=False)
                return
            except Exception as e:
                time.sleep(0.3)
                continue

            texto_voz = (texto_voz or "").lower().strip()
            if not texto_voz or texto_voz == "__TIMEOUT__":
                continue

            print(f"🗣️ [Orbit escuchó]: \"{texto_voz}\"")
            texto_norm = "".join(c for c in unicodedata.normalize("NFD", texto_voz) if unicodedata.category(c) != "Mn")

            patrones_cierre_karina = [
                r'\b(muchas\s+)?gracias\s+(por\s+)?(ensenarme|la\s+clase|las\s+clases|la\s+leccion)\b',
                r'\b(cerrar|cierra|cierral[oa]|terminar|finalizar|salir)\s*(el\s+)?(modo\s+)?(karina|carina|carino|duolingo|duolingorbit|aprender|aprendizaje|leccion)?\b',
                r'\b(cerrar|cierra|cierral[oa]|cerrando|cerrado)\b',
                r'\b(volver|regresar)\s*(a\s+los\s+ojos|a\s+la\s+cara|a\s+la\s+pantalla)?\b',
                r'\b(ya\s+)?(termine|listo|ok\s+listo)\b',
                r'\b(thank\s+you|thanks)\s+(for\s+teaching(\s+me)?|for\s+the\s+lesson)\b',
                r'\b(close|exit|quit)\s*(the\s+)?(karina|learning|duolingo)?\b'
            ]

            comando_confirmado = any(re.search(pat, texto_norm) for pat in patrones_cierre_karina)

            if comando_confirmado:
                print("🎯 [Aprende con Orbit] ¡Comando de cierre confirmado!")
                break

        if not self.ejecutando:
            self._cerrar_modo_aprender_karina(idioma=idioma, decir_despedida=False)
            return

        # Cerrar el navegador y regresar a los ojos
        self._cerrar_modo_aprender_karina(idioma=idioma, decir_despedida=True)

    def _cerrar_modo_aprender_karina(self, idioma="es", decir_despedida=True):
        """Cierra el proceso del navegador y devuelve el foco a los ojos de Orbit."""
        print("🔒 [Aprende con Orbit] Cerrando aplicación de aprendizaje y retornando a la cara de Orbit...")
        if self.proceso_aprender:
            try:
                self.proceso_aprender.terminate()
                self.proceso_aprender.wait(timeout=1.2)
            except Exception:
                try:
                    self.proceso_aprender.kill()
                except Exception:
                    pass
            self.proceso_aprender = None

        # Asegurar cierre de pestañas en Linux/Raspberry Pi
        if sys.platform.startswith("linux"):
            try:
                subprocess.run(["pkill", "-f", "chromium.*aprende-con-orbit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                subprocess.run(["pkill", "-f", "chromium-browser.*aprende-con-orbit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                subprocess.run(["pkill", "-f", "chromium.*kiosk.*aprender"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                subprocess.run(["wmctrl", "-a", "Orbit Face"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        elif sys.platform == "darwin":
            try:
                script = 'tell application "Google Chrome" to close (every window whose title contains "Learn with ORBIT" or title contains "aprende-con-orbit")'
                subprocess.run(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        # Respuesta amable solo si NO es un apagado forzado por Ctrl+C
        if decir_despedida and self.ejecutando:
            mensaje_cierre = (
                "It was an absolute pleasure teaching you the Kari'ña language! You did a fantastic job. What else would you like to explore?"
                if (self.modo_offline or idioma == "en") else
                "¡Ha sido todo un placer enseñarte la lengua Kari'ña! Practicaste excelente. Recuerda que siempre podemos seguir aprendiendo cuando quieras."
            )
            print(f"🤖 Orbit: \"{mensaje_cierre}\"")
            self.cara.cambiar_expresion("feliz")
            self.cara.pestaniar()
            if self.voz:
                self.voz.hablar(mensaje_cierre, idioma=idioma)
                self._esperar_voz()
                time.sleep(0.3)

            self.cara.cambiar_expresion("normal")
            self.cara.mirar_a(0.0, 0.0)
            self.seguir_ojos_activo = True
            self.tiempo_ultima_interaccion = time.time()

    # ── BASE DE CARGA & DETECCIÓN ESTÁTICA (MODO SIN MOTORES) ────────────────
    def _ejecutar_busqueda_base_carga(self, idioma="es"):
        """
        Escaneo visual estático del código ArUco ID 0 sin mover ruedas.
        """
        print("\n" + "=" * 68)
        print("🔋 [Base de Carga] MODO SIN MOTORES: Escaneo visual de ArUco DICT_7X7_50 ID 0")
        print("=" * 68)

        self.seguir_ojos_activo = False
        self.cara.cambiar_expresion("sorprendido")
        self.cara.pestaniar()

        # 1. Anuncio inicial por voz
        anuncio_inicio = (
            "Buscando marcador de base de carga en mi cámara..."
            if (not self.modo_offline and idioma != "en") else
            "Searching for charging dock marker in my camera..."
        )
        print(f"🤖 Orbit: \"{anuncio_inicio}\"")
        if self.voz:
            self.voz.hablar(anuncio_inicio, idioma=idioma)
            self._esperar_voz()
            time.sleep(0.2)

        # 2. Escaneo estático en cámara
        base_encontrada = False
        cx_hallado, cy_hallado, id_hallado = 0, 0, 0

        for _ in range(40):
            encontrado, m_id, cx, cy, corners, frame = self.vision.detectar_aruco(target_id=0)
            if encontrado and m_id == 0:
                base_encontrada = True
                cx_hallado, cy_hallado, id_hallado = cx, cy, m_id
                print(f"🎯 [Base de Carga] ¡Marcador ArUco ID {m_id} detectado en ({cx}, {cy})!")
                break
            time.sleep(0.05)

        # 3. Procesar confirmación o aviso
        if base_encontrada:
            self._confirmar_base_carga(cx_hallado, cy_hallado, id_hallado, idioma=idioma)
        else:
            self.cara.cambiar_expresion("triste")
            self.cara.mirar_a(0.0, -0.3)
            aviso_fallo = (
                "No detecté el código de la base de carga en mi campo visual. Por favor colócalo frente a mi cámara."
                if (not self.modo_offline and idioma != "en") else
                "Could not detect charging dock marker. Please hold it in front of my camera."
            )
            print(f"🤖 Orbit: \"{aviso_fallo}\"")
            if self.voz:
                self.voz.hablar(aviso_fallo, idioma=idioma)
                self._esperar_voz()
            self.seguir_ojos_activo = True
            self.tiempo_ultima_interaccion = time.time()
            self.cara.cambiar_expresion("normal")
            self.cara.mirar_a(0.0, 0.0)

    def _confirmar_base_carga(self, cx, cy, m_id, idioma="es"):
        """Fija la base de carga, centra la mirada en ella y emite confirmación."""
        self.movimiento.detener()
        self.base_carga_detectada = True
        self.base_carga_info = {
            "id": int(m_id),
            "cx": int(cx),
            "cy": int(cy),
            "timestamp": time.time(),
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Guardar permanentemente en base_carga.json
        try:
            ruta_bc = os.path.join(_BASE_DIR, "base_carga.json")
            with open(ruta_bc, "w", encoding="utf-8") as f_bc:
                json.dump(self.base_carga_info, f_bc, indent=4)
            print(f"💾 [Base de Carga] Posición guardada permanentemente en '{ruta_bc}'.")
        except Exception as e_bc:
            print(f"⚠️ [Base de Carga] Error guardando archivo JSON: {e_bc}")

        # Dirigir la mirada hacia el marcador detectado
        w_f = getattr(self.vision, "frame_width", 640) or 640
        h_f = getattr(self.vision, "frame_height", 765) or 765
        signo_x = 1.0 if self.invertir_ojos else -1.0
        ojo_x = float(np.clip(signo_x * ((cx - (w_f / 2.0)) / (w_f / 2.0)), -0.9, 0.9))
        ojo_y = float(np.clip(- ((cy - (h_f / 2.0)) / (h_f / 2.0)), -0.9, 0.9))

        self.cara.cambiar_expresion("feliz")
        self.cara.pestaniar()
        self.cara.mirar_a(ojo_x, ojo_y)

        anuncio_exito = (
            "¡Base de carga identificada! Me he detenido frente a ella y queda registrada como mi estación de recarga."
            if (not self.modo_offline and idioma != "en") else
            "Charging dock identified! I have stopped right in front of it and saved it as my charging station."
        )
        print(f"🤖 Orbit: \"{anuncio_exito}\"")
        if self.voz:
            self.voz.hablar(anuncio_exito, idioma=idioma)
            self._esperar_voz()
            time.sleep(0.4)

        # Registrar en métricas / historial
        try:
            historial_orbit.registrar_interaccion(
                pregunta="carga",
                respuesta=anuncio_exito,
                reaccion="🔋 Base de Carga Localizada",
                latencia_ms=50,
                idioma=idioma,
                origen="voz",
                tipo_entrada="comando",
                tema="acople_carga"
            )
        except Exception:
            pass

        # Ejecutar 'lo otro después': maniobra de aproximación y acople trasero completo
        self._ejecutar_acople_completo(idioma=idioma)

        self.seguir_ojos_activo = True
        self.tiempo_ultima_interaccion = time.time()
        self.tiempo_ultimo_rostro = time.time()
        self.cara.cambiar_expresion("feliz")

    def _ejecutar_acople_completo(self, idioma="es"):
        """En modo sin motor, no realiza maniobra física con ruedas."""
        print("ℹ️ [Auto-Docking] Modo sin motores: Maniobra de aproximación y giro físico omitida.")
        return True

    def _finalizar_conversacion(self):
        """Transición limpia de fin de conversación hacia búsqueda activa."""
        self.conversacion_activa = False
        self.silencios_consecutivos = 0
        self.movimiento.detener()
        if self.oido:
            self.oido.ultimo_idioma = "es"
        self.tiempo_ultimo_rostro = time.time() # Iniciar conteo de 15s para mirar alrededor
        self.tiempo_ultima_interaccion = time.time()
        self.estado_actual = self.ESTADO_BUSQUEDA
        print(f"🔄 [Orbit] Retornando a modo búsqueda. Si pasan {TIEMPO_INACTIVIDAD_BUSQUEDA:.0f}s sin personas, mirará alrededor.\n")

    def apagar(self):
        self.seguir_ojos_activo = False
        self.ejecutando = False
        self._cerrar_centro_comando(decir_despedida=False)
        self._cerrar_modo_aprender_karina(decir_despedida=False)
        if hasattr(self, "cara") and self.cara:
            self.cara.stop()
        if hasattr(self, "movimiento") and self.movimiento:
            self.movimiento.cerrar()
        if hasattr(self, "vision") and self.vision:
            self.vision.cerrar()
        print("👋 [Orbit Sin Motor] Robot y proceso facial apagados correctamente.")


# =============================================================================
# 🏁 PUNTO DE ENTRADA PRINCIPAL
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orbit V4.0 — Robot Autónomo Bilingüe")
    parser.add_argument("--puerto", type=str, default=None, help="Puerto serial de MegaPi (ej. /dev/ttyUSB0)")
    parser.add_argument("--cam", type=int, default=0, help="Índice de la cámara USB (si se usa modo monocámara)")
    parser.add_argument("--single-cam", action="store_true", help="Forzar modo de una sola cámara (desactiva visión alargada)")
    parser.add_argument("--cam-cabeza", type=int, default=None, help="Índice de la cámara Cabeza (por defecto calibración /dev/video1)")
    parser.add_argument("--cam-torso", type=int, default=None, help="Índice de la cámara Torso (por defecto calibración /dev/video0)")
    parser.add_argument("--sim", action="store_true", help="Ejecutar en modo simulado sin hardware físico")
    parser.add_argument("--gui", action="store_true", help="Mostrar ventana de video con HUD de centrado")
    parser.add_argument("--fullscreen", action="store_true", help="Ejecutar la cara en pantalla completa (activo por defecto)")
    parser.add_argument("--window", action="store_true", help="Ejecutar la cara en ventana pequeña (sin pantalla completa)")
    parser.add_argument("--offline", action="store_true", help="Forzar modo 100%% offline (Kokoro TTS am_echo, estricto en inglés, RAG local)")
    parser.add_argument("--invert-eyes", action="store_true", help="Invertir dirección horizontal de la mirada")
    args = parser.parse_args()

    usar_fullscreen = not args.window

    robot = OrbitFullRobot(
        puerto_serial=args.puerto,
        indice_camara=args.cam,
        modo_simulado=args.sim,
        mostrar_video=args.gui,
        pantalla_completa=usar_fullscreen,
        forzar_offline=args.offline,
        invertir_ojos=args.invert_eyes,
        usar_alargada=not args.single_cam,
        cam_cabeza=args.cam_cabeza,
        cam_torso=args.cam_torso
    )
    robot.iniciar()
