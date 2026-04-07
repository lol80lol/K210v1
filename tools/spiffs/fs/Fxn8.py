import time, machine, lcd, image
from modules import ws2812
from Maix import GPIO
from fpioa_manager import fm

# 1. Setup Buttons
fm.register(22, fm.fpioa.GPIO0) # S1: Mode Toggle
fm.register(23, fm.fpioa.GPIO1) # S2: Select/Reboot
btn_s1 = GPIO(GPIO.GPIO0, GPIO.IN, GPIO.PULL_UP)
btn_s2 = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)

# 2. Hardware Initialization
led = ws2812(25, 1)
lcd.init()
mode = 0
modes_count = 5
last_s1_state = 1

# Colors (R, G, B)
COLORS = [(50,0,0), (0,50,0), (0,0,50), (50,50,0), (50,20,0)] # R, G, B, Y, O
POLICE = [(0,0,50), (50,50,50), (50,0,0)] # Dark Blue, White, Red

def check_inputs():
    """Checks S1 for mode change and S2 for 5s reboot."""
    global mode, last_s1_state
    
    # S1 Toggle Logic (Mode change)
    current_s1 = btn_s1.value()
    if current_s1 == 0 and last_s1_state == 1:
        mode = (mode + 1) % modes_count
        time.sleep_ms(20) # Debounce
    last_s1_state = current_s1

    # S2 Reboot Logic (5s hold)
    if btn_s2.value() == 0:
        start = time.ticks_ms()
        while btn_s2.value() == 0:
            elapsed = time.ticks_diff(time.ticks_ms(), start)
            # Visual feedback
            img = image.Image(size=(320, 240))
            img.draw_rectangle(0, 220, int(elapsed / 3000 * 320), 20, fill=True, color=(236, 100, 43))
            img.draw_string(10, 200, "Mode: %d | Hold S2 to Exit" % mode, color=(255,255,255))
            lcd.display(img)
            if elapsed > 3000:
                led.set_led(0, (0,0,0))
                led.display()
                machine.reset() # Soft reboot
            time.sleep_ms(20)

# 3. Pattern Logic
step = 0
fade_val = 0
fade_dir = 1

while True:
    check_inputs()
    
    if mode == 0: # Default: Fixed Delay Cycle
        c = COLORS[step % len(COLORS)]
        led.set_led(0, c)
        led.display()
        time.sleep_ms(800)
        step += 1

    elif mode == 1: # Fast Fade
        led.set_led(0, (fade_val, fade_val // 2, 0)) # Example transition
        led.display()
        fade_val += (10 * fade_dir)
        if fade_val >= 100 or fade_val <= 0: fade_dir *= -1
        time.sleep_ms(20)

    elif mode == 2: # Slow Fade
        led.set_led(0, (0, fade_val, fade_val)) 
        led.display()
        fade_val += (2 * fade_dir)
        if fade_val >= 100 or fade_val <= 0: fade_dir *= -1
        time.sleep_ms(50)

    elif mode == 3: # Blink All Colors
        c = COLORS[step % len(COLORS)]
        led.set_led(0, c)
        led.display()
        time.sleep_ms(100)
        led.set_led(0, (0,0,0))
        led.display()
        time.sleep_ms(100)
        step += 1

    elif mode == 4: # Police Theme
        c = POLICE[step % len(POLICE)]
        led.set_led(0, c)
        led.display()
        time.sleep_ms(50)
        step += 1