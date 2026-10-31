#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎀 PinkPad — control your Mac with an 8BitDo Ultimate 2C controller 🎀

  Left stick ........ move the mouse cursor (smooth, sub-pixel, native Quartz)
  A ................. left click   (hold = drag)
  X or Right Trigger  right click
  L1 / LB ........... previous Desktop (Ctrl + Left Arrow)
  R1 / RB ........... next Desktop     (Ctrl + Right Arrow)
  D-pad ............. scroll (up/down/left/right, hold = faster)
  Left Trigger ...... precision (slow) mode while held (cursor + scroll)
  − / + (Select/Start) volume down / up  (tap = 1 step, hold = keeps going)
  − and + together .. pause / resume the script (Home button works too)
  Y (or L3+R3) ...... show / hide the on-screen keyboard (button can be changed with --learn)
  Ctrl+C in Terminal  quit

Run:        python3 pinkpad.py
Debug map:  python3 pinkpad.py --debug     (prints raw buttons/axes)
Learn map:  python3 pinkpad.py --learn     (teaches the −, +, Home and keyboard buttons; full wizard only if the pad isn't recognised)
"""

import os
import sys
import json
import math
import subprocess
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
INVERT_X = True   # True = flip left/right of the cursor stick
INVERT_Y = True        # True = flip up/down of the cursor stick
CURVE = 2.0              # >1 = finer control near the center of the stick
MAX_SPEED = 1500.0       # cursor speed in pixels/second at full deflection
PRECISION_FACTOR = 0.30  # speed multiplier while Left Trigger is held
TRIGGER_THRESHOLD = 0.5  # how far a trigger must be pulled to count as a press
LOOP_HZ = 144            # polling rate
DOUBLE_CLICK_TIME = 0.40 # seconds
SPACE_COOLDOWN = 0.12    # seconds between desktop switches
SCROLL_SPEED = 700.0     # scroll speed (pixels/second) when you start holding the D-pad
SCROLL_MAX = 2600.0      # top scroll speed after holding for SCROLL_RAMP seconds
SCROLL_RAMP = 1.0        # seconds of holding to reach top speed
SCROLL_INVERT = False    # set True if the scroll direction feels backwards
VOLUME_HOLD_DELAY = 0.35 # hold − or + this long (seconds) and the volume starts repeating
VOLUME_REPEAT = 0.09     # seconds between volume steps while holding
OSK_BUTTON = "y"          # extra single button for the on-screen keyboard ("y", "b" or None). L3+R3 always works too
VOLUME_METHOD = "keys"   # "keys" = real macOS volume keys (with on-screen HUD); "osascript" = alternative if keys do nothing
VOLUME_STEP = 6          # percent per step (only for VOLUME_METHOD = "osascript")

# Raw joystick fallback (used if SDL doesn't recognise the pad as a standard
# game controller). Run `python3 pinkpad.py --learn` once: it saves your real
# mapping to ~/.pinkpad_map.json and these defaults get overridden automatically.
RAW_AXES = {"lx": 0, "ly": 1}
RAW_BUTTONS = {"a": 0, "x": 2, "lb": 9, "rb": 10, "start": 6, "back": 4, "guide": 5, "star": 99, "l3": 99, "r3": 99, "y": 3, "b": 1}
RAW_SIGN = {"lx": 1, "ly": 1}
RAW_TRIGGERS = {
    "lt": {"type": "axis", "index": 4, "rest": -1.0, "full": 1.0},
    "rt": {"type": "axis", "index": 5, "rest": -1.0, "full": 1.0},
}
MAP_FILE = os.path.expanduser("~/.pinkpad_map.json")
# Buttons taught by --learn (raw joystick button numbers). They override the standard mapping:
# "back" = −/Select, "start" = +/Start, "guide" = Home.
EXTRA_BUTTONS = {}


def load_map():
    """Load the mapping saved by --learn (used ONLY if SDL doesn't recognise the pad)."""
    try:
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        RAW_AXES.update(data.get("axes", {}))
        RAW_BUTTONS.update(data.get("buttons", {}))
        RAW_SIGN.update(data.get("sign", {}))
        RAW_TRIGGERS.update(data.get("triggers", {}))
        EXTRA_BUTTONS.update({k: v for k, v in data.get("extra_buttons", {}).items() if isinstance(v, int)})
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[PinkPad] could not read {MAP_FILE}: {e}")


load_map()

# macOS virtual key codes
KEY_LEFT_ARROW = 123
KEY_RIGHT_ARROW = 124
KEY_CONTROL = 59
KEY_COMMAND = 55
KEY_OPTION = 58
KEY_F5 = 96

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
{PINK}   L1 / R1     {SOFT}→ switch desktops  {PINK}− / +     {SOFT}→ volume down / up
{PINK}   − and + together {SOFT}→ pause / resume
{PINK}   D-pad       {SOFT}→ scroll (hold = faster)
{PINK}   Y (or L3+R3) {SOFT}→ show / hide on-screen keyboard
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

    def scroll(self, dx, dy):
        """Smooth pixel scrolling. dy > 0 scrolls up, dx > 0 scrolls left."""
        self._sx = getattr(self, "_sx", 0.0) + dx
        self._sy = getattr(self, "_sy", 0.0) + dy
        ix, iy = int(self._sx), int(self._sy)
        if ix == 0 and iy == 0:
            return
        self._sx -= ix
        self._sy -= iy
        ev = Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitPixel, 2, iy, ix)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

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
        if sdl_controller.is_controller(index):
            self.ctrl = sdl_controller.Controller(index)
            try:
                self.name = sdl_controller.name_forindex(index) or self.name
            except Exception:
                pass
            try:                                   # raw access, used for buttons taught by --learn
                self.joy = pygame.joystick.Joystick(index)
                self.joy.init()
            except Exception:
                self.joy = None
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
            if name in EXTRA_BUTTONS and self.joy is not None:     # taught by --learn → always wins
                i = EXTRA_BUTTONS[name]
                return i < self.joy.get_numbuttons() and bool(self.joy.get_button(i))
            if self.ctrl is not None:
                const = {
                    "a": pygame.CONTROLLER_BUTTON_A,
                    "x": pygame.CONTROLLER_BUTTON_X,
                    "lb": pygame.CONTROLLER_BUTTON_LEFTSHOULDER,
                    "rb": pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
                    "start": pygame.CONTROLLER_BUTTON_START,
                    "back": pygame.CONTROLLER_BUTTON_BACK,
                    "guide": pygame.CONTROLLER_BUTTON_GUIDE,
                    "star": getattr(pygame, "CONTROLLER_BUTTON_MISC1", -1),
                    "y": pygame.CONTROLLER_BUTTON_Y,
                    "b": pygame.CONTROLLER_BUTTON_B,
                    "l3": pygame.CONTROLLER_BUTTON_LEFTSTICK,
                    "r3": pygame.CONTROLLER_BUTTON_RIGHTSTICK,
                    "up": pygame.CONTROLLER_BUTTON_DPAD_UP,
                    "down": pygame.CONTROLLER_BUTTON_DPAD_DOWN,
                    "left": pygame.CONTROLLER_BUTTON_DPAD_LEFT,
                    "right": pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
                }[name]
                return bool(self.ctrl.get_button(const))
            if name in ("up", "down", "left", "right"):      # raw pads usually expose the D-pad as a hat
                if self.joy.get_numhats() == 0:
                    return False
                hx, hy = self.joy.get_hat(0)
                return {"up": hy == 1, "down": hy == -1, "left": hx == -1, "right": hx == 1}[name]
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
            if self.joy is not None:
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
    sx, sy = (x / mag) * curved, (y / mag) * curved
    return (-sx if INVERT_X else sx), (-sy if INVERT_Y else sy)


def press_option_command_f5():
    """⌥⌘F5 = macOS Accessibility Shortcut. With ONLY 'Accessibility Keyboard' ticked there,
    it shows / hides the on-screen keyboard directly."""
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    cmd = Quartz.kCGEventFlagMaskCommand
    opt = Quartz.kCGEventFlagMaskAlternate
    fn = Quartz.kCGEventFlagMaskSecondaryFn
    _key(src, KEY_COMMAND, True, cmd)
    time.sleep(0.004)
    _key(src, KEY_OPTION, True, cmd | opt)
    time.sleep(0.004)
    _key(src, KEY_F5, True, cmd | opt | fn)
    time.sleep(0.004)
    _key(src, KEY_F5, False, cmd | opt | fn)
    time.sleep(0.004)
    _key(src, KEY_OPTION, False, cmd)
    time.sleep(0.004)
    _key(src, KEY_COMMAND, False, 0)


class KeyboardToggle:
    """Learned keyboard button (default Y), or L3 + R3 together → show / hide the on-screen keyboard."""

    def __init__(self):
        self.prev = False
        self.last = 0.0

    def update(self, pad):
        single = pad.button("osk") if "osk" in EXTRA_BUTTONS else (OSK_BUTTON and pad.button(OSK_BUTTON))
        cur = bool(single or (pad.button("l3") and pad.button("r3")))
        now = time.monotonic()
        if cur and not self.prev and now - self.last > 0.4:
            self.last = now
            press_option_command_f5()
            log("⌨️ ", "On-screen keyboard toggled", SOFT)
        self.prev = cur


class Scroller:
    """D-pad → scrolling. Holding the D-pad accelerates from SCROLL_SPEED to SCROLL_MAX."""

    def __init__(self):
        self.t0 = None

    def update(self, pad, mouse, dt, slow=False):
        vy = (1 if pad.button("up") else 0) - (1 if pad.button("down") else 0)       # +1 = scroll up
        vx = (1 if pad.button("left") else 0) - (1 if pad.button("right") else 0)    # +1 = scroll left
        if vx == 0 and vy == 0:
            self.t0 = None
            return
        now = time.perf_counter()
        if self.t0 is None:
            self.t0 = now
        k = clamp((now - self.t0) / SCROLL_RAMP, 0.0, 1.0)
        speed = SCROLL_SPEED + (SCROLL_MAX - SCROLL_SPEED) * k
        if slow:
            speed *= PRECISION_FACTOR
        if SCROLL_INVERT:
            vx, vy = -vx, -vy
        mouse.scroll(vx * speed * dt, vy * speed * dt)


NX_KEYTYPE_SOUND_UP = 0
NX_KEYTYPE_SOUND_DOWN = 1


def media_key(key):
    """Press a real macOS media key (shows the native volume HUD)."""
    from AppKit import NSEvent
    for down in (True, False):
        flags = (0xA if down else 0xB) << 8
        data1 = (key << 16) | flags
        ev = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            14, (0, 0), flags, 0, 0, None, 8, data1, -1)   # 14 = NSSystemDefined, 8 = aux control buttons
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev.CGEvent())


_vol_proc = None


def change_volume(up):
    """One volume step. VOLUME_METHOD = "keys" (media keys) or "osascript" (AppleScript)."""
    global _vol_proc
    if VOLUME_METHOD == "osascript":
        if _vol_proc is not None and _vol_proc.poll() is None:
            return                                   # previous step still running
        sign = "+" if up else "-"
        script = f"set volume output volume ((output volume of (get volume settings)) {sign} {VOLUME_STEP})"
        _vol_proc = subprocess.Popen(["osascript", "-e", script],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        media_key(NX_KEYTYPE_SOUND_UP if up else NX_KEYTYPE_SOUND_DOWN)


class VolumeKeys:
    """'−' (Back/Select) = volume down, '+' (Start) = volume up.
    Tap = one step, hold = repeat. Press both together = returns "pause"."""

    def __init__(self):
        self.down_t = {"back": None, "start": None}
        self.repeating = {"back": False, "start": False}
        self.last_rep = 0.0
        self.consumed = False

    @staticmethod
    def _step(which):
        change_volume(which == "start")

    def update(self, pad, active=True):
        now = time.monotonic()
        pressed = {"back": pad.button("back"), "start": pad.button("start")}

        if self.consumed:                         # wait for both to be released after a chord
            if not pressed["back"] and not pressed["start"]:
                self.consumed = False
            return None

        if pressed["back"] and pressed["start"]:  # both together = pause toggle
            self.consumed = True
            for k in self.down_t:
                self.down_t[k] = None
                self.repeating[k] = False
            return "pause"

        for k in ("back", "start"):
            if pressed[k]:
                if self.down_t[k] is None:
                    self.down_t[k] = now          # undecided: tap or hold?
                    self.repeating[k] = False
                elif now - self.down_t[k] > VOLUME_HOLD_DELAY:
                    if not self.repeating[k]:
                        self.repeating[k] = True
                        self.last_rep = 0.0
                    if active and now - self.last_rep >= VOLUME_REPEAT:
                        self._step(k)
                        self.last_rep = now
            elif self.down_t[k] is not None:
                if active and not self.repeating[k]:   # quick tap → one step
                    self._step(k)
                    log("🔊" if k == "start" else "🔉", "Volume " + ("up" if k == "start" else "down"), SOFT)
                self.down_t[k] = None
                self.repeating[k] = False
        return None


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
    """Wizard. ALWAYS teaches the −, + and Home buttons (volume / pause).
    If SDL doesn't recognise the pad (or you pass --full) it also teaches sticks, A/X, bumpers, triggers."""
    pygame.joystick.quit()
    pygame.joystick.init()
    print(f"{HOT}🎀 Learn mode — turn on your controller. Ctrl+C to cancel.{RESET}")
    while pygame.joystick.get_count() == 0:
        pygame.event.pump()
        time.sleep(0.1)
        pygame.joystick.quit()
        pygame.joystick.init()
    full = (not sdl_controller.is_controller(0)) or ("--full" in sys.argv)
    joy = pygame.joystick.Joystick(0)
    joy.init()
    nb, na = joy.get_numbuttons(), joy.get_numaxes()
    print(f"{SOFT}Found: {joy.get_name()}  ({nb} buttons, {na} axes){RESET}")
    if not full:
        print(f"{SOFT}Standard mapping detected → only the centre buttons (−, +, Home) and the keyboard button need teaching.{RESET}")
    print()

    def pump():
        pygame.event.pump()

    def wait_release():
        while any(joy.get_button(i) for i in range(nb)):
            pump()
            time.sleep(0.02)

    def ask_button(label, hint, timeout=None):
        print(f"{PINK}➜ Press {BOLD}{label}{RESET}{PINK}  {DIM}{hint}{RESET}", flush=True)
        wait_release()
        t0 = time.time()
        while True:
            pump()
            for i in range(nb):
                if joy.get_button(i):
                    wait_release()
                    time.sleep(0.2)
                    print(f"   {SOFT}→ button {i}{RESET}")
                    return i
            if timeout and time.time() - t0 > timeout:
                print(f"   {DIM}skipped{RESET}")
                return None
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
                    full_v = joy.get_axis(i)
                    print(f"   {SOFT}→ axis {i}{RESET}")
                    while abs(joy.get_axis(i) - base[i]) > 0.3:   # wait until released
                        pump()
                        time.sleep(0.02)
                    time.sleep(0.2)
                    return {"type": "axis", "index": i, "rest": base[i], "full": full_v}
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

    try:
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    # ---- step 1: the small centre buttons (always) --------------------------
    print(f"{HOT}{BOLD}Centre buttons{RESET}")
    extra = {}
    extra["back"] = ask_button("−  (SELECT)", "small button LEFT of the logo → volume DOWN")
    extra["start"] = ask_button("+  (START)", "small button RIGHT of the logo → volume UP")
    while extra["start"] == extra["back"]:
        print(f"   {HOT}That's the same button as −. Press the OTHER one (+).{RESET}")
        extra["start"] = ask_button("+  (START)", "small button RIGHT of the logo → volume UP")
    home = ask_button("HOME  (logo button)", "→ pause / resume · waits 8 s, then skipped", timeout=8)
    if home is not None and home not in (extra["back"], extra["start"]):
        extra["guide"] = home
    print(f"\n{HOT}{BOLD}On-screen keyboard{RESET}")
    while True:
        osk = ask_button("the button for the ON-SCREEN KEYBOARD",
                         "pick a free one: Y or B are good (NOT A, X, bumpers) · waits 10 s, then skipped (default: Y)",
                         timeout=10)
        if osk is None:
            break
        if osk in extra.values():
            print(f"   {HOT}That button is already used for volume / pause. Pick another one.{RESET}")
            continue
        extra["osk"] = osk
        break
    data["extra_buttons"] = extra

    # ---- step 2: everything else (only for unrecognised pads / --full) ------
    if full:
        print(f"\n{HOT}{BOLD}Main controls{RESET}")
        buttons = {}
        buttons["a"] = ask_button("A", "(the primary face button → left click)")
        buttons["x"] = ask_button("X", "(→ right click)")
        buttons["lb"] = ask_button("L1 / LB", "(left bumper → desktop left)")
        buttons["rb"] = ask_button("R1 / RB", "(right bumper → desktop right)")
        buttons["start"] = extra["start"]
        buttons["back"] = extra["back"]
        if "guide" in extra:
            buttons["guide"] = extra["guide"]

        sx = ask_axis("Tilt the LEFT STICK fully RIGHT and hold, then release")
        sy = ask_axis("Tilt the LEFT STICK fully DOWN and hold, then release")
        rt = ask_axis("Pull the RIGHT TRIGGER (R2/RT) fully — waits 10 s, else skipped", True, 10)
        lt = ask_axis("Pull the LEFT TRIGGER (L2/LT) fully — waits 10 s, else skipped", True, 10)
        data.update({
            "axes": {"lx": sx["index"], "ly": sy["index"]},
            "sign": {"lx": 1 if sx["full"] > sx["rest"] else -1,
                     "ly": 1 if sy["full"] > sy["rest"] else -1},
            "buttons": buttons,
            "triggers": {"rt": rt, "lt": lt},
        })

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
    scroller = Scroller()
    osk = KeyboardToggle()
    volume = VolumeKeys()
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
    prev = {"a": False, "x": False, "rt": False, "lb": False, "rb": False, "start": False, "guide": False}
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

            # ---- volume (−/+) and pause (− and + together, or Home) ---------
            vol_event = volume.update(pad, enabled)
            guide = pad.button("guide")
            if vol_event == "pause" or (guide and not prev["guide"]):
                enabled = not enabled
                if not enabled:
                    mouse.release_all()
                log("⏸️ " if not enabled else "▶️ ", "Paused" if not enabled else "Resumed", HOT)
            prev["guide"] = guide

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

                # ---- scroll (D-pad) -------------------------------------------
                scroller.update(pad, mouse, dt, pad.axis("lt") > 0.2)

                # ---- on-screen keyboard (★ or L3+R3) ----------------------------
                osk.update(pad)

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
