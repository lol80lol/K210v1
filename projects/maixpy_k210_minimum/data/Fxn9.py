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
sensor.set_framesize(sensor.QVGA) # 320x240
sensor.run(1)

# ---------------- KPU Model Configuration ----------------
MODEL_PATH = "/sd/20class.kmodel"
labels = [
    "aeroplane","bicycle","bird","boat","bottle",
    "bus","car","cat","chair","cow",
    "diningtable","dog","horse","motorbike","person",
    "pottedplant","sheep","sofa","train","tvmonitor"
]
anchors = (1.08, 1.19, 3.42, 4.41, 6.63, 11.38, 9.42, 5.11, 16.62, 10.52)

# Load Model
try:
    CLS20_MODEL = 0x380000
    try:
        task = kpu.load(MODEL_PATH)   # /sd/20class.kmodel
        print("20-class model loaded from SD")
    except:
        task = kpu.load(CLS20_MODEL)
    print("20-class model loaded from FLASH")
    kpu.init_yolo2(task, 0.5, 0.3, 5, anchors)
except Exception as e:
    print("Model error:", e)
    img = image.Image(size=(320, 240))
    img.draw_rectangle(0, 0, 320, 240, fill=True, color=(200, 0, 0))
    img.draw_string(40, 100, "20CLASS MODEL NOT FOUND", color=(255, 255, 255))
    lcd.display(img)
    task = None

clock = time.clock()

while True:
    img = sensor.snapshot()
    clock.tick()

    # --- S2 BUTTON CHECK (Long Press 5s to Reboot) ---
    if btn_s2.value() == 0:
        press_start = time.ticks_ms()
        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), press_start)
            img.draw_rectangle(0, 220, int(elapsed / 3000 * 320), 20, fill=True, color=(236, 100, 43))
            img.draw_string(10, 200, "Returning Home...", color=(255, 255, 255))
            lcd.display(img)
            
            if elapsed > 3000:
                if task: kpu.deinit(task)
                machine.reset()
            time.sleep_ms(20)

    # --- DETECTION LOGIC ---
    if task:
        objs = kpu.run_yolo2(task, img)
        if objs:
            for o in objs:
                x, y, w, h = o.rect()
                cls = o.classid()
                score = o.value()

                # Draw on LCD
                img.draw_rectangle(x, y, w, h, thickness=2, color=(0, 255, 0))
                label = "%s %.2f" % (labels[cls], score)
                img.draw_string(x, y - 20, label, scale=1.5, color=(0, 255, 0))

                # Send recognized object label over UART
                uart.write(labels[cls] + "\n")

    # FPS display
    img.draw_string(2, 2, "FPS: %.1f" % clock.fps(), color=(255, 255, 255), scale=1)
    lcd.display(img)