import multiprocessing
import tkinter as tk
from retro_terminal import RetroTerminal
from bot_telegram import start_bot
import time
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
LOG_FILE_BRAVO = os.getenv('LOG_FILE')
logging.basicConfig(filename=LOG_FILE_BRAVO, level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Shared queues for communication between processes
log_queue = multiprocessing.Queue()
led_control_queue = multiprocessing.Queue()

def run_gui(log_queue, led_control_queue):
    root = tk.Tk()
    terminal = RetroTerminal(root, 800, 600, log_queue=log_queue, led_control_queue=led_control_queue)
    root.mainloop()

def main():
    max_restarts = 3
    restart_count = 0
    
    while restart_count < max_restarts:
        try:
            logging.error("Starting Bravolith application")
            
            # Start GUI process
            gui_process = multiprocessing.Process(target=run_gui, args=(log_queue, led_control_queue))
            gui_process.start()

            # Start bot process
            bot_process = multiprocessing.Process(target=start_bot, args=(log_queue, led_control_queue))
            bot_process.start()

            # Wait for processes to finish
            gui_process.join()
            bot_process.join()
            
            # If we reach here, both processes have ended normally
            logging.error("Bravolith application ended normally")
            break
            
        except KeyboardInterrupt:
            logging.error("KeyboardInterrupt detected. Shutting down...")
            break
        except Exception as e:
            logging.error(f"An error occurred: {e}", exc_info=True)
            restart_count += 1
            logging.error(f"Restarting application (attempt {restart_count}/{max_restarts})...")
        finally:
            # Terminate processes if they're still running
            for process in [gui_process, bot_process]:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
            
            # Clear the queues
            for queue in [log_queue, led_control_queue]:
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except queue.Empty:
                        pass
            
            if restart_count < max_restarts:
                time.sleep(5)
    
    if restart_count == max_restarts:
        logging.error("Max restart attempts reached. Exiting.")

if __name__ == '__main__':
    main()