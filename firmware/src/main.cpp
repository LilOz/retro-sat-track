// Bench telemetry client; see README for remaining UI milestones.
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_HX8357.h>
#include <time.h>
#if __has_include("orbit_config.h")
#include "orbit_config.h"
#else
#include "orbit_config.example.h"
#endif

Adafruit_HX8357 display(10, 9, 14, HX8357D);
constexpr int POT_PIN = 1, LOW_BATTERY_PIN = 2, BACKLIGHT_PIN = 15;
constexpr int BACKLIGHT_CHANNEL = 0;
struct Sample {
  bool valid = false, oldElements = false;
  float altitude = 0, speed = 0, lat = 0, lon = 0;
  uint32_t received = 0;
  char utc[40] = {}, name[64] = {}, error[48] = {};
};
QueueHandle_t replies;
Sample latest, shown;

void network(void *) {
  uint32_t retry = 3000;
  for (;;) {
    Sample result;
    if (WiFi.status() != WL_CONNECTED) {
      snprintf(result.error, sizeof(result.error), "WIFI OFFLINE");
    } else {
      String base = API_BASE_URL;
      bool tls = base.startsWith("https://");
      WiFiClient plain;
      WiFiClientSecure secure;
      HTTPClient http;
      bool allowed = tls ? strlen(ROOT_CA) && time(nullptr) > 1700000000
                         : base.startsWith("http://") && ALLOW_LAN_HTTP;
      if (tls) secure.setCACert(ROOT_CA);
      http.useHTTP10(true);
      http.setConnectTimeout(4000);
      http.setTimeout(4000);
      String url = base + "/api/v1/satellites/25544/state?group=stations";
      bool begun = false;
      if (allowed) {
        if (tls) begun = http.begin(secure, url);
        else begun = http.begin(plain, url);
      }
      if (!begun) {
        snprintf(result.error, sizeof(result.error), "CHECK URL / CA / CLOCK");
      } else {
        if (strlen(API_TOKEN)) http.addHeader("Authorization", String("Bearer ") + API_TOKEN);
        int code = http.GET();
        if (code == 200 && http.getSize() > 0 && http.getSize() <= 4096) {
          JsonDocument filter, doc;
          for (const char *key : {"name", "utc", "altitude_km", "velocity_km_s", "latitude_deg", "longitude_deg", "elements_stale"}) filter[key] = true;
          // Filter on the stream, avoiding a duplicate whole-response String.
          auto err = deserializeJson(doc, http.getStream(), DeserializationOption::Filter(filter), DeserializationOption::NestingLimit(8));
          if (!err && doc["utc"].is<const char *>() && doc["altitude_km"].is<float>() && doc["velocity_km_s"].is<float>()) {
            result.valid = true;
            result.altitude = doc["altitude_km"];
            result.speed = doc["velocity_km_s"];
            result.lat = doc["latitude_deg"] | 0.0f;
            result.lon = doc["longitude_deg"] | 0.0f;
            result.oldElements = doc["elements_stale"] | true;
            strlcpy(result.utc, doc["utc"].as<const char *>(), sizeof(result.utc));
            strlcpy(result.name, doc["name"] | "UNKNOWN", sizeof(result.name));
            result.received = millis();
          } else snprintf(result.error, sizeof(result.error), "INVALID API JSON");
        } else snprintf(result.error, sizeof(result.error), "API HTTP %d", code);
      }
      http.end();
    }
    xQueueOverwrite(replies, &result);
    retry = result.valid ? 3000 : min(retry * 2, uint32_t(60000));
    vTaskDelay(pdMS_TO_TICKS(retry));
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(7, INPUT_PULLUP); pinMode(8, INPUT_PULLUP);
  SPI.begin(12, 13, 11, 10);
  pinMode(LOW_BATTERY_PIN, INPUT_PULLUP);
  analogReadResolution(12);
  ledcSetup(BACKLIGHT_CHANNEL, 5000, 8);
  ledcAttachPin(BACKLIGHT_PIN, BACKLIGHT_CHANNEL);
  ledcWrite(BACKLIGHT_CHANNEL, 100);
  // begin() takes SPI frequency, not the controller type (selected above).
  display.begin(16000000); display.setRotation(1);
  display.setTextWrap(false);
  display.fillScreen(HX8357_BLACK);
  WiFi.mode(WIFI_STA); WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  replies = xQueueCreate(1, sizeof(Sample));
  if (!replies || xTaskCreate(network, "api", 12288, nullptr, 1, nullptr) != pdPASS) {
    display.setCursor(8, 8); display.setTextColor(HX8357_GREEN); display.print("STARTUP FAILED");
    for (;;) delay(1000);
  }
}

void loop() {
  static uint32_t redraw = 0, changed = 0;
  static bool rawHold = false, hold = false;
  static uint32_t controlsAt = 0, lowSince = 0;
  static int brightness = 1600;
  static bool lowBattery = false;
  if (millis() - controlsAt >= 20) {
    controlsAt = millis();
    brightness = (brightness * 7 + analogRead(POT_PIN)) / 8;
    ledcWrite(BACKLIGHT_CHANNEL, map(brightness, 0, 4095, 12, 255));
    // LBO is translated through an NPN: HIGH means low battery. Never wire LBO directly.
    if (digitalRead(LOW_BATTERY_PIN) == HIGH) {
      if (!lowSince) lowSince = millis();
      lowBattery = millis() - lowSince >= 2000;
    } else { lowSince = 0; lowBattery = false; }
  }
  bool raw = digitalRead(7) == LOW;
  if (raw != rawHold) { rawHold = raw; changed = millis(); }
  if (millis() - changed > 25) hold = rawHold;
  Sample incoming;
  if (xQueueReceive(replies, &incoming, 0) == pdTRUE) {
    if (incoming.valid) latest = incoming;
    else strlcpy(latest.error, incoming.error, sizeof(latest.error));
  }
  if (!hold) shown = latest;
  if (millis() - redraw >= 1000) {
    redraw = millis();
    display.fillScreen(HX8357_BLACK);
    display.setTextSize(2); display.setTextColor(HX8357_GREEN);
    display.setCursor(8, 8); display.print("ORBIT / TELEMETRY");
    display.setCursor(8, 44);
    display.print(hold ? "HOLD" : "LIVE");
    if (!shown.valid || millis() - shown.received > 10000) display.print("  STALE/OFFLINE");
    display.setTextSize(1);
    display.setCursor(8, 82); display.print(shown.name);
    display.setCursor(8, 100); display.print(shown.utc);
    if (shown.valid) {
      display.setTextSize(2);
      display.setCursor(8, 132); display.printf("ALT %.1f km", shown.altitude);
      display.setCursor(8, 172); display.printf("VEL %.2f km/s", shown.speed);
      if (digitalRead(8) == LOW) {
        display.setTextSize(1); display.setCursor(8, 216);
        display.printf("LAT %.2f  LON %.2f", shown.lat, shown.lon);
      }
    }
    display.setTextSize(1); display.setCursor(8, 248);
    if (shown.oldElements) display.print("OLD ELEMENTS >7 DAYS");
    display.setCursor(8, 268); display.print(latest.error);
    display.setCursor(8, 296);
    if (lowBattery) display.print("LOW BATTERY - CONNECT CHARGER / SWITCH OFF");
  }
  delay(2);
}
