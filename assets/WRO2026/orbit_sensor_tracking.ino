#include <Arduino.h>
#include <MeMegaPi.h>

// =====================================================================
// MOTORES DC (Configuración MegaPi)
// =====================================================================
MeMegaPiDCMotor motorFL(PORT1B);  // Delantero Izquierdo
MeMegaPiDCMotor motorFR(PORT2B);  // Delantero Derecho
MeMegaPiDCMotor motorBL(PORT3B);  // Trasero Izquierdo
MeMegaPiDCMotor motorBR(PORT4B);  // Trasero Derecho

// Polaridades físicas para que avance recto
const int DIR_FL = 1;
const int DIR_BL = 1;
const int DIR_FR = -1;  
const int DIR_BR = -1;  

// =====================================================================
// SENSORES ULTRASÓNICOS (Puertos RJ25)
// =====================================================================
MeUltrasonicSensor sensorDer(PORT_5);   // Sensor Derecho (Puerto 5)
MeUltrasonicSensor sensorIzq(PORT_6);   // Sensor Izquierdo (Puerto 6)
MeUltrasonicSensor sensorAtras(PORT_7); // Sensor Trasero (Puerto 7)

// =====================================================================
// CALIBRACIÓN DE MOVIMIENTO
// =====================================================================
// Velocidades (0 - 255): Orbit es pesado con 4 ruedas de goma, necesita fuerza
const int VEL_GIRO    = 200;   // Potencia fuerte para derrapar las 4 ruedas en el piso
const int VEL_AVANCE  = 180;   // Potencia para avanzar con buena velocidad

// Tiempos en milisegundos (ms)
const int TIEMPO_GIRO_90  = 2200;  // 2.2 segundos para girar los 90 grados completos
const int TIEMPO_GIRO_180 = 4200;  // 4.2 segundos para girar 180 grados completos
const int TIEMPO_AVANCE   = 3000;  // 3.0 segundos para avanzar hacia donde detectó el objeto

// Distancia en centímetros para reaccionar (Ej. 40 cm)
const float DIST_MAX_DETECCION = 40.0;
const float DIST_MIN_SEGURIDAD = 8.0;   // Si está a menos de 8cm no avanza más para no chocar

void frenarRobot();
void avanzar(int vel);
void girar90Izquierda();
void girar90Derecha();
void girar180();

void setup() {
  Serial.begin(115200);
  frenarRobot();
  delay(1500); // Pausa de 1.5 segundos al encender
  Serial.println("Orbit Autónomo por Sensores Iniciado");
}

void loop() {
  // 1. Leer los tres sensores en centímetros
  float dDer   = sensorDer.distanceCm();
  float dIzq   = sensorIzq.distanceCm();
  float dAtras = sensorAtras.distanceCm();

  // Imprimir lecturas para monitoreo
  Serial.print("Izq: "); Serial.print(dIzq);
  Serial.print(" | Der: "); Serial.print(dDer);
  Serial.print(" | Atras: "); Serial.println(dAtras);

  // 2. Determinar si algún sensor detectó algo dentro del rango
  bool hayIzq   = (dIzq > DIST_MIN_SEGURIDAD && dIzq <= DIST_MAX_DETECCION);
  bool hayDer   = (dDer > DIST_MIN_SEGURIDAD && dDer <= DIST_MAX_DETECCION);
  bool hayAtras = (dAtras > DIST_MIN_SEGURIDAD && dAtras <= DIST_MAX_DETECCION);

  // 3. Reaccionar hacia la posición del objetivo

  // CASO 1: DETECCIÓN A LA IZQUIERDA
  // Gira 90° a la izquierda y avanza hacia allá
  if (hayIzq && (!hayDer || dIzq < dDer)) {
    Serial.println("-> Objetivo a la IZQUIERDA: Girando 90° Izq y avanzando...");
    frenarRobot();
    delay(150);
    girar90Izquierda();
    delay(150);
    avanzar(VEL_AVANCE);
    delay(TIEMPO_AVANCE);
    frenarRobot();
    delay(800); // Pausa para estabilizarse antes de volver a escanear
  }

  // CASO 2: DETECCIÓN A LA DERECHA
  // Gira 90° a la derecha y avanza hacia allá
  else if (hayDer) {
    Serial.println("-> Objetivo a la DERECHA: Girando 90° Der y avanzando...");
    frenarRobot();
    delay(150);
    girar90Derecha();
    delay(150);
    avanzar(VEL_AVANCE);
    delay(TIEMPO_AVANCE);
    frenarRobot();
    delay(800);
  }

  // CASO 3: DETECCIÓN ATRÁS
  // Gira 180° para quedar de frente al objetivo y avanza hacia allá
  else if (hayAtras) {
    Serial.println("-> Objetivo ATRÁS: Girando 180° y avanzando...");
    frenarRobot();
    delay(150);
    girar180();
    delay(150);
    avanzar(VEL_AVANCE);
    delay(TIEMPO_AVANCE);
    frenarRobot();
    delay(800);
  }

  // Si no detecta nada, permanece quieto en espera
  else {
    frenarRobot();
  }

  delay(60); // Pequeña pausa de muestreo
}

// =====================================================================
// FUNCIONES DE CONTROL DE MOVIMIENTO
// =====================================================================

void avanzar(int vel) {
  motorFL.run(vel * DIR_FL);
  motorBL.run(vel * DIR_BL);
  motorFR.run(vel * DIR_FR);
  motorBR.run(vel * DIR_BR);
}

void frenarRobot() {
  motorFL.stop();
  motorFR.stop();
  motorBL.stop();
  motorBR.stop();
  motorFL.run(0);
  motorFR.run(0);
  motorBL.run(0);
  motorBR.run(0);
}

void girar90Izquierda() {
  motorFL.run(-VEL_GIRO * DIR_FL);
  motorBL.run(-VEL_GIRO * DIR_BL);
  motorFR.run(VEL_GIRO * DIR_FR);
  motorBR.run(VEL_GIRO * DIR_BR);
  delay(TIEMPO_GIRO_90);
  frenarRobot();
}

void girar90Derecha() {
  motorFL.run(VEL_GIRO * DIR_FL);
  motorBL.run(VEL_GIRO * DIR_BL);
  motorFR.run(-VEL_GIRO * DIR_FR);
  motorBR.run(-VEL_GIRO * DIR_BR);
  delay(TIEMPO_GIRO_90);
  frenarRobot();
}

void girar180() {
  motorFL.run(VEL_GIRO * DIR_FL);
  motorBL.run(VEL_GIRO * DIR_BL);
  motorFR.run(-VEL_GIRO * DIR_FR);
  motorBR.run(-VEL_GIRO * DIR_BR);
  delay(TIEMPO_GIRO_180);
  frenarRobot();
}
