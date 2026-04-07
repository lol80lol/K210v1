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
sensor.set_framesize(sensor.QQVGA) # 160x120
sensor.run(1)

# Threshold for black line detection
GRAYSCALE_THRESHOLD = [(0, 45, -20, 20, -20, 20)]

while True:
    img = sensor.snapshot()

    # --- S2 BUTTON CHECK (Long Press 5s to Reboot) ---
    if btn_s2.value() == 0:
        press_start = time.ticks_ms()
        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), press_start)
            
            # Draw progress bar
            # We draw this BEFORE the binary operation to ensure color visibility
            img.draw_rectangle(0, 100, int(elapsed / 3000 * 160), 15, fill=True, color=(236, 100, 43))
            img.draw_string(10, 85, "Exiting...", color=(255, 255, 255))
            lcd.display(img)
            
            if elapsed > 3000:
                print("Rebooting...")
                machine.reset() # Soft reboot to return home
            time.sleep_ms(20)

    # --- LINE DETECTION LOGIC ---
    # This turns the black line WHITE and everything else BLACK
    img.binary(GRAYSCALE_THRESHOLD)

    # Look for the "white" blobs (the original black line)
    blobs = img.find_blobs([(100, 100, -128, 127, -128, 127)], merge=True)

    if blobs:
        # Use the largest blob as the main line
        largest_blob = max(blobs, key=lambda b: b.pixels())

        # Draw tracking markers
        img.draw_rectangle(largest_blob.rect(), color=(255))
        img.draw_cross(largest_blob.cx(), largest_blob.cy(), color=(255))

        # Calculate error from image center
        center_x = img.width() // 2
        error = largest_blob.cx() - center_x   # right = positive, left = negative

        # Send error over UART
        uart.write(str(error) + "\n")

    lcd.display(img)