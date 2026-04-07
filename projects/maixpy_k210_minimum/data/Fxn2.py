import audio, time, image, lcd, machine
from fpioa_manager import fm
from Maix import I2S, GPIO

# 1. Hardware Configuration
BUTTON_S2_PIN = 23    # S2 for Reboot

# Register I2S pins
fm.register(33, fm.fpioa.I2S0_OUT_D1, force=True)
fm.register(34, fm.fpioa.I2S0_SCLK, force=True)
fm.register(32, fm.fpioa.I2S0_WS, force=True)

# Register S2 Button (IO23)
fm.register(BUTTON_S2_PIN, fm.fpioa.GPIO2, force=True)
btn_s2 = GPIO(GPIO.GPIO2, GPIO.IN, GPIO.PULL_UP)

# 2. Audio and LCD Initialization
lcd.init()
wav_dev = I2S(I2S.DEVICE_0)

# Create a static UI background
bg = image.Image(size=(320, 240))
bg.draw_rectangle(0, 0, 320, 240, fill=True, color=(255, 255, 255))
bg.draw_string(60, 100, "Playing: 6.wav", color=(44, 40, 114), scale=2)
bg.draw_string(50, 180, "Hold S2 (3s) to Exit", color=(150, 150, 150), scale=1)
lcd.display(bg)

try:
    player = audio.Audio(path="/sd/6.wav")
    player.volume(60)
    wav_info = player.play_process(wav_dev)

    wav_dev.channel_config(wav_dev.CHANNEL_1, I2S.TRANSMITTER,
                           resolution=I2S.RESOLUTION_16_BIT,
                           cycles=I2S.SCLK_CYCLES_32,
                           align_mode=I2S.RIGHT_JUSTIFYING_MODE)
    wav_dev.set_sample_rate(wav_info[1])

    # 3. Main Playback Loop
    while True:
        ret = player.play()

        # Check Button S2 for Long Press (3 Seconds)
        if btn_s2.value() == 0:
            press_start = time.ticks_ms()
            while btn_s2.value() == 0:
                elapsed = time.ticks_diff(time.ticks_ms(), press_start)

                # Show progress bar on LCD
                img = bg.copy()
                img.draw_rectangle(0, 220, int(elapsed / 3000 * 320), 20, fill=True, color=(236, 100, 43))
                lcd.display(img)

                if elapsed > 3000:
                    print("Rebooting to Home...")
                    player.finish()
                    machine.reset() # Soft reboot back to boot.py
                time.sleep_ms(10)
            # If button released before 3s, restore the original UI
            lcd.display(bg)

        if ret is None or ret == 0: # End of file or error
            break

    player.finish()
    print("Playback finished. Returning home...")
    machine.reset()

except Exception as e:
    print("Error:", e)
    time.sleep(2)
    machine.reset()
