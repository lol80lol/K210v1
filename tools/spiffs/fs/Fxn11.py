import time
import ujson
import machine
import lcd
import image
from Maix import I2S, GPIO
from fpioa_manager import fm
from speech_recognizer import isolated_word
from machine import UART

# =========================================================
# HARDWARE
# =========================================================
fm.register(23, fm.fpioa.GPIO1, force=True)
btn_s2 = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)
# UART TX on IO19 at 115200
fm.register(19, fm.fpioa.UART1_TX, force=True)
uart = UART(UART.UART1, 115200, 8, None, 1, timeout=1000, read_buf_len=256)

fm.register(20, fm.fpioa.I2S0_IN_D0, force=True)
fm.register(30, fm.fpioa.I2S0_WS, force=True)
fm.register(31, fm.fpioa.I2S0_SCLK, force=True)

# =========================================================
# LCD
# =========================================================
lcd.init()
img = image.Image(size=(320, 240))

# Color palette
COL_BG      = (255, 255, 255)
COL_TITLE   = (44,  40,  114)
COL_READY   = (0,   140,  60)
COL_RESULT  = (0,   100, 200)
COL_ERROR   = (200,  30,  20)
COL_REBOOT  = (180,  40,  20)
COL_SUB     = (110, 110, 110)
COL_HINT    = (180, 180, 180)

def draw_status(main_text, sub_text="", color=None):
    """Draw status screen and immediately push to LCD."""
    if color is None:
        color = COL_READY
    img.draw_rectangle((0, 0, 320, 240), fill=True, color=COL_BG)
    img.draw_string(20, 18,  "Voice Control", color=COL_TITLE, scale=2)
    img.draw_line(20, 50, 300, 50, color=(220, 220, 220))
    img.draw_string(20, 80,  main_text, color=color, scale=3)
    if sub_text:
        img.draw_string(20, 150, sub_text, color=COL_SUB, scale=1)
    img.draw_string(20, 215, "Hold S2 3s: reboot", color=COL_HINT, scale=1)
    lcd.display(img)   # <-- always flush here immediately

def draw_result(cmd_name, score_val=None):
    """
    Dedicated function for showing a recognized command.
    Draws first, returns — caller handles restart AFTER this returns.
    """
    img.draw_rectangle((0, 0, 320, 240), fill=True, color=COL_BG)
    img.draw_string(20, 18, "Voice Control", color=COL_TITLE, scale=2)
    img.draw_line(20, 50, 300, 50, color=(220, 220, 220))

    # Big command label
    label = cmd_name.upper()
    img.draw_string(20, 70, label, color=COL_RESULT, scale=3)

    # Score (DTW distance — lower = better)
    if score_val is not None:
        score_str = "Score: " + str(score_val) + "  (lower=better)"
        img.draw_string(20, 140, score_str, color=COL_SUB, scale=1)

    # Detected badge
    img.draw_rectangle((20, 165, 120, 20), fill=True, color=(230, 245, 255))
    img.draw_string(25, 168, "DETECTED", color=COL_RESULT, scale=1)

    img.draw_string(20, 215, "Hold S2 3s: reboot", color=COL_HINT, scale=1)
    lcd.display(img)   # flush BEFORE any engine restart

def reboot_soft():
    draw_status("REBOOTING", "Please wait...", color=COL_REBOOT)
    time.sleep_ms(300)
    try:
        machine.soft_reset()
    except Exception:
        machine.reset()

# =========================================================
# I2S
# =========================================================
sample_rate = 16000
rx = I2S(I2S.DEVICE_0)
rx.channel_config(rx.CHANNEL_0, rx.RECEIVER, align_mode=I2S.STANDARD_MODE)
rx.set_sample_rate(sample_rate)

# =========================================================
# COMMANDS  (name, slot)
# =========================================================
save_dir = "/sd/voice_cmds"

commands = [
    ("hello",    0),
    ("stembotix", 2),
    ("left",     4),
    ("right",    6),
    ("stop",     8),
]

slot_to_name = {slot: name for name, slot in commands}

def load_template(cmd_name):
    sd_path = save_dir + "/" + cmd_name + ".json"
    flash_path = "/flash/voice_cmds/" + cmd_name + ".json"

    try:
        with open(sd_path, "r") as f:
            print("Loaded", cmd_name, "from SD")
            return ujson.load(f)
    except:
        with open(flash_path, "r") as f:
            print("Loaded", cmd_name, "from FLASH")
            return ujson.load(f)

def make_sr():
    s = isolated_word(dmac=2, i2s=I2S.DEVICE_0, size=10, shift=0)
    s.set_threshold(0, 0, 10000)
    missing = []
    for cmd_name, slot in commands:
        try:
            data = load_template(cmd_name)
            s.set(slot, data)
            print("Loaded:", cmd_name, "-> slot", slot)
        except Exception as e:
            print("ERROR loading", cmd_name, ":", e)
            missing.append(cmd_name)

    if missing:
        draw_status("MISSING TEMPLATES", ", ".join(missing), color=COL_ERROR)
        time.sleep_ms(3000)

    try:
        s.stop()
        time.sleep_ms(80)
    except Exception:
        pass
    try:
        s.run()
        time.sleep_ms(80)
    except Exception:
        pass

    return s

def restart_recognizer():
    """Stop/run cycle on the DTW engine. Call ONLY after LCD has been flushed."""
    try:
        sr.stop()
        time.sleep_ms(20)
    except Exception:
        pass
    try:
        sr.run()
        time.sleep_ms(20)
    except Exception:
        pass

# =========================================================
# START
# =========================================================
draw_status("LOADING...", "Reading SD templates...", color=(0, 0, 180))
sr = make_sr()
draw_status("READY", "Listening...", color=COL_READY)

last_ret   = None
last_state = None
last_cmd_time = 0
showing    = False
idle_start = time.ticks_ms()   # initialize before loop — no globals() hack
s2_down_since = None
while True:

    # ----- S2 long-press reboot -----
    if btn_s2.value() == 0:
        if s2_down_since is None:
            s2_down_since = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), s2_down_since) >= 3000:
            reboot_soft()
    else:
        if s2_down_since is not None:
            # released before 3s — just redraw ready
            draw_status("READY", "Listening...", color=COL_READY)
        s2_down_since = None

    # ----- Poll engine -----
    ret   = sr.recognize()
    state = sr.state()

    if ret != last_ret or state != last_state:
        print("ret =", ret, " state =", state)
        last_ret   = ret
        last_state = state

    # ----- Result ready -----
    if sr.Done == ret:
        res = sr.result()
        print("RESULT =", res)

        if res is not None:
            cmd       = slot_to_name.get(res[0], "unknown")
            score_val = res[1] if len(res) > 1 else None
            print("Detected:", cmd, " score:", score_val)

            # STEP 1 — draw to LCD first, fully
            draw_result(cmd, score_val)

            uart.write(cmd + "\n")

            # STEP 2 — small pause so SPI write fully completes
            time.sleep_ms(80)

            # STEP 3 — ONLY NOW restart the engine
            restart_recognizer()

            showing       = True
            last_cmd_time = time.ticks_ms()
            idle_start    = time.ticks_ms()

    # ----- Clear result after 2 seconds -----
    if showing and time.ticks_diff(time.ticks_ms(), last_cmd_time) > 2000:
        draw_status("READY", "Listening...", color=COL_READY)
        showing = False

    # ----- Watchdog: stuck at ret=5 state=5 -----
    if ret == 5 and state == 5:
        if time.ticks_diff(time.ticks_ms(), idle_start) > 1500:
            print("Watchdog: restarting engine")
            restart_recognizer()
            idle_start = time.ticks_ms()
    else:
        idle_start = time.ticks_ms()

    time.sleep_ms(10)