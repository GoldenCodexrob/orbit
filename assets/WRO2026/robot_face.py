"""
=============================================================================
🤖 ROBOT_FACE.PY — Motor Facial Multiprocesamiento Oficial de Orbit (WRO 2026)
=============================================================================
Diseñado para ejecución concurrente en segundo plano mediante 'multiprocessing':
- PROCESO INDEPENDIENTE DEL SO: El renderizado a 60 FPS y el pestañeo automático
  se ejecutan en su propio proceso de sistema operativo con su propio GIL.
- EVITA BLOQUEOS CON MEGAPi: La comunicación serial por UART/USB hacia la MegaPi
  (motores, encoders, giroscopio), la visión por computador y el procesamiento
  de voz NO congelan ni causan tirones en la animación facial de Orbit.
- PESTAÑEO AUTOMÁTICO AUTÓNOMO: Ocurre periódicamente en intervalos naturales
  (2.5s - 5.0s) dentro del proceso de fondo sin requerir llamadas del proceso principal.
- CONTROL ATÓMICO POR IPC: Mirada, emociones y pestañeo manual se controlan sin
  bloqueos mediante variables atómicas de memoria compartida (multiprocessing.Value/Event).
- GEOMETRÍA AUTÉNTICA Y CEJAS FRIJOL: Ojos 99.6% convexos extraídos del vídeo original
  'ORBIT_LOOP_INICIAL.mp4', cejas clásicas suaves flotando armónicamente y sin boca.

USO DESDE OTROS SCRIPTS (cerebro_v4.py, orbit_robot.py, controlador_movimiento.py):
-----------------------------------------------------------------------------
    from robot_face import OrbitFaceBackground

    # Iniciar en segundo plano
    face = OrbitFaceBackground(fullscreen=False)
    face.start()

    # Controlar desde el hilo de motores / lógica sin bloquear
    face.mirar_a(-0.5, 0.2)           # Mover ojos (X: -1.0 a 1.0, Y: -1.0 a 1.0)
    face.cambiar_expresion('feliz')   # 'normal', 'feliz', 'triste', 'sorprendido'
    face.pestaniar()                  # Pestañeo manual inmediato

    # El pestañeo automático sigue ocurriendo solo de fondo.
    # Para detenerlo al finalizar el programa:
    face.stop()
=============================================================================
"""

import os
import sys

# Desactivar extensiones problemáticas de XRandR en SDL2 bajo RealVNC / Xvnc
# Previene el crash 'X Error: BadRRCrtc (invalid Crtc parameter)'
os.environ["SDL_VIDEO_X11_XRANDR"] = "0"
os.environ["SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR"] = "0"
os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

import math
import time
import random
import multiprocessing as mp
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *

# ==========================================
# 📐 GEOMETRÍA VECTORIAL AUTÉNTICA DE ORBIT
# ==========================================
ORBIT_LEFT_EYE_POINTS = [(131.75, 0.0), (131.39, 6.89), (130.88, 13.76), (130.27, 20.63), (129.58, 27.54), (128.83, 34.52), (128.03, 41.6), (127.17, 48.82), (126.22, 56.2), (125.15, 63.76), (123.88, 71.52), (122.37, 79.47), (120.52, 87.56), (118.25, 95.76), (115.5, 104.0), (112.18, 112.18), (108.24, 120.21), (103.63, 127.97), (98.33, 135.34), (92.34, 142.2), (85.69, 148.42), (78.42, 153.9), (70.59, 158.55), (62.3, 162.29), (53.63, 165.07), (44.71, 166.88), (35.65, 167.71), (26.54, 167.6), (17.51, 166.59), (8.63, 164.76), (0.0, 162.19), (-8.33, 158.98), (-16.32, 155.23), (-23.92, 151.05), (-31.14, 146.53), (-37.98, 141.75), (-44.45, 136.81), (-50.58, 131.76), (-56.39, 126.65), (-61.92, 121.52), (-67.2, 116.39), (-72.26, 111.28), (-77.14, 106.17), (-81.85, 101.08), (-86.42, 95.98), (-90.86, 90.86), (-95.18, 85.7), (-99.39, 80.48), (-103.49, 75.19), (-107.49, 69.81), (-111.39, 64.31), (-115.18, 58.69), (-118.86, 52.92), (-122.43, 46.99), (-125.86, 40.89), (-129.15, 34.6), (-132.26, 28.11), (-135.18, 21.41), (-137.86, 14.49), (-140.28, 7.35), (-142.37, 0.0), (-144.09, -7.55), (-145.4, -15.28), (-146.24, -23.16), (-146.57, -31.16), (-146.35, -39.22), (-145.55, -47.29), (-144.14, -55.33), (-142.11, -63.27), (-139.46, -71.06), (-136.21, -78.64), (-132.38, -85.97), (-128.0, -93.0), (-123.12, -99.7), (-117.77, -106.04), (-112.02, -112.02), (-105.9, -117.61), (-99.46, -122.82), (-92.75, -127.66), (-85.8, -132.13), (-78.65, -136.23), (-71.32, -139.97), (-63.82, -143.35), (-56.19, -146.37), (-48.42, -149.02), (-40.54, -151.29), (-32.55, -153.15), (-24.48, -154.58), (-16.35, -155.56), (-8.18, -156.06), (-0.0, -156.06), (8.15, -155.54), (16.24, -154.49), (24.22, -152.91), (32.05, -150.8), (39.7, -148.18), (47.14, -145.07), (54.32, -141.5), (61.22, -137.5), (67.83, -133.12), (74.13, -128.4), (80.12, -123.37), (85.79, -118.07), (91.14, -112.54), (96.17, -106.81), (100.9, -100.9), (105.31, -94.82), (109.4, -88.59), (113.18, -82.23), (116.63, -75.74), (119.74, -69.13), (122.5, -62.42), (124.91, -55.61), (126.96, -48.73), (128.63, -41.8), (129.95, -34.82), (130.91, -27.83), (131.54, -20.83), (131.87, -13.86), (131.93, -6.91)]

ORBIT_LEFT_BROW_POINTS = [(44.01, 0.0), (46.03, 4.84), (45.97, 9.77), (43.86, 14.25), (39.99, 17.8), (34.88, 20.14), (29.17, 21.19), (23.5, 21.16), (18.38, 20.41), (14.09, 19.4), (10.71, 18.56), (8.1, 18.2), (5.99, 18.43), (4.08, 19.17), (2.12, 20.15), (0.0, 21.02), (-2.25, 21.45), (-4.51, 21.23), (-6.59, 20.29), (-8.36, 18.78), (-9.78, 16.94), (-10.98, 15.12), (-12.22, 13.57), (-13.83, 12.45), (-16.16, 11.74), (-19.43, 11.22), (-23.67, 10.54), (-28.66, 9.31), (-33.96, 7.22), (-38.97, 4.1), (-43.03, 0.0), (-45.55, -4.79), (-46.14, -9.81), (-44.68, -14.52), (-41.33, -18.4), (-36.53, -21.09), (-30.84, -22.4), (-24.9, -22.42), (-19.27, -21.4), (-14.35, -19.75), (-10.33, -17.89), (-7.21, -16.19), (-4.83, -14.86), (-2.97, -13.98), (-1.41, -13.45), (-0.0, -13.1), (1.34, -12.74), (2.6, -12.23), (3.76, -11.56), (4.81, -10.8), (5.84, -10.11), (7.03, -9.68), (8.65, -9.61), (10.97, -9.88), (14.23, -10.34), (18.5, -10.68), (23.67, -10.54), (29.39, -9.55), (35.11, -7.46), (40.2, -4.23)]


# Mapeo numérico de emociones para memoria compartida atómica
MAPA_EXPRESIONES = {
    0: 'normal',
    1: 'feliz',
    2: 'triste',
    3: 'sorprendido',
    4: 'pensando',
    5: 'escuchando'
}
EXPRESION_A_ID = {v: k for k, v in MAPA_EXPRESIONES.items()}

# ==========================================
# CONFIGURACIÓN GENERAL DE PANTALLA
# ==========================================
ANCHO_PANTALLA = 800
ALTO_PANTALLA = 480

class RobotFaceApp:
    """
    Clase central de renderizado OpenGL para la cara del robot Orbit.
    Soporta ejecución interactiva autónoma (run) o en segundo plano (run_shared).
    """
    def __init__(self, width=ANCHO_PANTALLA, height=ALTO_PANTALLA, fullscreen=False):
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        
        pygame.init()
        
        flags = pygame.OPENGL | pygame.DOUBLEBUF
        if self.fullscreen:
            try:
                info = pygame.display.Info()
                if info.current_w > 0 and info.current_h > 0:
                    self.width = info.current_w
                    self.height = info.current_h
            except Exception:
                pass
            # En Linux / Raspberry Pi / RealVNC, usar NOFRAME a resolución completa cubre el 100%
            # de la pantalla sin bordes, evitando que SDL2 llame a XRRGetCrtcInfo (BadRRCrtc)
            if sys.platform.startswith("linux"):
                flags |= pygame.NOFRAME
            else:
                flags |= pygame.FULLSCREEN
            
        # Selección adaptativa de visual GLX (compatible con Raspberry Pi, RealVNC, Mesa y Desktop)
        pantalla_inicializada = False
        for msaa in [4, 2, 0]:
            try:
                if msaa > 0:
                    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
                    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, msaa)
                else:
                    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0)
                    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 0)
                self.screen = pygame.display.set_mode((self.width, self.height), flags)
                pantalla_inicializada = True
                break
            except pygame.error:
                continue

        if not pantalla_inicializada:
            try:
                # Intento con resolución 0,0 para que SDL2 elija automáticamente en fullscreen
                self.screen = pygame.display.set_mode((0, 0) if self.fullscreen else (self.width, self.height), flags)
            except pygame.error:
                self.screen = pygame.display.set_mode((self.width, self.height), flags)

        try:
            sw, sh = self.screen.get_size()
            if sw > 0 and sh > 0:
                self.width = sw
                self.height = sh
        except Exception:
            pass

        if self.fullscreen:
            try:
                pygame.mouse.set_visible(False)
            except Exception:
                pass
        pygame.display.set_caption("Orbit Face — Interactive MultiProcessing (WRO 2026)")
        self.clock = pygame.time.Clock()
        
        # =====================================================================
        # 🎛️ CALIBRACIÓN GEOMÉTRICA AUTÉNTICA (800x480)
        # =====================================================================
        self.config = {
            # 🎨 Paleta de Color Pixar / WALL·E
            "fondo": (0, 0, 0),
            "esclerotica": (255, 255, 255),
            "iris_borde": (51, 153, 230),        # Celeste exterior
            "iris_centro": (70, 180, 245),       # Celeste interior brillante
            "pupila": (15, 15, 15),              # Negro profundo
            "brillo": (255, 255, 255),           # Blanco destello
            "cejas": (120, 75, 40),              # Marrón clásico frijol

            # 👁️ ESCALA Y GEOMETRÍA AGRANDADA PARA VISOR FÍSICO (WRO 2026)
            "escala_base": float(os.getenv("ORBIT_EYE_SCALE", "1.25")), # Ojos 25% más grandes para llenar visor
            "ojo_pos_x": 184.0,                   # Separación horizontal calibrada para evitar colisión
            "ojo_pos_y": float(os.getenv("ORBIT_EYE_OFFSET_Y", "-36.0")), # Bajado 5px (-36.0 px)
            
            # 👁️‍🗨️ MIRADA INTERNA (Iris, Pupila y Reflejos)
            "iris_radio": 58.5,                   # Radio iris
            "pupila_radio": 47.5,                 # Radio pupila
            "max_desplazamiento_mirada": 52.0,    # Rango máximo seguro dentro de la esclerótica

            # ✨ Destellos de Pupila (Specular Highlights)
            "brillo_primario_offset_x": 8.0,
            "brillo_primario_offset_y": 20.0,
            "brillo_primario_radio": 18.0,

            "brillo_secundario_offset_x": -26.0,
            "brillo_secundario_offset_y": -15.0,
            "brillo_secundario_radio": 9.0,

            # ⌒ CEJAS CLÁSICAS DE FRIJOL (Suaves y bien separadas)
            "ceja_pos_x": 145.0,                  # Posición X relativa centrada sobre ojos grandes
            "ceja_pos_y": float(os.getenv("ORBIT_CEJA_POS_Y", "192.0")), # Bajada 5px acompañando a los ojos (192.0 px)
            "ceja_rx": 58.0,                     # Ancho proporcional de la ceja
            "ceja_ry": 22.0,                     # Grosor de la ceja
            "ceja_curvatura": 18.5,              # Profundidad de concavidad inferior
            "ceja_angulo": -4.0,                 # Inclinación base
        }
        
        # Estado dinámico y cinemático
        self.mirada_actual_x = 0.0
        self.mirada_actual_y = 0.0
        self.mirada_target_x = 0.0
        self.mirada_target_y = 0.0

        # Pestañeo
        self.factor_pestaneo = 1.0
        self.pestaneando = False
        self.pestaneo_tiempo_inicio = 0.0
        self.pestaneo_duracion = 0.18
        self.pestaneo_automatico = True
        self.proximo_pestaneo = time.time() + random.uniform(2.5, 4.8)

        # Emociones y dilatación pupilar
        self.expresion = "normal"
        self.factor_felicidad = 0.0
        self.factor_tristeza = 0.0
        self.factor_sorpresa = 0.0
        self.factor_pensando = 0.0
        self.factor_escuchando = 0.0
        self.dilatacion_manual = 1.0
        self.dilatacion_actual = 1.0

        # Estado dinámico para visor multimedia cinematográfico (Kari'ña / Cultura)
        self.target_transicion_media = 0.0
        self.transicion_media = 0.0
        self.ruta_imagen_actual = ""
        self.media_tex_id = None
        self.media_tex_w = 0
        self.media_tex_h = 0

        self.init_gl()

    def init_gl(self):
        """Configura proyección ortogonal y antialiasing en OpenGL."""
        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        # Mantener escala virtual de referencia (480 px de altura) para cualquier resolución
        aspecto = self.width / max(1.0, float(self.height))
        virtual_h = 480.0
        virtual_w = virtual_h * aspecto
        gluOrtho2D(-virtual_w / 2.0, virtual_w / 2.0, -virtual_h / 2.0, virtual_h / 2.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.0, 0.0, 0.0, 1.0)

    def _set_color(self, color_tuple, alpha=1.0):
        glColor4f(color_tuple[0] / 255.0, color_tuple[1] / 255.0, color_tuple[2] / 255.0, alpha)

    def dibujar_circulo(self, cx, cy, radio, segmentos=72):
        """Dibuja un círculo suave con abanico de triángulos."""
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
        for i in range(segmentos + 1):
            theta = (i / segmentos) * 2.0 * math.pi
            glVertex2f(cx + math.cos(theta) * radio, cy + math.sin(theta) * radio)
        glEnd()

    def dibujar_ojo_orbit(self, es_izquierdo=True, is_left=None, escala=1.0, alpha=1.0):
        """
        Dibuja la esclerótica blanca orgánica con geometría 100% auténtica y convexa.
        Acepta 'es_izquierdo' o 'is_left' indistintamente.
        """
        if is_left is not None:
            es_izquierdo = is_left

        pestaneo = self.factor_pestaneo

        # 1. Relleno sólido antialiased con GL_TRIANGLE_FAN continuo
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0.0, 0.0)
        for px, py in ORBIT_LEFT_EYE_POINTS:
            actual_x = (px if es_izquierdo else -px) * escala
            actual_y = py * pestaneo * escala
            glVertex2f(actual_x, actual_y)
        p0x, p0y = ORBIT_LEFT_EYE_POINTS[0]
        actual_p0x = (p0x if es_izquierdo else -p0x) * escala
        actual_p0y = p0y * pestaneo * escala
        glVertex2f(actual_p0x, actual_p0y)
        glEnd()

        # 2. Borde exterior vectorial ultra nítido con antialiasing
        glLineWidth(2.5 * max(1.0, escala))
        glBegin(GL_LINE_LOOP)
        for px, py in ORBIT_LEFT_EYE_POINTS:
            actual_x = (px if es_izquierdo else -px) * escala
            actual_y = py * pestaneo * escala
            glVertex2f(actual_x, actual_y)
        glEnd()

    def dibujar_ceja_frijol(self, rx, ry, profundidad_curva):
        """Dibuja la ceja suave y lisa con forma de frijol clásica de Orbit."""
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0.0, 0.0)
        segmentos = 64
        for i in range(segmentos + 1):
            angulo = (i / segmentos) * 2.0 * math.pi
            x = math.cos(angulo) * rx
            y_original = math.sin(angulo) * ry
            if y_original > 0:
                y = y_original
            else:
                normal_x = x / rx
                curva_central = math.cos(normal_x * (math.pi / 2.0)) * profundidad_curva
                y = y_original + curva_central
            glVertex2f(x, y)
        glEnd()

        # Borde suavizado antialiased
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        for i in range(segmentos + 1):
            angulo = (i / segmentos) * 2.0 * math.pi
            x = math.cos(angulo) * rx
            y_original = math.sin(angulo) * ry
            if y_original > 0:
                y = y_original
            else:
                normal_x = x / rx
                curva_central = math.cos(normal_x * (math.pi / 2.0)) * profundidad_curva
                y = y_original + curva_central
            glVertex2f(x, y)
        glEnd()

    def dibujar_ceja(self, rx=None, ry=None, profundidad_curva=None, es_izquierdo=True, is_left=None):
        """Alias compatible para dibujar cejas frijol."""
        if rx is None: rx = self.config["ceja_rx"]
        if ry is None: ry = self.config["ceja_ry"]
        if profundidad_curva is None: profundidad_curva = self.config["ceja_curvatura"]
        self.dibujar_ceja_frijol(rx, ry, profundidad_curva)

    def render_ojo(self, es_izquierdo=True, is_left=None, escala=None, alpha=1.0, extra_dilatacion=0.0):
        """
        Renderiza un ojo completo con esclerótica, iris, pupila y doble destello Pixar.
        La mirada (lx, ly) se desacopla para movimiento estrictamente paralelo (sin estrabismo).
        Soporta escalado y atenuación suave durante transiciones hacia el visor multimedia.
        """
        if is_left is not None:
            es_izquierdo = is_left
        cfg = self.config
        if escala is None:
            escala = cfg.get("escala_base", 1.25)
        pos_x = (-cfg["ojo_pos_x"] if es_izquierdo else cfg["ojo_pos_x"])
        pos_y = cfg["ojo_pos_y"]

        glPushMatrix()
        glTranslatef(pos_x, pos_y, 0.0)

        # 1. Esclerótica blanca auténtica
        self._set_color(cfg["esclerotica"], alpha=alpha)
        self.dibujar_ojo_orbit(es_izquierdo=es_izquierdo, escala=escala, alpha=alpha)

        # 2. Pupila, Iris y Reflejos
        if self.factor_pestaneo > 0.20:
            lx = self.mirada_actual_x * escala
            ly = self.mirada_actual_y * self.factor_pestaneo * escala

            # Micro-deriva orgánica de pensamiento (simula escanear recuerdos / atención activa)
            if self.factor_pensando > 0.15:
                t = time.time()
                lx += math.sin(t * 3.2) * 4.5 * self.factor_pensando * escala
                ly += math.cos(t * 2.1) * 3.0 * self.factor_pensando * escala

            dist = math.sqrt(lx * lx + ly * ly)
            max_m = cfg["max_desplazamiento_mirada"] * escala
            if dist > max_m and dist > 0:
                lx = (lx / dist) * max_m
                ly = (ly / dist) * max_m

            # Dinámica de Pupila Orgánica y Dilatación Interactiva
            respiracion = math.sin(time.time() * 1.5) * 0.03
            pulso_pensando = math.sin(time.time() * 3.8) * 0.05 * self.factor_pensando
            escala_pupila = (
                self.dilatacion_actual
                + respiracion
                + self.factor_pensando * 0.22
                + pulso_pensando
                + self.factor_escuchando * 0.10
                + self.factor_sorpresa * 0.18
                + extra_dilatacion
            ) * escala
            pest_factor = min(1.0, self.factor_pestaneo * 1.15)

            # Iris Borde Exterior
            self._set_color(cfg["iris_borde"], alpha=alpha)
            self.dibujar_circulo(lx, ly, cfg["iris_radio"] * escala_pupila * pest_factor)

            # Iris Centro Luminoso
            self._set_color(cfg["iris_centro"], alpha=alpha)
            self.dibujar_circulo(lx, ly, cfg["iris_radio"] * 0.92 * escala_pupila * pest_factor)

            # Pupila Negra
            self._set_color(cfg["pupila"], alpha=alpha)
            self.dibujar_circulo(lx, ly, cfg["pupila_radio"] * escala_pupila * pest_factor)

            # Destello Primario (Superior Derecho)
            self._set_color(cfg["brillo"], alpha=alpha)
            p_off_x = cfg["brillo_primario_offset_x"] * escala
            p_off_y = cfg["brillo_primario_offset_y"] * self.factor_pestaneo * escala
            self.dibujar_circulo(lx + p_off_x, ly + p_off_y, cfg["brillo_primario_radio"] * pest_factor * escala)

            # Destello Secundario (Inferior Izquierdo - Rebote Pixar)
            self._set_color(cfg["brillo"], alpha=alpha)
            s_off_x = cfg["brillo_secundario_offset_x"] * escala
            s_off_y = cfg["brillo_secundario_offset_y"] * self.factor_pestaneo * escala
            self.dibujar_circulo(lx + s_off_x, ly + s_off_y, cfg["brillo_secundario_radio"] * pest_factor * escala)

        glPopMatrix()

    def render_cejas(self, offset_y=0.0, alpha=1.0):
        """Renderiza las cejas frijol suaves, armónicas y libres de colisión."""
        if alpha <= 0.01:
            return
        cfg = self.config
        self._set_color(cfg["cejas"], alpha=alpha)

        dy_base = (
            self.factor_sorpresa * 24.0
            - self.factor_tristeza * 6.0
            + self.factor_felicidad * 12.0
            + self.factor_escuchando * 8.0
            + offset_y
        )
        rot_base = self.factor_felicidad * 4.0 - self.factor_tristeza * 12.0

        # Efecto pensando asimétrico expresivo (muy notorio e inquisitivo)
        dy_izq = dy_base + self.factor_pensando * 26.0
        rot_izq = rot_base + self.factor_pensando * 18.0

        dy_der = dy_base - self.factor_pensando * 8.0
        rot_der = -rot_base - self.factor_pensando * 12.0

        # Ceja Izquierda
        glPushMatrix()
        glTranslatef(-cfg["ceja_pos_x"], cfg["ceja_pos_y"] + dy_izq, 0.0)
        glRotatef(cfg["ceja_angulo"] + rot_izq, 0.0, 0.0, 1.0)
        self.dibujar_ceja_frijol(cfg["ceja_rx"], cfg["ceja_ry"], cfg["ceja_curvatura"])
        glPopMatrix()

        # Ceja Derecha (Reflejo simétrico horizontal)
        glPushMatrix()
        glTranslatef(cfg["ceja_pos_x"], cfg["ceja_pos_y"] + dy_der, 0.0)
        glRotatef(-cfg["ceja_angulo"] + rot_der, 0.0, 0.0, 1.0)
        glScalef(-1.0, 1.0, 1.0)
        self.dibujar_ceja_frijol(cfg["ceja_rx"], cfg["ceja_ry"], cfg["ceja_curvatura"])
        glPopMatrix()

    def mirar_a(self, target_x, target_y):
        """Actualiza el objetivo de mirada en coordenadas normalizadas [-1.0, 1.0]."""
        max_dist = self.config["max_desplazamiento_mirada"]
        self.mirada_target_x = max(-max_dist, min(max_dist, target_x * max_dist))
        self.mirada_target_y = max(-max_dist, min(max_dist, target_y * max_dist))

    def pestaniar(self):
        """Inicia una animación de pestañeo natural."""
        if not self.pestaneando:
            self.pestaneando = True
            self.pestaneo_tiempo_inicio = time.time()

    def cambiar_expresion(self, nueva):
        """Cambia la expresión activa ('normal', 'feliz', 'triste', 'sorprendido')."""
        self.expresion = nueva

    def actualizar_animaciones(self, dt):
        """Actualiza interpolaciones cinemáticas suaves a 60 FPS."""
        # Pestañeo
        if self.pestaneando:
            t = (time.time() - self.pestaneo_tiempo_inicio) / self.pestaneo_duracion
            if t >= 1.0:
                self.pestaneando = False
                self.factor_pestaneo = 1.0
            else:
                self.factor_pestaneo = 0.5 * (1.0 - math.cos(t * 2.0 * math.pi))
        elif self.pestaneo_automatico and time.time() >= self.proximo_pestaneo:
            # Si está pensando, suspender o espaciar pestañeos para evitar parpadeos excesivos
            if self.factor_pensando > 0.3:
                self.proximo_pestaneo = time.time() + random.uniform(4.5, 7.0)
            else:
                self.pestaniar()
                self.proximo_pestaneo = time.time() + random.uniform(2.8, 5.2)

        # Mirada suave amortiguada
        velocidad_mirada = 14.0
        self.mirada_actual_x += (self.mirada_target_x - self.mirada_actual_x) * min(1.0, dt * velocidad_mirada)
        self.mirada_actual_y += (self.mirada_target_y - self.mirada_actual_y) * min(1.0, dt * velocidad_mirada)

        # Transiciones de emoción
        vel_emocion = 8.0
        target_felicidad = 1.0 if self.expresion == "feliz" else 0.0
        target_tristeza = 1.0 if self.expresion == "triste" else 0.0
        target_sorpresa = 1.0 if self.expresion == "sorprendido" else 0.0
        target_pensando = 1.0 if self.expresion == "pensando" else 0.0
        target_escuchando = 1.0 if self.expresion == "escuchando" else 0.0

        self.factor_felicidad += (target_felicidad - self.factor_felicidad) * min(1.0, dt * vel_emocion)
        self.factor_tristeza += (target_tristeza - self.factor_tristeza) * min(1.0, dt * vel_emocion)
        self.factor_sorpresa += (target_sorpresa - self.factor_sorpresa) * min(1.0, dt * vel_emocion)
        self.factor_pensando += (target_pensando - self.factor_pensando) * min(1.0, dt * vel_emocion)
        self.factor_escuchando += (target_escuchando - self.factor_escuchando) * min(1.0, dt * vel_emocion)

        # Suavizado cinemático continuo de dilatación pupilar
        vel_dilatacion = 10.0
        self.dilatacion_actual += (self.dilatacion_manual - self.dilatacion_actual) * min(1.0, dt * vel_dilatacion)

        # Suavizado cinemático de transición multimedia hacia el visor de ojos
        vel_transicion = 2.4
        if self.transicion_media < self.target_transicion_media:
            self.transicion_media = min(self.target_transicion_media, self.transicion_media + dt * vel_transicion)
        elif self.transicion_media > self.target_transicion_media:
            self.transicion_media = max(self.target_transicion_media, self.transicion_media - dt * vel_transicion)
            if self.transicion_media == 0.0:
                self.pestaniar()

    def _cargar_imagen_media(self, ruta_imagen: str):
        """Carga una imagen a textura 2D de OpenGL para el visor multimedia."""
        import os
        if not ruta_imagen or not os.path.isfile(ruta_imagen):
            return
        try:
            if self.media_tex_id is not None:
                try:
                    glDeleteTextures([self.media_tex_id])
                except Exception:
                    pass
                self.media_tex_id = None

            surf = pygame.image.load(ruta_imagen).convert_alpha()
            w, h = surf.get_size()
            img_data = pygame.image.tostring(surf, "RGBA", 1)

            tex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)

            self.media_tex_id = tex
            self.media_tex_w = w
            self.media_tex_h = h
            self.ruta_imagen_actual = ruta_imagen
        except Exception as e:
            print(f"[OrbitFace] Error cargando textura multimedia '{ruta_imagen}': {e}")

    def dibujar_rect_redondeado(self, cx, cy, ancho, alto, radio, segmentos_por_esquina=12):
        """Dibuja un cuadrilátero con esquinas redondeadas suavizadas con abanico."""
        hw = ancho / 2.0
        hh = alto / 2.0
        r = min(radio, hw, hh)
        glBegin(GL_POLYGON)
        glVertex2f(cx, cy)
        for i in range(segmentos_por_esquina + 1):
            ang = (i / segmentos_por_esquina) * (math.pi / 2.0)
            glVertex2f(cx + hw - r + math.cos(ang) * r, cy + hh - r + math.sin(ang) * r)
        for i in range(segmentos_por_esquina + 1):
            ang = (math.pi / 2.0) + (i / segmentos_por_esquina) * (math.pi / 2.0)
            glVertex2f(cx - hw + r + math.cos(ang) * r, cy + hh - r + math.sin(ang) * r)
        for i in range(segmentos_por_esquina + 1):
            ang = math.pi + (i / segmentos_por_esquina) * (math.pi / 2.0)
            glVertex2f(cx - hw + r + math.cos(ang) * r, cy - hh + r + math.sin(ang) * r)
        for i in range(segmentos_por_esquina + 1):
            ang = (3.0 * math.pi / 2.0) + (i / segmentos_por_esquina) * (math.pi / 2.0)
            glVertex2f(cx + hw - r + math.cos(ang) * r, cy - hh + r + math.sin(ang) * r)
        glEnd()

    def dibujar_borde_redondeado(self, cx, cy, ancho, alto, radio, segmentos_por_esquina=12):
        """Dibuja el contorno vectorial nítido con esquinas redondeadas."""
        hw = ancho / 2.0
        hh = alto / 2.0
        r = min(radio, hw, hh)
        glBegin(GL_LINE_LOOP)
        for i in range(segmentos_por_esquina + 1):
            ang = (i / segmentos_por_esquina) * (math.pi / 2.0)
            glVertex2f(cx + hw - r + math.cos(ang) * r, cy + hh - r + math.sin(ang) * r)
        for i in range(segmentos_por_esquina + 1):
            ang = (math.pi / 2.0) + (i / segmentos_por_esquina) * (math.pi / 2.0)
            glVertex2f(cx - hw + r + math.cos(ang) * r, cy + hh - r + math.sin(ang) * r)
        for i in range(segmentos_por_esquina + 1):
            ang = math.pi + (i / segmentos_por_esquina) * (math.pi / 2.0)
            glVertex2f(cx - hw + r + math.cos(ang) * r, cy - hh + r + math.sin(ang) * r)
        for i in range(segmentos_por_esquina + 1):
            ang = (3.0 * math.pi / 2.0) + (i / segmentos_por_esquina) * (math.pi / 2.0)
            glVertex2f(cx + hw - r + math.cos(ang) * r, cy - hh + r + math.sin(ang) * r)
        glEnd()

    def render_portal_media(self, ease: float):
        """
        Renderiza el portal holográfico/visor multimedia donde los ojos de Orbit
        se expanden y revelan la imagen cultural con marco de alta tecnología.
        """
        if ease <= 0.005:
            return

        cx, cy = 0.0, -5.0
        w_max = 660.0
        h_max = 400.0
        w_portal = w_max * ease
        h_portal = h_max * ease
        corner_r = 24.0 * ease

        # 1. Fondo oscuro translúcido tipo cristal protector (Dark Obsidian Glass)
        self._set_color((8, 14, 24), alpha=min(0.96, 0.96 * ease))
        self.dibujar_rect_redondeado(cx, cy, w_portal, h_portal, corner_r)

        # 2. Textura de imagen cultural
        if self.media_tex_id is not None and ease > 0.08:
            margin = 16.0 * ease
            w_disp_max = max(10.0, w_portal - margin * 2.0)
            h_disp_max = max(10.0, h_portal - margin * 2.0)

            ratio_img = self.media_tex_w / max(1, self.media_tex_h)
            ratio_box = w_disp_max / h_disp_max

            if ratio_box > ratio_img:
                h_img = h_disp_max
                w_img = h_img * ratio_img
            else:
                w_img = w_disp_max
                h_img = w_img / ratio_img

            hw = w_img / 2.0
            hh = h_img / 2.0

            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.media_tex_id)
            alpha_tex = min(1.0, ease * 1.15)
            glColor4f(1.0, 1.0, 1.0, alpha_tex)

            glBegin(GL_QUADS)
            glTexCoord2f(0.0, 0.0); glVertex2f(cx - hw, cy - hh)
            glTexCoord2f(1.0, 0.0); glVertex2f(cx + hw, cy - hh)
            glTexCoord2f(1.0, 1.0); glVertex2f(cx + hw, cy + hh)
            glTexCoord2f(0.0, 1.0); glVertex2f(cx - hw, cy + hh)
            glEnd()

            glDisable(GL_TEXTURE_2D)

        # 3. Marco de brillo y pulsación cibernética (Cyan característico de Orbit)
        pulse = 0.85 + 0.15 * math.sin(time.time() * 2.8)

        # Brillo suave exterior
        glLineWidth(3.5)
        glColor4f(51 / 255.0, 153 / 255.0, 230 / 255.0, 0.45 * ease * pulse)
        self.dibujar_borde_redondeado(cx, cy, w_portal + 4.0, h_portal + 4.0, corner_r + 2.0)

        # Línea nítida interior
        glLineWidth(2.0)
        glColor4f(90 / 255.0, 200 / 255.0, 255 / 255.0, 0.95 * ease)
        self.dibujar_borde_redondeado(cx, cy, w_portal, h_portal, corner_r)

        # 4. Acentos de esquina de alta tecnología (L-Brackets)
        if ease > 0.4:
            bracket_l = 22.0 * ease
            hw_p = w_portal / 2.0
            hh_p = h_portal / 2.0
            glLineWidth(3.0)
            glColor4f(160 / 255.0, 230 / 255.0, 255 / 255.0, 0.95 * ease)

            glBegin(GL_LINES)
            # Superior Derecha
            glVertex2f(cx + hw_p, cy + hh_p); glVertex2f(cx + hw_p - bracket_l, cy + hh_p)
            glVertex2f(cx + hw_p, cy + hh_p); glVertex2f(cx + hw_p, cy + hh_p - bracket_l)
            # Superior Izquierda
            glVertex2f(cx - hw_p, cy + hh_p); glVertex2f(cx - hw_p + bracket_l, cy + hh_p)
            glVertex2f(cx - hw_p, cy + hh_p); glVertex2f(cx - hw_p, cy + hh_p - bracket_l)
            # Inferior Izquierda
            glVertex2f(cx - hw_p, cy - hh_p); glVertex2f(cx - hw_p + bracket_l, cy - hh_p)
            glVertex2f(cx - hw_p, cy - hh_p); glVertex2f(cx - hw_p, cy - hh_p + bracket_l)
            # Inferior Derecha
            glVertex2f(cx + hw_p, cy - hh_p); glVertex2f(cx + hw_p - bracket_l, cy - hh_p)
            glVertex2f(cx + hw_p, cy - hh_p); glVertex2f(cx + hw_p, cy - hh_p + bracket_l)
            glEnd()

    def render_frame(self):
        """Dibuja un fotograma completo en el buffer de OpenGL con soporte multimedia."""
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        escala_base = self.config.get("escala_base", 1.25)
        if self.transicion_media > 0.001:
            t = self.transicion_media
            ease = 0.5 * (1.0 - math.cos(t * math.pi))

            # 1. Ojos dilatándose y expandiéndose antes de fundirse en el portal
            if ease < 0.95:
                alpha_ojos = max(0.0, 1.0 - ease * 1.35)
                escala_ojos = (1.0 + ease * 0.85) * escala_base
                self.render_ojo(es_izquierdo=True, escala=escala_ojos, alpha=alpha_ojos, extra_dilatacion=ease * 0.45)
                self.render_ojo(es_izquierdo=False, escala=escala_ojos, alpha=alpha_ojos, extra_dilatacion=ease * 0.45)

                alpha_cejas = max(0.0, 1.0 - ease * 1.5)
                dy_cejas = ease * 55.0
                self.render_cejas(offset_y=dy_cejas, alpha=alpha_cejas)

            # 2. Portal holográfico multimedia
            self.render_portal_media(ease)
        else:
            self.render_ojo(es_izquierdo=True, escala=escala_base)
            self.render_ojo(es_izquierdo=False, escala=escala_base)
            self.render_cejas()

        pygame.display.flip()

    def run_shared(self, shared_target_x, shared_target_y, shared_expresion_id,
                   shared_auto_blink, event_blink, shared_running, shared_dilatacion=None,
                   shared_media_activo=None, shared_media_path=None, shared_escala=None):
        """
        Bucle de ejecución para proceso hijo en segundo plano (MultiProcessing).
        Lee variables atómicas compartidas e intercala eventos de ventana de forma no bloqueante.
        """
        ultimo_tiempo = time.time()
        while shared_running.value:
            ahora = time.time()
            dt = ahora - ultimo_tiempo
            ultimo_tiempo = ahora

            # Procesar eventos para evitar advertencias de ventana del SO
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    shared_running.value = False
                    break
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                    shared_running.value = False
                    break

            # Pestañeo manual disparado por proceso padre
            if event_blink.is_set():
                event_blink.clear()
                self.pestaniar()

            # Leer estado compartido del proceso padre
            self.pestaneo_automatico = bool(shared_auto_blink.value)
            self.mirar_a(shared_target_x.value, shared_target_y.value)
            self.expresion = MAPA_EXPRESIONES.get(shared_expresion_id.value, "normal")
            if shared_dilatacion is not None:
                self.dilatacion_manual = float(shared_dilatacion.value)
            if shared_escala is not None and shared_escala.value > 0.1:
                self.config["escala_base"] = float(shared_escala.value)

            if shared_media_activo is not None:
                if bool(shared_media_activo.value):
                    if shared_media_path is not None:
                        try:
                            raw_bytes = bytes(shared_media_path.value)
                            raw_path = raw_bytes.split(b'\x00')[0].decode('utf-8', errors='ignore')
                            if raw_path and raw_path != self.ruta_imagen_actual:
                                self._cargar_imagen_media(raw_path)
                        except Exception:
                            pass
                    self.target_transicion_media = 1.0
                else:
                    self.target_transicion_media = 0.0

            self.actualizar_animaciones(dt)
            self.render_frame()
            self.clock.tick(60)

        pygame.quit()

    def run(self):
        """Bucle interactivo principal autónomo por teclado y ratón."""
        print("=" * 68)
        print("🤖 ORBIT FACE — MODO INTERACTIVO AUTÓNOMO:")
        print("  * MOUSE: Mueve el cursor para que Orbit siga tu mirada")
        print("  * [B] o [ESPACIO]: Pestañeo natural manual")
        print("  * [A]: Activar / Desactivar pestañeo automático")
        print("  * [H]: Expresión FELIZ (Ojos risueños)")
        print("  * [S]: Expresión TRISTE")
        print("  * [W]: Expresión SORPRENDIDO (Ojos grandes y cejas altas)")
        print("  * [N]: Expresión NORMAL (Neutral)")
        print("  * [C]: Centrar mirada")
        print("  * [FLECHAS]: Control manual de mirada")
        print("  * [ESC] o [Q]: Salir")
        print("=" * 68)

        corriendo = True
        ultimo_tiempo = time.time()

        while corriendo:
            ahora = time.time()
            dt = ahora - ultimo_tiempo
            ultimo_tiempo = ahora

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    corriendo = False

                elif event.type == pygame.MOUSEMOTION:
                    mx, my = event.pos
                    norm_x = (mx - self.width / 2.0) / (self.width / 2.0)
                    norm_y = -(my - self.height / 2.0) / (self.height / 2.0)
                    self.mirar_a(norm_x, norm_y)

                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        corriendo = False
                    elif event.key in (pygame.K_b, pygame.K_SPACE):
                        self.pestaniar()
                    elif event.key == pygame.K_a:
                        self.pestaneo_automatico = not self.pestaneo_automatico
                        print("Pestañeo automático:", "ACTIVADO" if self.pestaneo_automatico else "DESACTIVADO")
                    elif event.key == pygame.K_h:
                        self.cambiar_expresion("feliz" if self.expresion != "feliz" else "normal")
                    elif event.key == pygame.K_s:
                        self.cambiar_expresion("triste" if self.expresion != "triste" else "normal")
                    elif event.key == pygame.K_w:
                        self.cambiar_expresion("sorprendido" if self.expresion != "sorprendido" else "normal")
                    elif event.key == pygame.K_p:
                        self.cambiar_expresion("pensando" if self.expresion != "pensando" else "normal")
                    elif event.key == pygame.K_n:
                        self.cambiar_expresion("normal")
                    elif event.key == pygame.K_c:
                        self.mirar_a(0.0, 0.0)
                    elif event.key == pygame.K_LEFT:
                        self.mirar_a(-1.0, self.mirada_target_y / self.config["max_desplazamiento_mirada"])
                    elif event.key == pygame.K_RIGHT:
                        self.mirar_a(1.0, self.mirada_target_y / self.config["max_desplazamiento_mirada"])
                    elif event.key == pygame.K_UP:
                        self.mirar_a(self.mirada_target_x / self.config["max_desplazamiento_mirada"], 1.0)
                    elif event.key == pygame.K_DOWN:
                        self.mirar_a(self.mirada_target_x / self.config["max_desplazamiento_mirada"], -1.0)
                    elif event.key == pygame.K_k:
                        import os
                        karina_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "karina.jpg")
                        if self.target_transicion_media == 0.0:
                            self._cargar_imagen_media(karina_path)
                            self.target_transicion_media = 1.0
                            print("[OrbitFace] Visor multimedia: EXPANDIENDO OJOS (Cultura Kari'ña)")
                        else:
                            self.target_transicion_media = 0.0
                            print("[OrbitFace] Visor multimedia: CONTRAYENDO OJOS A MODO NATURAL")

            self.actualizar_animaciones(dt)
            self.render_frame()
            self.clock.tick(60)

        pygame.quit()
        sys.exit(0)

def _multiprocessing_worker_entry(shared_target_x, shared_target_y, shared_expresion_id,
                                 shared_auto_blink, event_blink, shared_running,
                                 shared_dilatacion, shared_media_activo, shared_media_path,
                                 width, height, fullscreen, shared_escala=None):
    """Punto de entrada de módulo para el proceso hijo de multiprocessing."""
    try:
        app = RobotFaceApp(width=width, height=height, fullscreen=fullscreen)
        app.run_shared(shared_target_x, shared_target_y, shared_expresion_id,
                       shared_auto_blink, event_blink, shared_running, shared_dilatacion,
                       shared_media_activo, shared_media_path, shared_escala)
    except Exception as e:
        print(f"⚠️ [OrbitFace Error]: {e}")
        import traceback
        traceback.print_exc()

class OrbitFaceBackground:
    """
    Controlador de Cara en Segundo Plano con MultiProcessing.
    Aísla completamente el motor visual de Pygame/OpenGL en un proceso independiente
    del sistema operativo con su propio GIL.

    Garantiza:
    1. Cero caídas de FPS o congelamiento cuando el hilo principal envía comandos
       a los motores de la MegaPi o realiza llamadas seriales/bloqueantes.
    2. Pestañeo automático continuo y autónomo en intervalos naturales.
    3. Control no bloqueante de mirada y emociones en tiempo real.
    """
    def __init__(self, width=800, height=480, fullscreen=False, escala_ojos=None):
        self.width = width
        self.height = height
        self.fullscreen = fullscreen

        # Atómicos de memoria compartida sin contención
        self._shared_target_x = mp.Value('d', 0.0)
        self._shared_target_y = mp.Value('d', 0.0)
        self._shared_expresion_id = mp.Value('i', 0)
        self._shared_auto_blink = mp.Value('b', True)
        self._event_blink = mp.Event()
        self._shared_running = mp.Value('b', False)
        self._shared_dilatacion = mp.Value('d', 1.0)
        default_scale = escala_ojos if escala_ojos is not None else float(os.getenv("ORBIT_EYE_SCALE", "1.25"))
        self._shared_escala = mp.Value('d', default_scale)
        self._shared_media_activo = mp.Value('b', False)
        self._shared_media_path = mp.Array('c', 512)

        self._process = None

    def start(self):
        """Inicia el proceso facial en segundo plano."""
        if self._process is not None and self._process.is_alive():
            print("[OrbitFace] El proceso de cara ya se encuentra en ejecución.")
            return

        self._shared_running.value = True
        self._process = mp.Process(
            target=_multiprocessing_worker_entry,
            args=(
                self._shared_target_x,
                self._shared_target_y,
                self._shared_expresion_id,
                self._shared_auto_blink,
                self._event_blink,
                self._shared_running,
                self._shared_dilatacion,
                self._shared_media_activo,
                self._shared_media_path,
                self.width,
                self.height,
                self.fullscreen,
                self._shared_escala
            ),
            daemon=True
        )
        self._process.start()
        print(f"[OrbitFace] Proceso secundario MultiProcessing iniciado (PID: {self._process.pid})")

    def mostrar_imagen(self, ruta_imagen: str):
        """
        Activa la animación de transición de los ojos: se dilatan y expanden
        suavemente para revelar la imagen cultural dentro del visor multimedia.
        """
        import os
        if isinstance(ruta_imagen, str) and os.path.isfile(ruta_imagen):
            encoded = ruta_imagen.encode('utf-8')[:511]
            self._shared_media_path.value = encoded
            self._shared_media_activo.value = True

    def ocultar_imagen(self):
        """
        Contrae suavemente el visor multimedia de vuelta a los ojos auténticos de Orbit
        con un pestañeo de reincorporación.
        """
        self._shared_media_activo.value = False

    def dilatar_pupilas(self, factor: float = 1.25):
        """Ajusta manualmente la dilatación de las pupilas (1.0 = normal, 1.25 = asombro/curiosidad)."""
        self._shared_dilatacion.value = float(max(0.7, min(1.4, factor)))

    def set_escala_ojos(self, escala: float):
        """Ajusta dinámicamente la escala de los ojos (1.0 = original, 1.25 = visor grande WRO)."""
        self._shared_escala.value = float(max(0.5, min(2.0, escala)))

    def mirar_a(self, x: float, y: float):
        """
        Actualiza el objetivo de mirada en coordenadas normalizadas [-1.0, 1.0].
        No bloqueante, atómico y de latencia cero.
        """
        self._shared_target_x.value = float(max(-1.0, min(1.0, x)))
        self._shared_target_y.value = float(max(-1.0, min(1.0, y)))

    def pestaniar(self):
        """Dispara un pestañeo manual inmediato en el proceso de fondo."""
        self._event_blink.set()

    def set_auto_pestaneo(self, activo: bool):
        """Activa o desactiva el pestañeo automático periódico en segundo plano."""
        self._shared_auto_blink.value = bool(activo)

    def cambiar_expresion(self, expresion: str):
        """Cambia la expresión activa ('normal', 'feliz', 'triste', 'sorprendido')."""
        exp_id = EXPRESION_A_ID.get(expresion.lower(), 0)
        self._shared_expresion_id.value = exp_id

    def stop(self, timeout=2.0):
        """Detiene limpiamente el proceso hijo."""
        if self._process is not None and self._process.is_alive():
            self._shared_running.value = False
            self._process.join(timeout=timeout)
            if self._process.is_alive():
                self._process.terminate()
            print("[OrbitFace] Proceso facial detenido limpiamente.")
            self._process = None

    def is_alive(self) -> bool:
        """Verifica si el proceso de cara está activo."""
        return self._process is not None and self._process.is_alive()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

# Alias de compatibilidad
OrbitFaceController = OrbitFaceBackground
RobotFaceBackgroundProcess = OrbitFaceBackground

if __name__ == "__main__":
    # Modo de prueba en segundo plano: 'python robot_face.py --bg'
    if "--bg" in sys.argv or "--test" in sys.argv:
        print("=" * 68)
        print("🤖 PROBANDO ORBIT FACE EN SEGUNDO PLANO (MULTIPROCESSING)...")
        print("Simulando que el proceso principal envía comandos a la MegaPi")
        print("y se bloquea con time.sleep(), mientras la cara NO se congela y pestañea sola.")
        print("=" * 68)
        with OrbitFaceBackground(fullscreen=False) as face:
          for i in range(1, 6):
            print(f"[{i}/5] Proceso principal bloqueado 2s con MegaPi... (Mira la ventana)")
            face.mirar_a(-0.8 if i % 2 == 1 else 0.8, 0.2)
            if i == 3:
              face.cambiar_expresion("feliz")
            time.sleep(2.0)
        print("Prueba de segundo plano completada con éxito.")
    else:
        # Modo interactivo autónomo con mouse y teclado
        app = RobotFaceApp()
        app.run()
