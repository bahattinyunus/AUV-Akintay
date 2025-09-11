#include <ESP32Servo.h>
#include <Wire.h>
#include <LSM6DSL.h>

// ESC PWM limits
static const int PWM_MIN_US = 1060;
static const int PWM_MAX_US = 1940;
static const int PWM_MID_US = 1500;

// Pins
static const int PIN_MOTOR_START = D1;  // D1..D8
static const int PIN_BUTTON_PHOTO = D9;
static const int PIN_BUTTON_VIDEO = D0;

// Modes
enum ControlMode { MODE_MANUAL = 0, MODE_VISION = 1, MODE_STABILIZE = 2, MODE_VEL = 3 };
volatile ControlMode currentMode = MODE_MANUAL;

// Vision command
char visionCmd = 'S';  // F/L/R/S (S = stop)
int  visionSpeed = 0;  // 0..100

// Velocity command (surge,sway,heave,yaw) in -100..100 domain
int velSurge = 0, velSway = 0, velHeave = 0, velYaw = 0;

// Joystick inputs mapped to 1000..2000us domain
float X1_us = PWM_MID_US, Y1_us = PWM_MID_US, X2_us = PWM_MID_US, Y2_us = PWM_MID_US;
float speedDivider = 1.0f;  // 1.0 → full, 2.0 → half
int deadzoneUs = 30;

// IMU and PID (assist)
LSM6DSL IMU;
bool imuOk = false;
float rollSetpoint = 0.0f, pitchSetpoint = 0.0f;
float actualRoll = 0.0f, actualPitch = 0.0f;
float Kp = 1.2f, Ki = 0.0f, Kd = 0.15f;
float rollErr = 0.0f, pitchErr = 0.0f;
float rollInt = 0.0f, pitchInt = 0.0f;
float rollLastErr = 0.0f, pitchLastErr = 0.0f;
unsigned long lastImuMs = 0;

// Motor mixing
Servo m[8];
int mUs[8];

// 45° mounting gains (assist only)
static const float k45 = 0.7071f;
float rollGain[8]  = { -k45,  k45,  k45, -k45, -k45,  k45,  k45, -k45 };
float pitchGain[8] = {  k45,  k45, -k45, -k45,  k45,  k45, -k45, -k45 };

// Failsafe
unsigned long lastCmdMs = 0;
static const unsigned long FAILSAFE_MS = 800;

// Debounce
unsigned long lastBtnMs = 0;

// Utils
static inline int clampUs(int v) {
  if (v < PWM_MIN_US) return PWM_MIN_US;
  if (v > PWM_MAX_US) return PWM_MAX_US;
  return v;
}

static inline float applyDeadzoneUs(float v) {
  if (v < PWM_MID_US + deadzoneUs && v > PWM_MID_US - deadzoneUs) return PWM_MID_US;
  return v;
}

void writeAllMotorsMid() {
  for (int i = 0; i < 8; i++) {
    m[i].writeMicroseconds(PWM_MID_US);
  }
}

void armEscs() {
  writeAllMotorsMid();
  delay(2000);
}

void attachMotors() {
  for (int i = 0; i < 8; i++) {
    m[i].attach(PIN_MOTOR_START + i);
  }
}

void readJoystickManual() {
  X1_us = analogRead(A0) / 4.0f + 1000.0f;
  Y1_us = analogRead(A2) / 4.0f + 1000.0f;
  X2_us = analogRead(A1) / 4.0f + 1000.0f;
  Y2_us = analogRead(A3) / 4.0f + 1000.0f;

  X1_us = PWM_MID_US + (X1_us - PWM_MID_US) / speedDivider;
  Y1_us = PWM_MID_US + (Y1_us - PWM_MID_US) / speedDivider;
  X2_us = PWM_MID_US + (X2_us - PWM_MID_US) / speedDivider;
  Y2_us = PWM_MID_US + (Y2_us - PWM_MID_US) / speedDivider;

  X1_us = applyDeadzoneUs(X1_us);
  Y1_us = applyDeadzoneUs(Y1_us);
  X2_us = applyDeadzoneUs(X2_us);
  Y2_us = applyDeadzoneUs(Y2_us);

  if (X1_us > PWM_MAX_US) X1_us = PWM_MAX_US;
  if (Y1_us > PWM_MAX_US) Y1_us = PWM_MAX_US;
  if (X2_us > PWM_MAX_US) X2_us = PWM_MAX_US;
  if (Y2_us > PWM_MAX_US) Y2_us = PWM_MAX_US;
  if (X1_us < PWM_MIN_US) X1_us = PWM_MIN_US;
  if (Y1_us < PWM_MIN_US) Y1_us = PWM_MIN_US;
  if (X2_us < PWM_MIN_US) X2_us = PWM_MIN_US;
  if (Y2_us < PWM_MIN_US) Y2_us = PWM_MIN_US;
}

void computeVisionSticks() {
  X1_us = PWM_MID_US; X2_us = PWM_MID_US; Y1_us = PWM_MID_US; Y2_us = PWM_MID_US;
  int delta = map(visionSpeed, 0, 100, 0, 300);  // conservative range
  if (visionCmd == 'F') {
    Y1_us = PWM_MID_US + delta;
    Y2_us = PWM_MID_US + delta;
  } else if (visionCmd == 'L') {
    X1_us = PWM_MID_US - delta;
    X2_us = PWM_MID_US - delta;
  } else if (visionCmd == 'R') {
    X1_us = PWM_MID_US + delta;
    X2_us = PWM_MID_US + delta;
  } else {
    // stop
  }
}

void computeVelSticks() {
  // Map VEL (surge, yaw) primarily; sway/heave reserved for future
  // Inputs are -100..100; map to +/-300us deltas
  int dSurge = map(abs(velSurge), 0, 100, 0, 300);
  if (velSurge < 0) dSurge = -dSurge;
  int dYaw = map(abs(velYaw), 0, 100, 0, 300);
  if (velYaw < 0) dYaw = -dYaw;

  X1_us = PWM_MID_US + dYaw;   // left/right turn maps to X axes
  X2_us = PWM_MID_US + dYaw;
  Y1_us = PWM_MID_US + dSurge; // forward/back maps to Y axes
  Y2_us = PWM_MID_US + dSurge;

  // Sway/heave (future): could be mixed via X1/X2 asymmetry or separate vertical thrusters
}

void mixAndWriteMotors(bool applyAssist) {
  int onsagust_deger = 1500 - (X1_us - 1500) - (X2_us - 1500) + (Y2_us - 1500) + (Y1_us - 1500);
  int onsolust_deger = 1500 + (X1_us - 1500) + (X2_us - 1500) + (Y2_us - 1500) + (Y1_us - 1500);
  int arsolust_deger = 1500 - (X1_us - 1500) + (X2_us - 1500) - (Y2_us - 1500) + (Y1_us - 1500);
  int arsagust_deger = 1500 + (X1_us - 1500) - (X2_us - 1500) - (Y2_us - 1500) + (Y1_us - 1500);
  int onsagalt_deger = 1500 - (X1_us - 1500) - (X2_us - 1500) + (Y2_us - 1500) - (Y1_us - 1500);
  int onsolalt_deger = 1500 + (X1_us - 1500) + (X2_us - 1500) + (Y2_us - 1500) - (Y1_us - 1500);
  int arsolalt_deger = 1500 - (X1_us - 1500) + (X2_us - 1500) - (Y2_us - 1500) - (Y1_us - 1500);
  int arsagalt_deger = 1500 + (X1_us - 1500) - (X2_us - 1500) - (Y2_us - 1500) - (Y1_us - 1500);

  mUs[0] = onsagust_deger; // M1
  mUs[1] = onsolust_deger; // M2
  mUs[2] = arsolust_deger; // M3
  mUs[3] = arsagust_deger; // M4
  mUs[4] = onsagalt_deger; // M5
  mUs[5] = onsolalt_deger; // M6
  mUs[6] = arsolalt_deger; // M7
  mUs[7] = arsagalt_deger; // M8

  if (applyAssist && imuOk) {
    float pitchOut, rollOut;
    unsigned long nowMs = millis();
    float dt = (nowMs - lastImuMs) / 1000.0f;
    if (dt <= 0.0f) dt = 0.01f;
    lastImuMs = nowMs;

    float gx, gy;
    if (IMU.readGyroscope(gx, gy, nullptr)) {
      actualPitch += gx * dt;
      actualRoll  += gy * dt;

      pitchErr = pitchSetpoint - actualPitch;
      rollErr  = rollSetpoint  - actualRoll;

      pitchInt += pitchErr * dt;
      rollInt  += rollErr  * dt;

      float pitchDer = (pitchErr - pitchLastErr) / dt;
      float rollDer  = (rollErr  - rollLastErr)  / dt;

      pitchOut = Kp * pitchErr + Ki * pitchInt + Kd * pitchDer;
      rollOut  = Kp * rollErr  + Ki * rollInt  + Kd * rollDer;

      pitchLastErr = pitchErr;
      rollLastErr  = rollErr;

      for (int i = 0; i < 8; i++) {
        float corrected = (float)mUs[i];
        corrected += pitchOut * pitchGain[i];
        corrected += rollOut  * rollGain[i];
        mUs[i] = clampUs((int)corrected);
      }
    }
  }

  for (int i = 0; i < 8; i++) {
    m[i].writeMicroseconds(clampUs(mUs[i]));
  }
}

void handleButtons() {
  unsigned long now = millis();
  if (now - lastBtnMs < 120) return;
  lastBtnMs = now;

  if (digitalRead(PIN_BUTTON_PHOTO) == LOW) {
    Serial.println("PHOTO");
  }
  if (digitalRead(PIN_BUTTON_VIDEO) == LOW) {
    Serial.println("VIDEO");
  }
}

void parseSerialLine(const String& line) {
  // Examples:
  // MODE:MANUAL
  // MODE:VISION
  // MODE:STAB
  // MODE:VEL
  // CMD:F;SPEED:60
  // VEL:10,0,0,15

  if (line.startsWith("MODE:")) {
    if (line.indexOf("MANUAL") > 0)      currentMode = MODE_MANUAL;
    else if (line.indexOf("VISION") > 0) currentMode = MODE_VISION;
    else if (line.indexOf("STAB") > 0)   currentMode = MODE_STABILIZE;
    else if (line.indexOf("VEL") > 0)    currentMode = MODE_VEL;
    return;
  }

  int sep = line.indexOf(';');
  String first = sep > 0 ? line.substring(0, sep) : line;
  String rest  = sep > 0 ? line.substring(sep + 1) : "";

  if (first.startsWith("CMD:")) {
    int colon = first.indexOf(':');
    if (colon > 0 && colon + 1 < first.length()) {
      visionCmd = first.substring(colon + 1).charAt(0);
    }
    if (rest.length() > 0 && rest.startsWith("SPEED:")) {
      int c = rest.indexOf(':');
      int spd = rest.substring(c + 1).toInt();
      if (spd < 0) spd = 0; if (spd > 100) spd = 100;
      visionSpeed = spd;
    }
    lastCmdMs = millis();
    return;
  }

  if (first.startsWith("VEL:")) {
    // Format: VEL:surge,sway,heave,yaw  (each -100..100)
    int c = first.indexOf(':');
    String vals = first.substring(c + 1);
    int p1 = vals.indexOf(',');
    int p2 = vals.indexOf(',', p1 + 1);
    int p3 = vals.indexOf(',', p2 + 1);
    if (p1 > 0 && p2 > p1 && p3 > p2) {
      velSurge = vals.substring(0, p1).toInt();
      velSway  = vals.substring(p1 + 1, p2).toInt();
      velHeave = vals.substring(p2 + 1, p3).toInt();
      velYaw   = vals.substring(p3 + 1).toInt();
      if (velSurge < -100) velSurge = -100; if (velSurge > 100) velSurge = 100;
      if (velSway  < -100) velSway  = -100; if (velSway  > 100) velSway  = 100;
      if (velHeave < -100) velHeave = -100; if (velHeave > 100) velHeave = 100;
      if (velYaw   < -100) velYaw   = -100; if (velYaw   > 100) velYaw   = 100;
      lastCmdMs = millis();
    }
  }
}

void readSerialNonBlocking() {
  static String buf;
  while (Serial.available() > 0) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (buf.length() > 0) {
        parseSerialLine(buf);
        buf = "";
      }
    } else {
      buf += ch;
      if (buf.length() > 128) buf = ""; // simple guard
    }
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();

  pinMode(PIN_BUTTON_PHOTO, INPUT_PULLUP);
  pinMode(PIN_BUTTON_VIDEO, INPUT_PULLUP);

  attachMotors();
  armEscs();

  if (IMU.begin()) {
    imuOk = true;
    lastImuMs = millis();
  } else {
    imuOk = false;
    Serial.println("IMU init failed, stabilize assist disabled");
  }

  Serial.println("AKINTAY Main Firmware ready");
  Serial.println("Default MODE: MANUAL");
}

void loop() {
  readSerialNonBlocking();
  handleButtons();

  bool timedOut = (millis() - lastCmdMs) > FAILSAFE_MS;

  if (currentMode == MODE_MANUAL) {
    readJoystickManual();
  } else if (currentMode == MODE_VISION) {
    if (timedOut) { visionCmd = 'S'; visionSpeed = 0; }
    computeVisionSticks();
  } else if (currentMode == MODE_VEL) {
    if (timedOut) { velSurge = velSway = velHeave = velYaw = 0; }
    computeVelSticks();
  } else if (currentMode == MODE_STABILIZE) {
    readJoystickManual();
  }

  bool assist = (currentMode == MODE_STABILIZE);
  mixAndWriteMotors(assist);

  // Debug minimal
  static unsigned long lastDbg = 0;
  if (millis() - lastDbg > 250) {
    lastDbg = millis();
    Serial.print("MODE:"); Serial.print((int)currentMode);
    Serial.print(" CMD:"); Serial.print(visionCmd);
    Serial.print(" SPD:"); Serial.print(visionSpeed);
    Serial.print(" M1:"); Serial.print(mUs[0]);
    Serial.print(" M2:"); Serial.print(mUs[1]);
    Serial.print(" M3:"); Serial.print(mUs[2]);
    Serial.print(" M4:"); Serial.print(mUs[3]);
    Serial.print(" M5:"); Serial.print(mUs[4]);
    Serial.print(" M6:"); Serial.print(mUs[5]);
    Serial.print(" M7:"); Serial.print(mUs[6]);
    Serial.print(" M8:"); Serial.println(mUs[7]);
  }

  delay(20);
}


