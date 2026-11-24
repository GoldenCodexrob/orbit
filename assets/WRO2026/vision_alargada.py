#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
ORBIT ROBOT - SISTEMA DE VISIÓN ALARGADA VERTICAL (Cabeza + Torso)
WRO 2026 - Future Innovators
===============================================================================
Combina en tiempo real los feeds de las dos cámaras de ORBIT:
  - Cámara Superior (Cabeza / /dev/video1): Rostros, expresiones, campo visual alto.
  - Cámara Inferior (Torso / /dev/video0): Suelo, obstáculos, marcadores ArUco, docking.

Resultado:
  Un único flujo de video vertical alargado (ej: 640 x 880 px) de campo amplio (FOV vertical)
  con mezcla suave (Alpha Blending) y corrección de desplazamiento (Offset X / Y).

Controles de Alineación, Rotación y Escala Individual:
  [W] / [S] : Ajustar solapamiento vertical (Overlap +/- px)
  [A] / [D] : Ajustar desplazamiento horizontal (Offset X +/- px)
  -----------------------------------------------------------------------------
  [1] / [2] : Ángulo fino Cámara CABEZA (+0.5° / -0.5°) para enderezar líneas
  [3] / [4] : Ángulo fino Cámara TORSO (+0.5° / -0.5°) para enderezar líneas
  [5] / [6] : Escala / Zoom individual CABEZA (+0.01x / -0.01x) [o teclas '[' y ']']
  [7] / [8] : Escala / Zoom individual TORSO (+0.01x / -0.01x) [o teclas ';' y ''']
  -----------------------------------------------------------------------------
  [R] / [T] : Rotar 90° Cámara Cabeza / Torso
  [H] / [J] : Espejo horizontal (Flip) de Cabeza / Torso
  [0]       : Resetear todo (Ángulos a 0°, Escalas a 1.00x)
  [B]       : Alternar modo de empalme (Mezcla Alpha suave / Corte neto / Línea guía)
  [P]       : Alternar mini-vistas individuales (Picture-in-Picture)
  [G]       : Guardar calibración permanente en 'calibracion_vision.json'
  [C]       : Tomar captura del panorama vertical alargado
  [X]       : Intercambiar cámaras (si se invirtieron los puertos USB)
  [Q / ESC] : Salir
===============================================================================
"""

import cv2
import numpy as np
import time
import threading
import os
import sys
import json
import argparse
from datetime import datetime

# Rutas de archivos de calibración y capturas
DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_CALIB = os.path.join(DIR_ACTUAL, "calibracion_vision.json")
DIR_CAPTURAS = os.path.join(DIR_ACTUAL, "capturas_vision")
os.makedirs(DIR_CAPTURAS, exist_ok=True)


# =============================================================================
# DETECCIÓN DE CÁMARAS DISPONIBLES
# =============================================================================
def escanear_camaras(max_dispositivos=8):
    """Escanea índices de cámaras operativas en el sistema."""
    encontradas = []
    backends = [cv2.CAP_V4L2, cv2.CAP_ANY] if hasattr(cv2, 'CAP_V4L2') and sys.platform.startswith('linux') else [cv2.CAP_ANY]
    
    for idx in range(max_dispositivos):
        for backend in backends:
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        encontradas.append(idx)
                        cap.release()
                        break
                    cap.release()
            except Exception:
                pass
    return encontradas


# =============================================================================
# GESTIÓN DE CONFIGURACIÓN Y CALIBRACIÓN
# =============================================================================
def cargar_calibracion():
    """Carga los parámetros de empalme o devuelve los valores empíricos óptimos."""
    defaults = {
        "cam_cabeza_idx": 1,        # /dev/video1 según captura del robot
        "cam_torso_idx": 0,         # /dev/video0 según captura del robot
        "overlap_px": 195,          # Solapamiento vertical calibrado por el usuario
        "offset_x_px": 2,           # Desplazamiento horizontal calibrado por el usuario
        "modo_blend": "linea",      # 'linea', 'alpha', 'corte'
        "rot_cabeza": 0,            # 0, 90, 180, 270
        "rot_torso": 0,             # 0, 90, 180, 270
        "angulo_cabeza": -6.0,      # Ángulo fino Cabeza calibrado (-6.0°)
        "angulo_torso": 0.0,        # Ángulo fino Torso calibrado (+0.0°)
        "scale_cabeza": 0.88,       # Escala individual Cabeza calibrada (0.88x)
        "scale_torso": 1.22,        # Escala individual Torso calibrada (1.22x)
        "flip_cabeza": False,       # Espejo horizontal
        "flip_torso": False,        # Espejo horizontal
        "width": 640,
        "height": 480,
        "fps": 30
    }
    rutas_buscar = [
        RUTA_CALIB,
        os.path.join(DIR_ACTUAL, "calibracion_vision.json"),
        os.path.join(os.path.dirname(DIR_ACTUAL), "calibracion_vision.json"),
        os.path.join(os.getcwd(), "calibracion_vision.json")
    ]
    for r in rutas_buscar:
        if os.path.exists(r):
            try:
                with open(r, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
                    print(f"📄 [Config] Calibración cargada desde '{r}'")
                    break
            except Exception as e:
                print(f"⚠️ [Config] Error leyendo calibración desde '{r}': {e}.")
    return defaults


def guardar_calibracion(config):
    """Guarda los parámetros de empalme en disco para persistencia permanente."""
    exito = False
    rutas_guardar = [RUTA_CALIB]
    parent_dir = os.path.dirname(DIR_ACTUAL)
    if os.path.isdir(parent_dir):
        rutas_guardar.append(os.path.join(parent_dir, "calibracion_vision.json"))

    for r in set(rutas_guardar):
        try:
            with open(r, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"💾 [Config] ¡Calibración guardada exitosamente en '{r}'!")
            exito = True
        except Exception as e:
            print(f"❌ [Config] Error al guardar calibración en '{r}': {e}")
    return exito


# =============================================================================
# HILO DE CAPTURA CON ROTACIÓN Y ESCALA INDIVIDUAL
# =============================================================================
class CamStreamThread:
    def __init__(self, src, name="Cam", width=640, height=480, fps=30, 
                 rotation_deg=0, fine_angle=0.0, scale=1.0, flip_h=False):
        self.src = src
        self.name = name
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.rotation_deg = rotation_deg  # 0, 90, 180, 270
        self.fine_angle = fine_angle      # float (+/- grados)
        self.scale = max(0.50, min(float(scale), 2.50))  # float (0.50x a 2.50x)
        self.flip_h = flip_h              # bool

        self.cap = None
        self.frame = None
        self.ret = False
        self.running = False
        self.lock = threading.Lock()
        
        self.fps_real = 0.0
        self._fps_count = 0
        self._fps_t0 = time.time()

    def start(self):
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY] if hasattr(cv2, 'CAP_V4L2') and sys.platform.startswith('linux') else [cv2.CAP_ANY]
        opened = False

        for b in backends:
            try:
                cap = cv2.VideoCapture(self.src, b)
                if cap.isOpened():
                    try:
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                    except Exception:
                        pass
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                    cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                    try:
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception:
                        pass

                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        self.cap = cap
                        self.ret = True
                        self.frame = self._aplicar_transformaciones(frame)
                        opened = True
                        break
                    else:
                        cap.release()
            except Exception:
                pass

        if not opened:
            # Fallback a apertura estándar
            try:
                cap = cv2.VideoCapture(self.src)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        self.cap = cap
                        self.ret = True
                        self.frame = self._aplicar_transformaciones(frame)
                        opened = True
            except Exception:
                pass

        if not opened:
            print(f"❌ [{self.name}] No se pudo abrir cámara en /dev/video{self.src}")
            return False

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print(f"🚀 [{self.name}] Activa en /dev/video{self.src}")
        return True

    def _loop(self):
        while self.running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.04)
                continue
            ret, raw = self.cap.read()
            if ret and raw is not None:
                proc = self._aplicar_transformaciones(raw)
                with self.lock:
                    self.frame = proc
                    self.ret = True
                self._fps_count += 1
                t = time.time()
                if t - self._fps_t0 >= 1.0:
                    self.fps_real = self._fps_count / (t - self._fps_t0)
                    self._fps_count = 0
                    self._fps_t0 = t
            else:
                time.sleep(0.01)

    def _aplicar_transformaciones(self, img):
        # 1. Rotación ortogonal (90°, 180°, 270°)
        if self.rotation_deg == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation_deg == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif self.rotation_deg == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # 2. Espejo horizontal (Flip)
        if self.flip_h:
            img = cv2.flip(img, 1)

        # 3. Rotación angular fina y Escala individual combinadas en matriz afín
        if abs(self.fine_angle) >= 0.05 or abs(self.scale - 1.0) >= 0.005:
            h, w = img.shape[:2]
            center = (w / 2.0, h / 2.0)
            M = cv2.getRotationMatrix2D(center, self.fine_angle, self.scale)
            img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

        return img

    def rotar_90(self):
        """Rota 90° en sentido horario."""
        self.rotation_deg = (self.rotation_deg + 90) % 360

    def ajustar_angulo(self, delta):
        """Ajusta el ángulo fino en +/- delta grados."""
        self.fine_angle = round(self.fine_angle + delta, 1)

    def ajustar_escala(self, delta):
        """Ajusta la escala individual en +/- delta (ej: 0.01)."""
        self.scale = round(max(0.50, min(self.scale + delta, 2.50)), 2)

    def toggle_flip(self):
        """Alterna el espejo horizontal."""
        self.flip_h = not self.flip_h

    def reset_rotacion(self):
        """Restablece rotaciones, ángulos y escalas a valores nominales."""
        self.rotation_deg = 0
        self.fine_angle = 0.0
        self.scale = 1.00
        self.flip_h = False

    def read(self):
        with self.lock:
            if self.ret and self.frame is not None:
                return True, self.frame.copy()
            return False, None

    def stop(self):
        self.running = False
        time.sleep(0.05)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None


# =============================================================================
# MOTOR DE VISIÓN ALARGADA (STITCHING & BLENDING SEGURO)
# =============================================================================
def construir_vision_alargada(frame_cabeza, frame_torso, overlap_px=65, offset_x=40, modo="alpha"):
    """
    Empalma verticalmente el frame de la cabeza (arriba) con el frame del torso (abajo).
    Aplica traslación horizontal de corrección (offset_x) y cortes con dimensiones estrictas.
    """
    h_c, w_c = frame_cabeza.shape[:2]
    h_t, w_t = frame_torso.shape[:2]

    # Igualar anchos si fuese necesario
    w = max(w_c, w_t)
    if w_c != w:
        frame_cabeza = cv2.resize(frame_cabeza, (w, int(h_c * (w / w_c))))
    if w_t != w:
        frame_torso = cv2.resize(frame_torso, (w, int(h_t * (w / w_t))))

    h_c, w = frame_cabeza.shape[:2]
    h_t, _ = frame_torso.shape[:2]

    # Aplicar desplazamiento horizontal (Offset X) al torso si es distinto de cero
    if offset_x != 0:
        M = np.float32([[1, 0, -offset_x], [0, 1, 0]])
        frame_torso = cv2.warpAffine(frame_torso, M, (w, h_t), borderMode=cv2.BORDER_REPLICATE)

    # Restringir overlap para evitar desbordamiento
    overlap = max(0, min(overlap_px, min(h_c, h_t) - 10))

    if overlap == 0:
        alargada = np.vstack([frame_cabeza, frame_torso])
        y_union = h_c
    else:
        h_total = h_c + h_t - overlap
        alargada = np.zeros((h_total, w, 3), dtype=np.uint8)

        # Región exclusiva Cabeza
        alargada[:h_c - overlap, :] = frame_cabeza[:h_c - overlap, :]

        # Región exclusiva Torso
        alargada[h_c:, :] = frame_torso[overlap:, :]

        # Zona de transición / solapamiento
        if modo == "alpha":
            # Mezcla suave mediante gradiente ponderado
            roi_c = frame_cabeza[h_c - overlap:h_c, :].astype(float)
            roi_t = frame_torso[:overlap, :].astype(float)
            alpha = np.linspace(1.0, 0.0, overlap).reshape((overlap, 1, 1))
            blended = (roi_c * alpha + roi_t * (1.0 - alpha)).astype(np.uint8)
            alargada[h_c - overlap:h_c, :] = blended
            y_union = h_c - (overlap // 2)

        elif modo == "corte":
            # Corte neto simétrico exacto (soporta números pares e impares)
            corte_sup = overlap // 2
            corte_inf = overlap - corte_sup

            alargada[h_c - overlap : h_c - overlap + corte_sup, :] = frame_cabeza[h_c - overlap : h_c - overlap + corte_sup, :]
            alargada[h_c - overlap + corte_sup : h_c, :] = frame_torso[corte_sup : overlap, :]
            y_union = h_c - overlap + corte_sup

        else: # modo == "linea"
            # Mezcla suave con líneas guía visuales
            roi_c = frame_cabeza[h_c - overlap:h_c, :].astype(float)
            roi_t = frame_torso[:overlap, :].astype(float)
            alpha = np.linspace(1.0, 0.0, overlap).reshape((overlap, 1, 1))
            blended = (roi_c * alpha + roi_t * (1.0 - alpha)).astype(np.uint8)
            alargada[h_c - overlap:h_c, :] = blended
            y_union = h_c - (overlap // 2)
            cv2.line(alargada, (0, h_c - overlap), (w, h_c - overlap), (0, 255, 255), 2)
            cv2.line(alargada, (0, h_c), (w, h_c), (0, 165, 255), 2)

    return alargada, y_union


# =============================================================================
# OVERLAY HUD Y GRÁFICOS
# =============================================================================
def dibujar_hud_alargada(canvas, cfg, fps, y_union, pip_cabeza=None, pip_torso=None, mostrar_pip=False, toast_msg=""):
    """Dibuja el panel de control superior, las marcas métricas y las mini-vistas PiP."""
    h, w = canvas.shape[:2]
    out = canvas.copy()

    # Barra superior oscura translúcida (dos líneas de info)
    overlay = out.copy()
    cv2.rectangle(overlay, (0, 0), (w, 64), (15, 23, 42), -1)
    cv2.addWeighted(overlay, 0.85, out, 0.15, 0, out)

    # Borde cian en encabezado
    cv2.line(out, (0, 0), (w, 0), (0, 240, 255), 4)

    # Línea 1: Título y métricas generales
    cv2.putText(out, "ORBIT - VISION ALARGADA VERTICAL", (16, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)
    info_txt = f"{w}x{h} | {fps:.1f} FPS | Overlap:{cfg['overlap_px']}px [W/S] | OffsetX:{cfg['offset_x_px']}px [A/D] | Blend:{cfg['modo_blend'].upper()} [B]"
    cv2.putText(out, info_txt, (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (0, 240, 255), 1, cv2.LINE_AA)

    # Línea 2: Parámetros de rotación y escala individual por sección
    s_c = cfg.get('scale_cabeza', 1.0)
    s_t = cfg.get('scale_torso', 1.0)
    rot_c = f"{cfg.get('rot_cabeza', 0)}°({cfg.get('angulo_cabeza', 0.0):+.1f}°)"
    rot_t = f"{cfg.get('rot_torso', 0)}°({cfg.get('angulo_torso', 0.0):+.1f}°)"
    
    line2_txt = f"Cab: {rot_c} Zoom:{s_c:.2f}x [5/6] | Tor: {rot_t} Zoom:{s_t:.2f}x [7/8] | Reset:[0] | Guardar:[G]"
    cv2.putText(out, line2_txt, (16, 57), cv2.FONT_HERSHEY_SIMPLEX, 0.37, (255, 200, 0), 1, cv2.LINE_AA)

    # Línea sutil en la zona de costura (seam)
    cv2.line(out, (0, y_union), (w, y_union), (0, 200, 255), 1, cv2.LINE_4)
    cv2.circle(out, (20, y_union), 5, (0, 200, 255), -1)
    cv2.putText(out, "SEAM", (32, y_union + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 200, 255), 1, cv2.LINE_AA)

    # Retículas de referencia (Cabeza y Torso)
    cx = w // 2
    cv2.circle(out, (cx, h // 4), 22, (0, 255, 128), 1, cv2.LINE_AA)
    cv2.line(out, (cx - 15, h // 4), (cx + 15, h // 4), (0, 255, 128), 1)
    cv2.circle(out, (cx, (3 * h) // 4), 22, (59, 130, 246), 1, cv2.LINE_AA)
    cv2.line(out, (cx - 15, (3 * h) // 4), (cx + 15, (3 * h) // 4), (59, 130, 246), 1)

    # Mini-vistas PiP (Picture in Picture) en esquina inferior derecha
    if mostrar_pip and pip_cabeza is not None and pip_torso is not None:
        pw, ph = 140, 105
        mini_c = cv2.resize(pip_cabeza, (pw, ph))
        mini_t = cv2.resize(pip_torso, (pw, ph))

        # Cuadro Cabeza
        y1 = h - 2 * ph - 25
        out[y1:y1 + ph, w - pw - 15:w - 15] = mini_c
        cv2.rectangle(out, (w - pw - 15, y1), (w - 15, y1 + ph), (0, 255, 128), 2)
        cv2.putText(out, f"Cabeza ({s_c:.2f}x)", (w - pw - 10, y1 + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)

        # Cuadro Torso
        y2 = h - ph - 15
        out[y2:y2 + ph, w - pw - 15:w - 15] = mini_t
        cv2.rectangle(out, (w - pw - 15, y2), (w - 15, y2 + ph), (59, 130, 246), 2)
        cv2.putText(out, f"Torso ({s_t:.2f}x)", (w - pw - 10, y2 + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)

    # Toast de notificación
    if toast_msg:
        cv2.rectangle(out, (0, h - 34), (w, h), (0, 0, 0), -1)
        cv2.putText(out, toast_msg, (15, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)

    return out


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="ORBIT Visión Alargada Vertical")
    parser.add_argument("--cabeza", type=int, default=None, help="Dispositivo cámara cabeza (default: 1)")
    parser.add_argument("--torso", type=int, default=None, help="Dispositivo cámara torso (default: 0)")
    parser.add_argument("--overlap", type=int, default=None, help="Solapamiento vertical en px (default: 195)")
    parser.add_argument("--offset-x", type=int, default=None, help="Desplazamiento horizontal en px (default: -2)")
    parser.add_argument("--scale-cabeza", type=float, default=None, help="Escala de Cabeza (default: 1.00)")
    parser.add_argument("--scale-torso", type=float, default=None, help="Escala de Torso (default: 1.00)")
    parser.add_argument("--blend", choices=["alpha", "corte", "linea"], default=None, help="Modo de fusión")
    parser.add_argument("--swap", action="store_true", help="Invertir asignación cabeza/torso")
    args = parser.parse_args()

    cfg = cargar_calibracion()

    if args.cabeza is not None: cfg["cam_cabeza_idx"] = args.cabeza
    if args.torso is not None: cfg["cam_torso_idx"] = args.torso
    if args.overlap is not None: cfg["overlap_px"] = args.overlap
    if args.offset_x is not None: cfg["offset_x_px"] = args.offset_x
    if args.scale_cabeza is not None: cfg["scale_cabeza"] = args.scale_cabeza
    if args.scale_torso is not None: cfg["scale_torso"] = args.scale_torso
    if args.blend is not None: cfg["modo_blend"] = args.blend
    if args.swap:
        cfg["cam_cabeza_idx"], cfg["cam_torso_idx"] = cfg["cam_torso_idx"], cfg["cam_cabeza_idx"]

    # Auto-detección de seguridad si las cámaras configuradas no coinciden
    if args.cabeza is None and args.torso is None:
        cams_activas = escanear_camaras()
        if len(cams_activas) >= 2:
            if cfg["cam_cabeza_idx"] not in cams_activas or cfg["cam_torso_idx"] not in cams_activas:
                print(f"ℹ️ [Auto-Detect] Reajustando cámaras a las disponibles: {cams_activas}")
                if 1 in cams_activas and 0 in cams_activas:
                    cfg["cam_cabeza_idx"] = 1
                    cfg["cam_torso_idx"] = 0
                else:
                    cfg["cam_cabeza_idx"] = cams_activas[1]
                    cfg["cam_torso_idx"] = cams_activas[0]

    print("\n" + "=" * 65)
    print("🚀 INICIANDO SISTEMA DE VISIÓN ALARGADA ORBIT")
    print("=" * 65)
    print(f"  • Cámara Superior (Cabeza): /dev/video{cfg['cam_cabeza_idx']}")
    print(f"  • Cámara Inferior (Torso):  /dev/video{cfg['cam_torso_idx']}")
    print(f"  • Solapamiento Vertical:    {cfg['overlap_px']} px")
    print(f"  • Desplazamiento X:         {cfg['offset_x_px']} px")
    print(f"  • Escala Cabeza:            {cfg.get('scale_cabeza', 1.0):.2f}x")
    print(f"  • Escala Torso:             {cfg.get('scale_torso', 1.0):.2f}x")
    print(f"  • Modo de Mezcla:           {cfg['modo_blend'].upper()}")
    print("=" * 65)

    # Iniciar hilos de captura con soporte de rotación, ángulo fino y escala individual
    stream_cabeza = CamStreamThread(
        src=cfg["cam_cabeza_idx"], 
        name="Cabeza", 
        width=cfg["width"], 
        height=cfg["height"], 
        fps=cfg["fps"], 
        rotation_deg=cfg.get("rot_cabeza", 0),
        fine_angle=cfg.get("angulo_cabeza", 0.0),
        scale=cfg.get("scale_cabeza", 1.0),
        flip_h=cfg.get("flip_cabeza", False)
    )
    stream_torso = CamStreamThread(
        src=cfg["cam_torso_idx"], 
        name="Torso", 
        width=cfg["width"], 
        height=cfg["height"], 
        fps=cfg["fps"], 
        rotation_deg=cfg.get("rot_torso", 0),
        fine_angle=cfg.get("angulo_torso", 0.0),
        scale=cfg.get("scale_torso", 1.0),
        flip_h=cfg.get("flip_torso", False)
    )

    ok_c = stream_cabeza.start()
    ok_t = stream_torso.start()

    if not ok_c and not ok_t:
        print("❌ Error crítico: No se pudo iniciar ninguna cámara.")
        sys.exit(1)

    WIN_MAIN = "ORBIT - Vision Alargada (Cabeza + Torso)"
    cv2.namedWindow(WIN_MAIN, cv2.WINDOW_NORMAL)

    mostrar_pip = True
    toast_msg = "VISIÓN ALARGADA | [5/6] Escala Cabeza | [7/8] Escala Torso | [G] Guardar"
    toast_t0 = time.time()
    fps_alargada = 30.0
    fps_count = 0
    fps_t0 = time.time()

    print("\n🎮 CONTROLES DE ALINEACIÓN, ROTACIÓN Y ESCALA:")
    print("   [W] / [S] : Modificar Solapamiento Vertical (+ / - píxeles)")
    print("   [A] / [D] : Modificar Desplazamiento Horizontal (+ / - píxeles)")
    print("   ---------------------------------------------------------------")
    print("   [1] / [2] : Ángulo fino Cámara CABEZA (+0.5° / -0.5°) para enderezar")
    print("   [3] / [4] : Ángulo fino Cámara TORSO (+0.5° / -0.5°) para enderezar")
    print("   [5] / [6] : Escala / Zoom CABEZA (+0.01x / -0.01x) [o teclas '[' y ']']")
    print("   [7] / [8] : Escala / Zoom TORSO (+0.01x / -0.01x) [o teclas ';' y ''']")
    print("   ---------------------------------------------------------------")
    print("   [R] / [T] : Rotar 90° Cámara Cabeza / Torso")
    print("   [H] / [J] : Espejo horizontal (Flip) de Cabeza / Torso")
    print("   [0]       : Resetear todo (Ángulos a 0°, Escalas a 1.00x)")
    print("   ---------------------------------------------------------------")
    print("   [B]       : Cambiar modo de fusión (Alpha / Corte / Línea)")
    print("   [P]       : Ocultar / Mostrar mini-vistas PiP individuales")
    print("   [G]       : Guardar calibración permanente en JSON")
    print("   [C]       : Guardar captura del panorama vertical alargado")
    print("   [X]       : Intercambiar cámaras (Swap)")
    print("   [Q / ESC] : Salir\n")

    try:
        while True:
            ret_c, frame_c = stream_cabeza.read()
            ret_t, frame_t = stream_torso.read()

            if not ret_c or frame_c is None:
                frame_c = np.zeros((cfg["height"], cfg["width"], 3), dtype=np.uint8)
                cv2.putText(frame_c, "ESPERANDO CAM CABEZA...", (40, cfg["height"] // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            if not ret_t or frame_t is None:
                frame_t = np.zeros((cfg["height"], cfg["width"], 3), dtype=np.uint8)
                cv2.putText(frame_t, "ESPERANDO CAM TORSO...", (40, cfg["height"] // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            # Construir la visión alargada
            alargada_raw, y_seam = construir_vision_alargada(
                frame_c, 
                frame_t, 
                overlap_px=cfg["overlap_px"], 
                offset_x=cfg["offset_x_px"], 
                modo=cfg["modo_blend"]
            )

            # Cálculo de FPS de la visión combinada
            fps_count += 1
            t_now = time.time()
            if t_now - fps_t0 >= 1.0:
                fps_alargada = fps_count / (t_now - fps_t0)
                fps_count = 0
                fps_t0 = t_now

            # Limpiar toast tras 3 segundos
            cur_toast = toast_msg if (time.time() - toast_t0 < 3.0) else ""

            # Añadir HUD interactivo
            alargada_display = dibujar_hud_alargada(
                alargada_raw, 
                cfg, 
                fps_alargada, 
                y_seam, 
                pip_cabeza=frame_c, 
                pip_torso=frame_t, 
                mostrar_pip=mostrar_pip, 
                toast_msg=cur_toast
            )

            cv2.imshow(WIN_MAIN, alargada_display)

            # Manejo interactivo de teclado
            key = cv2.waitKey(1) & 0xFF

            if key in [ord('q'), ord('Q'), 27]:
                break

            # [W] / [S]: Ajuste de overlap vertical
            elif key in [ord('w'), ord('W')]:
                cfg["overlap_px"] = min(cfg["overlap_px"] + 5, 350)
                toast_msg = f"Overlap Vertical: {cfg['overlap_px']} px"
                toast_t0 = time.time()
                print(f"📏 {toast_msg}")

            elif key in [ord('s'), ord('S')]:
                cfg["overlap_px"] = max(cfg["overlap_px"] - 5, 0)
                toast_msg = f"Overlap Vertical: {cfg['overlap_px']} px"
                toast_t0 = time.time()
                print(f"📏 {toast_msg}")

            # [A] / [D]: Ajuste de desplazamiento horizontal
            elif key in [ord('a'), ord('A')]:
                cfg["offset_x_px"] -= 2
                toast_msg = f"Offset X: {cfg['offset_x_px']} px"
                toast_t0 = time.time()
                print(f"↔️ {toast_msg}")

            elif key in [ord('d'), ord('D')]:
                cfg["offset_x_px"] += 2
                toast_msg = f"Offset X: {cfg['offset_x_px']} px"
                toast_t0 = time.time()
                print(f"↔️ {toast_msg}")

            # [R]: Rotar Cabeza 90°
            elif key in [ord('r'), ord('R')]:
                stream_cabeza.rotar_90()
                cfg["rot_cabeza"] = stream_cabeza.rotation_deg
                toast_msg = f"Rotación Cabeza 90° -> {stream_cabeza.rotation_deg}°"
                toast_t0 = time.time()
                print(f"🔄 {toast_msg}")

            # [T]: Rotar Torso 90°
            elif key in [ord('t'), ord('T')]:
                stream_torso.rotar_90()
                cfg["rot_torso"] = stream_torso.rotation_deg
                toast_msg = f"Rotación Torso 90° -> {stream_torso.rotation_deg}°"
                toast_t0 = time.time()
                print(f"🔄 {toast_msg}")

            # [1] / [2]: Ángulo fino Cabeza (+/- 0.5°)
            elif key == ord('1'):
                stream_cabeza.ajustar_angulo(+0.5)
                cfg["angulo_cabeza"] = stream_cabeza.fine_angle
                toast_msg = f"Ángulo Cabeza: {stream_cabeza.fine_angle:+.1f}°"
                toast_t0 = time.time()
                print(f"📐 {toast_msg}")

            elif key == ord('2'):
                stream_cabeza.ajustar_angulo(-0.5)
                cfg["angulo_cabeza"] = stream_cabeza.fine_angle
                toast_msg = f"Ángulo Cabeza: {stream_cabeza.fine_angle:+.1f}°"
                toast_t0 = time.time()
                print(f"📐 {toast_msg}")

            # [3] / [4]: Ángulo fino Torso (+/- 0.5°)
            elif key == ord('3'):
                stream_torso.ajustar_angulo(+0.5)
                cfg["angulo_torso"] = stream_torso.fine_angle
                toast_msg = f"Ángulo Torso: {stream_torso.fine_angle:+.1f}°"
                toast_t0 = time.time()
                print(f"📐 {toast_msg}")

            elif key == ord('4'):
                stream_torso.ajustar_angulo(-0.5)
                cfg["angulo_torso"] = stream_torso.fine_angle
                toast_msg = f"Ángulo Torso: {stream_torso.fine_angle:+.1f}°"
                toast_t0 = time.time()
                print(f"📐 {toast_msg}")

            # [5] / [6] o '[' / ']': Escala / Zoom individual Cabeza (+/- 0.01)
            elif key in [ord('5'), ord('[')]:
                stream_cabeza.ajustar_escala(+0.01)
                cfg["scale_cabeza"] = stream_cabeza.scale
                toast_msg = f"Escala Cabeza: {stream_cabeza.scale:.2f}x"
                toast_t0 = time.time()
                print(f"🔍 {toast_msg}")

            elif key in [ord('6'), ord(']')]:
                stream_cabeza.ajustar_escala(-0.01)
                cfg["scale_cabeza"] = stream_cabeza.scale
                toast_msg = f"Escala Cabeza: {stream_cabeza.scale:.2f}x"
                toast_t0 = time.time()
                print(f"🔍 {toast_msg}")

            # [7] / [8] o ';' / ''': Escala / Zoom individual Torso (+/- 0.01)
            elif key in [ord('7'), ord(';'), ord('{')]:
                stream_torso.ajustar_escala(+0.01)
                cfg["scale_torso"] = stream_torso.scale
                toast_msg = f"Escala Torso: {stream_torso.scale:.2f}x"
                toast_t0 = time.time()
                print(f"🔍 {toast_msg}")

            elif key in [ord('8'), ord("'"), ord('}')]:
                stream_torso.ajustar_escala(-0.01)
                cfg["scale_torso"] = stream_torso.scale
                toast_msg = f"Escala Torso: {stream_torso.scale:.2f}x"
                toast_t0 = time.time()
                print(f"🔍 {toast_msg}")

            # [H]: Flip horizontal Cabeza
            elif key in [ord('h'), ord('H')]:
                stream_cabeza.toggle_flip()
                cfg["flip_cabeza"] = stream_cabeza.flip_h
                toast_msg = f"Espejo Cabeza: {'ON' if stream_cabeza.flip_h else 'OFF'}"
                toast_t0 = time.time()
                print(f"🪞 {toast_msg}")

            # [J]: Flip horizontal Torso
            elif key in [ord('j'), ord('J')]:
                stream_torso.toggle_flip()
                cfg["flip_torso"] = stream_torso.flip_h
                toast_msg = f"Espejo Torso: {'ON' if stream_torso.flip_h else 'OFF'}"
                toast_t0 = time.time()
                print(f"🪞 {toast_msg}")

            # [0]: Resetear rotaciones y escalas a valores por defecto
            elif key == ord('0'):
                stream_cabeza.reset_rotacion()
                stream_torso.reset_rotacion()
                cfg["rot_cabeza"] = 0
                cfg["rot_torso"] = 0
                cfg["angulo_cabeza"] = 0.0
                cfg["angulo_torso"] = 0.0
                cfg["scale_cabeza"] = 1.00
                cfg["scale_torso"] = 1.00
                cfg["flip_cabeza"] = False
                cfg["flip_torso"] = False
                toast_msg = "Ángulos restablecidos a 0° y escalas a 1.00x"
                toast_t0 = time.time()
                print(f"🔄 {toast_msg}")

            # [B]: Alternar modo de mezcla
            elif key in [ord('b'), ord('B')]:
                modos = ["alpha", "corte", "linea"]
                idx = (modos.index(cfg["modo_blend"]) + 1) % len(modos)
                cfg["modo_blend"] = modos[idx]
                toast_msg = f"Modo Mezcla: {cfg['modo_blend'].upper()}"
                toast_t0 = time.time()
                print(f"🎨 {toast_msg}")

            # [P]: Alternar mini-vistas PiP
            elif key in [ord('p'), ord('P')]:
                mostrar_pip = not mostrar_pip
                toast_msg = f"Mini-vistas PiP: {'ACTIVADAS' if mostrar_pip else 'OCULTAS'}"
                toast_t0 = time.time()

            # [G]: Guardar calibración en JSON
            elif key in [ord('g'), ord('G')]:
                cfg["rot_cabeza"] = stream_cabeza.rotation_deg
                cfg["rot_torso"] = stream_torso.rotation_deg
                cfg["angulo_cabeza"] = stream_cabeza.fine_angle
                cfg["angulo_torso"] = stream_torso.fine_angle
                cfg["scale_cabeza"] = stream_cabeza.scale
                cfg["scale_torso"] = stream_torso.scale
                cfg["flip_cabeza"] = stream_cabeza.flip_h
                cfg["flip_torso"] = stream_torso.flip_h
                if guardar_calibracion(cfg):
                    toast_msg = "¡CALIBRACIÓN GUARDADA EN JSON!"
                    toast_t0 = time.time()

            # [C]: Captura de pantalla del panorama limpio
            elif key in [ord('c'), ord('C')]:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                fn = os.path.join(DIR_CAPTURAS, f"vision_alargada_{ts}.jpg")
                cv2.imwrite(fn, alargada_raw, [cv2.IMWRITE_JPEG_QUALITY, 95])
                toast_msg = f"¡CAPTURA GUARDADA! ({ts})"
                toast_t0 = time.time()
                print(f"📸 Panorama guardado en: {fn}")

            # [X]: Intercambiar cámaras
            elif key in [ord('x'), ord('X')]:
                stream_cabeza, stream_torso = stream_torso, stream_cabeza
                cfg["cam_cabeza_idx"] = stream_cabeza.src
                cfg["cam_torso_idx"] = stream_torso.src
                toast_msg = f"Cámaras intercambiadas (Cabeza: dev{stream_cabeza.src}, Torso: dev{stream_torso.src})"
                toast_t0 = time.time()
                print(f"🔄 {toast_msg}")

    except KeyboardInterrupt:
        pass
    finally:
        stream_cabeza.stop()
        stream_torso.stop()
        cv2.destroyAllWindows()
        print("✅ Recursos de visión alargada liberados.")


if __name__ == "__main__":
    main()
