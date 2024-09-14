import asyncio
import logging
import os
import random
import uuid
import io
import json
import urllib
import emoji

from urllib.parse import quote

from telethon import TelegramClient, events
from telethon.tl import types
from telethon.sessions import MemorySession

from pydub import AudioSegment
import requests

import comfyui_generation
import text_generation
import words

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
LOG_FILE_TELEGRAM = os.getenv('LOG_FILE_TELEGRAM')
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
KOBOLD_CONFIG_FILE = os.getenv('KOBOLD_CONFIG_FILE')
COMFYUI_VOICE = os.getenv('COMFYUI_VOICE')
COMFYUI_PROMPT_ENHANCE = os.getenv('COMFYUI_PROMPT_ENHANCE')
COMFYUI_PROMPT = os.getenv('COMFYUI_PROMPT')
COMFYUI_MUSIC = os.getenv('COMFYUI_MUSIC')
TTS_SERVER_URL = os.getenv('TTS_SERVER_URL')
FREEMYIP_URL = os.getenv('FREEMYIP_ENDPOINT')

# Set up logging
logging.basicConfig(filename=LOG_FILE_TELEGRAM, level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramBot:
    def __init__(self, log_queue, led_control_queue):
        self.log_queue = log_queue
        self.led_control_queue = led_control_queue
        self.client = TelegramClient(MemorySession(), TELEGRAM_API_ID, TELEGRAM_API_HASH)


    async def start(self):
        await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)

        self.bot_id = (await self.client.get_me()).id

        @self.client.on(events.NewMessage(pattern='/getip'))
        async def get_ip_handler(event):
            await self.get_ip(event)

        @self.client.on(events.NewMessage(pattern='/checkservices'))
        async def check_services_handler(event):
            await self.check_services(event)

        @self.client.on(events.NewMessage(pattern='/image'))
        async def handle_enhanced_image_handler(event):
            await self.process_image_prompt(event,'enhanced')

        @self.client.on(events.NewMessage(pattern='/normal'))
        async def handle_normal_image_handler(event):
            await self.process_image_prompt(event,'normal')

        @self.client.on(events.NewMessage(pattern='/random'))
        async def handle_random_image_handler(event):
            await self.process_random_prompt(event)

        @self.client.on(events.NewMessage(pattern='/speak_male'))
        async def handle_speak_male_handler(event):
            await self.handle_speak(event, 'male')

        @self.client.on(events.NewMessage(pattern='/speak_female'))
        async def handle_speak_female_handler(event):
            await self.handle_speak(event,'female')
        
        @self.client.on(events.NewMessage(pattern='/voice'))
        async def handle_voice_handler(event):
            await self.handle_voice(event)

        @self.client.on(events.NewMessage(pattern='/music'))
        async def handle_music_handler(event):
            await self.handle_music(event)

        @self.client.on(events.NewMessage(pattern='/ask'))
        async def handle_ask_handler(event):
            await self.handle_messages(event)

        @self.client.on(events.NewMessage(func=lambda e: e.is_private))
        async def handle_private_message(event):
            if not event.message.text.startswith('/'):
                await self.handle_messages(event)

        await self.client.run_until_disconnected()

    #-----------------------------------------------------------------------------------------
    #telegram bot

    async def get_ip(self, event):
        self.led_control_queue.put('telegram:' + str(True))
        ip_address, register = self.get_external_ip()
        self.log_queue.put(f"Ip Address Registration: {register}\n")
        await event.reply(f"The current external IP address is: {ip_address}")
        self.led_control_queue.put('telegram:' + str(False))

    def get_external_ip(self):
        try:
            response = requests.get('https://api.ipify.org')
            response_register = requests.get(FREEMYIP_URL)

            if response.status_code == 200:
                return response.text, response_register.text
            else:
                return "Could not fetch IP"
        except Exception as e:
            return f"Error: {str(e)}"

    async def check_services(self,event):
        self.led_control_queue.put('telegram:'+ str(True))
        services = {
            "Alpha_Camera": ("192.168.86.35",8000),
            "Webserver_Bravo": ("192.168.0.16", 80),
            "LLM_Bravo": ("192.168.0.16", 5001),
            "LLM_Monolith": ("192.168.0.6", 8051),
            "ComfyUI_Monolith": ("192.168.0.6", 7860),
            "Coqui_TTS_Monolith" : ("192.168.0.6",5002)
        }

        def get_service_status():
            results = []
            for service, (ip, port) in services.items():
                internal_url = f"http://{ip}:{port}"
                internal_status = "✅" if self.check_service(internal_url) else "❌"

                results.append(f"{service} @ {internal_url} is {internal_status}")
            
            return f"Service Status: \n" + "\n".join(results)

        message = get_service_status()
        self.log_queue.put(f"{message}\n")
        await event.reply(message)
        self.led_control_queue.put('telegram:'+ str(False))

    def check_service(self,url):
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    #------------------------------------------------------------------------------------------
    #helpers

    def load_json(self, filename):
        with open(filename, 'r') as file:
            return json.load(file)

    def convert_audio_to_mp3(self, audio_data, input_format):
        """
        String indicating the input format ('flac', 'ogg', or 'wav')
        """
        try:
            if input_format == 'ogg':
                audio = AudioSegment.from_ogg(io.BytesIO(audio_data))
            else:
                audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format)
            
            mp3_data = io.BytesIO()
            audio.export(mp3_data, format="mp3")
            mp3_data.seek(0)
            return mp3_data
        except Exception as e:
            raise ValueError(f"Error converting {input_format} to MP3: {str(e)}")
    
    #------------------------------------------------------------------------------------------
    #Text Generation - Koboldcpp

    async def handle_messages(self, event):
        self.led_control_queue.put('telegram:' + str(True))
        user_message = event.message.text
        if user_message.startswith('/ask'):
            user_message = user_message[5:].strip()
        
        if event.message.is_reply:
            replied = await event.message.get_reply_message()
            if replied.text:
                user_message += " " + replied.text
        
        self.log_queue.put(f"User Message: {user_message}\n")

        prompt = self.load_json(KOBOLD_CONFIG_FILE)
        prompt["max_length"] = 320
        prompt["temperature"] = 0.75
        prompt["memory"] = "[You are Roleplaying as Bravolith, A Female Artificial Intelligence, You are running on limited hardware, A Raspberry 5 8GB, use concise messages unless specified and use Emoji when appropriate]\n\n"
        prompt["prompt"] = f"<start_of_turn>user\n{user_message}<end_of_turn>\n<start_of_turn>model\n"

        self.led_control_queue.put('monolith:' + str(True))
        response_texts = text_generation.process_message(prompt)
        self.led_control_queue.put('monolith:' + str(False))

        for text_segment in response_texts:
            self.log_queue.put(f"Bravo Response: {text_segment}\n")
            await event.reply(text_segment)

        self.led_control_queue.put('telegram:' + str(False))

    #------------------------------------------------------------------------------------------
    #Image Generation - ComfyUI

    async def process_random_prompt(self,event):
        self.led_control_queue.put('telegram:'+ str(True))
        client_id = str(uuid.uuid4())
        prompt = self.load_json(COMFYUI_PROMPT)

        user_message = words.fetch_random_prompt()

        prompt["50"]["inputs"]["prompt"] = user_message
        prompt["25"]["inputs"]["noise_seed"] = random.randint(1,4294967294)

        self.log_queue.put(f"Generating Random Image of : {user_message}\n")
        await event.reply(f"Generating Random Image of : {user_message}\n")

        self.led_control_queue.put('monolith:'+ str(True))
        img_to_send,error = comfyui_generation.do_stuff('images',prompt,client_id)
        self.led_control_queue.put('monolith:'+ str(False))

        if img_to_send is not None:
            # Convert the image data to a file-like object
            image_file = io.BytesIO(img_to_send)
            image_file.name = 'generated_image.png'  # Give a name to the file

            # Send the image
            await event.reply(file=image_file)
        else:
            self.log_queue.put(f"Sorry, there was an error generating the image:\n{error}\n")
            await event.reply(f"Sorry, there was an error generating the image:\n{error}")

        self.led_control_queue.put('telegram:' + str(False))

    async def process_image_prompt(self,event,i_type):
        self.led_control_queue.put('telegram:'+ str(True))
        client_id = str(uuid.uuid4())
        
        user_message = event.message.text.split(None, 1)[1] if len(event.message.text.split()) > 1 else ''

        if event.message.is_reply:
            replied = await event.message.get_reply_message()
            if replied.text:
                user_message += " " + replied.text

        if not user_message:
            await event.reply('Please provide some text.')
            self.led_control_queue.put('telegram:'+ str(False))
            return

        prompt = {}

        if i_type == 'normal':
            prompt = self.load_json(COMFYUI_PROMPT)

        elif i_type == 'enhanced':
            prompt = self.load_json(COMFYUI_PROMPT_ENHANCE)
            prompt["97"]["inputs"]["seed"] = random.randint(1,4294967294)

        prompt["50"]["inputs"]["prompt"] = user_message
        prompt["25"]["inputs"]["noise_seed"] = random.randint(1,4294967294)

        self.log_queue.put(f"Generating {i_type} Image of : {user_message}\n")

        self.led_control_queue.put('monolith:'+ str(True))
        img_to_send,error = comfyui_generation.do_stuff('images',prompt,client_id)
        self.led_control_queue.put('monolith:'+ str(False))

        if img_to_send is not None:
            # Convert the image data to a file-like object
            image_file = io.BytesIO(img_to_send)
            image_file.name = 'generated_image.png'  # Give a name to the file

            # Send the image
            await event.reply(file=image_file)
        else:
            self.log_queue.put(f"Sorry, there was an error generating the image:\n{error}\n")
            await event.reply(f"Sorry, there was an error generating the image:\n{error}")

        self.led_control_queue.put('telegram:' + str(False))

    #------------------------------------------------------------------------------------------
    # voice

    async def handle_speak(self, event, v_type):
        self.led_control_queue.put('telegram:' + str(True))

        # TTS settings
        female_voice = 'p339'
        male_voice = 'p313'
        SPEAKER_ID = 'p376'  # You can change this or make it configurable
        LANGUAGE_ID = ''  # Leave empty or set as needed

        user_message = event.message.text.split(None, 1)[1] if len(event.message.text.split()) > 1 else ''

        if v_type == 'male':
            SPEAKER_ID = male_voice
        elif v_type == 'female':
            SPEAKER_ID = female_voice

        if event.message.is_reply:
            replied = await event.message.get_reply_message()
            if replied.text:
                user_message += " " + replied.text

        if not user_message:
            await event.reply('Please provide some text.')
            self.led_control_queue.put('telegram:' + str(False))
            return
        
        self.log_queue.put(f"User Message: {user_message}\n")
        encoded_text = urllib.parse.quote(user_message)
        full_url = f'{TTS_SERVER_URL}/api/tts?text={encoded_text}&speaker_id={SPEAKER_ID}&style_wav=&language_id={LANGUAGE_ID}'

        # Send a request to the Coqui TTS server
        try:
            self.led_control_queue.put('monolith:' + str(True))
            response = requests.get(full_url, timeout=30)
            response.raise_for_status()
            self.led_control_queue.put('monolith:' + str(False))
            
            # The response should contain the audio file in WAV format
            wav_content = response.content
            mp3_content = self.convert_audio_to_mp3(wav_content, "wav")
            
            if mp3_content is not None:
                # Convert the MP3 data to a file-like object
                audio_file = io.BytesIO(mp3_content.getvalue())
                audio_file.name = 'bravolith_speak.mp3'

                # Send the audio file
                await event.reply(file=audio_file, attributes=[
                    types.DocumentAttributeAudio(
                        duration=0,  # You can set the duration if known
                        title="Coqui TTS",
                        performer="Bravolith"
                    )
                ])
            else:
                self.log_queue.put(f'Error converting audio to MP3\n')
                await event.reply('Error converting audio to MP3')

        except requests.RequestException as e:
            self.log_queue.put(f'Error communicating with TTS server: {str(e)}\n')
            await event.reply(f'Error communicating with TTS server: {str(e)}')

        self.led_control_queue.put('telegram:' + str(False))

    async def handle_voice(self, event):
        self.led_control_queue.put('telegram:'+ str(True))
        client_id = str(uuid.uuid4())

        user_message = event.message.text.split(None, 1)[1] if len(event.message.text.split()) > 1 else ''

        if event.message.is_reply:
            replied = await event.message.get_reply_message()
            if replied.text:
                user_message += " " + replied.text

        if not user_message:
            await event.reply('Please provide some text.')
            self.led_control_queue.put('telegram:' + str(False))
            return

        prompt = self.load_json(COMFYUI_VOICE)
        prompt["95"]["inputs"]["text"] = user_message
        prompt["95"]["inputs"]["speaker"] = "Pigston_Banker_ill.ogg" 

        self.log_queue.put(f"Generate Voice Saying: {user_message}\n")
              
        self.led_control_queue.put('monolith:'+ str(True))
        raw_flac,error = comfyui_generation.do_stuff('audio',prompt,client_id)
        self.led_control_queue.put('monolith:'+ str(False))
        if raw_flac is not None:
            mp3_data = self.convert_audio_to_mp3(raw_flac,"flac")
            if mp3_data is not None:
                # Convert the MP3 data to a file-like object
                audio_file = io.BytesIO(mp3_data.getvalue())
                audio_file.name = 'bravolith_speak.mp3'

                # Send the audio file
                await event.reply(file=audio_file, attributes=[
                    types.DocumentAttributeAudio(
                        duration=0,  # You can set the duration if known
                        title="ComfyUI Voice",
                        performer="Bravolith"
                    )
                ])
            else:
                self.log_queue.put(f'Error converting audio to MP3\n')
                await event.reply('Error converting audio to MP3')
        else:
            c_error = f"ComfyUI error:\n{error}"
            self.log_queue.put(f"{c_error}\n")
            await event.reply(text=f"{c_error}")

        self.led_control_queue.put('telegram:'+ str(False))

    #------------------------------------------------------------------------------------------
    # music

    async def handle_music(self, event):
        self.led_control_queue.put('telegram:'+ str(True))

        client_id = str(uuid.uuid4())
       # Get the full message text
        full_message = event.message.text

        # Remove the command from the beginning of the message
        user_message = full_message.split(None, 1)[1] if len(full_message.split()) > 1 else ''

        # Split the user message into words
        args = user_message.split()

        prompt = self.load_json(COMFYUI_MUSIC)
        prompt["11"]["inputs"]["seconds"] = 20  # Default value

        # Check if the first argument is a number (file length)
        if args and args[0].isdigit():
            file_length = int(args[0])
            prompt["11"]["inputs"]["seconds"] = file_length
            args = args[1:]  # Remove the first argument
            user_message = ' '.join(args)  # Rejoin the remaining arguments
        
        if event.message.is_reply:
            replied = await event.message.get_reply_message()
            if replied.text:
                user_message += " " + replied.text

        if not user_message:
            await event.reply('Please provide some text.')
            self.led_control_queue.put('telegram:' + str(False))
            return

        prompt["6"]["inputs"]["text"] = user_message
        prompt["3"]["inputs"]["seed"] = random.randint(1,4294967294)

        self.log_queue.put(f"Generating Music File about: {user_message}\n")
        
        self.led_control_queue.put('monolith:'+ str(True))
        raw_flac,error = comfyui_generation.do_stuff('audio',prompt,client_id)
        self.led_control_queue.put('monolith:'+ str(False))

        if raw_flac is not None:
            try:
                mp3_data = self.convert_audio_to_mp3(raw_flac, "flac")
                
                # Convert the MP3 data to a file-like object
                audio_file = io.BytesIO(mp3_data.getvalue())
                audio_file.name = 'music_sample.mp3'

                # Get the user's name for the performer attribute
                user = await event.get_sender()
                performer = user.first_name if user.first_name else user.username
                performer = f"BRAVOLITH feat. {performer}"

                # Send the audio file
                await event.reply(file=audio_file, attributes=[
                    types.DocumentAttributeAudio(
                        duration=0,  # You can set the duration if known
                        title="Generated Music Sample",
                        performer=performer
                    )
                ])

            except Exception as e:
                await event.reply(f"Sorry, there was an error converting the audio: {str(e)}")
        else:
            await event.reply(f"ComfyUI error:\n{error}")

        self.led_control_queue.put('telegram:' + str(False))

def start_bot(log_queue, led_control_queue):
    bot = TelegramBot(log_queue, led_control_queue)
    asyncio.run(bot.start())

# If this script is run directly, start the bot
if __name__ == '__main__':
    start_bot(None, None)