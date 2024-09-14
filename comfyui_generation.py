import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import urllib.request
import urllib.parse
import json, os, logging

from dotenv import load_dotenv
# Load environment variables
load_dotenv()

COMFYUI_ENDPOINT = os.getenv('COMFYUI_ENDPOINT')

def do_stuff(toggle_flag,prompt, client_id):
    try:
        # Connect to WebSocket, send the prompt, wwait for images
        ws = websocket.WebSocket()
        ws.connect("ws://{}/ws?clientId={}".format(COMFYUI_ENDPOINT, client_id))

        # send prompt to comfyui
        files = send_prompt(toggle_flag,ws, prompt, client_id)
        
        # Check if files are available and send the first file of the first node
        for node_id in files:
            if files[node_id]:  # Check if the list is not empty
                file_data = files[node_id][0]  # Get the first file of this node   
                return file_data,None
            
        else:
            logging.error("Empty results from API.")
            return None,"Sorry, I couldn't process your message.(sent bad json)"

    except Exception as e:
        logging.error(f"Request to API failed: {e}")
        return None,e

def send_prompt(toggle_flag,ws, prompt,client_id):
    prompt_id = queue_prompt(prompt,client_id)['prompt_id']

    output_files = {}

    # Wait for the execution to complete
    while True:
        out = ws.recv()
        if isinstance(out, str):  # Check if the output is string (JSON data)
            message = json.loads(out)
            if message['type'] == 'executing' and message['data']['node'] is None and message['data']['prompt_id'] == prompt_id:
                break  # Execution is done, exit the loop
        else:
            continue  # Ignore binary data (previews)

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        output = []  # Initialize images_output outside the 'if'
        if toggle_flag in node_output:
            for file in node_output[toggle_flag]:
                file_data = get_file(file['filename'], file['subfolder'], file['type'])
                output.append(file_data)
                
        output_files[node_id] = output  # Assign collected images or an empty list if no images

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
