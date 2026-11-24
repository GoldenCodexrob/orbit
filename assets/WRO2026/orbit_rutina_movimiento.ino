#include <Arduino.h>

// =====================================================================
// ORBIT WRO 2026 - AVANZAR DIRECTO (TODOS LOS MOTORES ADELANTE)
// =====================================================================

// Delantero Izquierdo (Front Left)
const int PWM_FL = 4;
const int IN1_FL = 5;
const int IN2_FL = 2;

// Trasero Izquierdo (Back Left)
const int PWM_BL = 6;
const int IN1_BL = 9;
const int IN2_BL = 3;

// Trasero Derecho (Back Right)
const int PWM_BR = 7;
const int IN1_BR = 8;
const int IN2_BR = 19;

// Delantero Derecho (Front Right)
const int PWM_FR = 11;
const int IN1_FR = 12;
const int IN2_FR = 18;

// Velocidad (de 0 a 255)
const int VELOCIDAD = 180;

void setup() {
  // Configuración de pines como salidas
  pinMode(PWM_FL, OUTPUT); pinMode(IN1_FL, OUTPUT); pinMode(IN2_FL, OUTPUT);
  pinMode(PWM_BL, OUTPUT); pinMode(IN1_BL, OUTPUT); pinMode(IN2_BL, OUTPUT);
  pinMode(PWM_BR, OUTPUT); pinMode(IN1_BR, OUTPUT); pinMode(IN2_BR, OUTPUT);
  pinMode(PWM_FR, OUTPUT); pinMode(IN1_FR, OUTPUT); pinMode(IN2_FR, OUTPUT);

  // Espera de seguridad de 2 segundos antes de arrancar
  delay(2000);

  // --- ENCENDER TODOS LOS MOTORES HACIA ADELANTE ---

  // 1. Delantero Izquierdo
  digitalWrite(IN1_FL, HIGH);
  digitalWrite(IN2_FL, LOW);
  analogWrite(PWM_FL, VELOCIDAD);

  // 2. Trasero Izquierdo
  digitalWrite(IN1_BL, HIGH);
  digitalWrite(IN2_BL, LOW);
  analogWrite(PWM_BL, VELOCIDAD);

  // 3. Trasero Derecho
  digitalWrite(IN1_BR, HIGH);
  digitalWrite(IN2_BR, LOW);
  analogWrite(PWM_BR, VELOCIDAD);

  // 4. Delantero Derecho
  digitalWrite(IN1_FR, HIGH);
  digitalWrite(IN2_FR, LOW);
  analogWrite(PWM_FR, VELOCIDAD);
}

void loop() {
  // Se mantienen encendidos hacia adelante todo el tiempo
}
