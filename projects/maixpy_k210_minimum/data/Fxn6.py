import sensor, image, lcd, time, machine, os
from Maix import GPIO
from fpioa_manager import fm
from machine import UART

# 1. Setup Button S2 (IO23)
fm.register(23, fm.fpioa.GPIO1)
btn_s2 = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)

# 1.1 Setup UART TX on IO19 at 115200 baud
fm.register(19, fm.fpioa.UART1_TX, force=True)
uart = UART(UART.UART1, 115200, 8, None, 1, timeout=1000, read_buf_len=256)

# 2. Hardware Initialization
lcd.init()
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.run(1)

# Threshold Definitions
R_THR = (30, 100, 15, 127, 15, 127)
G_THR = (0, 80, -70, -10, 0, 30)
B_THR = (0, 80, -20, 40, -127, -20)
CENTER_X = 160

# 3. Load Selected Color
try:
    with open("/flash/track_cfg.txt", "r") as f:
        cfg = int(f.read())
    if cfg == 0:
        target_threshold = R_THR
        c_name = "RED"
    elif cfg == 1:
        target_threshold = G_THR
        c_name = "GREEN"
    else:
        target_threshold = B_THR
        c_name = "BLUE"
except:
    target_threshold = G_THR
    c_name = "GREEN" # Default

while True:
    img = sensor.snapshot()

    # --- S2 LONG PRESS REBOOT (5s) ---
    if btn_s2.value() == 0:
        press_start = time.ticks_ms()
        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), press_start)
            img.draw_rectangle(0, 220, int(elapsed / 3000 * 320), 20, fill=True, color=(236, 100, 43))
            img.draw_string(10, 200, "Returning Home...", color=(255, 255, 255))
            lcd.display(img)
            if elapsed > 3000:
                machine.reset()
            time.sleep_ms(20)

    # --- TRACKING LOGIC ---
    blobs = img.find_blobs([target_threshold], pixels_threshold=200, area_threshold=200)
    if blobs:
        max_blob = max(blobs, key=lambda b: b.pixels())
        img.draw_rectangle(max_blob.rect())
        img.draw_string(max_blob.x(), max_blob.y()-20, c_name, color=(255,255,255))
        error_x = max_blob.cx() - CENTER_X
        img.draw_string(0, 0, "Error: %d" % error_x, color=(255,255,255), scale=2)

        # Send error over UART
        uart.write(str(error_x) + "\n")
    else:
        img.draw_string(0, 0, "Searching %s..." % c_name, color=(255,0,0), scale=2)

    lcd.display(img)