#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 Smart Gesture-Controlled Industrial Valve System — HMI (Human Machine Interface)
================================================================================

 Computer-vision SCADA front-end:
   * Tracks one hand with MediaPipe Hands.
   * Measures the thumb-index "pinch" distance, normalized by hand size and
     mapped to a 0-100 % valve-opening setpoint.
   * Renders an industrial HUD (circular gauge, valve angle, system status).
   * Streams the setpoint to the Arduino firmware over serial as a single
     byte (0..10). Runs standalone (simulation mode) when no board is found.

 Safety logic:
   * > 90 % for 10 s  ->  emergency shutdown (system lock).
   * Lock is released by fully closing the pinch (< 5 %).

 Usage:
     python gesture_scada.py [--port COM4] [--baud 9600] [--camera 0]
                             [--width 1280] [--height 720]

 Controls:
     Left click (welcome screen) : start system
     Q                          : quit

 Released under the MIT License.
================================================================================
"""

import argparse
import math
import sys
import time

import cv2
import numpy as np

# ---- Optional dependencies (project is usable without a serial board) -------
try:
    import serial
except ImportError:                                    # nochannel: dry-run mode
    serial = None

try:
    import mediapipe as mp
except ImportError:
    sys.exit("MediaPipe is required:  pip install mediapipe")

try:
    from PIL import Image, ImageDraw, ImageFont
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_UI = True
except ImportError:                                    # Fall back to English UI
    ARABIC_UI = False

if sys.platform == "win32":
    import winsound
else:
    winsound = None


# ============================== Configuration =================================

SMOOTHING_FACTOR   = 0.15    # EMA factor; lower = smoother motion
PINCH_RATIO_MIN    = 0.25    # Calibration: pinch ratio -> 0 %
PINCH_RATIO_MAX    = 1.20    # Calibration: pinch ratio -> 100 %
DEAD_ZONE_LOW      = 3       # % snap-to-zero threshold (anti-jitter)
DEAD_ZONE_HIGH     = 97      # % snap-to-full threshold (anti-jitter)
DANGER_THRESHOLD   = 90      # % -> warning state
SHUTDOWN_DELAY_S   = 10.0    # s above threshold before emergency lock
UNLOCK_LEVEL       = 5       # % below which the emergency lock releases

# Landmark indices (MediaPipe Hands)
LM_THUMB_TIP, LM_INDEX_TIP = 4, 8
LM_WRIST, LM_MIDDLE_MCP    = 0, 9

# UI palette (BGR)
COLOR_BG     = (25, 25, 25)
COLOR_ACCENT = (0, 255, 255)
COLOR_DANGER = (0, 0, 255)
COLOR_SAFE   = (0, 255, 0)
COLOR_TEXT   = (255, 255, 255)
COLOR_MUTED  = (200, 200, 200)
COLOR_BAR    = (10, 10, 10)

FONT_PATHS = ("arial.ttf", "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


# ============================== UI helpers ====================================

_font_cache = {}                      # Avoid re-loading TTF fonts every frame


def load_font(size: int):
    """Load a TrueType font once per size (major perf. win over per-frame load)."""
    if size not in _font_cache:
        for path in FONT_PATHS:
            try:
                _font_cache[size] = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
        else:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def put_text(img, text, pos, size=30, color=(255, 255, 255)):
    """Draw text (Arabic-aware, RTL-shaped) onto a BGR numpy frame."""
    if ARABIC_UI:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        pil = Image.fromarray(img)
        ImageDraw.Draw(pil).text(pos, bidi_text, font=load_font(size), fill=color)
        return np.asarray(pil)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_DUPLEX, size / 30.0, color, 2)
    return img


def beep(freq, dur):
    if winsound:
        try:
            winsound.Beep(freq, dur)
        except RuntimeError:
            pass


def draw_gauge(img, center, radius, percentage, color):
    """Industrial circular gauge: 135 deg -> 405 deg sweep."""
    cv2.ellipse(img, center, (radius, radius), 0, 135, 405, (50, 50, 50), 15)
    end_angle = 135 + (270 * percentage / 100.0)
    cv2.ellipse(img, center, (radius, radius), 0, 135, end_angle, color, 15)
    text = f"{int(percentage)}%"
    org  = (center[0] - 44, center[1] + 12)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_DUPLEX, 1.5, COLOR_TEXT, 2)


# ============================== Serial link ===================================

class SerialLink:
    """Thin wrapper with graceful degradation when no board / pyserial exists."""

    def __init__(self, port, baud):
        self.connected = False
        self._board = None
        if serial is None or not port:
            return
        try:
            self._board = serial.Serial(port, baud, timeout=1)
            time.sleep(2)                       # Arduino auto-reset grace period
            self.connected = True
        except (OSError, serial.SerialException):
            self._board = None

    def send(self, level: int) -> None:
        if self._board is not None:
            try:
                self._board.write(bytes([level]))
            except (OSError, serial.SerialException):
                self.connected = False

    def close(self):
        if self._board is not None:
            try:
                self._board.close()
            except OSError:
                pass


# ============================== Main loop =====================================

def parse_args():
    p = argparse.ArgumentParser(description="Gesture-controlled valve HMI")
    p.add_argument("--port",   default="COM4",     help="Serial port (default COM4)")
    p.add_argument("--baud",   type=int, default=9600, help="Baud rate (default 9600)")
    p.add_argument("--camera", type=int, default=0,    help="Camera index (default 0)")
    p.add_argument("--width",  type=int, default=1280, help="Window width")
    p.add_argument("--height", type=int, default=720, help="Window height")
    return p.parse_args()


def main():
    args = parse_args()

    state = {
        "mode": "WELCOME",            # WELCOME | RUNNING
        "locked": False,
        "warning_since": 0.0,
        "warning": False,
        "smoothed": 0.0,
        "last_sent": -1,              # Serial send-on-change cache
        "btn": (500, 400, 780, 480),  # Start-button hitbox
    }

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN and state["mode"] == "WELCOME":
            bx1, by1, bx2, by2 = state["btn"]
            if bx1 < x < bx2 and by1 < y < by2:
                state["mode"] = "RUNNING"
                beep(1000, 100)

    link = SerialLink(args.port, args.baud)

    hands = mp.solutions.hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.8,
        min_tracking_confidence=0.8,
    )
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        sys.exit(f"Cannot open camera {args.camera}")

    win = "Industrial SCADA System"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, on_mouse)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            img = cv2.flip(cv2.resize(frame, (args.width, args.height)), 1)

            if state["mode"] == "WELCOME":
                img = draw_welcome(img, link.connected, state["btn"])
            else:
                img = draw_running(img, hands, link, state)

            cv2.imshow(win, img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        hands.close()
        cap.release()
        cv2.destroyAllWindows()
        link.close()


def draw_welcome(img, connected, btn):
    """Welcome / splash screen with connection status and start button."""
    img[:] = COLOR_BG
    img = put_text(img, "نظام التحكم الصناعي الذكي",        (420, 150), 50, COLOR_ACCENT)
    img = put_text(img, "مشروع التخرج - محاكاة SCADA",      (480, 230), 30, COLOR_MUTED)

    bx1, by1, bx2, by2 = btn
    cv2.rectangle(img, (bx1, by1), (bx2, by2), (0, 100, 0), cv2.FILLED)
    cv2.rectangle(img, (bx1, by1), (bx2, by2), COLOR_SAFE, 2)
    img = put_text(img, "تشغيل النظام", (560, 415), 35, COLOR_TEXT)

    status = "متصل" if connected else "مفصول (محاكاة)"
    color  = COLOR_SAFE if connected else COLOR_DANGER
    img = put_text(img, f"حالة الاتصال: {status}", (50, 650), 20, color)
    return img


def draw_running(img, hands, link, state):
    """Main SCADA screen: hand tracking + HUD + safety logic."""
    h, w = img.shape[:2]

    # Dark sidebar for the HUD
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (350, h), (20, 20, 20), cv2.FILLED)
    img = cv2.addWeighted(overlay, 0.85, img, 0.15, 0)

    percentage = energy = angle = 0
    locked = state["locked"]
    now = time.time()

    # ---- Emergency-lock screen -------------------------------------------
    if locked:
        cv2.rectangle(img, (0, 0), (w, h), (0, 0, 50), cv2.FILLED)
        img = put_text(img, "توقف طارئ للنظام!",       (450, 300), 50, COLOR_DANGER)
        img = put_text(img, "أغلق يدك لإعادة التشغيل",  (480, 400), 30, COLOR_TEXT)

    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if results.multi_hand_landmarks:
        lms = [(int(lm.x * w), int(lm.y * h))
               for lm in results.multi_hand_landmarks[0].landmark]

        x1, y1 = lms[LM_THUMB_TIP]
        x2, y2 = lms[LM_INDEX_TIP]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        # Size-invariant pinch ratio
        ref = math.hypot(lms[LM_MIDDLE_MCP][0] - lms[LM_WRIST][0],
                         lms[LM_MIDDLE_MCP][1] - lms[LM_WRIST][1]) or 1.0
        ratio = math.hypot(x2 - x1, y2 - y1) / ref

        # Calibration + exponential smoothing + edge dead zones
        target = float(np.interp(ratio, [PINCH_RATIO_MIN, PINCH_RATIO_MAX], [0, 100]))
        state["smoothed"] += (target - state["smoothed"]) * SMOOTHING_FACTOR
        percentage = int(state["smoothed"])
        if percentage < DEAD_ZONE_LOW:
            percentage = 0
        elif percentage > DEAD_ZONE_HIGH:
            percentage = 100

        energy = round(percentage / 10)                 # 0..10 protocol level
        angle  = round(percentage * 1.8)                # 0..180 deg valve angle

        # ---- Release the emergency lock ------------------------------------
        if locked:
            if percentage < UNLOCK_LEVEL:
                state["locked"] = False
                state["warning"] = False
                state["smoothed"] = 0.0
            return img

        # ---- Over-pressure warning / auto shutdown -------------------------
        line_color = COLOR_ACCENT
        if percentage > DANGER_THRESHOLD:
            if not state["warning"]:
                state["warning"], state["warning_since"] = True, now
            elapsed   = now - state["warning_since"]
            remaining = max(0, int(SHUTDOWN_DELAY_S - elapsed))
            line_color = COLOR_DANGER

            if int(now * 5) % 2 == 0:                   # Blinking danger halo
                cv2.circle(img, (cx, cy), 130, COLOR_DANGER, 4)
            img = put_text(img, f"إغلاق تلقائي: {remaining}",
                           (cx - 80, cy - 130), 25, COLOR_DANGER)
            if int(now * 2) % 2 == 0:
                beep(2500, 50)

            if elapsed > SHUTDOWN_DELAY_S:
                state["locked"] = True
                link.send(0)                            # Fail-safe: close valve
                beep(500, 1000)
        else:
            state["warning"] = False

        # ---- Hand overlay ----------------------------------------------------
        cv2.line(img, (x1, y1), (x2, y2), line_color, 3)
        cv2.circle(img, (x1, y1), 8, line_color, cv2.FILLED)
        cv2.circle(img, (x2, y2), 8, line_color, cv2.FILLED)

        # ---- Serial: send on change only (bus + CPU friendly) ---------------
        if not state["locked"] and energy != state["last_sent"]:
            link.send(energy)
            state["last_sent"] = energy
    else:
        state["warning"] = False
        state["smoothed"] = 0.0
        if not state["locked"] and state["last_sent"] != 0:
            link.send(0)                                # No hand -> valve closed
            state["last_sent"] = 0

    # ---- Sidebar HUD --------------------------------------------------------
    if not state["locked"]:
        img = put_text(img, "لوحة البيانات", (60, 50), 40, COLOR_ACCENT)

        gauge_color = COLOR_SAFE
        if percentage > 60:
            gauge_color = COLOR_ACCENT
        if percentage > DANGER_THRESHOLD:
            gauge_color = COLOR_DANGER
        draw_gauge(img, (175, 200), 100, percentage, gauge_color)

        img = put_text(img, "زاوية الصمام:", (30, 350), 25, COLOR_MUTED)
        cv2.putText(img, f"{angle} deg", (30, 400),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLOR_TEXT, 2)

        img = put_text(img, "حالة النظام:", (30, 460), 25, COLOR_MUTED)
        status = "مستقر"
        if percentage > DANGER_THRESHOLD:
            status = "خطر مرتفع"
        elif percentage == 0:
            status = "مغلق"
        img = put_text(img, status, (30, 510), 30, gauge_color)

        # Connection footer
        cv2.rectangle(img, (0, h - 40), (w, h), COLOR_BAR, cv2.FILLED)
        if link.connected:
            img = put_text(img, "متصل بالأردوينو", (20, h - 35), 20, COLOR_SAFE)
        else:
            img = put_text(img, "وضع المحاكاة (مفصول)", (20, h - 35), 20, COLOR_DANGER)
        img = put_text(img, "اضغط Q للخروج", (w - 200, h - 35), 20, COLOR_TEXT)

    return img


if __name__ == "__main__":
    main()
