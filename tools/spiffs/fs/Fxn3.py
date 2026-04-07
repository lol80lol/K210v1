import sensor, image, lcd, time, machine
import KPU as kpu
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
sensor.skip_frames(time=2000)

# Load the MNIST model from SD card
try:
    MNIST_MODEL = 0x500000
    try:
        task = kpu.load("/sd/mnist.kmodel")
        print("MNIST model loaded from SD")
    except:
        task = kpu.load(MNIST_MODEL)
        print("MNIST model loaded from FLASH")
except:
    print("Model not found on SD!")
    machine.reset()

while True:
    img = sensor.snapshot()

    # --- S2 BUTTON CHECK (Long Press 5s to Reboot) ---
    if btn_s2.value() == 0:
        press_start = time.ticks_ms()
        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), press_start)
            # Visual feedback: Orange progress bar
            img.draw_rectangle(0, 100, int(elapsed / 3000 * 160), 15, fill=True, color=(236, 100, 43))
            img.draw_string(10, 85, "Hold to Exit", color=(255, 255, 255), scale=1)
            lcd.display(img)
            
            if elapsed > 3000:
                kpu.deinit(task) # Clean up KPU memory before reset
                machine.reset() # Soft reboot to return home
            time.sleep_ms(20)

    # --- KPU INFERENCE LOGIC ---
    roi = (50, 30, 60, 60)
    # Extract, Gray, and Resize to EXACTLY 28x28 for the AI model
    img_kpu = img.copy(roi).to_grayscale().resize(28, 28)
    img_kpu.invert()      # Prepare background for AI
    img_kpu.pix_to_ai()   # Memory rearrangement for KPU hardware

    fmap = kpu.forward(task, img_kpu)
    plist = fmap[:]
    max_conf = max(plist)

    # Display results
    if max_conf > 0.70:
        digit = plist.index(max_conf)
        img.draw_string(50, 10, "Digit: %d" % digit, color=(0,255,0), scale=1)
        img.draw_string(50, 20, "Conf: %d%%" % int(max_conf*100), color=(0,255,0), scale=1)

        # Send recognized digit over UART on IO19
        uart.write(str(digit) + "\n")

    # UI Elements
    img.draw_rectangle(roi, color=(255, 255, 0)) # Yellow search box
    img.draw_image(img_kpu, 0, 0) # Show what the AI sees in top left
    
    lcd.display(img)