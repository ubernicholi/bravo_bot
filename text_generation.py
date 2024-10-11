import requests, json,logging,os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()
KOBOLD_ENDPOINT = os.getenv('KOBOLD_ENDPOINT')
MONOLITH_ENDPOINT = os.getenv('MONOLITH_ENDPOINT')
ALPHA_TTS_ENDPOINT = os.getenv('ALPHA_TTS_ENDPOINT')
    
LOG_FILE_TELEGRAM = os.getenv('LOG_FILE_TELEGRAM')
# Set up logging
logging.basicConfig(filename=LOG_FILE_TELEGRAM, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def split_into_messages(text):
    return [text[i:i+4000] for i in range(0, len(text),4000)]

def process_message(prompt):
    try:
        response = requests.post(f"{MONOLITH_ENDPOINT}/api/v1/generate", json=prompt)
        if response.status_code == 200:
            try:
                results = response.json().get('results', [])
                if results:
                    text = results[0].get('text', '').replace("  ", " ")
                    text = text.replace('<0x0A>', '\n')
                    response_texts = split_into_messages(text)
                    for text_segment in response_texts:
                        json_that_thing = {
                            "text": f"{text_segment}"
                        }
                        #requests.post(f"{ALPHA_TTS_ENDPOINT}", json=json_that_thing)

                    return response_texts
                else:
                    logging.error("Empty results from API.")
                    return ["Sorry, I couldn't process your message.(sent bad json)"]
            except json.JSONDecodeError as e:
                logging.error(f"JSON decoding failed: {e}")
                return [f"Sorry, I couldn't process your message.(bad result)."]
        else:
            logging.error(f"API request failed with status code: {response.status_code}")
            return [f"Sorry, there was a problem with the server. Status Code\n\n{response.status_code}"]
    except requests.RequestException as e:
        logging.error(f"Request to API failed: {e}")
        return [f"Sorry, there was a problem processing your request.(kobold API not Active)"]
    