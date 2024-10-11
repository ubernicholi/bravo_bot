import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import urllib.request
import urllib.parse
import json, os, logging
import threading

from dotenv import load_dotenv
# Load environment variables
load_dotenv()

COMFYUI_ENDPOINT = os.getenv('COMFYUI_ENDPOINT')
LOG_FILE_TELEGRAM = os.getenv('LOG_FILE_TELEGRAM')
# Set up logging
logging.basicConfig(filename=LOG_FILE_TELEGRAM, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class WebSocketManager:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.lock = threading.Lock()

    def create_connection(self, client_id):
        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.endpoint}/ws?clientId={client_id}")
        return ws

    def send_prompt(self,toggle_flag, ws, prompt, client_id):
        with self.lock:
            return send_prompt(toggle_flag, ws, prompt, client_id)

ws_manager = WebSocketManager(COMFYUI_ENDPOINT)

def do_stuff(toggle_flag, prompt, client_id):
    try:
        ws = ws_manager.create_connection(client_id)
        files = ws_manager.send_prompt(toggle_flag, ws, prompt, client_id)
        ws.close()

        for node_id in files:
            if files[node_id]:
                file_data = files[node_id][0]
                return file_data, None

        logging.error("Empty results from API.")
        return None, "Sorry, I couldn't process your message.(sent bad json)"

    except Exception as e:
        logging.error(f"Request to API failed: {e}")
        return None, e

def send_prompt(toggle_flag, ws, prompt, client_id):
    prompt_id = queue_prompt(prompt, client_id)['prompt_id']
    output_files = {}

    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing' and message['data']['node'] is None and message['data']['prompt_id'] == prompt_id:
                break
        else:
            continue

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        output = []
        if toggle_flag in node_output:
            for file in node_output[toggle_flag]:
                file_data = get_file(file['filename'], file['subfolder'], file['type'])
                output.append(file_data)
                
        output_files[node_id] = output

    return output_files

def queue_prompt(prompt,client_id):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(COMFYUI_ENDPOINT), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_file(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(COMFYUI_ENDPOINT, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(COMFYUI_ENDPOINT, prompt_id)) as response:
        return json.loads(response.read())
