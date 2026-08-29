<div dir="rtl" align="center">

# 🎯 نظام التحكم بالصمام الصناعي بالإيماءات الذكية

**واجهة SCADA بالرؤية الحاسوبية تتحكم بصمام سيرفو عبر حركة القبضة — Python + Arduino + SimulIDE**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Arduino](https://img.shields.io/badge/Arduino-UNO-00979D?logo=arduino&logoColor=white)](https://arduino.cc)
[![SimulIDE](https://img.shields.io/badge/Simulation-SimulIDE%201.1.0-teal)](https://simulide.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](#-quick-start--التشغيل-السريع)

[English](#-overview) | [العربية](#-نظرة-عامة)

</div>

---

<div dir="rtl">

## 📖 نظرة عامة

نظام تحكم صناعي ذكي يتيح للمشغّل التحكم بصمام عملية صناعية باستخدام **حركة القبضة (Pinch)** فقط. تتتبع الكاميرا اليد عبر مكتبة MediaPipe، وتُطبَّع المسافة بين الإبهام والسبابة حسب حجم اليد وتحوَّل إلى قيمة ضبط **0–100%**، ثم تُرسَل للأردوينو عبر المنفذ التسلسلي. بدوره يحرّك الفيرموير **صمام السيرفو (0–180°)** ويضيء **شريطاً من 10 ليدات**. ويمكن تشغيل النظام كاملاً **افتراضياً** في SimulIDE دون أي عتاد.

</div>

```
        ┌─────────────────────┐   serial (1 byte, 0-10)   ┌──────────────────────┐
 🖐️ →   │  واجهة Python HMI   │ ───────────────────────▶  │  Arduino UNO         │
        │  OpenCV + MediaPipe │      9600 baud, 8N1       │  صمام سيرفو + ليدات  │
        └─────────────────────┘                           └──────────────────────┘
              منفذ COM حقيقي — أو — جسر SimulIDE التسلسلي (زوج COM افتراضي)
```

<div dir="rtl">

## ✨ المميزات

| الميزة                 | الوصف                                                                             |
| ---------------------- | --------------------------------------------------------------------------------- |
| 🖐️ **تحكم بالإيماءات** | كشف قبضة غير معتمد على الحجم — يعمل على أي مسافة من الكاميرا                      |
| 📊 **تكييف الإشارة**   | تنعيم أُسّي (EMA) + مناطق موت عند الأطراف لقراءات خالية من الاهتزاز               |
| 🖥️ **واجهة صناعية**    | عداد دائري، قراءة زاوية الصمام، شريط حالة مباشر، واجهة عربية RTL                  |
| 🚨 **قفل أمان**        | البقاء فوق 90% لمدة 10 ثوانٍ يفعّل إيقافاً طارئاً؛ فتح القبضة (< 5%) يعيد التشغيل |
| 🔊 **إنذارات صوتية**   | نغمات تحذير عند المستوى العالي وصفارة عند الإغلاق الطارئ                          |
| 🎛️ **جاهزية المحاكاة** | دائرة SimulIDE مع جسر تسلسلي لتشغيل المصنع الافتراضي من الواجهة                   |
| 🛡️ **تدهور آمن**       | يعمل بوضع المحاكاة المستقل عند عدم توصيل لوحة، ويغلق الصمام عند فقدان اليد        |
| ⚡ **بروتوكول خفيف**   | بايت واحد لكل تحديث، يُرسَل فقط عند تغيّر القيمة                                  |

</div>

---

<div align="center">

[**⬆ Back to Top / العودة للأعلى ⬆**](#-نظام-التحكم-بالصمام-الصناعي-بالإيماءات-الذكية)

</div>

## 🇬🇧 Overview

An industrial-style **Human–Machine Interface (HMI)** where the operator controls a process valve using a simple **pinch gesture**. A webcam tracks the hand with MediaPipe; the thumb–index distance is normalized by hand size and mapped to a **0–100 %** valve setpoint, then streamed to an Arduino over serial. The firmware positions a **servo-driven valve (0–180°)** and lights a **10-LED bargraph**. The whole plant also runs **virtually** in SimulIDE — no hardware required.

## ✨ Features

| Feature                     | Description                                                                               |
| --------------------------- | ----------------------------------------------------------------------------------------- |
| 🖐️ **Gesture control**      | Size-invariant pinch detection — works at any distance from the camera                    |
| 📊 **Signal conditioning**  | Exponential smoothing (EMA) + edge dead-zones for jitter-free readings                    |
| 🖥️ **Industrial HUD**       | Circular gauge, valve-angle readout, live status bar, Arabic RTL UI                       |
| 🚨 **Safety interlock**     | Holding > 90 % for 10 s triggers emergency shutdown; releasing the pinch (< 5 %) restarts |
| 🔊 **Acoustic alarms**      | Warning beeps at high level, siren on shutdown                                            |
| 🎛️ **Simulation ready**     | SimulIDE circuit with serial-port bridge driving the virtual plant                        |
| 🛡️ **Graceful degradation** | Standalone simulation mode without a board; fail-safe valve closure on hand loss          |
| ⚡ **Efficient protocol**   | Single byte per update, sent only when the level changes                                  |

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
├── README.md                      # This file
├── LICENSE                        # MIT License
├── requirements.txt               # Python dependencies
├── .gitignore
└── .gitattributes
```

## 🚀 Quick Start

### 1️⃣ Python HMI

```bash
# Install dependencies
pip install -r requirements.txt

# Run (adjust --port to your Arduino / virtual COM pair)
python software/gesture_scada.py --port COM4
```

<details>
<summary><b>Command-line flags</b></summary>

| Flag                   | Default        | Description                                 |
| ---------------------- | -------------- | ------------------------------------------- |
| `--port`               | `COM4`         | Serial port of the board / virtual COM pair |
| `--baud`               | `9600`         | Baud rate (must match firmware)             |
| `--camera`             | `0`            | Webcam index                                |
| `--width` / `--height` | `1280` / `720` | HMI window size                             |

</details>

### 2️⃣ Real Hardware

1. Flash [`firmware/valve_controller/valve_controller.ino`](firmware/valve_controller/valve_controller.ino) onto an Arduino UNO (Arduino IDE).
2. Wire the plant:

   | Component           | Connection                               |
   | ------------------- | ---------------------------------------- |
   | Servo signal        | **D12** (external 5 V power recommended) |
   | LED bargraph anodes | **D2 … D11** via ~220 Ω resistors        |
   | LED cathodes        | GND                                      |

3. Launch the HMI with your board's COM port: `python software/gesture_scada.py --port COMx`.

### 3️⃣ Virtual Plant (SimulIDE)

1. Download [SimulIDE](https://www.simulide.com/p/home.html) (1.1.0 or newer).
2. Open [`simulation/valve_system.sim1`](simulation/valve_system.sim1).
3. The circuit auto-loads `../firmware/valve_controller/firmware.hex` into the virtual UNO.
4. Attach the circuit's **SerialPort** element to a virtual COM pair (`com0com` on Windows, `socat` on Linux) and point the HMI at it — or run the HMI in standalone simulation mode.

## 🔧 How It Works

### Gesture → Setpoint (Python)

1. MediaPipe Hands extracts 21 landmarks per frame.
2. `pinch = |thumb_tip − index_tip| / |wrist − middle_mcp|` → **scale-invariant** ratio.
3. Ratio calibrated to 0–100 % (`0.25 → 0 %`, `1.20 → 100 %`), smoothed with an EMA (`α = 0.15`), snapped by dead-zones (`<3 % → 0`, `>97 % → 100`).
4. Quantized to 10 steps (`0–10`) and sent as **one byte**, only on change.

### Setpoint → Actuation (Arduino)

1. `loop()` polls the serial port; each valid byte is clamped to `0..10`.
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

_9600 baud, 8 data bits, no parity, 1 stop bit._

## 🛠️ Tech Stack

| Layer        | Technology                                                                  |
| ------------ | --------------------------------------------------------------------------- |
| HMI / Vision | Python 3.9+, OpenCV, MediaPipe, NumPy, Pillow, arabic-reshaper, python-bidi |
| Firmware     | Arduino C++ (Servo library), ATmega328P @ 16 MHz                            |
| Simulation   | SimulIDE 1.1.0 (Arduino UNO + servo + LEDs + serial bridge)                 |
| Audio        | Windows `winsound` (optional, platform-guarded)                             |

<div dir="rtl">

## 🤝 المساهمة | Contributing

1. اعمل Fork للمستودع ثم أنشئ فرعاً جديداً: `git checkout -b feature/amazing`
2. اكتب تعديلاتك مع الالتزام بأسلوب الكود الحالي
3. أضف توثيقاً مناسباً واختبر التغييرات
4. افتح Pull Request بوصف واضح

## 📄 الترخيص | License

هذا المشروع مرخّص بموجب **رخصة MIT** — راجع ملف [`LICENSE`](LICENSE).

هذا المشروع جزء من مشروع تخرج جامعي في الذكاء الاصطناعي والأنظمة المضمنة.

</div>

## 📄 License

Distributed under the **MIT License** — see [`LICENSE`](LICENSE).

This project is part of a university graduation project in AI and embedded systems.

---

<div align="center">

**⭐ If you find this project useful, consider giving it a star! ⭐**

</div>
