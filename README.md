Понял тебя, косяк! Сейчас сделаем по красоте: весь текст целиком в одном Markdown-блоке, чтобы ты просто скопировал и вставил в свой `README.md`, включая готовый блок для `requirements.txt`.

Копируй вот это:

```markdown
# 🌸 PinkPad

> Turn your **8BitDo Ultimate C** controller into a remote mouse and media companion for macOS.

**PinkPad** is a lightweight Python script that lets you control your Mac right from your couch or bed using your 8BitDo controller. Built with Python, Pygame, and PyObjC.

---

## ✨ Features

* **Mouse Navigation** — Control the mouse cursor smoothly using the **Left Stick**.
* **Media Controls** — Adjust system volume using the **`-` and `+`** buttons.
* **Playback / Power** — Use the **Logo / Start** button as a pause/play or controller state toggle.
* **Scrolling** — Scroll up, down, left, and right using the **D-Pad**.
* **Button Mapping / Learning Mode** — Built-in calibration tool to easily adapt or map your controller layout via `--learn`.

---

## 🛠️ Requirements

* **macOS** (Tested on Apple Silicon MacBooks)
* **Python 3**
* An **8BitDo Ultimate C** controller (connected via Bluetooth or 2.4g wireless).

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/pinkpad.git](https://github.com/YOUR_USERNAME/pinkpad.git)
   cd pinkpad

```

2. **Create and activate a virtual environment:**
```bash
python3 -m venv pinkpad-env
source pinkpad-env/bin/activate

```


3. **Create the `requirements.txt` file:**
Создай файл `requirements.txt` в корне проекта и добавь туда следующие зависимости:
```text
pygame==2.6.1
pyobjc-core==11.1
pyobjc-framework-ApplicationServices==11.1
pyobjc-framework-Cocoa==11.1
pyobjc-framework-CoreText==11.1
pyobjc-framework-Quartz==11.1
rumps==0.4.0

```


4. **Install dependencies:**
```bash
pip install -r requirements.txt

```



---

## 🎮 Usage

Make sure your virtual environment is active and your controller is connected, then:

* **First run / Calibrate mappings:**
```bash
python3 pinkpad.py --learn

```


*(Follow the on-screen prompts to press your controller buttons).*
* **Run PinkPad normally:**
```bash
python3 pinkpad.py

```



---

## ⚠️ Known Quirks & Notes

* **Focus jump on volume change:** When adjusting the volume using `-` or `+`, the Python terminal window might occasionally pop up or steal focus for a moment. Don't worry—it usually settles down and calms itself after a minute.
* **Triggers:** Left and right triggers (`LT` / `RT`) are wired in, though sensitivity/speed scaling is still experimental. Feel free to test them out!

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

```

```
