import multiprocessing
import tkinter as tk
from retro_terminal import RetroTerminal
from bot_telegram import start_bot
import time
import os, logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
LOG_FILE = os.getenv('LOG_FILE')
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Shared queues for communication between processes
log_queue = multiprocessing.Queue()
led_control_queue = multiprocessing.Queue()

def run_gui(log_queue, led_control_queue):
    root = tk.Tk()
    terminal = RetroTerminal(root, 800, 600, log_queue=log_queue, led_control_queue=led_control_queue)
    root.mainloop()

if __name__ == '__main__':
    while True:
        try:
            # Start GUI process
            gui_process = multiprocessing.Process(target=run_gui, args=(log_queue, led_control_queue))
            gui_process.start()

            # Start bot process
            bot_process = multiprocessing.Process(target=start_bot, args=(log_queue, led_control_queue))
            bot_process.start()

            # Wait for processes to finish
            gui_process.join()
            bot_process.join()
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected. Shutting down...")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Terminate processes if they're still running
            if gui_process.is_alive():
                gui_process.terminate()
            if bot_process.is_alive():
                bot_process.terminate()
            
            # Clear the queues
            for queue in [log_queue, led_control_queue]:
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except:
                        pass
            print("Restarting in 5 seconds...")
            time.sleep(5)
        print("Restarting application...")