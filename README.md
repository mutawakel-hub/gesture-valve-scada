# Smart Gesture-Controlled Industrial Valve System

<p align="center">
  <b>Computer-vision SCADA system that drives a servo valve with hand-gesture input — Python + Arduino + SimulIDE.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/platform-Arduino%20UNO%20%7C%20SimulIDE-teal" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT">
</p>

---

## 📖 Overview

An industrial-style **Human–Machine Interface (HMI)** where the operator controls a
process valve using a simple **pinch gesture**. A webcam tracks the hand with
MediaPipe, the thumb–index distance is normalized by hand size and mapped to a
**0–100 %** valve setpoint, and the level is streamed to an Arduino over serial.
The firmware positions a **servo-driven valve (0–180°)** and lights a **10-LED
bargraph**. The whole plant can also run **virtually** in SimulIDE — no hardware
required.

```
        ┌─────────────────────┐   serial (1 byte, 0-10)   ┌──────────────────────┐
 🖐️ →   │  Python HMI         │ ───────────────────────▶  │  Arduino UNO         │
        │  OpenCV + MediaPipe │      9600 baud, 8N1       │  servo valve + LEDs  │
        └─────────────────────┘                           └──────────────────────┘
              real COM port — or — SimulIDE SerialPort bridge (virtual COM pair)
```

## ✨ Features

- **Gesture control** — size-invariant pinch detection (works at any distance from the camera)
- **Signal conditioning** — exponential smoothing (EMA) + edge dead-zones for jitter-free readings
- **Industrial HUD** — circular gauge, valve angle readout, live status bar, Arabic RTL UI
- **Safety interlock** — holding > 90 % for 10 s triggers an emergency shutdown; releasing the pinch (< 5 %) restarts the system
- **Acoustic alarms** — warning beeps at high level, siren on shutdown
- **Simulation ready** — SimulIDE circuit with serial-port bridge so the HMI can drive the virtual plant
- **Graceful degradation** — runs in standalone simulation mode when no board is connected
- **Efficient serial protocol** — single byte per update, sent only when the level changes

## 📂 Repository Structure

```
.
├── firmware/
│   └── valve_controller/
│       ├── valve_controller.ino   # Arduino sketch (servo + LED bargraph)
│       └── firmware.hex           # Prebuilt binary loaded by the SimulIDE circuit
├── software/
│   └── gesture_scada.py           # Python HMI (OpenCV + MediaPipe + serial)
├── simulation/
│   └── valve_system.sim1          # SimulIDE circuit (UNO + servo + 10 LEDs + serial bridge)
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
```

## 🚀 Quick Start

### 1. Python HMI

```bash
# 1) Install dependencies
pip install -r requirements.txt

# 2) Run (adjust --port to your Arduino / virtual COM pair)
python software/gesture_scada.py --port COM4
```

Useful flags:

| Flag                   | Default        | Description                                                               |
| ---------------------- | -------------- | ------------------------------------------------------------------------- |
| `--port`               | `COM4`         | Serial port (`--port none` style disable by leaving pyserial uninstalled) |
| `--baud`               | `9600`         | Baud rate (must match firmware)                                           |
| `--camera`             | `0`            | Webcam index                                                              |
| `--width` / `--height` | `1280` / `720` | HMI window size                                                           |

### 2. Real Hardware

1. Flash [`firmware/valve_controller/valve_controller.ino`](firmware/valve_controller/valve_controller.ino) onto an Arduino UNO using the Arduino IDE.
2. Wire the plant:
   - Servo signal → **D12** (servo power from external 5 V recommended)
   - LED bargraph anodes → **D2 … D11** (with ~220 Ω resistors), cathodes → GND
3. Note the board's COM port and launch the HMI with `--port <COMx>`.

### 3. Virtual Plant (SimulIDE)

1. Download [SimulIDE](https://www.simulide.com/p/home.html) (1.1.0 or newer).
2. Open [`simulation/valve_system.sim1`](simulation/valve_system.sim1).
3. The circuit already loads `../firmware/valve_controller/firmware.hex` into the virtual UNO.
4. Attach the circuit's **SerialPort** element to a virtual COM pair and point the HMI at it
   (e.g. `com0com` on Windows, `socat` on Linux), or simply run the HMI in simulation mode.

## 🔧 How It Works

### Gesture → Setpoint (Python)

1. MediaPipe Hands extracts 21 landmarks per frame.
2. `pinch = |thumb_tip − index_tip| / |wrist − middle_mcp|` gives a **scale-invariant** ratio.
3. The ratio is calibrated to 0–100 % (`0.25 → 0 %`, `1.20 → 100 %`), then smoothed with an
   exponential moving average (`α = 0.15`) and snapped by dead-zones (`<3 % → 0`, `>97 % → 100`).
4. The percentage is quantized to 10 steps (`0–10`) and sent as **one byte**, only on change.

### Setpoint → Actuation (Arduino)

1. `loop()` polls the serial port; every valid byte is clamped to `0..10`.
2. Redundant levels are skipped (prevents servo jitter).
3. Level → servo angle via `map(level, 0, 10, 0, 180)`; the bargraph lights `level` LEDs.

### Safety State Machine

```
        normal (< 90 %)                > 90 % held 10 s
  ┌──────────────────────┐         ┌──────────────────────┐
  │        RUN           │ ─────▶  │   EMERGENCY LOCK     │
  │  valve follows hand  │ ◀─────  │  valve forced to 0   │
  └──────────────────────┘  pinch  └──────────────────────┘
                            < 5 %
```

## 📡 Serial Protocol

| Direction | Payload         | Meaning                                          |
| --------- | --------------- | ------------------------------------------------ |
| HMI → MCU | 1 byte, `0..10` | Target valve level (0 = closed, 10 = fully open) |

9600 baud, 8 data bits, no parity, 1 stop bit.

## 🛠️ Tech Stack

| Layer        | Technology                                                                  |
| ------------ | --------------------------------------------------------------------------- |
| HMI / Vision | Python 3.9+, OpenCV, MediaPipe, NumPy, Pillow, arabic-reshaper, python-bidi |
| Firmware     | Arduino C++ (Servo library), ATmega328P @ 16 MHz                            |
| Simulation   | SimulIDE 1.1.0 (Arduino UNO + servo + LEDs + serial bridge)                 |
| Audio        | Windows `winsound` (optional, platform-guarded)                             |

## 📄 License

Distributed under the MIT License — see [`LICENSE`](LICENSE).
