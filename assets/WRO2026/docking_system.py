"""
=============================================================================
ORBIT V4.0 — SISTEMA DE AUTO-CARGA CON MARCADOR ARUCO (DOCKING SYSTEM)
=============================================================================
Flujo de Funcionamiento:
1. ESPERA DE ENTRADA: El usuario presiona ENTER o la tecla 'D' para iniciar el docking.
2. BÚSQUEDA 360°: Orbit realiza un giro sobre su propio eje buscando el marcador ArUco ID 0.
3. APROXIMACIÓN: Al detectar el marcador, se alinea con el centro y avanza hacia él.
4. GIRO 180°: Cuando está suficientemente cerca de la estación, frena y gira 180°.
5. RETROCESO Y ACOPLE: Retrocede suavemente para acoplar los contactos traseros de carga.
6. CARGA: Frena y queda conectado a la base.
=============================================================================
"""

import cv2
import time
import serial
import math
import sys

# ── Configuración de Conexión Serial (MegaPi) ─────────────────────
ser = None
for port in ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0"]:
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
        print(f"✅ Conectado a MegaPi en {port}")
        break
    except Exception:
        pass

if not ser:
    print("⚠️ Modo simulación activo (MegaPi no detectado, comandos se imprimirán en consola)")

def send_motor(cmd: str):
    """Envía un comando de motor a la MegaPi."""
    if ser:
        try:
            ser.write(f"{cmd}\n".encode())
        except Exception:
            pass
    # Descomentar para depurar en consola:
    # print(f"[MOTOR] -> {cmd}")

# ── Configuración de Visión ArUco (DICT_7X7_50, ID 0) ────────────
try:
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_7X7_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    def detectar_aruco(img):
        return detector.detectMarkers(img)
except AttributeError:
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_7X7_50)
    parameters = cv2.aruco.DetectorParameters_create()
    def detectar_aruco(img):
        return cv2.aruco.detectMarkers(img, aruco_dict, parameters=parameters)

# ── Auto-Detección de Cámara ─────────────────────────────────────
cap = None
for idx in [0, 1, 2, 3, 4, 5, 6]:
    temp = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    if temp.isOpened():
        ret, _ = temp.read()
        if ret:
            print(f"✅ Cámara encontrada y abierta en el índice {idx}")
            cap = temp
            break
    temp.release()

if cap is None:
    print("❌ ERROR: No se pudo abrir ninguna cámara USB. Revisa la conexión.")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ── Parámetros de Calibración ─────────────────────────────────────
ID_BASE = 0                 # ID del marcador ArUco de la base
ZONA_MUERTA = 40            # Tolerancia de centrado (píxeles)
ANCHO_CERCA_PX = 230        # Tamaño en píxeles del marcador cuando está listo para girar 180°
TIEMPO_MAX_GIRO_360 = 5.0   # Segundos máximos para una vuelta completa de 360°
TIEMPO_RETROCESO = 3.0      # Segundos de marcha atrás para acoplarse si no responde sensor trasero

# Estados de la Máquina de Estados
ESTADO_ESPERA = "ESPERANDO_ORDEN"
ESTADO_BUSQUEDA_360 = "BUSCANDO_360"
ESTADO_APROXIMACION = "APROXIMANDO"
ESTADO_GIRO_180 = "GIRANDO_180"
ESTADO_RETROCESO = "RETROCEDIENDO_BASE"
ESTADO_CARGANDO = "CARGANDO_ACOPLADO"

estado_actual = ESTADO_ESPERA
inicio_estado = time.time()

print("\n" + "="*60)
print("SISTEMA DE CARGA AUTÓNOMA ORBIT INICIADO")
print("Presiona la tecla 'D' o ENTER en la consola para iniciar el Docking.")
print("Presiona 'Q' para salir.")
print("="*60 + "\n")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = detectar_aruco(gray)

        marcador_detectado = False
        offset = 0
        ancho_aruco = 0

        # Procesar marcador ArUco
        if ids is not None and ID_BASE in ids:
            marcador_detectado = True
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            idx_base = list(ids.flatten()).index(ID_BASE)
            esquinas = corners[idx_base][0]

            # Calcular centro y ancho del marcador
            c_x = int(sum([p[0] for p in esquinas]) / 4)
            c_y = int(sum([p[1] for p in esquinas]) / 4)
            ancho_aruco = int(math.hypot(esquinas[0][0] - esquinas[1][0], esquinas[0][1] - esquinas[1][1]))

            centro_pantalla = frame.shape[1] // 2
            offset = c_x - centro_pantalla

            # Dibujar mira de puntería
            cv2.circle(frame, (c_x, c_y), 8, (0, 255, 0), -1)
            cv2.line(frame, (centro_pantalla, 0), (centro_pantalla, frame.shape[0]), (255, 255, 0), 1)

        # ── LÓGICA DE LA MÁQUINA DE ESTADOS ──────────────────────

        # 1. ESPERANDO ORDEN DEL USUARIO
        if estado_actual == ESTADO_ESPERA:
            send_motor("C")
            # Texto en pantalla
            cv2.putText(frame, "PRESIONA 'D' PARA INICIAR DOCKING", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # 2. BÚSQUEDA EN 360° (Giro continuo hasta encontrar el marcador)
        elif estado_actual == ESTADO_BUSQUEDA_360:
            if marcador_detectado:
                print("🎯 ¡Marcador de base localizado! Frenando y pasando a aproximación.")
                send_motor("C")
                estado_actual = ESTADO_APROXIMACION
                inicio_estado = time.time()
            else:
                send_motor("R") # Giro sobre su propio eje buscando
                cv2.putText(frame, "BUSCANDO BASE EN 360 GRADOS...", (30, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

                # Si completa una vuelta entera y no lo ve
                if time.time() - inicio_estado > TIEMPO_MAX_GIRO_360:
                    print("⚠️ Giro 360° completado sin ver el marcador. Pausando búsqueda.")
                    send_motor("C")
                    estado_actual = ESTADO_ESPERA

        # 3. APROXIMACIÓN (Avanzar de frente centrándose)
        elif estado_actual == ESTADO_APROXIMACION:
            if not marcador_detectado:
                print("Perdí el marcador momentáneamente, buscando...")
                send_motor("C")
            else:
                # Comprobar si ya está suficientemente cerca
                if ancho_aruco >= ANCHO_CERCA_PX:
                    print(f"📏 Distancia alcanzada (Ancho {ancho_aruco} px). Preparando giro 180°.")
                    send_motor("C")
                    time.sleep(0.3)
                    estado_actual = ESTADO_GIRO_180
                    inicio_estado = time.time()
                elif offset > ZONA_MUERTA:
                    # Marcador a la derecha -> corregir
                    send_motor("R")
                elif offset < -ZONA_MUERTA:
                    # Marcador a la izquierda -> corregir
                    send_motor("L")
                else:
                    # Marcador centrado -> avanzar
                    send_motor("F")

            cv2.putText(frame, f"APROXIMANDO: Ancho {ancho_aruco}/{ANCHO_CERCA_PX} px", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 4. GIRO DE 180° (U-Turn)
        elif estado_actual == ESTADO_GIRO_180:
            cv2.putText(frame, "GIRANDO 180 GRADOS PARA ACOPLE TRASERO...", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            # Enviar comando 'U' de giro 180 a la MegaPi
            send_motor("U")
            time.sleep(1.6) # Esperar a que la MegaPi termine el giro físico
            send_motor("C")
            print("🔄 Giro de 180° completado. Espalda mirando a la estación de carga.")
            estado_actual = ESTADO_RETROCESO
            inicio_estado = time.time()

        # 5. RETROCEDER HACIA LA BASE
        elif estado_actual == ESTADO_RETROCESO:
            cv2.putText(frame, "RETROCEDIENDO HACIA LA ESTACION...", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            send_motor("B") # Retroceder marcha atrás

            # Leer si la MegaPi avisa que el sensor trasero tocó tope
            if ser and ser.in_waiting > 0:
                linea = ser.readline().decode(errors="ignore").strip()
                if "DOCK_CONTACT" in linea:
                    print("⚡ ¡Contacto físico detectado por sensor trasero!")
                    send_motor("C")
                    estado_actual = ESTADO_CARGANDO

            # O por límite de tiempo de retroceso
            if time.time() - inicio_estado > TIEMPO_RETROCESO:
                print("⚡ Tiempo de acople completado.")
                send_motor("C")
                estado_actual = ESTADO_CARGANDO

        # 6. CARGANDO Y ACOPLADO
        elif estado_actual == ESTADO_CARGANDO:
            send_motor("C")
            cv2.putText(frame, "⚡ ORBIT CONECTADO A LA BASE DE CARGA ⚡", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 3)

        # Mostrar HUD con estado actual
        cv2.putText(frame, f"ESTADO: {estado_actual}", (30, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow("Orbit Auto-Docking System", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('d') and estado_actual == ESTADO_ESPERA:
            print("🚀 Iniciando maniobra de carga autónoma...")
            estado_actual = ESTADO_BUSQUEDA_360
            inicio_estado = time.time()
        elif key == ord('r'):
            # Resetear a espera
            print("Reiniciando a modo espera.")
            estado_actual = ESTADO_ESPERA
            send_motor("C")

except KeyboardInterrupt:
    pass

send_motor("C")
cap.release()
cv2.destroyAllWindows()
print("Sistema de Docking finalizado.")
