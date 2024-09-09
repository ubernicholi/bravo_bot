import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import random
from collections import deque
import textwrap
import os, logging, time, psutil
from led_controller import LEDController
import cv2
import threading
from dotenv import load_dotenv
import urllib.request
import numpy as np

# Load environment variables
load_dotenv()

LOG_FILE_TERMINAL = os.getenv('LOG_FILE_TERMINAL')

logging.basicConfig(filename=LOG_FILE_TERMINAL, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class RetroTerminal:
    def __init__(self, master, width, height, max_logs=11, font_size=12, log_queue=None, led_control_queue=None):
        self.master = master
        self.master.title("Bravolith Terminal")
        
        self.width = width
        self.height = height
        self.master.geometry(f"{width}x{height}")
        
        self.log_queue = log_queue
        self.max_logs = max_logs
        self.font_size = font_size
        self.log_lines = deque(maxlen=max_logs)

        self.canvas = tk.Canvas(master, bg="gray5", width=width, height=height)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.led_controller = LEDController()
        self.led_control_queue = led_control_queue

        

        # Start video stream
        self.video_stream_url = "http://192.168.0.5:8000/stream.mjpg"
        self.video_stream = None
        self.start_video_stream()

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
            width // 2, 50,
            text=self.ascii_art_2,
            fill="blue",
            font=("Courier", 10),
            anchor="n"
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



        # Create CPU activity LED
        self.led_radius = 10
        self.leds = {}
        led_positions = [(width - 100, 20), (width - 200, 20), (width - 300, 20), (width - 400, 20)]
        led_names = ['cpu', 'webcam', 'telegram', 'motd']
        
        for i, (name, pos) in enumerate(zip(led_names, led_positions)):
            self.leds[name] = self.canvas.create_oval(
                pos[0], pos[1], pos[0] + 20, pos[1] + 20, 
                fill=self.led_controller.get_led_color(name), outline='gray5'
            )
            self.canvas.create_text(
                pos[0] + 27, pos[1] + 12, 
                text=name.upper(), 
                fill="ivory2", 
                font=("Courier", 10),
                anchor="w"
            )

        self.last_cpu_check = time.time()
        # Start updating LED activity
        self.update_led_activity()


    def start_video_stream(self):
        self.video_stream = self.canvas.create_image(
            self.width // 2 + 1, self.height // 2 + 1,
            anchor="center"
        )
        self.update_video_frame()

    def update_video_frame(self):
        try:
            self.toggle_webcam(True)
            # Read the image from the URL
            stream_url = "http://192.168.0.5:8000/stream.mjpg"
            cap = cv2.VideoCapture(stream_url)
            _,frame = cap.read()
            # Resize the frame to fit inside the CRT frame
            frame = cv2.resize(frame, (self.width - 123, self.height - 124))
            
            # Convert the image from BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PhotoImage
            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image=image)
            
            # Update the image on the canvas
            self.canvas.itemconfig(self.video_stream, image=photo)
            self.canvas.image = photo  # Keep a reference to avoid garbage collection
        except Exception as e:
            self.toggle_webcam(False)

            print(f"Error updating video frame: {e}")

        # Schedule the next update
        self.master.after(66, self.update_video_frame)  # Update roughly 15 times per second

    def update_led_activity(self):
        while not self.led_control_queue.empty():
            try:
                message = self.led_control_queue.get_nowait()
                if message.startswith('telegram:'):
                    _, state = message.split(':')
                    self.toggle_telegram(state == 'True')
            except:
                pass

        current_time = time.time()
        if current_time - self.last_cpu_check >= 1:  # Update every second
            cpu_percent = psutil.cpu_percent()
            self.led_controller.set_cpu_usage(cpu_percent)
            self.last_cpu_check = current_time

        for led_name, led_oval in self.leds.items():
            color = self.led_controller.get_led_color(led_name)
            self.canvas.itemconfig(led_oval, fill=color)

        self.master.after(100, self.update_led_activity)

    def toggle_webcam(self, is_active):
        self.led_controller.toggle_webcam(is_active)

    def toggle_telegram(self, is_active):
        self.led_controller.toggle_telegram(is_active)

    def set_motd(self, message):
        self.led_controller.set_motd(message)

    def create_crt_frame(self, width, height, border_width=60):
        image = Image.new('RGBA', (width, height), (0, 0, 0, 100))
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

    def calculate_max_lines(self):
        font = ImageFont.truetype("courier.ttf", self.font_size)
        _,_,_, line_height = font.getbbox("A")  # text width, height
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
        colors = ["blue", "magenta", "cyan", "hot pink"]
        for char in text:
            if random.random() < 0.02:
                glitched_text += random.choice("@#$%&*░▒▓█▄▀▐")
            else:
                glitched_text += char

        self.canvas.itemconfig(self.log_display, text=glitched_text)

        if random.random() < 0.1:
            glitch_color = random.choice(colors)
            self.canvas.itemconfig(self.log_display, fill=glitch_color)
        else:
            self.canvas.itemconfig(self.log_display, fill="green")