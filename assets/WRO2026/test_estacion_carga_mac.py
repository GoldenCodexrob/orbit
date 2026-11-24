#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
⚡ TEST_ESTACION_CARGA_MAC.PY — Detector Simple de Estación de Carga ArUco
===============================================================================
Robot Autónomo ORBIT — WRO 2026
Script independiente y optimizado para probar en macOS (con cámara FaceTime o imagen).

Características:
  • Abre la cámara de tu Mac automáticamente (índice 0 o 1).
  • Detecta marcadores ArUco (DICT_4X4_50 y DICT_7X7_50, por defecto ID 0).
  • Etiqueta visualmente el marcador como "⚡ ESTACIÓN DE CARGA".
  • Dibuja caja delimitadora, centro, y vector de alineación al centro del visor.
  • Indica instrucciones de dirección: CENTRADO, GIRAR IZQUIERDA o GIRAR DERECHA.
  • Estima la distancia aproximada en cm al marcador.
  • Compatible con OpenCV 4.7+ (ArucoDetector) y versiones anteriores.
  • Si no tienes cámara o permisos activos, incluye un modo de prueba con imagen.

Uso:
  python3 test_estacion_carga_mac.py              # Modo cámara web en vivo
  python3 test_estacion_carga_mac.py --test       # Modo prueba con imagen sintética / generada
  python3 test_estacion_carga_mac.py --cam 1      # Usar cámara externa / índice 1
===============================================================================
"""

import sys
import os
import time
import argparse
import cv2
import numpy as np

# Ancho físico real aproximado del marcador ArUco impreso (en centímetros)
MARCADOR_ANCHO_REAL_CM = 10.0
# Distancia focal aproximada estándar para cámaras web de laptop (~700 px a 640x480)
FOCAL_LENGTH_PX = 650.0


class DetectorEstacionCarga:
    def __init__(self, target_id=0):
        self.target_id = target_id
        self.detectores = []
        self._configurar_aruco()

    def _configurar_aruco(self):
        """Configura los diccionarios ArUco compatibles (4x4 y 7x7)."""
        diccionarios_ids = [
            ("DICT_4X4_50", cv2.aruco.DICT_4X4_50),
            ("DICT_7X7_50", cv2.aruco.DICT_7X7_50),
            ("DICT_6X6_250", cv2.aruco.DICT_6X6_250),
        ]

        for nombre, d_id in diccionarios_ids:
            try:
                # OpenCV >= 4.7.0
                d = cv2.aruco.getPredefinedDictionary(d_id)
                params = cv2.aruco.DetectorParameters()
                # Parámetros ajustados para detección rápida y robusta bajo luz variable
                params.adaptiveThreshWinSizeMin = 3
                params.adaptiveThreshWinSizeMax = 23
                params.adaptiveThreshWinSizeStep = 10
                detector = cv2.aruco.ArucoDetector(d, params)
                self.detectores.append((nombre, detector, "modern"))
            except AttributeError:
                # OpenCV < 4.7.0 (Legacy)
                d = cv2.aruco.Dictionary_get(d_id)
                params = cv2.aruco.DetectorParameters_create()
                self.detectores.append((nombre, (d, params), "legacy"))

    def detectar(self, frame):
        """
        Detecta marcadores ArUco en el frame usando todos los diccionarios configurados.
        Retorna lista de tuplas: (corners, id, nombre_diccionario)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resultados = []
        ids_vistos = set()

        for nombre_dict, detector_obj, modo in self.detectores:
            if modo == "modern":
                corners, ids, _ = detector_obj.detectMarkers(gray)
            else:
                d, params = detector_obj
                corners, ids, _ = cv2.aruco.detectMarkers(gray, d, parameters=params)

            if ids is not None and len(ids) > 0:
                for c, m_id in zip(corners, ids.ravel()):
                    # Evitar duplicados si dos diccionarios reportan el mismo id
                    clave = (int(m_id), int(c[0][0][0]))
                    if clave not in ids_vistos:
                        ids_vistos.add(clave)
                        resultados.append((c, int(m_id), nombre_dict))

        return resultados


def dibujar_hud(frame, resultados, fps, centro_visor):
    """Dibuja la interfaz visual HUD profesional en el frame."""
    h, w = frame.shape[:2]
    cx_visor, cy_visor = centro_visor

    # 1. Mira central del robot (Centro de la cámara)
    cv2.drawMarker(frame, (cx_visor, cy_visor), (180, 180, 180), cv2.MARKER_CROSS, 24, 1)
    cv2.circle(frame, (cx_visor, cy_visor), 35, (80, 80, 80), 1)

    estacion_encontrada = False

    for corners, m_id, dict_name in resultados:
        pts = corners.reshape((4, 2)).astype(int)

        # Centro del marcador
        mcx = int(pts[:, 0].mean())
        mcy = int(pts[:, 1].mean())

        # Ancho aparente en píxeles (promedio de los lados superior e inferior)
        ancho_px = (np.linalg.norm(pts[0] - pts[1]) + np.linalg.norm(pts[2] - pts[3])) / 2.0
        distancia_estimada_cm = (MARCADOR_ANCHO_REAL_CM * FOCAL_LENGTH_PX) / max(ancho_px, 1.0)

        # Desviación horizontal respecto al centro de la cámara
        delta_x = mcx - cx_visor

        # Es la estación de carga? (ID 0 o cualquier marcador en este test)
        es_estacion = (m_id == 0)
        color_caja = (0, 255, 0) if es_estacion else (0, 200, 255) # Verde brillante o Amarillo

        # 2. Dibujar contorno del marcador
        cv2.polylines(frame, [pts], isClosed=True, color=color_caja, thickness=3)

        # Puntos de las 4 esquinas
        for i, (px, py) in enumerate(pts):
            cv2.circle(frame, (px, py), 5, (0, 0, 255), -1)

        # 3. Punto central del marcador
        cv2.circle(frame, (mcx, mcy), 6, (0, 255, 0), -1)

        # 4. Línea guía desde centro de la cámara hasta el marcador
        color_linea = (0, 255, 0) if abs(delta_x) < 35 else (0, 165, 255)
        cv2.line(frame, (cx_visor, cy_visor), (mcx, mcy), color_linea, 2)

        # 5. Badge flotante sobre el marcador
        label_titulo = f"ESTACION DE CARGA [ID: {m_id}]" if es_estacion else f"MARCADOR ARUCO [ID: {m_id}]"
        label_sub = f"Dist: ~{distancia_estimada_cm:.1f}cm | Offset: {delta_x:+d}px"

        # Fondo del badge flotante
        badge_y = max(pts[:, 1].min() - 25, 30)
        badge_x = max(pts[:, 0].min() - 20, 10)
        cv2.rectangle(frame, (badge_x, badge_y - 25), (badge_x + 310, badge_y + 25), (20, 20, 20), -1)
        cv2.rectangle(frame, (badge_x, badge_y - 25), (badge_x + 310, badge_y + 25), color_caja, 2)

        cv2.putText(frame, label_titulo, (badge_x + 8, badge_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.putText(frame, label_sub, (badge_x + 8, badge_y + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, color_caja, 1)

        estacion_encontrada = True

    # 6. Barra Superior HUD
    cv2.rectangle(frame, (0, 0), (w, 55), (15, 15, 15), -1)
    cv2.line(frame, (0, 55), (w, 55), (0, 200, 100), 2)

    # Título principal
    cv2.putText(frame, "ORBIT BASE DE CARGA - TEST VISION MAC", (15, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    # Estado de Detección
    if estacion_encontrada:
        # Calcular dirección recomendada basada en el primer marcador
        mcx = int(resultados[0][0].reshape((4, 2)).mean(axis=0)[0])
        dx = mcx - cx_visor
        if abs(dx) < 35:
            estado_txt = "ESTACION EN EL CENTRO [ALINEADO]"
            estado_color = (0, 255, 0)
        elif dx < -35:
            estado_txt = f"<-- GIRAR IZQUIERDA (Offset: {dx}px)"
            estado_color = (0, 200, 255)
        else:
            estado_txt = f"GIRAR DERECHA --> (Offset: {dx}px)"
            estado_color = (0, 200, 255)
    else:
        estado_txt = "BUSCANDO ESTACION DE CARGA... (Muestra el codigo a la camara)"
        estado_color = (100, 100, 255)

    cv2.putText(frame, estado_txt, (15, 46),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, estado_color, 2)

    # FPS en la esquina derecha
    fps_txt = f"{fps:.1f} FPS"
    cv2.putText(frame, fps_txt, (w - 110, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)

    # 7. Barra Inferior de Información
    cv2.rectangle(frame, (0, h - 28), (w, h), (15, 15, 15), -1)
    ayuda_txt = "Controles: [Q] Salir | [S] Guardar Captura | [ESPACIO] Pausar"
    cv2.putText(frame, ayuda_txt, (15, h - 9),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    return frame


def crear_frame_simulacion(detector, t):
    """Genera un frame de simulación con el marcador moviéndose para probar sin cámara."""
    w, h = 640, 480
    frame = np.ones((h, w, 3), dtype=np.uint8) * 45

    # Cargar el marcador generado o marcador de seguimiento
    ruta_marcador = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estacion_carga_id0_4x4.png")
    if not os.path.isfile(ruta_marcador):
        ruta_marcador = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marcador_seguimiento_id0.png")

    if os.path.isfile(ruta_marcador):
        m_img = cv2.imread(ruta_marcador)
        if m_img is not None:
            # Tamaño oscilante (simula acercamiento y alejamiento)
            scale = 0.35 + 0.1 * np.sin(t * 1.5)
            nh = int(m_img.shape[0] * scale)
            nw = int(m_img.shape[1] * scale)
            m_res = cv2.resize(m_img, (nw, nh))

            # Posición oscilante (simula movimiento lateral)
            pos_x = int(w / 2 - nw / 2 + 120 * np.sin(t * 1.0))
            pos_y = int(h / 2 - nh / 2 + 40 * np.cos(t * 1.0))

            pos_x = max(10, min(pos_x, w - nw - 10))
            pos_y = max(60, min(pos_y, h - nh - 35))

            frame[pos_y:pos_y + nh, pos_x:pos_x + nw] = m_res

    # Marca de modo simulación
    cv2.putText(frame, "[MODO SIMULACION - SIN CAMARA FISICA]", (w - 380, h - 9),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    return frame


def main():
    parser = argparse.ArgumentParser(description="Detector Simple de Estación de Carga ArUco para Mac")
    parser.add_argument("--cam", type=int, default=0, help="Índice de la cámara web (defecto: 0)")
    parser.add_argument("--test", action="store_true", help="Forzar modo de prueba con marcador simulado")
    parser.add_argument("--img", type=str, default=None, help="Probar con una imagen fija")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🤖 ORBIT — DETECTOR DE ESTACIÓN DE CARGA ARUCO (TEST MAC)")
    print("=" * 70)
    print("Iniciando detector ArUco (DICT_4X4_50 / DICT_7X7_50)...")

    detector = DetectorEstacionCarga(target_id=0)

    # Modo de imagen fija
    if args.img:
        if not os.path.isfile(args.img):
            print(f"❌ Error: No se encontró la imagen en {args.img}")
            return
        frame = cv2.imread(args.img)
        resultados = detector.detectar(frame)
        h, w = frame.shape[:2]
        dibujar_hud(frame, resultados, 0.0, (w // 2, h // 2))
        print(f"✅ Detección completada: {len(resultados)} marcador(es) encontrado(s).")
        cv2.imshow("Estacion de Carga - Test Imagen", frame)
        print("Presiona cualquier tecla para cerrar la ventana.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    # Iniciar Cámara o Simulación
    cap = None
    usar_simulacion = args.test

    if not usar_simulacion:
        print(f"Intentando abrir cámara índice {args.cam} (FaceTime / USB)...")
        cap = cv2.VideoCapture(args.cam)
        
        # Si falla el índice especificado, probar con el índice 1 o 0
        if not cap.isOpened():
            alt_cam = 1 if args.cam == 0 else 0
            print(f"Intentando cámara alternativa (índice {alt_cam})...")
            cap = cv2.VideoCapture(alt_cam)

        if not cap.isOpened():
            print("\n⚠️ No se pudo acceder a la cámara web de macOS.")
            print("Posibles causas:")
            print("  1. Permiso de Cámara denegado en macOS para Terminal / VS Code:")
            print("     Ve a: Ajustes del Sistema -> Privacidad y Seguridad -> Cámara")
            print("     y asegúrate de que tu Terminal / VS Code tenga el permiso activado.")
            print("  2. La cámara está siendo usada por otra aplicación (FaceTime, Zoom, etc.)")
            print("\n💡 Activando automáticamente el [MODO SIMULACION] para que puedas probar el algoritmo...")
            usar_simulacion = True

    if not usar_simulacion and cap.isOpened():
        # Configurar resolución recomendada
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("✅ Cámara web conectada exitosamente.")

    print("\n----------------------------------------------------------------------")
    print("🟢 VENTANA INICIADA")
    print("Muestra el marcador ArUco a la cámara (impreso o en la pantalla de tu móvil).")
    print("Controles:")
    print("  • 'q' o ESC : Salir")
    print("  • 's'       : Guardar captura de pantalla en disco")
    print("  • ESPACIO   : Pausar / Continuar video")
    print("----------------------------------------------------------------------\n")

    nombre_ventana = "ORBIT - Detector Estacion de Carga (Mac)"
    cv2.namedWindow(nombre_ventana, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(nombre_ventana, 800, 600)

    t_inicio = time.time()
    frames_cont = 0
    fps = 30.0
    pausado = False
    ultimo_frame = None

    try:
        while True:
            t_ahora = time.time()

            if not pausado:
                if usar_simulacion:
                    frame = crear_frame_simulacion(detector, t_ahora - t_inicio)
                else:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        print("Error al leer frame de la cámara. Pasando a simulación...")
                        usar_simulacion = True
                        continue

                ultimo_frame = frame.copy()

                # Detección
                resultados = detector.detectar(frame)

                # Cálculo de FPS
                frames_cont += 1
                if frames_cont % 10 == 0:
                    dt = t_ahora - t_inicio
                    if dt > 0:
                        fps = 10.0 / dt
                    t_inicio = t_ahora

                # Dibujar Interfaz
                h, w = frame.shape[:2]
                dibujar_hud(frame, resultados, fps, (w // 2, h // 2))
                cv2.imshow(nombre_ventana, frame)

            key = cv2.waitKey(15) & 0xFF
            if key == ord('q') or key == 27: # 'q' o ESC
                print("\nCerrando detector...")
                break
            elif key == ord(' '): # Espacio: pausar
                pausado = not pausado
                print("⏸️ Pausado" if pausado else "▶️ Reanudado")
            elif key == ord('s') and ultimo_frame is not None: # 's': Guardar captura
                nombre_archivo = f"captura_estacion_{int(time.time())}.png"
                cv2.imwrite(nombre_archivo, ultimo_frame)
                print(f"📸 Captura guardada como: {nombre_archivo}")

    finally:
        if cap is not None and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()
        print("Detector finalizado correctamente.")


if __name__ == "__main__":
    main()
