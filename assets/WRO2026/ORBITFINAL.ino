#include "MeMegaPi.h"
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_VL53L0X.h>

// ==========================================
// CONFIGURACIÓN DE SENSORES Y PINES
// ==========================================
const int xshut_L = A2;
const int xshut_R = A3;
const int pinRele = A5;       
const int pinReleLuces = A4;  

Adafruit_VL53L0X loxL = Adafruit_VL53L0X();
Adafruit_VL53L0X loxR = Adafruit_VL53L0X();
MeGyro gyro;
Adafruit_ADS1115 ads;

// Motores (4 Drivers BTS7960)
const int M1_RPWM = 11; const int M1_LPWM = 12; 
const int M2_RPWM = 6;  const int M2_LPWM = 9; 
const int M3_RPWM = 7;  const int M3_LPWM = 8; 
const int M4_RPWM = 4;  const int M4_LPWM = 5; 

// ==========================================
// PARÁMETROS DEL CONTROLADOR
// ==========================================
float alpha = 0.2;           
float filteredAngleZ = 0.0;  
float Kp = 1.2;              
float Kd = 0.4;              

float targetAngle = 0.0;     
float lastError = 0.0;       
float deadzone = 1.5;        
float correction = 0.0;      

// Estados de control del robot
char estadoMovimiento = 'X'; 
int velocidadActual = 200; 
bool lucesManual = false;

// Variables para giros controlados
float anguloInicioGiro = 0.0;
float gradosGiroObjetivo = 0.0;

// ADS1115 Baterías
const float R1 = 100000.0; 
const float R2 = 50000.0;  
const float FACTOR_DIVISOR = (R1 + R2) / R2; 

unsigned long lastTime = 0;
unsigned long lastTelemetryTime = 0; 

// Buffers no bloqueantes para serial
String serialBufferPi = "";
String serialBufferBt = "";

// ==========================================
// SETUP
// ==========================================
void setup() {
    pinMode(pinRele, OUTPUT);
    pinMode(pinReleLuces, OUTPUT);
    pinMode(xshut_L, OUTPUT);
    pinMode(xshut_R, OUTPUT);
    
    pinMode(M1_RPWM, OUTPUT); pinMode(M1_LPWM, OUTPUT);
    pinMode(M2_RPWM, OUTPUT); pinMode(M2_LPWM, OUTPUT);
    pinMode(M3_RPWM, OUTPUT); pinMode(M3_LPWM, OUTPUT);
    pinMode(M4_RPWM, OUTPUT); pinMode(M4_LPWM, OUTPUT);

    detener(); 
    digitalWrite(pinRele, LOW); 
    digitalWrite(pinReleLuces, LOW); 
    
    // ⚠️ NOTA: Si tu Raspberry Pi está conectada a los pines TX1/RX1 (18/19), 
    // cambia 'Serial' por 'Serial1' en todo el código. Si es por USB, deja 'Serial'.
    Serial.begin(115200);   
    Serial3.begin(115200);  // Bluetooth para debugging y comandos
    
    delay(1000); 

    // Inicializar sensores ToF con cambio de dirección I2C
    digitalWrite(xshut_L, LOW);
    digitalWrite(xshut_R, LOW);
    delay(10);
    
    digitalWrite(xshut_L, HIGH); 
    delay(10); 
    loxL.begin(0x30); 
    loxL.startRangeContinuous();
    
    digitalWrite(xshut_R, HIGH); 
    delay(10); 
    loxR.begin(0x31); 
    loxR.startRangeContinuous();

    gyro.begin();
    delay(500);

    if (ads.begin()) {
        ads.setGain(GAIN_ONE); 
    }

    digitalWrite(pinRele, HIGH); 
    lastTime = millis();
    lastTelemetryTime = millis();
    
    Serial3.println("DEBUG: MegaPi Iniciado y Listo");
}

// ==========================================
// LOOP PRINCIPAL
// ==========================================
void loop() {
    unsigned long currentTime = millis();
    float dt = (currentTime - lastTime) / 1000.0;

    // --- 1. LECTURA NO BLOQUEANTE RASPBERRY PI (Serial) ---
    while (Serial.available() > 0) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            if (serialBufferPi.length() > 0) {
                procesarComando(serialBufferPi, Serial);
                serialBufferPi = "";
            }
        } else {
            serialBufferPi += c;
            if (serialBufferPi.length() > 64) serialBufferPi = ""; // Prevención de desbordamiento
        }
    }

    // --- 2. LECTURA NO BLOQUEANTE BLUETOOTH (Serial3) ---
    while (Serial3.available() > 0) {
        char c = Serial3.read();
        if (c == '\n' || c == '\r') {
            if (serialBufferBt.length() > 0) {
                procesarComando(serialBufferBt, Serial3); // Reutiliza el mismo parser
                serialBufferBt = "";
            }
        } else {
            serialBufferBt += c;
            if (serialBufferBt.length() > 64) serialBufferBt = "";
        }
    }

    // --- 3. LAZO DE CONTROL Y MOVIMIENTO (Cada 10ms) ---
    if (currentTime - lastTime >= 10) {
        lastTime = currentTime;
        gyro.update();
        
        float rawAngleZ = gyro.getAngleZ();
        filteredAngleZ = (alpha * rawAngleZ) + ((1.0 - alpha) * filteredAngleZ);

        if (estadoMovimiento == 'W' || estadoMovimiento == 'S') {
            float error = targetAngle - filteredAngleZ;
            correction = 0.0;
            if (abs(error) > deadzone) {
                float derivative = (error - lastError) / dt;
                correction = (Kp * error) + (Kd * derivative);
            }
            lastError = error;

            int speedLeft = 0, speedRight = 0;
            bool esAdelante = (estadoMovimiento == 'W');

            if (esAdelante) {
                speedLeft  = constrain(velocidadActual + correction, 0, 255);
                speedRight = constrain(velocidadActual - correction, 0, 255);
            } else {
                speedLeft  = constrain(velocidadActual - correction, 0, 255);
                speedRight = constrain(velocidadActual + correction, 0, 255);
            }

            moverMotorDireccion(M1_RPWM, M1_LPWM, speedLeft, esAdelante);
            moverMotorDireccion(M2_RPWM, M2_LPWM, speedLeft, esAdelante);
            moverMotorDireccion(M3_RPWM, M3_LPWM, speedRight, esAdelante);
            moverMotorDireccion(M4_RPWM, M4_LPWM, speedRight, esAdelante);
        }
        else if (estadoMovimiento == 'L') {
            moverMotorDireccion(M1_RPWM, M1_LPWM, velocidadActual, false);
            moverMotorDireccion(M2_RPWM, M2_LPWM, velocidadActual, false);
            moverMotorDireccion(M3_RPWM, M3_LPWM, velocidadActual, true);
            moverMotorDireccion(M4_RPWM, M4_LPWM, velocidadActual, true);
        }
        else if (estadoMovimiento == 'R') {
            moverMotorDireccion(M1_RPWM, M1_LPWM, velocidadActual, true);
            moverMotorDireccion(M2_RPWM, M2_LPWM, velocidadActual, true);
            moverMotorDireccion(M3_RPWM, M3_LPWM, velocidadActual, false);
            moverMotorDireccion(M4_RPWM, M4_LPWM, velocidadActual, false);
        }
        else if (estadoMovimiento == 'G') {
            float desplazamientoGiro = filteredAngleZ - anguloInicioGiro;
            // Nota: Asumimos giros menores a 180° para evitar complejidad de wrap-around
            if (abs(desplazamientoGiro) < abs(gradosGiroObjetivo)) {
                bool girarDerecha = (gradosGiroObjetivo > 0);
                moverMotorDireccion(M1_RPWM, M1_LPWM, velocidadActual, !girarDerecha);
                moverMotorDireccion(M2_RPWM, M2_LPWM, velocidadActual, !girarDerecha);
                moverMotorDireccion(M3_RPWM, M3_LPWM, velocidadActual, girarDerecha);
                moverMotorDireccion(M4_RPWM, M4_LPWM, velocidadActual, girarDerecha);
            } else {
                detener();
                targetAngle = filteredAngleZ; 
                estadoMovimiento = 'X';
                if (!lucesManual) digitalWrite(pinReleLuces, LOW);
                Serial.println("ACK:GIRO_COMPLETADO");
                Serial3.println("DEBUG: Giro completado");
            }
        }
    }

    // --- 4. TELEMETRÍA PERIÓDICA (Cada 200ms) ---
    if (currentTime - lastTelemetryTime >= 200) {
        lastTelemetryTime = currentTime;
        enviarTelemetria();
    }
}

// ==========================================
// FUNCIONES AUXILIARES
// ==========================================
void enviarTelemetria() {
    gyro.update();
    float v1 = obtenerVoltaje(0);
    float v2 = obtenerVoltaje(1);
    float v3 = obtenerVoltaje(2);
    
    uint16_t dL = loxL.isRangeComplete() ? loxL.readRange() : 9999;
    uint16_t dR = loxR.isRangeComplete() ? loxR.readRange() : 9999;

    // Formato CSV robusto: T,z,cor,x,v1,v2,v3,distL,distR
    Serial.print("T,");
    Serial.print(filteredAngleZ, 2); Serial.print(",");
    Serial.print(correction, 2); Serial.print(",");
    Serial.print(gyro.getAngleX(), 2); Serial.print(",");
    Serial.print(v1, 2); Serial.print(",");
    Serial.print(v2, 2); Serial.print(",");
    Serial.print(v3, 2); Serial.print(",");
    Serial.print(dL); Serial.print(",");
    Serial.println(dR);

    // Debugging resumido por Bluetooth
    Serial3.print("TEL: Z="); Serial3.print(filteredAngleZ, 1);
    Serial3.print(" V1="); Serial3.print(v1, 1);
    Serial3.print(" dL="); Serial3.print(dL);
    Serial3.print(" dR="); Serial3.println(dR);
}

void procesarComando(String cmd, Stream &puertoRespuesta) {
    cmd.trim();
    if (cmd.length() == 0) return;

    int coma1 = cmd.indexOf(',');
    if (coma1 == -1) {
        puertoRespuesta.println("ERR:FORMATO_INVALIDO");
        return;
    }

    String accion = cmd.substring(0, coma1);
    String resto = cmd.substring(coma1 + 1);

    if (accion == "MOVE") {
        int coma2 = resto.indexOf(',');
        if (coma2 == -1) return;
        char sentido = resto.charAt(0); // 'W', 'S', 'L', 'R', 'X'
        int vel = resto.substring(coma2 + 1).toInt();
        velocidadActual = constrain(vel, 0, 255);
        
        if (sentido == 'W' || sentido == 'S') {
            gyro.update(); 
            targetAngle = gyro.getAngleZ(); 
            lastError = 0.0;
            cambiarEstado(sentido);
        } else if (sentido == 'L' || sentido == 'R' || sentido == 'X') {
            cambiarEstado(sentido);
        }
        puertoRespuesta.println("ACK:MOVE_OK");
    } 
    else if (accion == "PID") {
        int coma2 = resto.indexOf(',');
        if (coma2 != -1) {
            Kp = resto.substring(0, coma2).toFloat();
            Kd = resto.substring(coma2 + 1).toFloat();
            puertoRespuesta.println("ACK:PID_UPDATED");
        }
    } 
    else if (accion == "ANGLE") {
        int coma2 = resto.indexOf(',');
        if (coma2 != -1) {
            float grados = resto.substring(0, coma2).toFloat();
            int vel = resto.substring(coma2 + 1).toInt();
            velocidadActual = constrain(vel, 0, 255);
            gyro.update(); 
            anguloInicioGiro = gyro.getAngleZ(); 
            gradosGiroObjetivo = grados; 
            cambiarEstado('G');
            puertoRespuesta.println("ACK:ANGLE_SET");
        }
    } 
    else if (accion == "LIGHTS") {
        lucesManual = (resto == "ON");
        digitalWrite(pinReleLuces, lucesManual ? HIGH : LOW);
        puertoRespuesta.println("ACK:LIGHTS_" + String(lucesManual ? "ON" : "OFF"));
    }
    else {
        puertoRespuesta.println("ERR:COMANDO_DESCONOCIDO");
    }
}

void cambiarEstado(char nuevoEstado) {
    if (estadoMovimiento == nuevoEstado) return;
    detener(); 
    delay(50); 
    estadoMovimiento = nuevoEstado;
    if (estadoMovimiento != 'X') digitalWrite(pinReleLuces, HIGH);
    else if (!lucesManual) digitalWrite(pinReleLuces, LOW);
}

float obtenerVoltaje(int canal) {
    int16_t adc = ads.readADC_SingleEnded(canal);
    return (adc * 0.000125F) * FACTOR_DIVISOR;
}

void moverMotorDireccion(int rpwm, int lpwm, int velocidad, bool adelante) {
    if (adelante) {
        analogWrite(rpwm, velocidad);
        analogWrite(lpwm, 0);
    } else {
        analogWrite(rpwm, 0);
        analogWrite(lpwm, velocidad);
    }
}

void detener() {
    analogWrite(M1_RPWM, 0); analogWrite(M1_LPWM, 0);
    analogWrite(M2_RPWM, 0); analogWrite(M2_LPWM, 0);
    analogWrite(M3_RPWM, 0); analogWrite(M3_LPWM, 0);
    analogWrite(M4_RPWM, 0); analogWrite(M4_LPWM, 0);
}