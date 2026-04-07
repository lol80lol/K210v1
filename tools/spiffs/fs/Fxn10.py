import sensor, image, lcd, time, machine
from Maix import GPIO
from fpioa_manager import fm
from machine import UART

# 1. Hardware Setup
# S2 (IO23) for Reboot logic
fm.register(23, fm.fpioa.GPIO1)
btn_s2 = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)

# UART TX on IO19 at 115200 baud
fm.register(19, fm.fpioa.UART1_TX, force=True)
uart = UART(UART.UART1, 115200, 8, None, 1, timeout=1000, read_buf_len=256)

lcd.init()
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA) # 320x240
sensor.set_vflip(0) # Flip if camera is inverted
sensor.run(1)

def show_header(img):
    """Draws consistent VisionCore UI elements."""
    img.draw_rectangle(0, 0, 320, 30, fill=True, color=(44, 40, 114))
    img.draw_string(10, 5, "QR Code Scanner", color=(255, 255, 255), scale=1.5)

while True:
    # --- IDE Friendly Delay ---
    time.sleep_ms(1) 

    img = sensor.snapshot()
    show_header(img)

    # --- S2 REBOOT LOGIC (5-second long press) ---
    if btn_s2.value() == 0:
        press_start = time.ticks_ms()
        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), press_start)
            # Visual progress bar
            img.draw_rectangle(0, 230, int(elapsed / 3000 * 320), 10, fill=True, color=(236, 100, 43))
            lcd.display(img)
            if elapsed > 3000:
                machine.reset() # Soft reboot back to home
            time.sleep_ms(20)

    # --- QR CODE DETECTION ---
    res = img.find_qrcodes()
    if len(res) > 0:
        for qr in res:
            # Draw box around detected QR
            img.draw_rectangle(qr.rect(), color=(0, 255, 0), thickness=3)
            
            # Extract and display the decoded string
            payload = qr.payload()
            # Draw a background box for the text to make it readable
            img.draw_rectangle(0, 190, 320, 40, fill=True, color=(0, 0, 0))
            img.draw_string(10, 200, payload, color=(255, 255, 255), scale=1.2)
            print("QR Decoded:", payload)

            # Send decoded string over UART
            uart.write(payload + "\n")

    lcd.display(img)