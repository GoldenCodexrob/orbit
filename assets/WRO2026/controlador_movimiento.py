"""
=============================================================================
🤖 CONTROLADOR_MOVIMIENTO.PY — Driver Serial MegaPi para Orbit V4.0
=============================================================================
Control de tracción y sensores MegaPi según protocolo de ORBITFINAL.ino:
- MOVE,<sentido>,<vel>: 'W' (adelante con PID giroscopio), 'S' (atrás),
  'L' (giro izquierda), 'R' (giro derecha), 'X' (detener motores).
- ANGLE,<grados>,<vel>: Giro en lazo cerrado por giroscopio (-180° a +180°).
  Espera ACK:GIRO_COMPLETADO al finalizar.
- LIGHTS,ON / LIGHTS,OFF: Conmutación de relé de luces.
- Telemetría periódica no bloqueante: T,z,cor,x,v1,v2,v3,distL,distR
=============================================================================
"""

import os
import sys
import time
import glob
import threading
import serial

class ControladorMegaPi:
    def __init__(self, puerto=None, baudios=115200, timeout=0.1, simulado=False):
        self.puerto = puerto
        self.baudios = baudios
        self.timeout = timeout
        self.ser = None
        self.conectado = False
        self.simulado = simulado
        
        self._lock = threading.Lock()
        self._running = False
        self._hilo_lectura = None
        
        # Estado de telemetría más reciente
        self.telemetria = {
            "angulo_z": 0.0,
            "correccion": 0.0,
            "angulo_x": 0.0,
            "v1": 0.0,
            "v2": 0.0,
            "v3": 0.0,
            "dist_l": 9999,
            "dist_r": 9999,
            "ultimo_update": 0.0
        }
        
        # Evento para giros controlados
        self.evento_giro = threading.Event()
        self.ultimo_estado = 'X'
        self.ultima_vel = 0
        
        if not self.simulado:
            self.conectar()
        else:
            print("🔄 [MegaPi] Inicializado directamente en MODO SIMULADOR.")

    def _buscar_puerto_automatico(self):
        """Detecta automáticamente el puerto de conexión del MegaPi."""
        if self.puerto and os.path.exists(self.puerto):
            return self.puerto
            
        candidatos = []
        if sys.platform.startswith("linux"):
            candidatos = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        elif sys.platform == "darwin":
            candidatos = glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.usbmodem*")
        elif sys.platform == "win32":
            candidatos = [f"COM{i}" for i in range(1, 21)]
            
        for c in candidatos:
            try:
                s = serial.Serial(c, self.baudios, timeout=0.5)
                s.close()
                return c
            except Exception:
                continue
        return None

    def conectar(self):
        puerto_efectivo = self._buscar_puerto_automatico()
        if not puerto_efectivo:
            print("⚠️ [MegaPi] No se detectó puerto serial físico. Operando en MODO SIMULADO.")
            self.simulado = True
            self.conectado = False
            return False

        try:
            print(f"🔌 [MegaPi] Conectando a {puerto_efectivo} a {self.baudios} baudios...")
            self.ser = serial.Serial(puerto_efectivo, self.baudios, timeout=self.timeout)
            time.sleep(1.8) # Esperar reinicio de MegaPi tras apertura serial
            self.puerto = puerto_efectivo
            self.conectado = True
            self.simulado = False
            
            # Detener motores inicialmente
            self.detener()
            
            # Activar corroboraciones y evasión autónoma ToF en MegaPi ("OK ToF")
            self.activar_tof()

            # Iniciar hilo de lectura no bloqueante
            self._running = True
            self._hilo_lectura = threading.Thread(target=self._bucle_lectura, daemon=True)
            self._hilo_lectura.start()
            
            print(f"✅ [MegaPi] Conexión establecida exitosamente en {puerto_efectivo}")
            return True
        except Exception as e:
            print(f"⚠️ [MegaPi] Error al conectar ({e}). Operando en MODO SIMULADO.")
            self.simulado = True
            self.conectado = False
            return False

    def _bucle_lectura(self):
        """Lee telemetría y respuestas ACK en segundo plano."""
        buffer = ""
        while self._running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    raw = self.ser.read(self.ser.in_waiting).decode("utf-8", errors="ignore")
                    buffer += raw
                    while "\n" in buffer:
                        linea, buffer = buffer.split("\n", 1)
                        linea = linea.strip()
                        if not linea:
                            continue
                            
                        # Procesar telemetría
                        if linea.startswith("T,"):
                            partes = linea.split(",")
                            if len(partes) >= 9:
                                try:
                                    self.telemetria["angulo_z"] = float(partes[1])
                                    self.telemetria["correccion"] = float(partes[2])
                                    self.telemetria["angulo_x"] = float(partes[3])
                                    self.telemetria["v1"] = float(partes[4])
                                    self.telemetria["v2"] = float(partes[5])
                                    self.telemetria["v3"] = float(partes[6])
                                    self.telemetria["dist_l"] = int(partes[7])
                                    self.telemetria["dist_r"] = int(partes[8])
                                    self.telemetria["ultimo_update"] = time.time()
                                except (ValueError, IndexError):
                                    pass
                        elif "ACK:GIRO_COMPLETADO" in linea:
                            self.evento_giro.set()
                        elif "ACK:OK_TOF" in linea:
                            print("✅ [MegaPi] Confirmación recibida: ToF activado (ACK:OK_TOF)")
                        elif "ACK:STOP_TOF" in linea:
                            print("⏸️ [MegaPi] Confirmación recibida: ToF pausado (ACK:STOP_TOF)")
                        elif linea.startswith("DEBUG:") or linea.startswith("ACK:"):
                            pass
                else:
                    time.sleep(0.01)
            except Exception:
                time.sleep(0.05)

    def enviar_comando(self, cmd: str):
        cmd = cmd.strip()
        if self.simulado:
            return
        if self.conectado and self.ser and self.ser.is_open:
            try:
                with self._lock:
                    self.ser.write(f"{cmd}\n".encode("utf-8"))
            except Exception as e:
                print(f"⚠️ [MegaPi] Error enviando comando '{cmd}': {e}")

    def mover(self, sentido: str, vel: int = 120):
        """
        Envía comando de movimiento continuo.
        sentido: 'W' (adelante), 'S' (atrás), 'L' (izquierda), 'R' (derecha), 'X' (parar)
        vel: 0-255
        """
        sentido = sentido.upper()
        if sentido not in ['W', 'S', 'L', 'R', 'X']:
            sentido = 'X'
        vel = max(0, min(255, int(vel)))
        
        # Evitar inundar el bus serial con comandos repetidos innecesarios
        if sentido == self.ultimo_estado and vel == self.ultima_vel and sentido != 'X':
            return
            
        self.ultimo_estado = sentido
        self.ultima_vel = vel
        self.enviar_comando(f"MOVE,{sentido},{vel}")

    def detener(self):
        """Detiene de inmediato todos los motores."""
        self.ultimo_estado = 'X'
        self.ultima_vel = 0
        self.enviar_comando("MOVE,X,0")

    def girar_angulo(self, grados: float, vel: int = 120, timeout: float = 6.0, callback_cancelar=None):
        """
        Giro en lazo cerrado por giroscopio ejecutado por el MegaPi.
        grados: Positivo = Derecha, Negativo = Izquierda.
        callback_cancelar: función opcional que retorna True si se debe abortar el giro
                           (por ejemplo, si la cámara detecta una cara).
        """
        vel = max(60, min(255, int(vel)))
        grados = round(float(grados), 1)
        
        if self.simulado:
            print(f"🔄 [Simulador MegaPi] Girando {grados}° a vel {vel}...")
            t_fin = time.time() + min(timeout, abs(grados) / 45.0)
            while time.time() < t_fin:
                if callback_cancelar and callback_cancelar():
                    print("🛑 [Simulador MegaPi] Giro interrumpido.")
                    return False
                time.sleep(0.05)
            print("✅ [Simulador MegaPi] Giro completado.")
            return True

        self.evento_giro.clear()
        self.enviar_comando(f"ANGLE,{grados},{vel}")
        
        t0 = time.time()
        while not self.evento_giro.is_set():
            if callback_cancelar and callback_cancelar():
                self.detener()
                print("🛑 [MegaPi] Giro abortado por detección temprana.")
                return False
            if time.time() - t0 > timeout:
                self.detener()
                print("⏱️ [MegaPi] Timeout en giro angular.")
                return False
            time.sleep(0.02)
            
        return True

    def activar_tof(self):
        """Habilita las correcciones y reacciones autónomas de los sensores ToF en MegaPi."""
        if self.simulado:
            print("📡 [Simulador MegaPi] Comando 'OK ToF' simulado -> ToF activado.")
            return
        self.enviar_comando("OK ToF")
        print("📡 [MegaPi] Comando 'OK ToF' enviado -> Correcciones ToF habilitadas.")

    def desactivar_tof(self):
        """Pausa las correcciones autónomas de los sensores ToF en MegaPi."""
        if self.simulado:
            print("📡 [Simulador MegaPi] Comando 'STOP ToF' simulado -> ToF pausado.")
            return
        self.enviar_comando("STOP ToF")
        print("📡 [MegaPi] Comando 'STOP ToF' enviado -> Correcciones ToF pausadas.")

    def luces(self, encender: bool = True):
        cmd = "LIGHTS,ON" if encender else "LIGHTS,OFF"
        self.enviar_comando(cmd)

    def cerrar(self):
        self._running = False
        self.desactivar_tof()
        self.detener()
        time.sleep(0.05)
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.conectado = False
