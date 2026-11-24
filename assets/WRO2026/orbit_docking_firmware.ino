#include <Arduino.h>
#include <MeMegaPi.h>

// =====================================================================
// MOTORES DC (Configuración oficial MegaPi)
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
MeUltrasonicSensor sensorAtras(PORT_7); // Sensor Trasero (Puerto 7 - Para la base)

// =====================================================================
// CALIBRACIÓN DE VELOCIDAD Y TIEMPOS
// =====================================================================
const int VEL_AVANCE    = 45;   // Velocidad al acercarse a la base
const int VEL_RETROCESO = 35;   // Velocidad suave para acoplarse atrás
const int VEL_GIRO      = 55;   // Fuerza para giros y rotación
const int TIEMPO_180    = 1400; // ms para girar 180° exactos (Ajustar según piso)

unsigned long ultimoComando = 0;
char comandoActual = 'C';

void frenarRobot();
void avanzar(int vel);
void retroceder(int vel);
void girarIzquierda(int vel);
void girarDerecha(int vel);
void ejecutarGiro180();

void setup() {
  Serial.begin(115200);
  frenarRobot();
  Serial.println("MegaPi Docking Firmware Ready");
}

void loop() {
  // 1. Leer comandos desde la Raspberry Pi por Serial
  if (Serial.available() > 0) {
    char c = Serial.read();

    if (c == 'F') {
      comandoActual = 'F';
      avanzar(VEL_AVANCE);
      ultimoComando = millis();
    }
    else if (c == 'B') {
      comandoActual = 'B';
      retroceder(VEL_RETROCESO);
      ultimoComando = millis();
    }
    else if (c == 'L') {
      comandoActual = 'L';
      girarIzquierda(VEL_GIRO);
      ultimoComando = millis();
    }
    else if (c == 'R') {
      comandoActual = 'R';
      girarDerecha(VEL_GIRO);
      ultimoComando = millis();
    }
    else if (c == 'C') {
      comandoActual = 'C';
      frenarRobot();
      ultimoComando = millis();
    }
    else if (c == 'U') {
      // Giro automático de 180 grados
      comandoActual = 'C';
      ejecutarGiro180();
      Serial.println("180_DONE");
      ultimoComando = millis();
    }
    else if (c == 'S') {
      // Telemetría de sensores
      float dD = sensorDer.distanceCm();
      float dI = sensorIzq.distanceCm();
      float dA = sensorAtras.distanceCm();
      Serial.print("DIST:D="); Serial.print(dD);
      Serial.print(",I="); Serial.print(dI);
      Serial.print(",A="); Serial.println(dA);
    }
  }

  // 2. Seguridad durante el retroceso: el sensor trasero (Port 7) detecta el tope
  if (comandoActual == 'B') {
    float distAtras = sensorAtras.distanceCm();
    if (distAtras > 0.0 && distAtras <= 5.0) {
      // Llegó a menos de 5cm de los contactos de carga -> Frenar de inmediato
      frenarRobot();
      comandoActual = 'C';
      Serial.println("DOCK_CONTACT");
    }
  }

  // 3. Perro guardián de seguridad (Watchdog 600ms)
  // Si la Raspberry Pi se congela, frena los motores
  if (comandoActual != 'C' && (millis() - ultimoComando > 600)) {
    frenarRobot();
    comandoActual = 'C';
  }
}

// =====================================================================
// FUNCIONES DE CONTROL DE MOTORES
// =====================================================================

void avanzar(int vel) {
  motorFL.run(vel * DIR_FL);
  motorBL.run(vel * DIR_BL);
  motorFR.run(vel * DIR_FR);
  motorBR.run(vel * DIR_BR);
}

void retroceder(int vel) {
  motorFL.run(-vel * DIR_FL);
  motorBL.run(-vel * DIR_BL);
  motorFR.run(-vel * DIR_FR);
  motorBR.run(-vel * DIR_BR);
}

void girarIzquierda(int vel) {
  motorFL.run(-vel * DIR_FL);
  motorBL.run(-vel * DIR_BL);
  motorFR.run(vel * DIR_FR);
  motorBR.run(vel * DIR_BR);
}

void girarDerecha(int vel) {
  motorFL.run(vel * DIR_FL);
  motorBL.run(vel * DIR_BL);
  motorFR.run(-vel * DIR_FR);
  motorBR.run(-vel * DIR_BR);
}

void frenarRobot() {
  motorFL.run(0);
  motorFR.run(0);
  motorBL.run(0);
  motorBR.run(0);
}

void ejecutarGiro180() {
  frenarRobot();
  delay(150);
  // Rotación a la derecha para girar 180°
  motorFL.run(VEL_GIRO * DIR_FL);
  motorBL.run(VEL_GIRO * DIR_BL);
  motorFR.run(-VEL_GIRO * DIR_FR);
  motorBR.run(-VEL_GIRO * DIR_BR);
  delay(TIEMPO_180);
  frenarRobot();
  delay(200);
}
