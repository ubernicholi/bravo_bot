import time
import threading
import gpiod

class LEDController:
    def __init__(self):
        self.leds = {
            'cpu': {'color': 'green','color2': 'red', 'state': False, 'gpio_pin': 17,'active' : False},
            'webcam': {'color': 'yellow','color2': 'DarkGoldenrod4', 'state': False, 'active' : False},
            'telegram': {'color': 'dodger blue','color2': 'blue4', 'state': False, 'active' : False},
            'monolith': {'color': 'red','color2': 'brown4', 'state': False, 'active' : False}
        }
        self.setup_gpio()
        self.start_blink_threads()

    def setup_gpio(self):
        try:
            self.chip = gpiod.Chip('gpiochip4')  # Raspberry Pi 5 uses gpiochip4
            self.led_line = self.chip.get_line(self.leds['cpu']['gpio_pin'])
            self.led_line.request(consumer="LED", type=gpiod.LINE_REQ_DIR_OUT)
            self.gpio_available = True
            print("Creeper is CHARGING....")
        except Exception as e:
            print(f"Error initializing GPIO: {e}. Creeper is DEAD.")
            self.gpio_available = False

    def set_led_state(self, led_name, state):
        self.leds[led_name]['state'] = state
        if led_name == 'cpu' and self.gpio_available:
            try:
                self.led_line.set_value(1 if state else 0)
            except Exception as e:
                print(f"Error setting LED state: {e}")

    def blink_led(self, led_name):
        while True:
            if led_name == 'cpu':
                self.cpu_blink()
            elif led_name == 'webcam':
                self.webcam_blink()
            elif led_name == 'telegram':
                self.telegram_blink()
            elif led_name == 'monolith':
                self.monolith_blink()

    def cpu_blink(self):
        blink_speed = 0.4
        if self.leds['cpu']['active']:
            blink_speed = 0.2
        self.set_led_state('cpu', True)
        time.sleep(blink_speed)
        self.set_led_state('cpu', False)
        time.sleep(blink_speed)

    def webcam_blink(self):
        blink_speed = 1.5
        if self.leds['webcam']['active']:
            blink_speed = 0.5
        self.set_led_state('webcam', True)
        time.sleep(blink_speed)  # On for longer
        self.set_led_state('webcam', False)
        time.sleep(blink_speed)  # Off for shorter

    def telegram_blink(self):
        blink_speed = 1.6
        if self.leds['telegram']['active']:
            blink_speed = 0.4
        self.set_led_state('telegram', True)
        time.sleep(blink_speed)
        self.set_led_state('telegram', False)
        time.sleep(blink_speed)
    
    def monolith_blink(self):
        blink_speed = 2
        if self.leds['monolith']['active']:
            blink_speed = 0.2
        self.set_led_state('monolith', True)
        time.sleep(blink_speed)
        self.set_led_state('monolith', False)
        time.sleep(blink_speed)

    def start_blink_threads(self):
        for led_name in self.leds:
            thread = threading.Thread(target=self.blink_led, args=(led_name,))
            thread.daemon = True
            thread.start()

    def get_led_state(self, led_name):
        return self.leds[led_name]['state']

    def get_led_color(self, led_name):
        led = self.leds[led_name]

        if not led['state']:
            return 'grey14'

        if led_name == 'cpu':
            return led['color2'] if led['active'] else led['color']
        else:
            return led['color'] if led['active'] else led['color2']

    def set_cpu_usage(self, cpu_percent):
        if cpu_percent > 50:
            self.leds['cpu']['active'] = True
        else:
            self.leds['cpu']['active'] = False

    def toggle_webcam(self, is_active):
        self.leds['webcam']['active'] = is_active

    def toggle_telegram(self, is_active):
        self.leds['telegram']['active'] = is_active

    def toggle_monolith(self, is_active):
        self.leds['monolith']['active'] = is_active
