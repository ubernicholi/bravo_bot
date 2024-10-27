import asyncio
import logging
import os
import random
import uuid
import io
import json
import urllib
import emoji

from collections import deque
from functools import partial

from urllib.parse import quote

from telethon import TelegramClient, events, Button
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
logging.basicConfig(filename=LOG_FILE_TELEGRAM, level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class TelegramBot:
    def __init__(self, log_queue, led_control_queue):
        self.log_queue = log_queue
        self.led_control_queue = led_control_queue
        self.client = TelegramClient(MemorySession(), TELEGRAM_API_ID, TELEGRAM_API_HASH)
        self.task_queue = asyncio.Queue()
        self.max_concurrent_tasks = 1
        self.running_tasks = set()

        # Define preset resolutions
        self.preset_resolutions = {
            "portrait": (512, 768),
            "landscape": (768, 512),
            "square": (512, 512),
            "hd": (1024, 768),
            "wide":(1536,512)
        }
        self.affirmative_responses = [
            "Got it! 👍",
            "Processing your request... ⚡",
            "On it! 🎨",
            "Starting generation... 🖼️",
            "Working on it! 🎯",
            "Challenge accepted! 🚀",
            "Let's make some art! 🎨",
            "Here we go! ✨",
            "Creating your vision... 🌟",
            "Magic in progress... ✨",
            "Beginning the creative process... 🎭",
            "Starting the image journey... 🗺️",
            "Firing up the generators... ⚡",
            "Initializing creative mode... 🎨",
            "Ready to create! 🎯"
        ]

        # Store user states for resolution selection
        self.user_states = {}

    async def start(self):
        await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
        self.bot_id = (await self.client.get_me()).id

        # Register handlers
        self.register_handlers()
        
        # Start task processor
        asyncio.create_task(self.process_tasks())
        
        await self.client.run_until_disconnected()

    def register_handlers(self):
        handlers = [
            ('/getip', self.get_ip),
            ('/checkservices', self.check_services),
            ('/image', self.handle_image_generation),  # New unified command
            ('/random', self.process_random_prompt),
            ('/speak_male', partial(self.handle_speak, 'male')),
            ('/speak_female', partial(self.handle_speak, 'female')),
            ('/voice', self.handle_voice),
            ('/music', self.handle_music),
            ('/ask', self.handle_messages),
            ('/webcam_on', self.handle_webcam_on),
            ('/webcam_off', self.handle_webcam_off),
            
        ]
        
        for command, handler in handlers:
            self.client.add_event_handler(
                self.create_command_handler(command, handler),
                events.NewMessage(pattern=command)
            )
        
        # Add handler for resolution selection callbacks
        self.client.add_event_handler(
            self.handle_callback,
            events.CallbackQuery()
        )
        
        # Handler for private messages
        self.client.add_event_handler(
            self.handle_private_message,
            events.NewMessage(func=lambda e: e.is_private and not e.message.text.startswith('/'))
        )

    def create_command_handler(self, command, handler):
        async def wrapper(event):
            #await self.acknowledge_command(event)
            await self.task_queue.put((event, handler))
        return wrapper

    async def acknowledge_command(self, event):
        command = event.message.text.split()[0] if event.message and event.message.text else "Unknown command"
        await event.reply(f"Received command {command}. Processing...")

    async def process_tasks(self):
        while True:
            if len(self.running_tasks) < self.max_concurrent_tasks:
                event, handler = await self.task_queue.get()
                task = asyncio.create_task(self.run_handler(event, handler))
                self.running_tasks.add(task)
                task.add_done_callback(self.running_tasks.discard)
            else:
                await asyncio.sleep(0.1)

    async def run_handler(self, event, handler):
        try:
            await handler(event)
        except Exception as e:
            error_message = f"Error in handler: {str(e)}\n"
            self.log_queue.put(error_message)
            await event.reply(f"An error occurred while processing your request: {str(e)}")
            logging.error(error_message, exc_info=True)

    # Make sure they're all async methods

    async def handle_private_message(self, event):
        if not event.message.text.startswith('/'):
            await self.handle_messages(event)

    async def get_ip_handler(self, event):
        await self.get_ip(event)

    async def check_services_handler(self, event):
        await self.check_services(event)

    async def handle_image_generation(self, event):
        user_id = event.sender_id
        message = event.message.text.split(None, 1)
        
        # Create inline keyboard for generation type selection
        keyboard = [
            [
                Button.inline("Normal Generation", data=f"type_normal_{user_id}"),
                Button.inline("Enhanced Generation", data=f"type_enhanced_{user_id}")
            ]
        ]
        
        # Store the original prompt in user state
        prompt = message[1] if len(message) > 1 else ''
        self.user_states[user_id] = {
            'prompt': prompt,
            'original_message': event
        }
        
        await event.reply(
            "Please select generation type:",
            buttons=keyboard
        )

    async def show_resolution_options(self, event, user_id):
        keyboard = [
            [
                Button.inline("Portrait (512x768)", data=f"res_portrait_{user_id}"),
                Button.inline("Landscape (768x512)", data=f"res_landscape_{user_id}")
            ],
            [
                Button.inline("Square (512x512)", data=f"res_square_{user_id}"),
                Button.inline("HD (1024x768)", data=f"res_hd_{user_id}")
            ],
            [
                Button.inline("Wide (1536x512)", data=f"res_wide_{user_id}"),
                #Button.inline("Custom Resolution", data=f"res_custom_{user_id}")
            ]
        ]
        
        await event.edit(
            "Please select an image resolution:",
            buttons=keyboard
        )

    async def handle_callback(self, event):
        user_id = int(event.data.decode().split('_')[-1])
        callback_type = event.data.decode().split('_')[0]
        
        if user_id not in self.user_states:
            await event.answer("Session expired. Please try again.")
            return
        
        if callback_type == 'type':
            # Handle generation type selection
            generation_type = event.data.decode().split('_')[1]
            self.user_states[user_id]['generation_type'] = generation_type
            await event.answer()
            await self.show_resolution_options(event, user_id)
            return
            
        elif callback_type == 'res':
            resolution_type = event.data.decode().split('_')[1]
            
            if resolution_type == 'custom':
                await event.answer()
                await event.reply(
                    "Please enter your desired resolution in the format 'WxH' (e.g., 640x480).\n"
                    "Supported dimensions: Width: 256-1536, Height: 256-1536"
                )
                self.user_states[user_id]['waiting_for_resolution'] = True
                return
            
            # Get resolution from presets
            width, height = self.preset_resolutions[resolution_type]
            original_event = self.user_states[user_id]['original_message']
            prompt = self.user_states[user_id]['prompt']
            generation_type = self.user_states[user_id]['generation_type']
            
            # Clean up user state
            del self.user_states[user_id]
            
            await event.answer()
            await original_event.reply(random.choice(self.affirmative_responses))
            await self.process_image_prompt(generation_type, original_event, width, height, prompt)

    def is_valid_resolution(self, width, height):
        return (256 <= width <= 1536 and 
                256 <= height <= 1536)

    async def handle_random_image_handler(self, event):
        await self.process_random_prompt(event)

    async def handle_speak_male_handler(self, event):
        await self.handle_speak(event, 'male')

    async def handle_speak_female_handler(self, event):
        await self.handle_speak(event,'female')
    
    async def handle_voice_handler(self, event):
        await self.handle_voice(event)

    async def handle_music_handler(self, event):
        await self.handle_music(event)

    async def handle_ask_handler(self, event):
        await self.handle_messages(event)

    async def handle_webcam_on_handler(self, event):
        await self.handle_webcam_on(event)

    async def handle_webcam_off_handler(self, event):
        await self.handle_webcam_off(event)


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
    
    async def handle_webcam_on(self, event):
        self.led_control_queue.put('webcam:' + str(True))
        self.log_queue.put("Webcam Toggled: ON\n")
        await event.reply(f"ok : ON")
        
    async def handle_webcam_off(self, event):
        self.led_control_queue.put('webcam:' + str(False))
        self.log_queue.put("Webcam Toggled: OFF\n")
        await event.reply(f"ok : OFF")
        

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

        prompt["102"]["inputs"]["text"] = user_message

        self.log_queue.put(f"Generating Random Image of : {user_message}\n")
        await event.reply(f"Generating Random Image of : {user_message}\n")

        self.led_control_queue.put('monolith:'+ str(True))
        images_data,error = comfyui_generation.do_stuff('images',prompt,client_id)
        self.led_control_queue.put('monolith:'+ str(False))

        if images_data is not None:
            # Send each image in the batch
            for i, img_data in enumerate(images_data, 1):
                image_file = io.BytesIO(img_data)
                image_file.name = f'generated_image_{i}.png'
                
                # Add a small delay between sends to avoid rate limiting
                if i > 1:
                    await asyncio.sleep(0.5)
                
                try:
                    await event.reply(
                        file=image_file
                        #caption=f"Image {i} of {len(images_data)}" if len(images_data) > 1 else None
                    )
                except Exception as e:
                    self.log_queue.put(f"Error sending image {i}: {str(e)}\n")
                    await event.reply(f"Error sending image {i}: {str(e)}")
        else:
            self.log_queue.put(f"Sorry, there was an error generating the images:\n{error}\n")
            await event.reply(f"Sorry, there was an error generating the images:\n{error}")
            
        self.led_control_queue.put('telegram:' + str(False))

    async def process_image_prompt(self, i_type, event, width=512, height=512, user_message=''):
        self.led_control_queue.put('telegram:' + str(True))
        client_id = str(uuid.uuid4())
        
        if not user_message:
            user_message = event.message.text.split(None, 1)[1] if len(event.message.text.split()) > 1 else ''
            if event.message.is_reply:
                replied = await event.message.get_reply_message()
                if replied.text:
                    user_message += " " + replied.text
        
        if not user_message:
            await event.reply('Please provide some text.')
            self.led_control_queue.put('telegram:' + str(False))
            return
            
        prompt = {}
        if i_type == 'normal':
            prompt = self.load_json(COMFYUI_PROMPT)
        elif i_type == 'enhanced':
            prompt = self.load_json(COMFYUI_PROMPT_ENHANCE)
            
        # Update the prompt with resolution
        prompt["102"]["inputs"]["text"] = user_message
        prompt["100"]["inputs"]["seed"] = random.randint(1, 4294967294)
        prompt["80"]["inputs"]["width"] = width
        prompt["80"]["inputs"]["height"] = height
        #prompt["80"]["inputs"]["batch_size"] = 2
        
        generation_type = "Normal" if i_type == "normal" else "Enhanced"
        self.log_queue.put(f"Generating {generation_type} Image of: {user_message} at {width}x{height}\n")
        self.led_control_queue.put('monolith:' + str(True))
        
        images_data, error = comfyui_generation.do_stuff('images', prompt, client_id)
        self.led_control_queue.put('monolith:' + str(False))
        
        if images_data is not None:
            # Send each image in the batch
            for i, img_data in enumerate(images_data, 1):
                image_file = io.BytesIO(img_data)
                image_file.name = f'generated_image_{i}.png'
                
                # Add a small delay between sends to avoid rate limiting
                if i > 1:
                    await asyncio.sleep(0.5)
                
                try:
                    await event.reply(
                        file=image_file
                        #caption=f"Image {i} of {len(images_data)}" if len(images_data) > 1 else None
                    )
                except Exception as e:
                    self.log_queue.put(f"Error sending image {i}: {str(e)}\n")
                    await event.reply(f"Error sending image {i}: {str(e)}")
        else:
            self.log_queue.put(f"Sorry, there was an error generating the images:\n{error}\n")
            await event.reply(f"Sorry, there was an error generating the images:\n{error}")
            
        self.led_control_queue.put('telegram:' + str(False))

    #------------------------------------------------------------------------------------------
    # voice

    async def handle_speak(self, v_type, event):
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