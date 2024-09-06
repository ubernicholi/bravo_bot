import time
import threading
import gpiod

class LEDController:
    def __init__(self):
        self.leds = {
            'cpu': {'color': 'green','color2': 'red', 'state': False, 'gpio_pin': 17,'active' : False},
            'webcam': {'color': 'yellow','color2': 'DarkGoldenrod4', 'state': False, 'active' : False},
            'telegram': {'color': 'dodger blue','color2': 'blue4', 'state': False, 'active' : False},
            'motd': {'color': 'cyan','color2': 'cyan4', 'state': False, 'active' : True}
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
            elif led_name == 'motd':
                self.motd_blink()

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
        time.sleep(0.2)  # Off for shorter

    def telegram_blink(self):
        blink_speed = 1.6
        if self.leds['telegram']['active']:
            blink_speed = 0.4
        self.set_led_state('telegram', True)
        time.sleep(blink_speed)
        self.set_led_state('telegram', False)
        time.sleep(0.3)
    
    def motd_blink(self):
        # Implement MOTD morse code blinking logic here
        time.sleep(0.5)

    def start_blink_threads(self):
        for led_name in self.leds:
            thread = threading.Thread(target=self.blink_led, args=(led_name,))
            thread.daemon = True
            thread.start()

    def get_led_state(self, led_name):
        return self.leds[led_name]['state']

    def get_led_color(self, led_name):
        if led_name == 'cpu':
            if self.leds[led_name]['state'] == False:
                return 'grey14'
            elif self.leds[led_name]['active'] == True:
                return self.leds[led_name]['color2']
            else:
                return self.leds[led_name]['color']
        else:
            if self.leds[led_name]['state'] == True:
                if self.leds[led_name]['active'] == True:
                    return self.leds[led_name]['color']
                elif self.leds[led_name]['active'] == False:
                    return self.leds[led_name]['color2']
            elif self.leds[led_name]['state'] == True:
                return self.leds[led_name]['color2']
            else:
                return 'grey14'

    def set_cpu_usage(self, cpu_percent):
        if cpu_percent > 50:
            self.leds['cpu']['active'] = True
        else:
            self.leds['cpu']['active'] = False

    def toggle_webcam(self, is_active):
        self.leds['webcam']['active'] = is_active

    def toggle_telegram(self, is_active):
        self.leds['telegram']['active'] = is_active

    def set_motd(self, message):
        # Convert message to morse code and store it for blinking
        pass

# Usage example:
# led_controller = LEDController()
# led_controller.set_cpu_usage(60)
# led_controller.toggle_webcam(True)
# led_controller.toggle_telegram(True)
# led_controller.set_motd("Hello World")