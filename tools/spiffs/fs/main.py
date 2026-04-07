import lcd, image, time, os, sys, gc
from Maix import GPIO
from fpioa_manager import fm

# Hardware Setup
fm.register(22, fm.fpioa.GPIO0) # S1
fm.register(23, fm.fpioa.GPIO1) # S2
btn_s1 = GPIO(GPIO.GPIO0, GPIO.IN, GPIO.PULL_UP)
btn_s2 = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)

lcd.init()

def show_welcome():
    w, h = lcd.width(), lcd.height()
    img = image.Image(size=(w, h))
    img.draw_rectangle((0, 0, w, h), fill=True, color=(255, 255, 255))

    info = "Welcome to VisionCore"
    img.draw_string(int(w//2 - len(info) * 5), h//4, info, color=(0, 0, 0), scale=2)

    text1, text2 = "STEM", "botix"
    scale, char_w = 2, 16
    total_w = (len(text1) + len(text2)) * char_w
    x0, y0 = int(w//2 - total_w//2), h//3 + 20
    img.draw_string(x0, y0, text1, color=(236, 100, 43), scale=scale, mono_space=1)
    img.draw_string(x0 + len(text1)*char_w, y0, text2, color=(44, 40, 114), scale=scale, mono_space=1)

    # NEW: Instruction line below branding
    prompt = "Press any button for menu"
    img.draw_string(int(w//2 - len(prompt) * 2.7), y0 + 40, prompt, color=(150, 150, 150), scale=1)

    v = sys.implementation.version
    vers = "v{}.{}.{}".format(v[0], v[1], v[2])
    img.draw_string(10, h - 20, vers, color=(0, 0, 0), scale=1)

    # Status Check
    sd_status = "SDcard found, mount at /sd/" if "sd" in os.listdir("/") else "SDcard not found, use flash!"
    img.draw_string(90, 180, sd_status, color=(150, 150, 150), scale=1)
    prompt = "Press any button for menu"
    img.draw_string(int(w//2 - len(prompt) * 2.7), y0 + 40, prompt, color=(150, 150, 150), scale=1)
    v = sys.implementation.version
    vers = "v{}.{}.{}".format(v[0], v[1], v[2])
    img.draw_string(10, h - 20, vers, color=(0, 0, 0), scale=1)
    lcd.display(img)
    del img, v, info, vers, prompt
    gc.collect()

show_welcome()

# Main Listener Loop
while True:
    # S1 or S2 triggers the Menu
    if btn_s1.value() == 0 or btn_s2.value() == 0:
        time.sleep_ms(20) # Debounce
        if btn_s1.value() == 0 or btn_s2.value() == 0:
                print("Button pressed, loading menu...")
        import menu
        break # Exit loop once menu starts
    
    # IMPORTANT: Small sleep allows IDE to interrupt the loop
    time.sleep_ms(100)