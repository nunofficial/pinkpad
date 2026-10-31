<!--
  ╔══════════════════════════════════════════════════════════════════════╗
  ║  📸 PLACES FOR YOUR PICTURES  (create an `assets/` folder in the repo) ║
  ╠══════════════════════════════════════════════════════════════════════╣
  ║  assets/logo.png            – logo, square, ~512×512, transparent bg   ║
  ║  assets/demo.gif            – short demo (cursor, scroll, desktops…)   ║
  ║  assets/controller-map.png  – photo/diagram of the controller + labels ║
  ║  assets/terminal.png        – screenshot of the pink terminal output   ║
  ║  assets/permissions.png     – screenshot of Accessibility settings     ║
  ║  Delete this comment when you're done.                                 ║
  ╚══════════════════════════════════════════════════════════════════════╝
-->

<div align="center">

<img src="Pinkpad Retro Gaming Logo.png" alt="PinkPad logo" width="160">

# 🎀 PinkPad

**Control your Mac with a game controller.**
Mouse · clicks · scrolling · desktop switching · volume · on-screen keyboard.

Made for the pink **8BitDo Ultimate 2C** 💖 — one Python file, no Docker, runs in the background.

![macOS](https://img.shields.io/badge/macOS-only-ff69b4?logo=apple&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9%2B-ff69b4?logo=python&logoColor=white)
![Controller](https://img.shields.io/badge/8BitDo-Ultimate%202C-ff69b4)
<!-- ![License](https://img.shields.io/badge/license-MIT-ff69b4) -->

<img src="assets/demo.gif" alt="PinkPad demo" width="720">

</div>

---

## 📖 Table of contents

- [What it does](#-what-it-does)
- [Controls](#-controls)
- [Quick start (TL;DR)](#-quick-start-tldr)
- [Full step-by-step guide (from zero)](#-full-step-by-step-guide-from-zero)
- [Running it in the background](#-running-it-in-the-background)
- [Settings](#%EF%B8%8F-settings)
- [Troubleshooting](#-troubleshooting)
- [How it works](#-how-it-works)
- [Known limitations](#-known-limitations)
- [Privacy & safety](#-privacy--safety)

---

## ✨ What it does

PinkPad turns your controller into a remote control for your whole Mac:

- 🖱️ **Mouse** – smooth, precise cursor with the left stick (native macOS events, no lag), left/right click and drag
- 📜 **Scrolling** – scroll any page with the D-pad (hold it and it speeds up)
- 🖥️ **Desktops (Spaces)** – switch left/right with the bumpers
- 🔊 **Volume** – up/down with the `−` / `+` buttons, with the normal macOS volume pop-up
- ⌨️ **On-screen keyboard** – show/hide macOS's Accessibility Keyboard with one button
- 🎯 **Precision mode** – hold the left trigger to slow everything down for pixel-perfect aiming
- ⏯️ **Pause** – temporarily switch it off (handy when you want to play a game)
- 🎀 **Pink terminal** – because of course

Everything lives in **one file**: [`pinkpad.py`](pinkpad.py).

---

## 🎮 Controls

<div align="center">
<img src="assets/controller-map.png" alt="Controller map" width="640">
</div>

| Controller | What it does |
|---|---|
| **Left stick** | Move the mouse cursor |
| **A** | Left click (hold = drag, double-click works) |
| **X** or **Right trigger (RT)** | Right click |
| **Left trigger (LT)** *(hold)* | Precision mode – slower cursor & scrolling |
| **D-pad** ↑ ↓ ← → | Scroll up / down / left / right (hold = faster) |
| **L1 / LB** | Previous desktop (`Ctrl` + `←`) |
| **R1 / RB** | Next desktop (`Ctrl` + `→`) |
| **`+`** (Start) | Volume up – tap = one step, hold = keeps going |
| **`−`** (Select) | Volume down – tap = one step, hold = keeps going |
| **`−` and `+` together** *or* **Home** | Pause / resume PinkPad |
| **Y** *or* **L3 + R3** (press both sticks) | Show / hide the on-screen keyboard |
| `Ctrl` + `C` in Terminal | Quit |

> 💡 The button for the on-screen keyboard can be changed to any free button with `--learn` (see below).
> ⭐ The little **star** button on the 8BitDo is handled inside the controller and is **not sent to the Mac**, so it can't be used.

---

## ⚡ Quick start (TL;DR)

Already comfortable with Terminal? Here's the short version:

```bash
git clone https://github.com/YOUR_USERNAME/pinkpad.git
cd pinkpad
python3 -m venv pinkpad-env
source pinkpad-env/bin/activate
pip install pygame pyobjc-framework-Quartz pyobjc-framework-ApplicationServices
python3 pinkpad.py --learn     # one-time: teaches −, +, Home and the keyboard button
python3 pinkpad.py
```

Then give your Terminal **Accessibility** + **Input Monitoring** permission and enable the **Mission Control** shortcuts
([steps 5–7](#-full-step-by-step-guide-from-zero)). New to all this? Follow the full guide below. 👇

---

## 🧭 Full step-by-step guide (from zero)

You don't need any programming experience. Just copy the commands exactly as written.

### Step 1 – Open Terminal

Press `⌘ Command` + `Space`, type **Terminal** and press `Enter`. A window with a text prompt opens. This is where you'll paste the commands.

### Step 2 – Check that Python is installed

```bash
python3 --version
```

- If it prints something like `Python 3.9.6` (or higher) – great, go to Step 3.
- If macOS offers to install **command line developer tools**, click **Install** and wait for it to finish, then run the command again.
- Still nothing? Download Python from <https://www.python.org/downloads/> and install it, then restart Terminal.

### Step 3 – Download PinkPad

**Option A – with git** (if you have it):

```bash
cd ~/Documents
git clone https://github.com/YOUR_USERNAME/pinkpad.git
cd pinkpad
```

**Option B – without git:**

1. On this page click the green **Code** button → **Download ZIP**.
2. Unzip it and move the folder to your `Documents`.
3. In Terminal go into the folder (the name may be `pinkpad-main`):

```bash
cd ~/Documents/pinkpad-main
```

> Tip: you can type `cd ` (with a space) and then **drag the folder** from Finder into the Terminal window – it fills in the path for you.

### Step 4 – Install the dependencies

These commands create an isolated "box" for PinkPad's libraries so nothing else on your Mac is touched:

```bash
python3 -m venv pinkpad-env
source pinkpad-env/bin/activate
pip install --upgrade pip
pip install pygame pyobjc-framework-Quartz pyobjc-framework-ApplicationServices
```

When it works, your prompt starts with `(pinkpad-env)`.

> ⚠️ Every time you open a **new** Terminal window you must go to the folder and activate the box again:
> ```bash
> cd ~/Documents/pinkpad
> source pinkpad-env/bin/activate
> ```

### Step 5 – Give Terminal permission to control your Mac

macOS blocks programs from moving the cursor or pressing keys until you allow it. You need **two** permissions for the app you run PinkPad from (**Terminal**, or iTerm / VS Code if you use those).

<div align="center">
<img src="assets/permissions.png" alt="Accessibility permissions" width="640">
</div>

1. Open **System Settings → Privacy & Security → Accessibility**
   *(Russian: Системные настройки → Конфиденциальность и безопасность → Универсальный доступ)*.
2. Click **`+`**, choose **Terminal** (it's in `Applications → Utilities`), and make sure its switch is **on**.
3. Do the same in **System Settings → Privacy & Security → Input Monitoring**
   *(Russian: Мониторинг ввода)*.
4. **Quit Terminal completely** (`⌘ Command` + `Q`) and open it again. This is important – the permission only applies after a restart.

> When you run PinkPad for the first time macOS may also show a pop-up asking for permission. Click **Open System Settings** and switch the toggle on.

### Step 6 – Turn on the desktop-switching shortcuts

PinkPad switches desktops by pressing `Ctrl` + `←` / `→`. Make sure those shortcuts are enabled in macOS:

**System Settings → Keyboard → Keyboard Shortcuts… → Mission Control** → tick
**Move left a space** and **Move right a space**.

### Step 7 – Set up the on-screen keyboard shortcut (optional)

Skip this if you don't need the on-screen keyboard.

PinkPad shows/hides the keyboard by pressing the macOS shortcut **`⌥ ⌘ F5`**. For that shortcut to toggle the keyboard *directly*, only one feature must be selected for it:

1. Open **System Settings → Accessibility** and scroll to the very bottom → **Shortcut**.
2. Tick **only** **Accessibility Keyboard** (untick everything else).
3. Test it: press `⌥ Option` + `⌘ Command` + `F5` on your real keyboard. The on-screen keyboard should appear, and the same combination hides it again.

> If a small panel with a list appears instead, more than one feature is ticked (or none).

### Step 8 – Connect your controller

Turn the controller on and connect it to the Mac with the 2.4 GHz dongle or over Bluetooth. If you're not sure the Mac can see it, the check in Step 10 will tell you.

### Step 9 – Teach PinkPad your buttons (do this once)

The small `−`, `+` and Home buttons are not always recognised the standard way, so PinkPad learns them from you. It takes about 30 seconds:

```bash
python3 pinkpad.py --learn
```

Just press what the wizard asks for:

| The wizard asks… | You press… |
|---|---|
| `−` (SELECT) | the small button **left** of the logo |
| `+` (START) | the small button **right** of the logo |
| HOME | the logo button (waits 8 s – skips itself if macOS keeps it) |
| ON-SCREEN KEYBOARD | any **free** button, e.g. **Y** or **B** (not A, X or the bumpers). Skip = Y |

The answers are saved to `~/.pinkpad_map.json` in your home folder. Run `--learn` again any time you want to change them; delete the file to reset.

> If your controller is **not** recognised as a standard gamepad, `--learn` automatically becomes a longer wizard that also asks for the stick, A, X, bumpers and triggers – just follow it.

### Step 10 – Run it! 🎀

```bash
python3 pinkpad.py
```

You should see the pink banner and a line like:

```
💖  Connected: 8BitDo Ultimate 2C · standard mapping
```

<div align="center">
<img src="assets/terminal.png" alt="PinkPad in the terminal" width="640">
</div>

Move the left stick – the cursor moves. Press `A` – it clicks. 🎉

To **quit**, click the Terminal window and press `Ctrl` + `C`.

---

## 🌙 Running it in the background

As written above, PinkPad runs as long as its Terminal window is open. If you want to close the window, pick one of these:

### Option 1 – Just minimise the Terminal window

The simplest way. PinkPad keeps working while the window is in the background (that's what the `SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS` setting inside the script is for).

### Option 2 – Detach it from the Terminal

```bash
cd ~/Documents/pinkpad
source pinkpad-env/bin/activate
nohup python3 pinkpad.py >/dev/null 2>&1 &
```

You can now close the window; PinkPad keeps running. To stop it:

```bash
pkill -f pinkpad.py
```

It won't start again by itself after a restart.

### Option 3 – Start automatically when you log in *(experimental)*

macOS can launch PinkPad for you at every login using a *LaunchAgent*. This one is more advanced: because macOS starts Python directly (not through Terminal), **Python itself** needs the permissions from Step 5.

**3a. Give Python the permission.** Open Finder at Python's app bundle:

```bash
cd ~/Documents/pinkpad
source pinkpad-env/bin/activate
REAL=$(python3 -c "import os,sys; print(os.path.realpath(sys.executable))")
open -R "$(dirname "$(dirname "$REAL")")/Resources/Python.app"
```

A Finder window opens with **Python.app** selected. Drag it into the list in **Privacy & Security → Accessibility** and also into **Input Monitoring**, and switch both on.

**3b. Create the LaunchAgent** (paste the whole block):

```bash
DIR="$HOME/Documents/pinkpad"      # <- change if you put PinkPad somewhere else
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.pinkpad.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.pinkpad</string>
  <key>ProgramArguments</key>
  <array>
    <string>$DIR/pinkpad-env/bin/python3</string>
    <string>$DIR/pinkpad.py</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/PinkPad.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/PinkPad.log</string>
</dict>
</plist>
EOF
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.pinkpad.plist
```

Check that it's running and look at the log if it isn't:

```bash
launchctl list | grep pinkpad      # a number in the first column = running; "-" = not running
tail -n 30 ~/Library/Logs/PinkPad.log
```

**To remove the auto-start:**

```bash
launchctl bootout gui/$(id -u)/com.pinkpad
rm ~/Library/LaunchAgents/com.pinkpad.plist
```

> This option depends on your Python setup and macOS version. If it doesn't work, Options 1 and 2 are the reliable way.

---

## ⚙️ Settings

All settings are plain variables at the top of [`pinkpad.py`](pinkpad.py). Open it in any text editor, change a value, save, and restart PinkPad.

| Setting | Default | What it does |
|---|---|---|
| `DEADZONE` | `0.14` | Ignores tiny stick drift. Raise it (e.g. `0.18`) if the cursor creeps by itself |
| `CURVE` | `2.0` | Stick response. Lower (e.g. `1.6`) = more sensitive near the centre |
| `MAX_SPEED` | `1500.0` | Cursor speed in pixels/second at full stick tilt |
| `INVERT_X` / `INVERT_Y` | `False` | Flip left/right or up/down of the cursor stick |
| `PRECISION_FACTOR` | `0.30` | How much the left trigger slows things down |
| `SCROLL_SPEED` | `700.0` | Scroll speed when you start holding the D-pad |
| `SCROLL_MAX` | `2600.0` | Top scroll speed after holding for a moment |
| `SCROLL_RAMP` | `1.0` | Seconds of holding needed to reach top scroll speed |
| `SCROLL_INVERT` | `False` | Set to `True` if scrolling goes the wrong way |
| `VOLUME_HOLD_DELAY` | `0.35` | Seconds to hold `−`/`+` before the volume starts repeating |
| `VOLUME_REPEAT` | `0.09` | Seconds between repeated volume steps while holding |
| `VOLUME_METHOD` | `"keys"` | `"keys"` = real macOS volume keys. Use `"osascript"` if the volume doesn't change |
| `VOLUME_STEP` | `6` | Percent per step (only for `"osascript"`) |
| `OSK_BUTTON` | `"y"` | Default button for the on-screen keyboard (`"y"`, `"b"` or `None`). `--learn` overrides it |
| `DOUBLE_CLICK_TIME` | `0.40` | Max seconds between two clicks to count as a double-click |
| `SPACE_COOLDOWN` | `0.12` | Minimum seconds between desktop switches |

### Command-line options

| Command | What it does |
|---|---|
| `python3 pinkpad.py` | Run PinkPad |
| `python3 pinkpad.py --learn` | Teach it the `−`, `+`, Home and on-screen-keyboard buttons |
| `python3 pinkpad.py --learn --full` | Re-teach **everything** (sticks, A, X, bumpers, triggers) |
| `python3 pinkpad.py --debug` | Live view of what the controller sends – handy for bug reports |

---

## 🩺 Troubleshooting

<details>
<summary><b>The cursor doesn't move / nothing happens</b></summary>

1. Look at the terminal. You should see `Connected: …`. If it says `Waiting for controller…`, the Mac doesn't see the controller – reconnect it, or add Terminal to **Input Monitoring** (Step 5) and restart Terminal.
2. Make sure Terminal is enabled in **Accessibility** and that you **fully quit and reopened** Terminal afterwards.
3. Run `python3 pinkpad.py --debug`, move the stick and press buttons. If numbers change, the controller is fine and it's a permissions issue.
</details>

<details>
<summary><b>The cursor moves the wrong way (up ↔ down, left ↔ right)</b></summary>

Set `INVERT_X = True` and/or `INVERT_Y = True` at the top of `pinkpad.py`.
</details>

<details>
<summary><b>The cursor is jerky / stutters</b></summary>

Delete the saved mapping and let PinkPad use the standard one:

```bash
rm -f ~/.pinkpad_map.json
```

Then run `python3 pinkpad.py --learn` again (it will only ask for the centre buttons if the controller is recognised as standard).
</details>

<details>
<summary><b>Scrolling goes the wrong direction</b></summary>

Set `SCROLL_INVERT = True`.
</details>

<details>
<summary><b>Desktops don't switch (L1 / R1)</b></summary>

Enable **Move left a space** / **Move right a space** in **System Settings → Keyboard → Keyboard Shortcuts → Mission Control** (Step 6). Also check you actually have more than one desktop.
</details>

<details>
<summary><b><code>−</code> / <code>+</code> do nothing</b></summary>

Run `python3 pinkpad.py --learn` (Step 9) and press the buttons when asked. When it works, every quick tap prints `Volume up` / `Volume down` in the terminal.
</details>

<details>
<summary><b>The terminal says "Volume up" but the volume doesn't change</b></summary>

Change `VOLUME_METHOD = "keys"` to `VOLUME_METHOD = "osascript"` at the top of `pinkpad.py`. (No on-screen volume pop-up in that mode, but it's very reliable.)
</details>

<details>
<summary><b>The on-screen keyboard doesn't appear</b></summary>

1. Do the manual test from Step 7: press `⌥ ⌘ F5` on the real keyboard. If a list panel appears instead of the keyboard, tick **only** *Accessibility Keyboard* in **Accessibility → Shortcut**.
2. If the manual test works but the button doesn't, run `--learn` and pick a different button, or use `L3 + R3`.
</details>

<details>
<summary><b>Step 9 (<code>--learn</code>) says "no setup needed" or skips things</b></summary>

That's normal – your controller is recognised as a standard gamepad, so only the small centre buttons need teaching. Use `--learn --full` if you want the full wizard anyway.
</details>

<details>
<summary><b><code>zsh: command not found: python3</code></b></summary>

Python isn't installed – see Step 2.
</details>

<details>
<summary><b><code>(pinkpad-env)</code> is missing from my prompt / <code>No module named pygame</code></b></summary>

You opened a new Terminal window. Run:

```bash
cd ~/Documents/pinkpad
source pinkpad-env/bin/activate
```
</details>

Still stuck? [Open an issue](../../issues) and include the output of `python3 pinkpad.py --debug` and your macOS version.

---

## 🛠️ How it works

- **Controller input:** [`pygame`](https://www.pygame.org/) (SDL game-controller layer) reads the buttons and sticks. A learned mapping from `~/.pinkpad_map.json` is applied on top for the small centre buttons.
- **Mouse:** native `Quartz` / CoreGraphics events (via [PyObjC](https://pyobjc.readthedocs.io/)) – sub-pixel accumulation, deadzone + response curve, works across several displays. Much smoother than `pyautogui`.
- **Scrolling:** Quartz pixel-scroll events.
- **Desktops:** synthetic `Ctrl` + `←/→` key presses, which macOS maps to *Move left/right a space*.
- **Volume:** real media-key events (the same ones your keyboard sends), with an AppleScript fallback.
- **On-screen keyboard:** synthetic `⌥⌘F5` – the macOS *Accessibility Shortcut*.

---

## ⚠️ Known limitations

- **macOS only.** It uses macOS-specific APIs.
- Built and tested with the **8BitDo Ultimate 2C**. Other controllers that macOS recognises as a standard gamepad (Xbox, PlayStation, other 8BitDo models) may work too, but button names and the centre buttons can differ – use `--learn`.
- The 8BitDo **star ★** button isn't visible to the Mac, and macOS may keep the **Home** button for itself.
- One controller at a time.
- The Terminal (or Python, for auto-start) needs **Accessibility** and **Input Monitoring** permission – macOS requires it for anything that controls the cursor.

---

## 🔒 Privacy & safety

- PinkPad reads **only your controller** and sends **only mouse / keyboard / volume events** to your own Mac.
- It has **no network access** – nothing is uploaded anywhere. You can read the whole thing in one file.
- The only file it writes is `~/.pinkpad_map.json` (your button mapping), plus an optional log if you use the auto-start option.
- To stop everything: `Ctrl` + `C` in Terminal, or `pkill -f pinkpad.py`.

---

<div align="center">

Made with 🎀 and a pink controller.

<!-- ## License — add a LICENSE file (for example MIT) and uncomment the badge at the top. -->

</div>
