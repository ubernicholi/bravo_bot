import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import random
from collections import deque
import textwrap
import os, logging, time, psutil
from led_controller import LEDController
import cv2
from dotenv import load_dotenv
import urllib.request
import numpy as np
import threading
import queue

# Load environment variables
load_dotenv()

LOG_FILE_TERMINAL = os.getenv('LOG_FILE_TERMINAL')

logging.basicConfig(filename=LOG_FILE_TERMINAL, level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class CRTFrame:
    def __init__(self, width, height, border_width=60):
        self.width = width
        self.height = height
        self.border_width = border_width
        self.frame_image = self.create_frame()

    def create_frame(self):
        image = Image.new('RGBA', (self.width, self.height), (0, 25, 0, 100))
        draw = ImageDraw.Draw(image)
        
        # Draw the main CRT frame
        draw.rectangle(
            [(0, 0), (self.width, self.height)],
            outline=(100, 100, 100, 255),
            width=self.border_width
        )
        
        # Draw diagonal lines
        line_color = (50, 50, 50, 255)  # Darker grey for subtle effect
        line_color2 = (25, 25, 25, 255)  # Even darker grey for subtle effect
        
        thickness = 4
        thickness2 = 4
        
        # Draw frame edges
        self.draw_frame_edge(draw, line_color, thickness)
        
        # Draw corner lines
        self.draw_corner_lines(draw, line_color2, thickness2)

        return ImageTk.PhotoImage(image)

    def draw_frame_edge(self, draw, color, thickness):
        edges = [
            [(self.border_width, self.border_width), (self.width - self.border_width, self.border_width)],
            [(self.border_width, self.border_width), (self.border_width, self.height - self.border_width)],
            [(self.border_width, self.height - self.border_width), (self.width - self.border_width, self.height - self.border_width)],
            [(self.width - self.border_width, self.border_width), (self.width - self.border_width, self.height - self.border_width)]
        ]
        for edge in edges:
            draw.line(edge, fill=color, width=thickness)

    def draw_corner_lines(self, draw, color, thickness):
        corners = [
            [(0, 0), (self.border_width, self.border_width)],
            [(self.width, 0), (self.width - self.border_width, self.border_width)],
            [(0, self.height), (self.border_width, self.height - self.border_width)],
            [(self.width, self.height), (self.width - self.border_width, self.height - self.border_width)]
        ]
        for corner in corners:
            draw.line(corner, fill=color, width=thickness)

    def get_frame(self):
        return self.frame_image

class VideoStream:
    def __init__(self, url, width, height):
        self.url = url
        self.width = width
        self.height = height
        self.frame_queue = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._capture_frames)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join()

    def _capture_frames(self):
        cap = cv2.VideoCapture(self.url)
        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (self.width, self.height))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
            else:
                time.sleep(0.1)
        cap.release()

    def get_frame(self):
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

class RetroTerminal:
    def __init__(self, master, width, height, max_logs=4, font_size=12, log_queue=None, led_control_queue=None):
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
        self.video_frame = None

        self.led_update_interval = 100  # milliseconds
        self.log_update_interval = 100  # milliseconds
        self.led_states = {name: False for name in ['cpu', 'webcam', 'telegram', 'monolith']}
        self.log_buffer = []

        self.setup_video_stream()

        self.create_ascii_art()
        self.create_log_display()
    
        # Create CRT frame
        self.crt_frame = CRTFrame(width, height)
        self.canvas.create_image(0, 0, anchor="nw", image=self.crt_frame.get_frame())
    
        self.create_leds()

        self.last_cpu_check = time.time()
        self.start_update_loops()

    def create_ascii_art(self):
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
            self.width // 2, 54,
            text=self.ascii_art_2,
            fill="blue",
            font=("Courier", 10),
            anchor="n"
        )

    def create_log_display(self):
        self.log_display_width = int(self.width * 0.8)
        self.log_display_height = int(self.height * 0.6)
        self.log_display_x = self.width // 2
        self.log_display_y = (self.height // 7) * 3

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

    def create_leds(self):
        self.led_radius = 10
        self.leds = {}
        led_positions = [(self.width - 100, 20), (self.width - 200, 20), (self.width - 300, 20), (self.width - 400, 20)]
        led_names = ['cpu', 'webcam', 'telegram', 'monolith']
        
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

    def setup_video_stream(self):
        video_width = self.width - 123
        video_height = self.height - 124
        self.video_stream = VideoStream(self.video_stream_url, video_width, video_height)
        self.video_frame = self.canvas.create_image(
            self.width // 2 + 1, self.height // 2 + 1,
            anchor="center"
        )

    def start_video_stream(self):
        self.video_stream.start()
        self.update_video_frame()
        self.toggle_webcam(True)

    def stop_video_stream(self):
        self.video_stream.stop()
        self.toggle_webcam(False)

    def update_video_frame(self):
        frame = self.video_stream.get_frame()
        if frame is not None:
            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image=image)
            self.canvas.itemconfig(self.video_frame, image=photo)
            self.canvas.image = photo  # Keep a reference to avoid garbage collection

        self.master.after(66, self.update_video_frame)  # Update roughly 30 times per second

    def start_update_loops(self):
        self.update_led_activity()
        self.update_logs()

    def update_led_activity(self):
        current_time = time.time()
        if current_time - self.last_cpu_check >= 1:  # Update CPU usage every second
            cpu_percent = psutil.cpu_percent()
            self.led_controller.set_cpu_usage(cpu_percent)
            self.last_cpu_check = current_time

        while not self.led_control_queue.empty():
            try:
                message = self.led_control_queue.get_nowait()
                if message.startswith('telegram:'):
                    _, state = message.split(':')
                    self.toggle_telegram(state == 'True')
                if message.startswith('monolith:'):
                    _, state = message.split(':')
                    self.toggle_monolith(state == 'True')
            except queue.Empty:
                break

        led_updates = []
        for led_name, led_oval in self.leds.items():
            new_color = self.led_controller.get_led_color(led_name)
            if new_color != self.led_states[led_name]:
                led_updates.append((led_oval, new_color))
                self.led_states[led_name] = new_color

        if led_updates:
            self.canvas.after(0, self.batch_update_leds, led_updates)

        self.master.after(self.led_update_interval, self.update_led_activity)

    def batch_update_leds(self, updates):
        for led_oval, color in updates:
            self.canvas.itemconfig(led_oval, fill=color)

    def update_logs(self):
        try:
            while not self.log_queue.empty():
                log = self.log_queue.get_nowait()
                self.log_buffer.append(log)
        except queue.Empty:
            pass

        if self.log_buffer:
            self.process_log_buffer()

        self.master.after(self.log_update_interval, self.update_logs)

    def process_log_buffer(self):
        for log in self.log_buffer:
            wrapped_lines = textwrap.wrap(log, width=self.log_display_width // (self.font_size // 2))
            self.log_lines.extend(wrapped_lines)

        self.log_buffer.clear()
        self.display_logs()

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

    def toggle_webcam(self, is_active):
        self.led_controller.toggle_webcam(is_active)
        if is_active and not self.video_stream.thread:
            self.start_video_stream()
        elif not is_active and self.video_stream.thread:
            self.stop_video_stream()

    def toggle_telegram(self, is_active):
        self.led_controller.toggle_telegram(is_active)

    def toggle_monolith(self, is_active):
        self.led_controller.toggle_monolith(is_active)

    def calculate_max_lines(self):
        font = ImageFont.truetype("courier.ttf", self.font_size)
        _,_,_, line_height = font.getbbox("A")  # text width, height
        self.max_lines = self.log_display_height // line_height

