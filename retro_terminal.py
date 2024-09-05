import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import random
from collections import deque
import textwrap
import os, logging, time, psutil


from dotenv import load_dotenv

# Load environment variables
load_dotenv()

LOG_FILE = os.getenv('LOG_FILE_TERMINAL')

logging.basicConfig(filename=LOG_FILE, level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

try:
    import gpiod
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

class RetroTerminal:
    def __init__(self, master, width, height, max_logs=11, font_size=12, log_queue=None):
        self.master = master
        self.master.title("Bravolith Terminal")
        
        self.width = width
        self.height = height
        self.master.geometry(f"{width}x{height}")
        
        self.log_queue = log_queue
        self.max_logs = max_logs
        self.font_size = font_size
        self.log_lines = deque(maxlen=max_logs)

        self.canvas = tk.Canvas(master, bg="black", width=width, height=height)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.create_crt_frame(width, height)


        self.ascii_art = """
____________  ___  _   _  _____ _     _____ _____ _   _ 
| ___ \ ___ \/ _ \| | | ||  _  | |   |_   _|_   _| | | |
| |_/ / |_/ / /_\ \ | | || | | | |     | |   | | | |_| |
| ___ \    /|  _  | | | || | | | |     | |   | | |  _  |
| |_/ / |\ \| | | \ \_/ /\ \_/ / |_____| |_  | | | | | |
\____/\_| \_\_| |_/\___/  \___/\_____/\___/  \_/ \_| |_/
"""
        self.ascii_art_2 = """
 ▄▄▄▄    ██▀███   ▄▄▄    ██▒   █▓ ▒█████   ██▓     ██▓▄▄▄█████▓ ██░ ██ 
▓█████▄ ▓██ ▒ ██▒▒████▄ ▓██░   █▒▒██▒  ██▒▓██▒    ▓██▒▓  ██▒ ▓▒▓██░ ██▒
▒██▒ ▄██▓██ ░▄█ ▒▒██  ▀█▄▓██  █▒░▒██░  ██▒▒██░    ▒██▒▒ ▓██░ ▒░▒██▀▀██░
▒██░█▀  ▒██▀▀█▄  ░██▄▄▄▄██▒██ █░░▒██   ██░▒██░    ░██░░ ▓██▓ ░ ░▓█ ░██ 
░▓█  ▀█▓░██▓ ▒██▒ ▓█   ▓██▒▒▀█░  ░ ████▓▒░░██████▒░██░  ▒██▒ ░ ░▓█▒░██▓
░▒▓███▀▒░ ▒▓ ░▒▓░ ▒▒   ▓▒█░░ ▐░  ░ ▒░▒░▒░ ░ ▒░▓  ░░▓    ▒ ░░    ▒ ░░▒░▒
▒░▒   ░   ░▒ ░ ▒░  ▒   ▒▒ ░░ ░░    ░ ▒ ▒░ ░ ░ ▒  ░ ▒ ░    ░     ▒ ░▒░ ░
 ░    ░   ░░   ░   ░   ▒     ░░  ░ ░ ░ ▒    ░ ░    ▒ ░  ░       ░  ░░ ░
 ░         ░           ░  ░   ░      ░ ░      ░  ░ ░            ░  ░  ░
      ░                      ░                                         
"""
        self.ascii_display = self.canvas.create_text(
            width // 7, height // 7,
            text=self.ascii_art_2,
            fill="blue",
            font=("Courier", 10),
            anchor="nw"
        )

        self.log_display_width = int(width * 0.8)
        self.log_display_height = int(height * 0.6)
        self.log_display_x = width // 2
        self.log_display_y = (height // 7)*3

        self.log_display = self.canvas.create_text(
            self.log_display_x, self.log_display_y,
            text="",
            fill="green",
            font=("Courier", self.font_size),
            anchor="n",
            justify='left',
            width=self.log_display_width
        )

        self.calculate_max_lines()
        self.update_logs()

        # Initialize CPU usage variables
        self.cpu_percent = 0
        self.last_cpu_check = time.time()

        self.THRESHOLD = 50  # CPU usage threshold percentage

        
        # Create CPU activity LED
        self.led_radius = 10
        self.led = self.canvas.create_oval(
            width - 100, 15, width - 80, 35, 
            fill='green', outline='black'
        )
        
        # Set up GPIO for physical LED if available
        self.LED_PIN = 17  # GPIO pin number where the LED is connected
        self.setup_gpio()
        
        # Start updating CPU activity
        self.update_cpu_activity()

    def setup_gpio(self):
        self.gpio_available = False
        if GPIO_AVAILABLE:
            try:
                self.chip = gpiod.Chip('gpiochip4')  # Raspberry Pi 5 uses gpiochip4
                self.led_line = self.chip.get_line(self.LED_PIN)
                self.led_line.request(consumer="LED", type=gpiod.LINE_REQ_DIR_OUT)
                self.gpio_available = True
                print("Successfully initialized GPIO for Raspberry Pi 5")
            except Exception as e:
                print(f"Error initializing GPIO: {e}. Physical LED control is disabled.")
        else:
            print("GPIO module not available. Physical LED control is disabled.")

    def __del__(self):
        # Clean up GPIO when the object is destroyed
        if hasattr(self, 'led_line') and self.gpio_available:
            self.led_line.release()
        if hasattr(self, 'chip') and self.gpio_available:
            self.chip.close()

    def create_crt_frame(self, width, height, border_width=60):
        image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(image)
        
        # Draw the main CRT frame
        draw.rectangle(
            [(0, 0), (width, height)],
            outline=(100, 100, 100, 255),
            width=border_width
        )
        
        # Draw diagonal lines
        line_color = (50, 50, 50, 255)  # Darker grey for subtle effect
        line_color2 = (25, 25, 25, 255)  # Darker grey for subtle effect
        
        thiccness = 4
        thiccness2 = 4
        # Top-left to top-right
        draw.line([(border_width, border_width), (width - border_width, border_width)], fill=line_color, width=thiccness)
        
        # Top-left to bottom-left
        draw.line([(border_width, border_width), (border_width, height - border_width)], fill=line_color, width=thiccness)
        
        # Bottom-left to bottom-right
        draw.line([(border_width, height - border_width), (width - border_width, height - border_width)], fill=line_color, width=thiccness)
        
        # Top-right to bottom-right
        draw.line([(width - border_width, border_width), (width - border_width, height - border_width)], fill=line_color, width=thiccness)

        # Top-left corner
        draw.line([(0, 0), (border_width, border_width)], fill=line_color2, width=thiccness2)
        
        # Top-right corner
        draw.line([(width, 0), (width - border_width, border_width)], fill=line_color2, width=thiccness2)
        
        # Bottom-left corner
        draw.line([(0, height), (border_width, height - border_width)], fill=line_color2, width=thiccness2)
        
        # Bottom-right corner
        draw.line([(width, height), (width - border_width, height - border_width)], fill=line_color2, width=thiccness2)

        self.crt_frame = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.crt_frame)

        self.canvas.create_text(
            width - 90, 45, 
            text="CPU", 
            fill="white", 
            font=("Courier", 10)
        )

    def update_cpu_activity(self):
        current_time = time.time()
        if current_time - self.last_cpu_check >= 1:  # Update every second
            self.cpu_percent = psutil.cpu_percent()
            self.last_cpu_check = current_time

        color = 'red' if self.cpu_percent > self.THRESHOLD else 'green'

        if self.cpu_percent > self.THRESHOLD:
            # CPU usage is above threshold, blink rapidly
            blink_state = int(current_time * 10) % 2 == 0  # Blink 5 times per second
            self.set_led_state(blink_state, color)
        else:
            # CPU usage is below threshold, blink slowly
            blink_state = int(current_time) % 2 == 0  # Blink once per second
            self.set_led_state(blink_state, color)

        # Update GUI LED color
        
        #self.canvas.itemconfig(self.led, fill=color)

        # Schedule the next update
        self.master.after(100, self.update_cpu_activity)

    def set_led_state(self, state, color):
        # Update physical LED if available
        if self.gpio_available:
            try:
                self.led_line.set_value(1 if state else 0)
            except Exception as e:
                print(f"Error setting LED state: {e}")
        
        # Update GUI LED
        if state:
            self.canvas.itemconfig(self.led, fill=color)
        else:
            self.canvas.itemconfig(self.led, fill=f'dark {color}')
        #self.canvas.itemconfig(self.led, state='normal' if state else 'hidden')


    def calculate_max_lines(self):
        font = ImageFont.truetype("courier.ttf", self.font_size)
        unused1,unused2,unused3, line_height = font.getbbox("A")  # text width, height
        self.max_lines = self.log_display_height // line_height

    def update_logs(self):
        try:
            while not self.log_queue.empty():
                log = self.log_queue.get_nowait()
                wrapped_lines = textwrap.wrap(log, width=self.log_display_width // (self.font_size // 2))
                self.log_lines.extend(wrapped_lines)
            self.display_logs()
        except:
            pass
        self.master.after(100, self.update_logs)

    def add_log(self, log_text):
        self.log_queue.put(log_text)

    def display_logs(self):
        display_lines = list(self.log_lines)[-self.max_lines:]
        display_text = "\n".join(display_lines)
        self.glitch_print(display_text)

    def glitch_print(self, text):
        glitched_text = ""
        colors = ["blue", "magenta", "cyan"]
        for char in text:
            if random.random() < 0.02:
                glitched_text += random.choice("@#$%&*")
            else:
                glitched_text += char

        self.canvas.itemconfig(self.log_display, text=glitched_text)

        if random.random() < 0.1:
            glitch_color = random.choice(colors)
            self.canvas.itemconfig(self.log_display, fill=glitch_color)
        else:
            self.canvas.itemconfig(self.log_display, fill="green")