import lcd, image, time, machine, os
from Maix import GPIO
from fpioa_manager import fm

# 1. Hardware Setup (4.7K External Pull-ups)
fm.register(22, fm.fpioa.GPIO0) # S1: Toggle
fm.register(23, fm.fpioa.GPIO1) # S2: Select
btn_s1 = GPIO(GPIO.GPIO0, GPIO.IN, GPIO.PULL_UP)
btn_s2 = GPIO(GPIO.GPIO1, GPIO.IN, GPIO.PULL_UP)

# 2. Function List (9 Functions)
functions = [
    "1. Camera", 
    "2. Music Player",   
    "3. Digit AI",       
    "4. Line Follower",  
    "5. Color Recog",    
    "6. Color Track",    
    "7. RGB LED",
    "8. Object Detect",
    "9. QR Code",
    "10. Voice Command",
    "11. Traffic Sign"
]

cur = 0
last_act = time.ticks_ms()

def draw_main():
    """Renders a scrolling menu showing only 5 items at a time."""
    img = image.Image(size=(320, 240))
    img.draw_rectangle((0,0,320,240), fill=True, color=(255,255,255))
    
    # Header
    img.draw_string(20, 15, "VisionCore Menu", color=(44, 40, 114), scale=2)
    img.draw_line(20, 45, 300, 45, color=(150, 150, 150))

    # Calculate scrolling window (show 5 items)
    # This keeps the 'cur' index visible within the 5-item window
    start_idx = max(0, min(cur - 2, len(functions) - 5))
    if len(functions) <= 5: start_idx = 0

    for i in range(5):
        idx = start_idx + i
        if idx >= len(functions): break
        
        y = 65 + (i * 32) # Increased spacing for larger font
        name = functions[idx]
        
        if idx == cur:
            # Highlighted Selection (Orange)
            img.draw_rectangle(15, y-4, 290, 28, fill=True, color=(236, 100, 43))
            img.draw_string(25, y, "> " + name, color=(255, 255, 255), scale=1.5)
        else:
            # Standard Item (Black)
            img.draw_string(25, y, "  " + name, color=(0, 0, 0), scale=1.5)
            
    # Scroll indicators (arrows) if more items exist
    if start_idx > 0:
        img.draw_string(300, 55, "^", color=(150, 150, 150), scale=1)
    if start_idx + 5 < len(functions):
        img.draw_string(300, 210, "v", color=(150, 150, 150), scale=1)

    lcd.display(img)

def color_submenu():
    """Sub-menu for Color Tracking with Input Buffer Clearing."""
    # CRITICAL: Wait for user to release S2 from the main menu selection
    # This prevents the sub-menu from 'auto-selecting' Red.
    while btn_s2.value() == 0:
        time.sleep_ms(10)
    
    sub_opts = ["Red", "Green", "Blue"]
    sub_cur = 0
    sub_start = time.ticks_ms()
    
    while True:
        # 1. 10s Timeout Logic
        elapsed_total = time.ticks_diff(time.ticks_ms(), sub_start)
        if elapsed_total > 10000:
            machine.reset()

        # 2. UI Drawing
        img = image.Image(size=(320, 240))
        img.draw_rectangle((0,0,320,240), fill=True, color=(255,255,255))
        img.draw_string(20, 20, "Select Target Color:", color=(44, 40, 114), scale=2)
        
        for i, name in enumerate(sub_opts):
            y = 80 + (i * 40)
            is_sel = (i == sub_cur)
            color = (236, 100, 43) if is_sel else (0,0,0)
            img.draw_string(40, y, "> " + name if is_sel else "  " + name, color=color, scale=1.5)
        
        # Countdown Timer
        rem = 10 - (elapsed_total // 1000)
        img.draw_string(220, 210, "Exit: %ds" % rem, color=(150,150,150), scale=1)
        lcd.display(img)

        # 3. Handle S1 (Toggle Color)
        if btn_s1.value() == 0:
            time.sleep_ms(20) # Debounce
            if btn_s1.value() == 0:
                sub_cur = (sub_cur + 1) % len(sub_opts)
                sub_start = time.ticks_ms() # Reset 10s timer on activity
                while btn_s1.value() == 0: time.sleep_ms(10)

        # 4. Handle S2 (Confirm Selection)
        if btn_s2.value() == 0:
            time.sleep_ms(20) # Debounce
            if btn_s2.value() == 0:
                # Save choice for Fxn6.py
                with open("/flash/track_cfg.txt", "w") as f:
                    f.write(str(sub_cur))
                
                # Visual Confirmation
                img.draw_rectangle(0,0,320,240, fill=True, color=(0,0,0))
                img.draw_string(80, 110, "Starting %s..." % sub_opts[sub_cur], color=(255,255,255), scale=1.5)
                lcd.display(img)
                time.sleep_ms(500)
                
                import Fxn6 # Now it only starts when pressed again
                break
        
        time.sleep_ms(50)
lcd.init()
draw_main()

while True:
    # 30s Inactivity Timeout -> Home
    if time.ticks_diff(time.ticks_ms(), last_act) > 30000:
        machine.reset()

    if btn_s1.value() == 0: # S1 Toggle
        time.sleep_ms(20)
        if btn_s1.value() == 0:
            cur = (cur + 1) % len(functions)
            last_act = time.ticks_ms()
            draw_main()
            while btn_s1.value() == 0: time.sleep_ms(10)

    if btn_s2.value() == 0: # S2 Select
        time.sleep_ms(20)
        if btn_s2.value() == 0:
            # Logic for importing Fxn1-Fxn9
            if cur == 0: import Fxn13
            elif cur == 1: import Fxn2
            elif cur == 2: import Fxn3
            elif cur == 3: import Fxn4
            elif cur == 4: import Fxn5
            elif cur == 5: color_submenu()
            elif cur == 6: import Fxn8
            elif cur == 7: import Fxn9
            elif cur == 8: import Fxn10
            elif cur == 9: import Fxn11
            elif cur == 10: import Fxn12

    time.sleep_ms(50)