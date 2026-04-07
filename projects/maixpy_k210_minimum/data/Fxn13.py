import sensor, image, lcd, time, machine, os
import KPU as kpu
from Maix import GPIO
from fpioa_manager import fm

# =========================================================
# BUTTON SETUP
# S1 (IO22) -> capture photo
# S2 (IO23) -> long press reboot
# =========================================================
fm.register(22, fm.fpioa.GPIO0, force=True)
fm.register(23, fm.fpioa.GPIO1, force=True)

btn_s1 = GPIO(GPIO.GPIO0, GPIO.IN, GPIO.PULL_UP)
btn_s2 = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)

# =========================================================
# LCD + CAMERA INIT
# =========================================================
lcd.init()
lcd.clear(lcd.BLACK)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)   # 320x240
sensor.skip_frames(time=2000)
sensor.run(1)

clock = time.clock()

# 3. KPU Model Loading & Safety Check
# =========================================================
# FACE MODEL LOAD
# Flash address assumed: 0x300000
# =========================================================
task = None
model_ok = False
FACE_MODEL = 0x300000

try:
    try:
        task = kpu.load("/sd/facedetect.kmodel")
        print("Face model loaded from SD")
    except:
        task = kpu.load(FACE_MODEL)
        print("Face model loaded from FLASH")

    anchor = (
        1.889, 2.5245,
        2.9465, 3.94056,
        3.99987, 5.3658,
        5.155437, 6.92275,
        6.718375, 9.01025
    )
    kpu.init_yolo2(task, 0.5, 0.3, 5, anchor)
    model_ok = True

except Exception as e:
    print("Face model load failed:", e)
    model_ok = False
# =========================================================
# HELPERS
# =========================================================
last_s1 = 1
capture_freeze_ms = 1200   # how long to show saved overlay

def get_save_path():
    # save to SD if present, else flash
    if "sd" in os.listdir("/"):
        return "/sd/"
    return "/flash/"

def save_photo(img):
    path = get_save_path()
    fname = path + "IMG_" + str(time.ticks_ms()) + ".jpg"
    img.save(fname)
    return fname

# =========================================================
# MAIN LOOP
# =========================================================
while True:
    clock.tick()
    img = sensor.snapshot()

    # -----------------------------------------------------
    # FACE DETECTION
    # -----------------------------------------------------
    if model_ok:
        try:
            code = kpu.run_yolo2(task, img)
            if code:
                for i in code:
                    img.draw_rectangle(i.rect(), color=(0, 255, 0))
                    img.draw_string(i.x(), max(0, i.y() - 18), "FACE",
                                    color=(0, 255, 0), scale=1)
        except Exception as e:
            img.draw_string(5, 25, "KPU ERR", color=(255, 0, 0), scale=1)
            print("KPU runtime error:", e)
    else:
        img.draw_string(5, 25, "NO FACE MODEL", color=(255, 0, 0), scale=1)

    # -----------------------------------------------------
    # HUD / LIVE VIEW INFO
    # -----------------------------------------------------
    img.draw_rectangle(0, 0, 320, 18, fill=True, color=(0, 0, 0))
    img.draw_string(4, 2, "FPS: %.1f" % clock.fps(), color=(255, 255, 255), scale=1)

    # -----------------------------------------------------
    # S1 PHOTO CAPTURE (edge detect so one press = one photo)
    # -----------------------------------------------------
    s1_now = btn_s1.value()
    if last_s1 == 1 and s1_now == 0:
        fname = save_photo(img)

        # show saved overlay on frozen frame
        img.draw_rectangle(0, 205, 320, 35, fill=True, color=(0, 0, 0))
        img.draw_string(8, 214, "SAVED: " + fname, color=(0, 255, 0), scale=1)
        lcd.display(img)
        time.sleep_ms(capture_freeze_ms)

    last_s1 = s1_now

    # -----------------------------------------------------
    # S2 LONG PRESS REBOOT
    # -----------------------------------------------------
    if btn_s2.value() == 0:
        press_start = time.ticks_ms()

        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), press_start)

            # take fresh frame during holding
            hold_img = sensor.snapshot()

            # keep face boxes in reboot screen too
            if model_ok:
                try:
                    code = kpu.run_yolo2(task, hold_img)
                    if code:
                        for i in code:
                            hold_img.draw_rectangle(i.rect(), color=(0, 255, 0))
                except:
                    pass

            # progress bar
            bar_w = int((elapsed * 320) / 3000)
            if bar_w > 320:
                bar_w = 320

            hold_img.draw_rectangle(0, 200, 320, 40, fill=True, color=(0, 0, 0))
            hold_img.draw_string(10, 205, "Hold S2 to reboot...", color=(255, 255, 255), scale=1)
            hold_img.draw_rectangle(0, 225, bar_w, 12, fill=True, color=(236, 100, 43))
            lcd.display(hold_img)

            if elapsed >= 3000:
                print("Rebooting...")
                if task:
                    try:
                        kpu.deinit(task)
                    except:
                        pass
                machine.reset()

            time.sleep_ms(20)

    # -----------------------------------------------------
    # DISPLAY LIVE FEED
    # -----------------------------------------------------
    lcd.display(img)