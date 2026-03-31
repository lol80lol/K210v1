import os, sys, time

sys.path.append('')
sys.path.append('.')

# chdir to "/sd" or "/flash"
devices = os.listdir("/")
if "sd" in devices:
    os.chdir("/sd")
    sys.path.append('/sd')
else:
    os.chdir("/flash")
sys.path.append('/flash')
del devices

print("[MaixPy] init end") # for IDE
for i in range(200):
    time.sleep_ms(1) # wait for key interrupt(for maixpy ide)
del i

# check IDE mode
ide_mode_conf = "/flash/ide_mode.conf"
ide = True
try:
    f = open(ide_mode_conf)
    f.close()
    del f
except Exception:
    ide = False

if ide:
    os.remove(ide_mode_conf)
    from machine import UART
    import lcd
    lcd.init(color=lcd.PINK)
    repl = UART.repl_uart()
    repl.init(1500000, 8, None, 1, read_buf_len=2048, ide=True, from_ide=False)
    sys.exit()
del ide, ide_mode_conf

# detect boot.py
main_py = '''
try:
    import gc, lcd, image, sys, os
    gc.collect()
    lcd.init()

    w = lcd.width()
    h = lcd.height()

    # Create canvas and fill White
    img = image.Image(size=(w, h))
    img.draw_rectangle((0, 0, w, h), fill=True, color=(255, 255, 255))

    # Welcome line (Black)
    info = "Welcome to VisionCore"
    img.draw_string(int(w//2 - len(info) * 5), h//4, info, color=(0, 0, 0), scale=2)

    # STEMbotix in two colors, centered
    text1 = "STEM"
    text2 = "botix"
    scale = 2
    char_w = 8 * scale # MaixPy built-in font approx width
    total_w = (len(text1) + len(text2)) * char_w
    x0 = int(w//2 - total_w//2)
    y0 = h//3 + 20
    img.draw_string(x0, y0, text1, color=(236, 100, 43), scale=scale, mono_space=1)
    img.draw_string(x0 + len(text1)*char_w, y0, text2, color=(44, 40, 114), scale=scale, mono_space=1)

    # Version info (Black) - Fixed positioning
    v = sys.implementation.version
    vers = "v{}.{}.{}".format(v[0], v[1], v[2])
    img.draw_string(10, h - 20, vers, color=(0, 0, 0), scale=1)

    # SD Card Detection Logic
    try:
        os.listdir("/sd")
        tf = "SDcard found, mount at /sd/"
        status_color = (0, 128, 0) # Green for success
    except:
        tf = "SDcard not found, use flash!"
        status_color = (255, 0, 0) # Red for warning

    # Draw SD status in Black or Status Color (NOT White)
    img.draw_string(int((w - len(tf) * 7)//2), h - 40, tf, color=(0, 0, 0), scale=1)

    # Final single display call
    lcd.display(img)
    del img, v, info, vers
    gc.collect()
finally:
    gc.collect()
'''

flash_ls = os.listdir()
if not "main.py" in flash_ls:
    f = open("main.py", "wb")
    f.write(main_py)
    f.close()
    del f
del main_py

flash_ls = os.listdir("/flash")
try:
    sd_ls = os.listdir("/sd")
except Exception:
    sd_ls = []
if "cover.boot.py" in sd_ls:
    code0 = ""
    if "boot.py" in flash_ls:
        with open("/flash/boot.py") as f:
            code0 = f.read()
    with open("/sd/cover.boot.py") as f:
        code=f.read()
    if code0 != code:
        with open("/flash/boot.py", "w") as f:
            f.write(code)
        import machine
        machine.reset()

if "cover.main.py" in sd_ls:
    code0 = ""
    if "main.py" in flash_ls:
        with open("/flash/main.py") as f:
            code0 = f.read()
    with open("/sd/cover.main.py") as f:
        code = f.read()
    if code0 != code:
        with open("/flash/main.py", "w") as f:
            f.write(code)
        import machine
        machine.reset()

try:
    del flash_ls
    del sd_ls
    del code0
    del code
except Exception:
    pass


