import gpiod
import time
import psutil

LED_PIN = 17  # GPIO pin number where the LED is connected
THRESHOLD = 50  # CPU usage threshold percentage

chip = gpiod.Chip('gpiochip4')
led_line = chip.get_line(LED_PIN)
led_line.request(consumer="LED", type=gpiod.LINE_REQ_DIR_OUT)

def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

try:
    while True:
        cpu_usage = get_cpu_usage()
        if cpu_usage > THRESHOLD:
            # CPU usage is above threshold, blink rapidly
            for _ in range(5):
                led_line.set_value(1)
                time.sleep(0.1)
                led_line.set_value(0)
                time.sleep(0.1)
        else:
            # CPU usage is below threshold, blink slowly
            led_line.set_value(1)
            time.sleep(1)
            led_line.set_value(0)
            time.sleep(1)
        
        print(f"CPU Usage: {cpu_usage}%")

finally:
    led_line.release()
    chip.close()