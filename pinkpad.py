#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎀 PinkPad — control your Mac with an 8BitDo Ultimate 2C controller 🎀

  Left stick ........ move the mouse cursor (smooth, sub-pixel, native Quartz)
  A ................. left click   (hold = drag)
  X or Right Trigger  right click
  L1 / LB ........... previous Desktop (Ctrl + Left Arrow)
  R1 / RB ........... next Desktop     (Ctrl + Right Arrow)
  Left Trigger ...... precision (slow) mode while held
  Start ............. pause / resume the script
  Ctrl+C in Terminal  quit

Run:        python3 pinkpad.py
Debug map:  python3 pinkpad.py --debug     (prints raw buttons/axes)
Learn map:  python3 pinkpad.py --learn     (wizard: teaches the script YOUR buttons)
"""

import os
import sys
import json
import math
import time
import signal

# --- SDL / pygame environment (must be set BEFORE importing pygame) ----------
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")  # work while Terminal isn't focused
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")                   # no window needed
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from pygame._sdl2 import controller as sdl_controller
import Quartz

# =============================== SETTINGS ====================================
DEADZONE = 0.14          # ignore tiny stick drift (0.0 - 1.0)
CURVE = 2.0              # >1 = finer control near the center of the stick
MAX_SPEED = 1500.0       # cursor speed in pixels/second at full deflection
PRECISION_FACTOR = 0.30  # speed multiplier while Left Trigger is held
TRIGGER_THRESHOLD = 0.5  # how far a trigger must be pulled to count as a press
LOOP_HZ = 144            # polling rate
DOUBLE_CLICK_TIME = 0.40 # seconds
SPACE_COOLDOWN = 0.12    # seconds between desktop switches

# Raw joystick fallback (used if SDL doesn't recognise the pad as a standard
# game controller). Run `python3 pinkpad.py --learn` once: it saves your real
# mapping to ~/.pinkpad_map.json and these defaults get overridden automatically.
RAW_AXES = {"lx": 0, "ly": 1}
RAW_BUTTONS = {"a": 0, "x": 2, "lb": 9, "rb": 10, "start": 6}
RAW_SIGN = {"lx": 1, "ly": 1}
RAW_TRIGGERS = {
    "lt": {"type": "axis", "index": 4, "rest": -1.0, "full": 1.0},
    "rt": {"type": "axis", "index": 5, "rest": -1.0, "full": 1.0},
}
MAP_FILE = os.path.expanduser("~/.pinkpad_map.json")
FORCE_RAW = False


def load_map():
    """Load the mapping saved by --learn (if any)."""
    global FORCE_RAW
    try:
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        RAW_AXES.update(data.get("axes", {}))
        RAW_BUTTONS.update(data.get("buttons", {}))
        RAW_SIGN.update(data.get("sign", {}))
        RAW_TRIGGERS.update(data.get("triggers", {}))
        FORCE_RAW = bool(data.get("force_raw", False))
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[PinkPad] could not read {MAP_FILE}: {e}")


load_map()

# macOS virtual key codes
KEY_LEFT_ARROW = 123
KEY_RIGHT_ARROW = 124
KEY_CONTROL = 59

# ================================ PINK UI ====================================
PINK = "\033[38;2;255;105;180m"
HOT = "\033[38;2;255;20;147m"
SOFT = "\033[38;2;255;182;193m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log(icon, text, color=PINK):
    stamp = time.strftime("%H:%M:%S")
    print(f"{DIM}{SOFT}{stamp}{RESET}  {color}{icon}  {text}{RESET}", flush=True)


def banner():
    print(f"""{HOT}{BOLD}
   ╔═══════════════════════════════════════════╗
   ║   🎀  P I N K P A D  ·  Mac Controller  🎀  ║
   ╚═══════════════════════════════════════════╝{RESET}
{PINK}   Left stick  {SOFT}→ mouse            {PINK}A        {SOFT}→ left click
{PINK}   X / RT      {SOFT}→ right click      {PINK}LT (hold){SOFT}→ precision mode
{PINK}   L1 / R1     {SOFT}→ switch desktops  {PINK}Start    {SOFT}→ pause / resume
{PINK}   Ctrl+C      {SOFT}→ quit{RESET}
""")


# ============================ MACOS: MOUSE ===================================
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class MacMouse:
    def __init__(self):
        self.left_down = False
        self.right_down = False
        self.need_sync = True          # re-read the real cursor position on next move
        self.fx, self.fy = self.actual()
        self.last_click_t = 0.0
        self.last_click_pos = (0.0, 0.0)
        self.click_count = 1
        self.min_x = self.min_y = 0.0
        self.max_x = self.max_y = 0.0
        self.refresh_bounds()

    @staticmethod
    def actual():
        loc = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
        return float(loc.x), float(loc.y)

    def refresh_bounds(self):
        """Union of all connected displays, so the cursor can roam across monitors."""
        try:
            err, ids, count = Quartz.CGGetActiveDisplayList(16, None, None)
            rects = [Quartz.CGDisplayBounds(d) for d in list(ids)[:count]]
            if not rects:
                raise RuntimeError("no displays")
        except Exception:
            rects = [Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())]
        self.min_x = min(r.origin.x for r in rects)
        self.min_y = min(r.origin.y for r in rects)
        self.max_x = max(r.origin.x + r.size.width for r in rects)
        self.max_y = max(r.origin.y + r.size.height for r in rects)

    def idle(self):
        """Call when the stick is centred: next movement re-syncs with the real cursor
        (so trackpad movement in between is respected)."""
        self.need_sync = True

    def move(self, dx, dy):
        if self.need_sync:
            self.fx, self.fy = self.actual()
            self.need_sync = False
        self.fx = clamp(self.fx + dx, self.min_x, self.max_x - 1)
        self.fy = clamp(self.fy + dy, self.min_y, self.max_y - 1)

        if self.left_down:
            etype, btn = Quartz.kCGEventLeftMouseDragged, Quartz.kCGMouseButtonLeft
        elif self.right_down:
            etype, btn = Quartz.kCGEventRightMouseDragged, Quartz.kCGMouseButtonRight
        else:
            etype, btn = Quartz.kCGEventMouseMoved, Quartz.kCGMouseButtonLeft

        ev = Quartz.CGEventCreateMouseEvent(None, etype, (self.fx, self.fy), btn)
        Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventDeltaX, int(round(dx)))
        Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventDeltaY, int(round(dy)))
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

    def _pos(self):
        return self.actual() if self.need_sync else (self.fx, self.fy)

    def _button(self, right, down):
        x, y = self._pos()
        if right:
            etype = Quartz.kCGEventRightMouseDown if down else Quartz.kCGEventRightMouseUp
            btn = Quartz.kCGMouseButtonRight
        else:
            etype = Quartz.kCGEventLeftMouseDown if down else Quartz.kCGEventLeftMouseUp
            btn = Quartz.kCGMouseButtonLeft

        if down:
            now = time.monotonic()
            near = math.hypot(x - self.last_click_pos[0], y - self.last_click_pos[1]) < 8
            self.click_count = self.click_count + 1 if (now - self.last_click_t < DOUBLE_CLICK_TIME and near) else 1
            self.last_click_t = now
            self.last_click_pos = (x, y)

        ev = Quartz.CGEventCreateMouseEvent(None, etype, (x, y), btn)
        Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventClickState, self.click_count)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

    def left(self, down):
        if down == self.left_down:
            return
        self.left_down = down
        self._button(False, down)

    def right(self, down):
        if down == self.right_down:
            return
        self.right_down = down
        self._button(True, down)

    def release_all(self):
        self.left(False)
        self.right(False)


# ============================ MACOS: KEYBOARD ================================
def _key(source, code, down, flags):
    ev = Quartz.CGEventCreateKeyboardEvent(source, code, down)
    Quartz.CGEventSetFlags(ev, flags)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def ctrl_arrow(keycode):
    """Simulate Ctrl + Arrow (Mission Control: move left/right a space)."""
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    ctrl = Quartz.kCGEventFlagMaskControl
    ctrl_fn = ctrl | Quartz.kCGEventFlagMaskSecondaryFn  # arrow keys carry the Fn flag natively
    _key(src, KEY_CONTROL, True, ctrl)
    time.sleep(0.004)
    _key(src, keycode, True, ctrl_fn)
    time.sleep(0.004)
    _key(src, keycode, False, ctrl_fn)
    time.sleep(0.004)
    _key(src, KEY_CONTROL, False, 0)


# ============================== CONTROLLER ===================================
class Pad:
    """Uniform wrapper: SDL GameController (standard mapping) with raw-joystick fallback."""

    def __init__(self, index):
        self.ctrl = None
        self.joy = None
        self.name = "controller"
        if sdl_controller.is_controller(index) and not FORCE_RAW:
            self.ctrl = sdl_controller.Controller(index)
            try:
                self.name = sdl_controller.name_forindex(index) or self.name
            except Exception:
                pass
        else:
            self.joy = pygame.joystick.Joystick(index)
            self.joy.init()
            self.name = self.joy.get_name()

    @property
    def standard(self):
        return self.ctrl is not None

    def alive(self):
        try:
            if self.ctrl is not None:
                return self.ctrl.attached()
            return pygame.joystick.get_count() > 0 and self.joy.get_init()
        except Exception:
            return False

    def axis(self, name):
        """Return -1.0..1.0 (sticks) or 0.0..1.0 (triggers)."""
        try:
            if self.ctrl is not None:
                const = {
                    "lx": pygame.CONTROLLER_AXIS_LEFTX,
                    "ly": pygame.CONTROLLER_AXIS_LEFTY,
                    "lt": pygame.CONTROLLER_AXIS_TRIGGERLEFT,
                    "rt": pygame.CONTROLLER_AXIS_TRIGGERRIGHT,
                }[name]
                return clamp(self.ctrl.get_axis(const) / 32767.0, -1.0, 1.0)
            if name in ("lt", "rt"):
                t = RAW_TRIGGERS.get(name, {})
                if t.get("type") == "button":
                    i = t["index"]
                    return 1.0 if (i < self.joy.get_numbuttons() and self.joy.get_button(i)) else 0.0
                if t.get("type") == "axis":
                    i = t["index"]
                    if i >= self.joy.get_numaxes():
                        return 0.0
                    span = t["full"] - t["rest"]
                    if abs(span) < 0.2:
                        return 0.0
                    return clamp((self.joy.get_axis(i) - t["rest"]) / span, 0.0, 1.0)
                return 0.0
            idx = RAW_AXES[name]
            if idx >= self.joy.get_numaxes():
                return 0.0
            return clamp(self.joy.get_axis(idx) * RAW_SIGN.get(name, 1), -1.0, 1.0)
        except Exception:
            return 0.0

    def button(self, name):
        try:
            if self.ctrl is not None:
                const = {
                    "a": pygame.CONTROLLER_BUTTON_A,
                    "x": pygame.CONTROLLER_BUTTON_X,
                    "lb": pygame.CONTROLLER_BUTTON_LEFTSHOULDER,
                    "rb": pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
                    "start": pygame.CONTROLLER_BUTTON_START,
                }[name]
                return bool(self.ctrl.get_button(const))
            idx = RAW_BUTTONS[name]
            if idx >= self.joy.get_numbuttons():
                return False
            return bool(self.joy.get_button(idx))
        except Exception:
            return False

    def close(self):
        try:
            if self.ctrl is not None:
                self.ctrl.quit()
            elif self.joy is not None:
                self.joy.quit()
        except Exception:
            pass


def open_pad():
    pygame.joystick.quit()
    pygame.joystick.init()
    sdl_controller.quit()
    sdl_controller.init()
    count = pygame.joystick.get_count()
    for i in range(count):
        try:
            return Pad(i)
        except Exception:
            continue
    return None


def shape_stick(x, y):
    """Radial deadzone + response curve → (-1..1, -1..1)."""
    mag = math.hypot(x, y)
    if mag < DEADZONE:
        return 0.0, 0.0
    scaled = (min(mag, 1.0) - DEADZONE) / (1.0 - DEADZONE)
    curved = scaled ** CURVE
    return (x / mag) * curved, (y / mag) * curved


# ================================ DEBUG ======================================
def debug_loop():
    print(f"{PINK}🎀 Debug mode — press buttons / move sticks. Ctrl+C to quit.{RESET}")
    pad = None
    last_scan = 0.0
    last = ""
    while True:
        pygame.event.pump()
        if pad is None or not pad.alive():
            if time.time() - last_scan > 1:
                last_scan = time.time()
                pad = open_pad()
                if pad:
                    mode = "standard mapping" if pad.standard else "RAW mapping"
                    print(f"{HOT}Connected: {pad.name} ({mode}){RESET}")
            time.sleep(0.05)
            continue
        if pad.standard:
            line = " ".join(f"{n}={'1' if pad.button(n) else '0'}" for n in ("a", "x", "lb", "rb", "start"))
            line += " | " + " ".join(f"{n}={pad.axis(n):+.2f}" for n in ("lx", "ly", "lt", "rt"))
        else:
            j = pad.joy
            btn = [i for i in range(j.get_numbuttons()) if j.get_button(i)]
            axes = [f"{i}:{j.get_axis(i):+.2f}" for i in range(j.get_numaxes())]
            line = f"buttons pressed: {btn} | axes: {' '.join(axes)}"
        if line != last:
            print(f"{PINK}{line}{RESET}", flush=True)
            last = line
        time.sleep(0.05)



# ================================= LEARN =====================================
def learn():
    """Wizard: press each button once, the script saves YOUR controller's mapping."""
    pygame.joystick.quit()
    pygame.joystick.init()
    print(f"{HOT}🎀 Learn mode — turn on your controller. Ctrl+C to cancel.{RESET}")
    while pygame.joystick.get_count() == 0:
        pygame.event.pump()
        time.sleep(0.1)
        pygame.joystick.quit()
        pygame.joystick.init()
    joy = pygame.joystick.Joystick(0)
    joy.init()
    nb, na = joy.get_numbuttons(), joy.get_numaxes()
    print(f"{SOFT}Found: {joy.get_name()}  ({nb} buttons, {na} axes){RESET}\n")

    def pump():
        pygame.event.pump()

    def wait_release():
        while any(joy.get_button(i) for i in range(nb)):
            pump()
            time.sleep(0.02)

    def ask_button(label, hint):
        print(f"{PINK}➜ Press {BOLD}{label}{RESET}{PINK}  {DIM}{hint}{RESET}", flush=True)
        wait_release()
        while True:
            pump()
            for i in range(nb):
                if joy.get_button(i):
                    wait_release()
                    time.sleep(0.2)
                    print(f"   {SOFT}→ button {i}{RESET}")
                    return i
            time.sleep(0.01)

    def ask_axis(label, allow_button=False, timeout=None):
        print(f"{PINK}➜ {BOLD}{label}{RESET}", flush=True)
        time.sleep(0.5)
        pump()
        base = [joy.get_axis(i) for i in range(na)]
        t0 = time.time()
        while True:
            pump()
            for i in range(na):
                if abs(joy.get_axis(i) - base[i]) > 0.6:
                    time.sleep(0.4)
                    pump()
                    full = joy.get_axis(i)
                    print(f"   {SOFT}→ axis {i}{RESET}")
                    while abs(joy.get_axis(i) - base[i]) > 0.3:   # wait until released
                        pump()
                        time.sleep(0.02)
                    time.sleep(0.2)
                    return {"type": "axis", "index": i, "rest": base[i], "full": full}
            if allow_button:
                for i in range(nb):
                    if joy.get_button(i):
                        wait_release()
                        print(f"   {SOFT}→ button {i}{RESET}")
                        return {"type": "button", "index": i}
            if timeout and time.time() - t0 > timeout:
                print(f"   {DIM}skipped{RESET}")
                return {"type": "none"}
            time.sleep(0.01)

    buttons = {}
    buttons["a"] = ask_button("A", "(the primary face button → left click)")
    buttons["x"] = ask_button("X", "(→ right click)")
    buttons["lb"] = ask_button("L1 / LB", "(left bumper → desktop left)")
    buttons["rb"] = ask_button("R1 / RB", "(right bumper → desktop right)")
    buttons["start"] = ask_button("START", "(→ pause / resume)")

    sx = ask_axis("Push the LEFT STICK fully RIGHT and hold, then release")
    sy = ask_axis("Push the LEFT STICK fully DOWN and hold, then release")
    rt = ask_axis("Pull the RIGHT TRIGGER (R2/RT) fully — waits 10 s, else skipped", True, 10)
    lt = ask_axis("Pull the LEFT TRIGGER (L2/LT) fully — waits 10 s, else skipped", True, 10)

    data = {
        "force_raw": True,
        "axes": {"lx": sx["index"], "ly": sy["index"]},
        "sign": {"lx": 1 if sx["full"] > sx["rest"] else -1,
                 "ly": 1 if sy["full"] > sy["rest"] else -1},
        "buttons": buttons,
        "triggers": {"rt": rt, "lt": lt},
    }
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\n{HOT}💖 Saved to {MAP_FILE}{RESET}")
    print(f"{SOFT}Now run:  python3 pinkpad.py   (or restart pinkpad_menubar.py){RESET}\n")

# ================================= MAIN ======================================
def accessibility_check():
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
        trusted = bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
    except Exception:
        return
    if not trusted:
        print(f"{HOT}⚠️  Accessibility permission is NOT granted for this Terminal yet.{RESET}")
        print(f"{SOFT}   System Settings → Privacy & Security → Accessibility → enable Terminal,")
        print(f"   then fully quit (⌘Q) and reopen Terminal and run the script again.{RESET}\n")


def main():
    pygame.init()
    pygame.joystick.init()
    sdl_controller.init()

    banner()

    if "--learn" in sys.argv:
        try:
            learn()
        except KeyboardInterrupt:
            print(f"\n{SOFT}Cancelled.{RESET}")
        return

    if "--debug" in sys.argv:
        try:
            debug_loop()
        except KeyboardInterrupt:
            return

    accessibility_check()

    mouse = MacMouse()
    running = True
    enabled = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    pad = None
    last_scan = 0.0
    waiting_msg = False
    prev = {"a": False, "x": False, "rt": False, "lb": False, "rb": False, "start": False}
    last_space = 0.0
    last_t = time.perf_counter()
    frame = 1.0 / LOOP_HZ
    last_bounds = time.time()

    try:
        while running:
            pygame.event.pump()
            now = time.perf_counter()

            # ---- (re)connect -------------------------------------------------
            if pad is None or not pad.alive():
                if pad is not None:
                    log("💔", "Controller disconnected", HOT)
                    mouse.release_all()
                    pad.close()
                    pad = None
                if time.time() - last_scan > 1.0:
                    last_scan = time.time()
                    pad = open_pad()
                    if pad:
                        mode = "standard mapping" if pad.standard else "RAW mapping (run: python3 pinkpad.py --learn)"
                        log("💖", f"Connected: {pad.name} · {mode}", HOT)
                        waiting_msg = False
                        last_t = time.perf_counter()
                    elif not waiting_msg:
                        log("🌸", "Waiting for controller… turn it on / pair it via Bluetooth or dongle", SOFT)
                        waiting_msg = True
                time.sleep(0.05)
                continue

            dt = clamp(now - last_t, 0.0, 0.05)
            last_t = now

            # refresh display layout occasionally (monitor plugged in/out)
            if time.time() - last_bounds > 5:
                mouse.refresh_bounds()
                last_bounds = time.time()

            # ---- pause toggle -----------------------------------------------
            start = pad.button("start")
            if start and not prev["start"]:
                enabled = not enabled
                if not enabled:
                    mouse.release_all()
                log("⏸️ " if not enabled else "▶️ ", "Paused" if not enabled else "Resumed", HOT)
            prev["start"] = start

            if enabled:
                # ---- mouse movement ------------------------------------------
                sx, sy = shape_stick(pad.axis("lx"), pad.axis("ly"))
                if sx == 0.0 and sy == 0.0:
                    mouse.idle()
                else:
                    speed = MAX_SPEED * (PRECISION_FACTOR if pad.axis("lt") > 0.2 else 1.0)
                    mouse.move(sx * speed * dt, sy * speed * dt)

                # ---- clicks ---------------------------------------------------
                a = pad.button("a")
                if a != prev["a"]:
                    mouse.left(a)
                    if a:
                        log("🖱️ ", "Left click" + (f" ×{mouse.click_count}" if mouse.click_count > 1 else ""))
                    prev["a"] = a

                rdown = pad.button("x") or pad.axis("rt") > TRIGGER_THRESHOLD
                if rdown != (prev["x"] or prev["rt"]):
                    mouse.right(rdown)
                    if rdown:
                        log("💗", "Right click")
                prev["x"] = pad.button("x")
                prev["rt"] = pad.axis("rt") > TRIGGER_THRESHOLD
                # keep the combined state consistent
                if not (prev["x"] or prev["rt"]):
                    mouse.right(False)

                # ---- desktops (Spaces) ---------------------------------------
                lb, rb = pad.button("lb"), pad.button("rb")
                t = time.monotonic()
                if lb and not prev["lb"] and t - last_space > SPACE_COOLDOWN:
                    ctrl_arrow(KEY_LEFT_ARROW)
                    last_space = t
                    log("⬅️ ", "Desktop ← left", SOFT)
                if rb and not prev["rb"] and t - last_space > SPACE_COOLDOWN:
                    ctrl_arrow(KEY_RIGHT_ARROW)
                    last_space = t
                    log("➡️ ", "Desktop → right", SOFT)
                prev["lb"], prev["rb"] = lb, rb

            # ---- pace the loop ------------------------------------------------
            spare = frame - (time.perf_counter() - now)
            if spare > 0:
                time.sleep(spare)
    finally:
        mouse.release_all()
        if pad:
            pad.close()
        pygame.quit()
        print(f"\n{HOT}🎀 PinkPad stopped. Bye! 🎀{RESET}")


if __name__ == "__main__":
    main()
