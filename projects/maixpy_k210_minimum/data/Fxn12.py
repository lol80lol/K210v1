import sensor, image, lcd, time, os
import KPU as kpu
from machine import UART
from Maix import GPIO 
import gc, sys
from fpioa_manager import fm

input_size = (224, 224)
labels = ['left', 'fwd', 'uturn', 'noent', '20', 'right']
anchors = [2.48, 4.12, 1.59, 2.56, 1.34, 2.03, 1.0, 2.7, 1.19, 2.09]

# UART setup on IO19
fm.register(19, fm.fpioa.UART1_TX, force=True)
uart = UART(UART.UART1, 115200, 8, None, 1, timeout=1000, read_buf_len=256)

try:
    fm.register(23, fm.fpioa.GPIO1)
except Exception:
    pass
btn_s2 = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)

def lcd_show_except(e):
    img = image.Image(size=(320, 240))
    img.draw_rectangle(0, 0, 320, 240, fill=True, color=(0, 0, 0))
    img.draw_string(10, 10, "Error:", color=(255, 0, 0), scale=2)
    img.draw_string(10, 40, str(e), color=(255, 255, 255), scale=1)
    lcd.display(img)

def check_exit_button(img):
    if btn_s2.value() == 0:
        start = time.ticks_ms()
        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), start)
            progress_width = int((elapsed / 3000) * 320)
            img.draw_rectangle(0, 220, progress_width, 20, color=(236, 100, 43), fill=True)
            lcd.display(img)
            if elapsed > 3000:
                import machine
                machine.reset()
            time.sleep_ms(20)
        return True
    return False

def main(anchors, labels, model_addr="/sd/traffic_model.kmodel"):
    task = None
    last_sent_label = None

    lcd.init(type=1)
    lcd.rotation(0)
    lcd.clear(lcd.WHITE)

    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    sensor.set_windowing(input_size)
    sensor.run(1)

    try:
        TRAFFIC_MODEL = 0x580000

        try:
            task = kpu.load(model_addr)   # try SD first
            print("Traffic model loaded from SD")
        except:
            task = kpu.load(TRAFFIC_MODEL)   # fallback to flash
            print("Traffic model loaded from FLASH")

        kpu.init_yolo2(task, 0.5, 0.3, 5, anchors)

        while True:
            img = sensor.snapshot()
            check_exit_button(img)

            objects = kpu.run_yolo2(task, img)

            current_label = None

            if objects:
                obj = objects[0]
                x, y, w, h = obj.rect()
                current_label = labels[obj.classid()]

                img.draw_rectangle(int(x), int(y), int(w), int(h), color=(255, 0, 0), thickness=2)
                img.draw_string(int(x), int(y), current_label, color=(255, 0, 0), scale=2)

                if current_label != last_sent_label:
                    uart.write(current_label + "\n")
                    last_sent_label = current_label
            else:
                last_sent_label = None

            img.draw_string(0, 2, "Hold S2 to Exit", color=(255, 255, 255), scale=1)
            lcd.display(img)

    except Exception as e:
        display_img = image.Image(size=(320, 240))
        display_img.draw_rectangle(0, 0, 320, 240, fill=True, color=(0, 0, 0))
        display_img.draw_string(10, 80, "MODEL LOAD FAILED", color=(255, 0, 0), scale=2)
        display_img.draw_string(10, 120, str(e), color=(255, 255, 255), scale=1)
        lcd.display(display_img)
        raise e
    finally:
        if task is not None:
            kpu.deinit(task)
try:
    main(anchors=anchors, labels=labels)
except Exception as e:
    sys.print_exception(e)
    lcd_show_except(e)
finally:
    gc.collect()