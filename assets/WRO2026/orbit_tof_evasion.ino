#include "MeMegaPi.h"
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <Adafruit_VL53L0X.h>

// =============================================================================
// 🤖 ORBIT V4.0 — FIRMWARE DE CONTROL MOTORES Y REACCIÓN AUTÓNOMA TOF
// =============================================================================
// Sensores VL53L0X (4 ToF):
//   • Frontal   (F): xshut = 26 | I2C = 0x32
//   • Trasero   (B): xshut = 24 | I2C = 0x33
//   • Izquierdo (L): xshut = 30 | I2C = 0x30
//   • Derecho   (R): xshut = 28 | I2C = 0x31
//
// Comportamiento Autónomo por ToF (Umbral <= 20 cm / 200 mm):
//   1. Frontal   <= 20 cm -> Freno inmediato (se detiene).
//   2. Derecho   <= 20 cm -> Giro 90° a la derecha (+90°).
//   3. Izquierdo <= 20 cm -> Giro 90° a la izquierda (-90°).
//   4. Trasero   <= 20 cm -> Giro 180° (media vuelta).
// =============================================================================

// ==========================================
// CONFIGURACIÓN DE HARDWARE Y PINES
// ==========================================
const int xshut_L = 30; // ToF Izquierdo
const int xshut_R = 28; // ToF Derecho
const int xshut_F = 26; // ToF Frontal
const int xshut_B = 24; // ToF Trasero

const int pinRele = A5;             // Relé de potencia para drivers de motor
const int pinReleLuces = A4;        // Relé de luces / faros
const int pinReleVentilador = 35;   // Relé de disipación de calor

Adafruit_VL53L0X loxL, loxR, loxF, loxB;
MeGyro gyro;
Adafruit_ADS1115 ads;

// Control PWM Drivers BTS7960
const int M3_RPWM = 7;  const int M3_LPWM = 8; // Motor Izquierdo
const int M4_RPWM = 6;  const int M4_LPWM = 9; // Motor Derecho

// ==========================================
// PARÁMETROS DE CONTROL Y GIROSCOPIO
// ==========================================
float alpha = 0.3;           // Filtro paso bajo giroscopio
float filteredAngleZ = 0.0;  
float Kp = 1.5;              // Ganancia proporcional de seguimiento recto
float Kd = 0.6;              // Ganancia derivativa de amortiguación

float targetAngle = 0.0;     
float lastError = 0.0;       
float deadzone = 2.0;        // Grados de zona muerta para evitar vibración
float correction = 0.0;      

char estadoMovimiento = 'X'; 
int velocidadActual = 0; 

// Variables para giros angulares en lazo cerrado
float gradosGiroObjetivo = 0.0;
float gradosGiradosAcumulados = 0.0;
float ultimoAnguloFilt = 0.0;
unsigned long tiempoInicioGiro = 0;
const unsigned long TIMEOUT_GIRO_MS = 3800; // Máximo 3.8s por giro

// Factor de Trim para balancear asimetría física de los 2 motores
const float TRIM_FACTOR = 1.05; 

// Calibración de Offset del Giroscopio
float gyroOffsetZ = 0.0;
const int CALIBRATION_SAMPLES = 100;

// Divisor de voltaje para lectura de batería ADS1115
const float R1 = 100000.0; 
const float R2 = 50000.0;  
const float FACTOR_DIVISOR = (R1 + R2) / R2; 

unsigned long lastTime = 0;

// ==========================================
// SEGURIDAD Y WATCHDOG
// ==========================================
unsigned long lastCommandTime = 0;
const unsigned long SAFETY_TIMEOUT_MS = 500; 

// =============================================================================
// CONTROL DE VENTILADOR EN SEGUNDO PLANO (NON-BLOCKING)
// =============================================================================
// Ciclo: 120 segundos APAGADO -> 60 segundos ENCENDIDO -> Repite continuamente
const unsigned long FAN_INTERVAL_OFF_MS = 60000; // 120 segundos apagado (2 minutos)
const unsigned long FAN_DURATION_ON_MS  = 60000;  // 60 segundos encendido (1 minuto)

unsigned long lastFanToggleTime = 0;
bool fanEncendido = false;      // Estado actual del ventilador (false = apagado, true = encendido)
bool fanAutoHabilitado = true;  // Habilitado en segundo plano por defecto 

// ==========================================
// CONFIGURACIÓN DE EVASIÓN TOF
// ==========================================
// Frontal/Trasero: 20 cm (se mantienen exactamente igual)
const uint16_t TOF_FRONT_THRESHOLD_MM = 200; // 20 cm = 200 mm
const uint16_t TOF_BACK_THRESHOLD_MM  = 200; // 20 cm = 200 mm
// Laterales (L/R): 45 cm (15 cm más a cada lado: 30cm + 15cm)
const uint16_t TOF_SIDE_THRESHOLD_MM  = 450; // 45 cm = 450 mm
const uint16_t TOF_MIN_VALID_MM       = 25;  // 25 mm mínimo para descartar ruido
const unsigned long TOF_COOLDOWN_MS   = 750; // Cooldown entre giros sucesivos
unsigned long lastTofReactionTime = 0;
bool autoToFActivo = false;                 // Desactivado al inicio hasta recibir "OK ToF" desde Python

// Variables para retroceso reactivo autónomo por sensor frontal
bool retrocediendoPorToF = false;
unsigned long tiempoInicioRetroceso = 0;
const unsigned long MAX_TIEMPO_RETROCESO_MS = 2500; // 2.5s máximo de retroceso
const uint16_t DIST_FRONT_DESPEJADA_MM = 280;       // 28 cm para considerar el frente libre y detenerse

// ==========================================
// SISTEMA ROUND-ROBIN (LATENCIA ZERO)
// ==========================================
uint16_t cache_distL = 0xFFFF;
uint16_t cache_distR = 0xFFFF;
uint16_t cache_distF = 0xFFFF;
uint16_t cache_distB = 0xFFFF;
float cache_v1 = 0.0;
float cache_v2 = 0.0;
float cache_v3 = 0.0;
float cache_gyroX = 0.0;

int currentTurn = 0; 
unsigned long lastTurnTime = 0;
const unsigned long TURN_INTERVAL_MS = 20; 
const unsigned long TIMING_BUDGET_US = 30000;

// ==========================================
// PROTOCOLOS (BINARIO + TEXTO ASCII)
// ==========================================
#define CMD_MOVE       0x01
#define CMD_PID        0x02
#define CMD_ANGLE      0x03
#define CMD_STOP       0x04
#define CMD_REQ_TELEM  0x05
#define CMD_FAN        0x06
#define CMD_HEARTBEAT  0x07
#define CMD_LIGHTS     0x08       

#define TELEM_HEADER1  0xAA
#define TELEM_HEADER2  0x55

struct Telemetria {
    float z;
    float cor;
    float x;
    float v1;
    float v2;
    float v3;
    uint16_t distL;
    uint16_t distR;
    uint16_t distF; 
    uint16_t distB; 
};

String asciiBuffer = "";

// Declaraciones previas de funciones
void initToF(Adafruit_VL53L0X &sensor, int pin, byte addr, const char* name);
void executeMovement(float dt);
void iniciarGiro(float grados, int vel = 250);
void detener();
void cambiarEstado(char nuevoEstado);
void procesarComandoBinario(uint8_t cmd);
void procesarComandoASCII(String cmd);
void evaluarReaccionesToF();
void enviarTelemetriaBinaria();
float obtenerVoltaje(int canal);
void moverMotorDireccion(int rpwm, int lpwm, int velocidad, bool adelante);
void gestionarVentiladorBackground(unsigned long ahora);

// ==========================================
// SETUP
// ==========================================
void setup() {
    pinMode(pinRele, OUTPUT);
    pinMode(pinReleLuces, OUTPUT);
    pinMode(pinReleVentilador, OUTPUT);
    
    pinMode(xshut_L, OUTPUT);
    pinMode(xshut_R, OUTPUT);
    pinMode(xshut_F, OUTPUT);
    pinMode(xshut_B, OUTPUT);
    
    pinMode(M3_RPWM, OUTPUT); pinMode(M3_LPWM, OUTPUT);
    pinMode(M4_RPWM, OUTPUT); pinMode(M4_LPWM, OUTPUT);

    detener(); 
    digitalWrite(pinRele, LOW);          
    digitalWrite(pinReleLuces, LOW); 
    digitalWrite(pinReleVentilador, LOW); 
    fanEncendido = false;
    lastFanToggleTime = millis(); 
    
    Serial.begin(115200);
    delay(1000); 

    // --- Inicialización Secuencial de Sensores ToF ---
    digitalWrite(xshut_L, LOW); digitalWrite(xshut_R, LOW); 
    digitalWrite(xshut_F, LOW); digitalWrite(xshut_B, LOW); 
    delay(100);

    initToF(loxL, xshut_L, 0x30, "ToF L (Izquierda)");
    initToF(loxR, xshut_R, 0x31, "ToF R (Derecha)");
    initToF(loxF, xshut_F, 0x32, "ToF F (Frontal)");
    initToF(loxB, xshut_B, 0x33, "ToF B (Trasero)");

    // Calibración de Cero del Giroscopio
    Serial.println(F("Calibrando Giroscopio... Mantén el robot QUIETO"));
    gyro.begin();
    delay(500);
    
    float sumZ = 0.0;
    for(int i = 0; i < CALIBRATION_SAMPLES; i++) {
        gyro.update();
        sumZ += gyro.getAngleZ();
        delay(10);
    }
    gyroOffsetZ = sumZ / CALIBRATION_SAMPLES;
    filteredAngleZ = 0.0;
    ultimoAnguloFilt = 0.0;
    cache_gyroX = gyro.getAngleX();
    Serial.print(F("Offset Z Giroscopio: ")); Serial.println(gyroOffsetZ);

    if (ads.begin()) ads.setGain(GAIN_ONE);

    lastTime = millis();
    lastCommandTime = millis();
    lastTurnTime = millis();
    lastTofReactionTime = millis();

    Serial.println(F("🚀 ORBIT MegaPi Firmware LISTO (ToF en espera de 'OK ToF' desde Python)"));
}

void initToF(Adafruit_VL53L0X &sensor, int pin, byte addr, const char* name) {
    digitalWrite(pin, HIGH);
    delay(20); 
    
    if (sensor.begin(addr)) {
        sensor.setMeasurementTimingBudgetMicroSeconds(TIMING_BUDGET_US);
        sensor.startRangeContinuous();
        Serial.print(name); Serial.println(F(": OK"));
    } else {
        Serial.print(name); Serial.println(F(": FAIL"));
        digitalWrite(pin, LOW);
    }
}

// ==========================================
// LOOP PRINCIPAL
// ==========================================
void loop() {
    unsigned long currentTime = millis();
    float dt = (currentTime - lastTime) / 1000.0;
    if (dt <= 0.001) dt = 0.001;

    // --- 0. Control No Bloqueante del Ventilador en Segundo Plano (120s OFF / 60s ON) ---
    gestionarVentiladorBackground(currentTime);

    // --- 1. Lectura de Comandos Serial (Binario o ASCII) ---
    if (Serial.available() > 0) {
        uint8_t peekByte = Serial.peek();
        
        // Si el byte es <= 0x08 corresponde a los opcodes binarios
        if (peekByte >= 0x01 && peekByte <= 0x08) {
            uint8_t cmdByte = Serial.read();
            lastCommandTime = currentTime; 
            procesarComandoBinario(cmdByte);
        } else {
            // Procesamiento de comandos ASCII en texto plano (ej: MOVE,W,120)
            char c = (char)Serial.read();
            if (c == '\n' || c == '\r') {
                if (asciiBuffer.length() > 0) {
                    lastCommandTime = currentTime;
                    procesarComandoASCII(asciiBuffer);
                    asciiBuffer = "";
                }
            } else {
                if (asciiBuffer.length() < 64) {
                    asciiBuffer += c;
                } else {
                    asciiBuffer = "";
                }
            }
        }
    }

    // --- 2. Watchdog de Seguridad ---
    // Detener motores si no hay comando activo (excepto durante giros autónomos 'G' o retroceso ToF)
    if ((currentTime - lastCommandTime > SAFETY_TIMEOUT_MS) && 
        (estadoMovimiento != 'X') && 
        (estadoMovimiento != 'G') &&
        (!retrocediendoPorToF)) {
        detener();
        cambiarEstado('X');
    }

    // --- 3. Lectura Round-Robin No Bloqueante de Sensores ToF y Batería ---
    if (currentTime - lastTurnTime >= TURN_INTERVAL_MS) {
        lastTurnTime = currentTime;
        
        switch(currentTurn) {
            case 0: 
                if (loxL.isRangeComplete()) { 
                    uint16_t val = loxL.readRange(); 
                    if (val > 10 && val <= 2000) cache_distL = val; 
                } 
                break;
            case 1: 
                if (loxR.isRangeComplete()) { 
                    uint16_t val = loxR.readRange(); 
                    if (val > 10 && val <= 2000) cache_distR = val; 
                } 
                break;
            case 2: 
                if (loxF.isRangeComplete()) { 
                    uint16_t val = loxF.readRange(); 
                    if (val > 10 && val <= 2000) cache_distF = val; 
                } 
                break;
            case 3: 
                if (loxB.isRangeComplete()) { 
                    uint16_t val = loxB.readRange(); 
                    if (val > 10 && val <= 2000) cache_distB = val; 
                } 
                break;
            case 4: cache_v1 = obtenerVoltaje(0); break;
            case 5: cache_v2 = obtenerVoltaje(1); break;
            case 6: cache_v3 = obtenerVoltaje(2); break;
            case 7: 
                gyro.update(); 
                cache_gyroX = gyro.getAngleX(); 
                break;
        }
        
        currentTurn++;
        if (currentTurn > 7) currentTurn = 0;
    }

    // --- 4. Bucle de Control y Filtro de Giroscopio (10ms) ---
    if (currentTime - lastTime >= 10) {
        lastTime = currentTime;
        
        gyro.update();
        float rawAngleZ = gyro.getAngleZ() - gyroOffsetZ;
        
        // Normalización -180° a +180°
        while (rawAngleZ > 180.0) rawAngleZ -= 360.0;
        while (rawAngleZ < -180.0) rawAngleZ += 360.0;

        filteredAngleZ = (alpha * rawAngleZ) + ((1.0 - alpha) * filteredAngleZ);

        // Seguimiento acumulado para cálculo exacto de giro sin problemas de wrap-around
        float deltaGiro = filteredAngleZ - ultimoAnguloFilt;
        while (deltaGiro > 180.0) deltaGiro -= 360.0;
        while (deltaGiro < -180.0) deltaGiro += 360.0;
        gradosGiradosAcumulados += deltaGiro;
        ultimoAnguloFilt = filteredAngleZ;

        // --- 5. Evaluación de Reacciones Autónomas ToF (20cm) ---
        evaluarReaccionesToF();

        // Si está en reposo, no ejecutar movimiento
        if (estadoMovimiento == 'X') return;

        executeMovement(dt);
    }
}

// =============================================================================
// LÓGICA DE REACCIÓN INTELIGENTE DE LOS 4 SENSORES TOF (F/B: 20cm, L/R: 45cm)
// =============================================================================
void evaluarReaccionesToF() {
    if (!autoToFActivo) return;
    
    // Si el robot está ejecutando un giro, NO evaluar reacciones ni retroceder
    if (estadoMovimiento == 'G') {
        retrocediendoPorToF = false;
        return;
    }

    unsigned long ahora = millis();

    bool obstaculoF = (cache_distF != 0xFFFF && cache_distF >= TOF_MIN_VALID_MM && cache_distF <= TOF_FRONT_THRESHOLD_MM);
    bool obstaculoB = (cache_distB != 0xFFFF && cache_distB >= TOF_MIN_VALID_MM && cache_distB <= TOF_BACK_THRESHOLD_MM);
    bool obstaculoR = (cache_distR != 0xFFFF && cache_distR >= TOF_MIN_VALID_MM && cache_distR <= TOF_SIDE_THRESHOLD_MM);
    bool obstaculoL = (cache_distL != 0xFFFF && cache_distL >= TOF_MIN_VALID_MM && cache_distL <= TOF_SIDE_THRESHOLD_MM);

    // =========================================================================
    // CASO 1: EL ROBOT YA SE ESTÁ MOVIENDO HACIA ATRÁS POR EL SENSOR FRONTAL
    // (Solo aquí el sensor trasero está pendiente para no chocar con una pared)
    // =========================================================================
    if (retrocediendoPorToF) {
        lastCommandTime = ahora; // Evitar que el watchdog serial interrumpa el retroceso

        // 1. VIGILANCIA TRASERA ACTIVA: Si mientras retrocede siente pared atrás (<= 20cm) -> FRENAR
        if (obstaculoB) {
            detener();
            cambiarEstado('X');
            retrocediendoPorToF = false;
            lastTofReactionTime = ahora;
            Serial.print(F("🛑 [ToF RETROCESO DETENIDO] Pared trasera detectada a "));
            Serial.print(cache_distB);
            Serial.println(F(" mm -> ALTO TOTAL para no chocar atrás"));
            return;
        }

        // 2. PARÓ DE SENTIR ADELANTE: Si el obstáculo frontal ya no está (distancia > 22cm o sin eco) -> DETENERSE
        if (cache_distF > (TOF_FRONT_THRESHOLD_MM + 20) || cache_distF == 0xFFFF) {
            detener();
            cambiarEstado('X');
            retrocediendoPorToF = false;
            lastTofReactionTime = ahora;
            Serial.print(F("✅ [ToF RETROCESO COMPLETADO] Dejó de sentir adelante (distancia: "));
            Serial.print(cache_distF);
            Serial.println(F(" mm) -> DETENIDO (espacio recuperado)"));
            return;
        }

        // 3. Timeout de seguridad (máximo 3.0s retrocediendo)
        if (ahora - tiempoInicioRetroceso > 3000) {
            detener();
            cambiarEstado('X');
            retrocediendoPorToF = false;
            lastTofReactionTime = ahora;
            Serial.println(F("⏱️ [ToF RETROCESO] Timeout alcanzado -> DETENIDO"));
            return;
        }

        return; // Sigue retrocediendo normalmente
    }

    // =========================================================================
    // CASO 2: MODO NORMAL (ROBOT DETENIDO O AVANZANDO)
    // =========================================================================
    if (ahora - lastTofReactionTime < TOF_COOLDOWN_MS) return;

    // 1. SENSOR ADELANTE: Si siente a alguien adelante (<= 20cm)
    // Frena de inmediato los motores brevemente antes de iniciar el retroceso para disipar la inercia
    if (obstaculoF) {
        detener();
        cambiarEstado('X');
        delay(150); // Pausa breve de seguridad mecánica ("se paren muy poco tiempo para que no joda nada")

        velocidadActual = 220; // Torque alto para vencer la inercia al retroceder
        gyro.update();
        targetAngle = filteredAngleZ;
        lastError = 0.0;
        cambiarEstado('S'); // 'S' mueve físicamente el robot HACIA ATRÁS (alejándose)
        retrocediendoPorToF = true;
        tiempoInicioRetroceso = millis();
        lastCommandTime = millis();
        lastTofReactionTime = millis();
        Serial.print(F("🔙 [ToF RETROCESO] Obstáculo adelante a "));
        Serial.print(cache_distF);
        Serial.println(F(" mm -> Detención breve y retrocediendo..."));
        return;
    }

    // 2. SENSOR DERECHA: Giro 90° a la derecha (+90°)
    if (obstaculoR) {
        if (estadoMovimiento != 'X') {
            detener();
            cambiarEstado('X');
            delay(100); // Parada previa de seguridad
        }
        lastTofReactionTime = ahora;
        Serial.print(F("👉 [ToF GIRO DERECHA] Obstáculo Derecho a "));
        Serial.print(cache_distR);
        Serial.print(F(" mm (<= "));
        Serial.print(TOF_SIDE_THRESHOLD_MM);
        Serial.println(F(" mm) -> Girando +90°"));
        iniciarGiro(90.0, 250);
        return;
    }

    // 3. SENSOR IZQUIERDA: Giro 90° a la izquierda (-90°)
    if (obstaculoL) {
        if (estadoMovimiento != 'X') {
            detener();
            cambiarEstado('X');
            delay(100); // Parada previa de seguridad
        }
        lastTofReactionTime = ahora;
        Serial.print(F("👈 [ToF GIRO IZQUIERDA] Obstáculo Izquierdo a "));
        Serial.print(cache_distL);
        Serial.print(F(" mm (<= "));
        Serial.print(TOF_SIDE_THRESHOLD_MM);
        Serial.println(F(" mm) -> Girando -90°"));
        iniciarGiro(-90.0, 250);
        return;
    }

    // 4. SENSOR ATRÁS (EN FUNCIÓN NORMAL): Giro de 180 grados
    if (obstaculoB) {
        if (estadoMovimiento != 'X') {
            detener();
            cambiarEstado('X');
            delay(100); // Parada previa de seguridad
        }
        lastTofReactionTime = ahora;
        Serial.print(F("🔄 [ToF GIRO 180°] Obstáculo Trasero a "));
        Serial.print(cache_distB);
        Serial.print(F(" mm (<= "));
        Serial.print(TOF_BACK_THRESHOLD_MM);
        Serial.println(F(" mm) -> Girando 180°"));
        iniciarGiro(180.0, 250);
        return;
    }
}

// ==========================================
// CONTROL DE MOVIMIENTO Y MOTORES
// ==========================================
void iniciarGiro(float grados, int vel) {
    velocidadActual = constrain(vel, 80, 255);
    gradosGiradosAcumulados = 0.0;
    ultimoAnguloFilt = filteredAngleZ;
    gradosGiroObjetivo = grados;
    tiempoInicioGiro = millis();
    cambiarEstado('G');
}

void executeMovement(float dt) {
    if (estadoMovimiento == 'W' || estadoMovimiento == 'S') {
        float error = targetAngle - filteredAngleZ;
        correction = 0.0;
        
        if (abs(error) > deadzone) {
            float derivative = (error - lastError) / dt;
            correction = (Kp * error) + (Kd * derivative);
            float maxCorr = velocidadActual * 0.4;
            correction = constrain(correction, -maxCorr, maxCorr);
        }
        lastError = error;

        int speedLeft = 0, speedRight = 0;
        bool esAdelante = (estadoMovimiento == 'S');

        if (esAdelante) {
            speedLeft  = constrain(velocidadActual + correction, 0, 255);
            speedRight = constrain(velocidadActual - correction, 0, 255);
        } else {
            speedLeft  = constrain(velocidadActual - correction, 0, 255);
            speedRight = constrain(velocidadActual + correction, 0, 255);
        }
        
        if(speedLeft == 0 && velocidadActual > 0) speedLeft = 10;
        if(speedRight == 0 && velocidadActual > 0) speedRight = 10;

        moverMotorDireccion(M3_RPWM, M3_LPWM, speedLeft, esAdelante);
        moverMotorDireccion(M4_RPWM, M4_LPWM, speedRight, esAdelante);
    }
    else if (estadoMovimiento == 'L') {
        moverMotorDireccion(M3_RPWM, M3_LPWM, velocidadActual, false);
        moverMotorDireccion(M4_RPWM, M4_LPWM, velocidadActual, true);
    }
    else if (estadoMovimiento == 'R') {
        moverMotorDireccion(M3_RPWM, M3_LPWM, velocidadActual, true);
        moverMotorDireccion(M4_RPWM, M4_LPWM, velocidadActual, false);
    }
    else if (estadoMovimiento == 'G') {
        // Timeout de seguridad en giros
        if (millis() - tiempoInicioGiro > TIMEOUT_GIRO_MS) {
            detener();
            targetAngle = filteredAngleZ;
            cambiarEstado('X');
            Serial.println(F("WARN:TIMEOUT_GIRO"));
            return;
        }

        float errorRestante = abs(gradosGiroObjetivo) - abs(gradosGiradosAcumulados);
        
        // Perfil de velocidad con torque suficiente para chasis pesado
        int velGiro = velocidadActual; // Arranca en 250
        if (errorRestante < 28.0 && errorRestante > 6.0) {
            velGiro = 220; // Al faltar 28° mantiene potencia a 220
        } else if (errorRestante <= 6.0) {
            velGiro = 180; // Al faltar 6° baja a 180 para asegurar fuerza
        }
        
        // Girar aplicando factor de Trim
        if (errorRestante > 2.0) {
            bool girarDerecha = (gradosGiroObjetivo > 0);
            if (girarDerecha) {
                int sL = constrain((int)(velGiro * TRIM_FACTOR), 0, 255);
                moverMotorDireccion(M3_RPWM, M3_LPWM, sL, true);
                moverMotorDireccion(M4_RPWM, M4_LPWM, velGiro, false);
            } else {
                moverMotorDireccion(M3_RPWM, M3_LPWM, velGiro, false);
                int sR = constrain((int)(velGiro * TRIM_FACTOR), 0, 255);
                moverMotorDireccion(M4_RPWM, M4_LPWM, sR, true);
            }
        } else {
            // FRENO ACTIVO: Contra-pulso con suficiente fuerza para chasis pesado
            bool girarDerecha = (gradosGiroObjetivo > 0);
            int brakeSpeed = 160;
            
            if (girarDerecha) {
                moverMotorDireccion(M3_RPWM, M3_LPWM, brakeSpeed, false);
                moverMotorDireccion(M4_RPWM, M4_LPWM, brakeSpeed, true);
            } else {
                moverMotorDireccion(M3_RPWM, M3_LPWM, brakeSpeed, true);
                moverMotorDireccion(M4_RPWM, M4_LPWM, brakeSpeed, false);
            }
            delay(80);
            
            detener();
            targetAngle = filteredAngleZ;
            cambiarEstado('X');
            lastTofReactionTime = millis();
            Serial.println(F("ACK:GIRO_COMPLETADO"));
        }
    }
}

// ==========================================
// PARSERS DE COMANDOS (BINARIO Y ASCII)
// ==========================================
void procesarComandoBinario(uint8_t cmd) {
    switch (cmd) {
        case CMD_MOVE: {
            unsigned long t0 = millis();
            while (Serial.available() < 2 && millis() - t0 < 50) { }
            if (Serial.available() < 2) return;
            char sentido = Serial.read();
            uint8_t vel = Serial.read();
            
            velocidadActual = constrain(vel, 0, 255);
            
            if (sentido == 'W' || sentido == 'S') {
                gyro.update();
                targetAngle = gyro.getAngleZ() - gyroOffsetZ; 
                lastError = 0.0;
                cambiarEstado(sentido);
            } else if (sentido == 'L' || sentido == 'R' || sentido == 'X') {
                cambiarEstado(sentido);
            }
            break;
        }
        case CMD_PID: {
            unsigned long t0 = millis();
            while (Serial.available() < 8 && millis() - t0 < 50) { }
            if (Serial.available() < 8) return;
            float kp, kd;
            Serial.readBytes((uint8_t*)&kp, 4);
            Serial.readBytes((uint8_t*)&kd, 4);
            Kp = kp; Kd = kd;
            break;
        }
        case CMD_ANGLE: {
            unsigned long t0 = millis();
            while (Serial.available() < 5 && millis() - t0 < 50) { }
            if (Serial.available() < 5) return;
            float grados;
            uint8_t vel;
            Serial.readBytes((uint8_t*)&grados, 4);
            vel = Serial.read();
            
            iniciarGiro(grados, vel);
            break;
        }
        case CMD_STOP: 
            detener();
            cambiarEstado('X'); 
            break;
        case CMD_FAN: {
            if (Serial.available() > 0) {
                uint8_t estado = Serial.read();
                digitalWrite(pinReleVentilador, estado ? HIGH : LOW);
                fanEncendido = (estado != 0);
                lastFanToggleTime = millis();
            }
            break;
        }
        case CMD_LIGHTS: { 
            if (Serial.available() > 0) {
                uint8_t estado = Serial.read();
                digitalWrite(pinReleLuces, estado ? HIGH : LOW);
            }
            break;
        }
        case CMD_REQ_TELEM: 
            enviarTelemetriaBinaria(); 
            break;
        case CMD_HEARTBEAT: 
            break;
    }
}

void procesarComandoASCII(String cmd) {
    cmd.trim();
    if (cmd.length() == 0) return;

    if (cmd.startsWith("MOVE,")) {
        int firstComma = cmd.indexOf(',');
        int secondComma = cmd.indexOf(',', firstComma + 1);
        if (firstComma != -1 && secondComma != -1) {
            char sentido = cmd.charAt(firstComma + 1);
            int vel = cmd.substring(secondComma + 1).toInt();
            velocidadActual = constrain(vel, 0, 255);
            if (sentido == 'W' || sentido == 'S') {
                gyro.update();
                targetAngle = gyro.getAngleZ() - gyroOffsetZ;
                lastError = 0.0;
                cambiarEstado(sentido);
            } else if (sentido == 'L' || sentido == 'R' || sentido == 'X') {
                cambiarEstado(sentido);
            }
        }
    }
    else if (cmd.startsWith("ANGLE,")) {
        int firstComma = cmd.indexOf(',');
        int secondComma = cmd.indexOf(',', firstComma + 1);
        if (firstComma != -1 && secondComma != -1) {
            float grados = cmd.substring(firstComma + 1, secondComma).toFloat();
            int vel = cmd.substring(secondComma + 1).toInt();
            iniciarGiro(grados, vel);
        }
    }
    else if (cmd == "STOP" || cmd == "MOVE,X,0") {
        detener();
        cambiarEstado('X');
    }
    else if (cmd == "LIGHTS,ON") {
        digitalWrite(pinReleLuces, HIGH);
    }
    else if (cmd == "LIGHTS,OFF") {
        digitalWrite(pinReleLuces, LOW);
    }
    else if (cmd == "FAN,ON") {
        digitalWrite(pinReleVentilador, HIGH);
        fanEncendido = true;
        lastFanToggleTime = millis();
        Serial.println(F("ACK:FAN_ON"));
    }
    else if (cmd == "FAN,OFF") {
        digitalWrite(pinReleVentilador, LOW);
        fanEncendido = false;
        lastFanToggleTime = millis();
        Serial.println(F("ACK:FAN_OFF"));
    }
    else if (cmd == "FAN,AUTO,ON") {
        fanAutoHabilitado = true;
        lastFanToggleTime = millis();
        Serial.println(F("ACK:FAN_AUTO_ON"));
    }
    else if (cmd == "FAN,AUTO,OFF") {
        fanAutoHabilitado = false;
        digitalWrite(pinReleVentilador, LOW);
        fanEncendido = false;
        Serial.println(F("ACK:FAN_AUTO_OFF"));
    }
    else if (cmd.equalsIgnoreCase("OK ToF") || cmd == "AUTO_TOF,ON" || cmd == "OK_TOF") {
        autoToFActivo = true;
        lastTofReactionTime = millis();
        Serial.println(F("ACK:OK_TOF"));
    }
    else if (cmd.equalsIgnoreCase("STOP ToF") || cmd == "AUTO_TOF,OFF" || cmd == "STOP_TOF") {
        autoToFActivo = false;
        retrocediendoPorToF = false;
        detener();
        Serial.println(F("ACK:STOP_TOF"));
    }
}

// ==========================================
// TELEMETRÍA (BINARIA Y TEXTO)
// ==========================================
void enviarTelemetriaBinaria() {
    Telemetria t;
    t.z = filteredAngleZ;
    t.cor = correction;
    t.x = cache_gyroX;
    t.v1 = cache_v1;
    t.v2 = cache_v2;
    t.v3 = cache_v3;
    t.distL = cache_distL;
    t.distR = cache_distR;
    t.distF = cache_distF;
    t.distB = cache_distB;
    
    Serial.write(TELEM_HEADER1);
    Serial.write(TELEM_HEADER2);
    Serial.write((uint8_t*)&t, sizeof(t));
}

// ==========================================
// CONTROL DE ESTADO Y HARDWARE
// ==========================================
void cambiarEstado(char nuevoEstado) {
    if (estadoMovimiento == nuevoEstado) return;
    detener(); 
    delay(40); 
    estadoMovimiento = nuevoEstado;
    
    if (estadoMovimiento != 'S') {
        retrocediendoPorToF = false;
    }

    if (estadoMovimiento == 'X') {
        digitalWrite(pinRele, LOW);
    } else {
        digitalWrite(pinRele, HIGH);      
    }
}

float obtenerVoltaje(int canal) {
    int16_t adc = ads.readADC_SingleEnded(canal);
    return ((adc * 0.000125F) * FACTOR_DIVISOR) * 1.02;
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
    analogWrite(M3_RPWM, 0); analogWrite(M3_LPWM, 0);
    analogWrite(M4_RPWM, 0); analogWrite(M4_LPWM, 0);
}

// =============================================================================
// GESTIÓN NO BLOQUEANTE DEL VENTILADOR EN SEGUNDO PLANO (ZERO DELAYS)
// =============================================================================
// Se ejecuta en cada ciclo del loop sin retrasar el procesamiento de motores ni ToF.
void gestionarVentiladorBackground(unsigned long ahora) {
    if (!fanAutoHabilitado) return;

    if (fanEncendido) {
        // Ventilador ENCENDIDO -> Verificar si pasaron los 60 segundos
        if (ahora - lastFanToggleTime >= FAN_DURATION_ON_MS) {
            digitalWrite(pinReleVentilador, LOW);
            fanEncendido = false;
            lastFanToggleTime = ahora;
            Serial.println(F("❄️ [FAN BG] Ciclo de enfriamiento completado (60s) -> Ventilador APAGADO"));
        }
    } else {
        // Ventilador APAGADO -> Verificar si pasaron los 120 segundos
        if (ahora - lastFanToggleTime >= FAN_INTERVAL_OFF_MS) {
            digitalWrite(pinReleVentilador, HIGH);
            fanEncendido = true;
            lastFanToggleTime = ahora;
            Serial.println(F("💨 [FAN BG] Intervalo alcanzado (120s) -> Ventilador ENCENDIDO por 60s"));
        }
    }
}
