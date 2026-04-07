import sensor, image, lcd, time, machine
from Maix import GPIO
from fpioa_manager import fm
from machine import UART

# 1. Setup Button S2 (IO23) for Reboot logic
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

# Color Thresholds
thresholds = [
    (30, 100, 15, 127, 15, 127),  # Index 0: Red
    (0, 80, -70, -10, -0, 30),    # Index 1: Green
    (0, 80, -20, 40, -127, -20)   # Index 2: Blue
]

while True:
    img = sensor.snapshot()

    # --- S2 BUTTON CHECK (Long Press 5s to Reboot) ---
    if btn_s2.value() == 0:
        press_start = time.ticks_ms()
        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), press_start)
            # Orange progress bar
            img.draw_rectangle(0, 220, int(elapsed / 3000 * 320), 20, fill=True, color=(236, 100, 43))
            img.draw_string(10, 200, "Returning Home...", color=(255, 255, 255))
            lcd.display(img)
            
            if elapsed > 3000:
                machine.reset() # Soft reboot back to boot.py
            time.sleep_ms(20)

    # --- COLOR RECOGNITION LOGIC ---
    blobs = img.find_blobs(thresholds, pixels_threshold=200, area_threshold=200)

    if blobs:
        biggest_blob = max(blobs, key=lambda b: b.pixels())
        color_label = "Checking..."
        line_color = (255, 255, 255)

        if biggest_blob.code() == 1:
            color_label = "RED"
            line_color = (255, 0, 0)
        elif biggest_blob.code() == 2:
            color_label = "GREEN"
            line_color = (0, 255, 0)
        elif biggest_blob.code() == 4:
            color_label = "BLUE"
            line_color = (0, 0, 255)

        img.draw_rectangle(biggest_blob.rect(), color=line_color, thickness=2)
        img.draw_cross(biggest_blob.cx(), biggest_blob.cy(), color=line_color)
        img.draw_string(biggest_blob.x(), biggest_blob.y() - 22, color_label, color=line_color, scale=2)

        # Send recognized color over UART
        uart.write(color_label + "\n")

    lcd.display(img)