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
import words_flux

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
        self.prompt_generate = words_flux.FluxPromptGenerator()

        # Define preset resolutions
        self.preset_resolutions = {
            "portrait": (512, 768),
            "landscape": (768, 512),
            "square": (512, 512),
            "hd": (1024, 768),
            "wide":(1536,512)
        }

        self.response_styles = {
            'enthusiastic': {
                'general': [
                    "Making this! 👍",
                    "Processing my request... ⚡",
                    "On it! 🎨",
                    "Starting generation... 🖼️",
                    "Working on it! 🎯",
                    "Challenge accepted! 🚀",
                    "Let's make some art! 🎨",
                    "Here we go! ✨",
                    "Creating my vision... 🌟",
                    "Magic in progress... ✨",
                    "Beginning the creative process... 🎭",
                    "Starting the image journey... 🗺️",
                    "Firing up the generators... ⚡",
                    "Initializing creative mode... 🎨",
                    "Ready to create! 🎯"
                ],
                'image': [
                    "Let's make some art! 🎨",
                    "Creating your vision... 🌟",
                    "Starting the image journey... 🗺️",
                ],
                'music': [
                    "Let's lay down some tracks! 🎵",
                    "Time to make musical magic! 🎹",
                    "Getting the studio warmed up! 🎼",
                    "Ready to compose something special! 🎸",
                    "About to drop the beat... 🎧"
                ]
            },
            'sarcastic': {
                'general': [
                    "Well, that is... certainly a choice... 🤨",
                    "Interesting use of technology.... 👀",
                    "Do your parents know you're into that? 😅",
                    "Oh, we're really doing this, huh? 🫣",
                    "This should be... something... ✨",
                    "Preparing to make... whatever this is... 🎨",
                    "Your genius is... fascinating... 🧐",
                    "Starting your... unique... request... 🤔",
                    "This will definitely be one for the archives... 📚",
                    "Well, someone had to try it, I guess... 🤷",
                    "Your creativity is... remarkable... 🎭",
                    "Processing your... distinctive... vision... 👁️",
                    "This should be... memorable... 🫢",
                    "Living dangerously today, aren't we? 😏",
                    "Boldly going where taste hasn't gone before... 🚀" 
               ],
                'image': [
                    "Preparing to make... whatever this is... 🎨",
                    "Your artistic vision is... unique... 👁️",
                    "This should be... interesting... 🎭"
                ],
                'music': [
                    "Ah yes, another future Grammy nominee... 🏆",
                    "Making 'music' in air quotes... 🫢",
                    "Your neighbors are gonna love this... 🏡",
                    "Beethoven is rolling in his grave... but let's do it! ⚰️",
                    "Auto-tune can fix anything, right? 🎤"
                ]
            },
            'pretentious': {
                'general': [
                    "*Adjusts monocle* Contemplating your request... 🧐",
                    "How... avant-garde of you... ✨",
                ],
                'image': [
                    "Analyzing the post-modern implications of your composition... 🎭",
                    "Calculating the golden ratio for optimal aesthetics... 📐",
                    "Channeling the spirits of the great masters... 👻"
                ],
                'music': [
                    "*Adjusts monocle* Preparing to generate in A♭ minor... 🧐",
                    "Contemplating the post-modern implications of your request... 🎭",
                    "Ensuring proper resonance with the cosmic frequency... ✨",
                    "Calculating the golden ratio of beats per minute... 📐",
                    "Channeling the avant-garde spirits... 👻"
                ]
            }
        }

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
            ('/speak', self.handle_speak_handler),
            ('/voice', self.handle_voice),
            ('/music', self.handle_music_handler),
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
    """
    async def acknowledge_command(self, event):
        command = event.message.text.split()[0] if event.message and event.message.text else "Unknown command"
        await event.reply(f"Received command {command}. Processing...")
    """
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
                Button.inline("Normal Generation", data=f"type_Normal_{user_id}"),
                Button.inline("Enhanced Generation", data=f"type_Enhanced_{user_id}")
            ],
            [
                Button.inline("Random Generation", data=f"type_Random_{user_id}")
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

    async def handle_speak_handler(self, event):
        user_id = event.sender_id
        message = event.message.text.split(None, 1)
        
        # Create inline keyboard for generation type selection
        keyboard = [
            [
                Button.inline("Male Voice 1", data=f"voice_maleA_{user_id}"),
                Button.inline("Male voice 2", data=f"voice_maleB_{user_id}")
            ],
            [
                Button.inline("Woman Voice 1", data=f"voice_womanA_{user_id}"),
                Button.inline("Woman Voice 2", data=f"voice_womanB_{user_id}")

            ]
        ]
        
        # Store the original prompt in user state
        prompt = message[1] if len(message) > 1 else ''
        self.user_states[user_id] = {
            'prompt': prompt,
            'original_message': event
        }
        
        await event.reply(
            "Please select voice type:",
            buttons=keyboard
        )

    async def handle_voice_handler(self, event):
        await self.handle_voice(event)

    async def handle_music_handler(self, event):
        user_id = event.sender_id
        message = event.message.text.split(None, 1)
        
        # Create inline keyboard for generation type selection
        keyboard = [
            [
                Button.inline("3 Sec", data=f"music_3_{user_id}"),
                Button.inline("5 Sec", data=f"music_5_{user_id}"),
                Button.inline("10 Sec", data=f"music_10_{user_id}")
            ],
            [
                Button.inline("15 Sec", data=f"music_15_{user_id}"),
                Button.inline("20 Sec", data=f"music_20_{user_id}"),
                Button.inline("30 Sec", data=f"music_30_{user_id}")
            ],
            [
                Button.inline("60 Sec", data=f"music_60_{user_id}"),
                Button.inline("90 Sec", data=f"music_90_{user_id}"),
                Button.inline("120 Sec", data=f"music_120_{user_id}")
            ]
        ]
        
        # Store the original prompt in user state
        prompt = message[1] if len(message) > 1 else ''
        self.user_states[user_id] = {
            'prompt': prompt,
            'original_message': event
        }
        
        await event.reply(
            "How long do you want that sample to be?",
            buttons=keyboard
        )


        #await self.handle_music(event)

    async def handle_ask_handler(self, event):
        await self.handle_messages(event)

    async def handle_webcam_on_handler(self, event):
        await self.handle_webcam_on(event)

    async def handle_webcam_off_handler(self, event):
        await self.handle_webcam_off(event)

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
            generation_type = self.user_states[user_id]['generation_type']
            if generation_type == 'Random':
                u_prompt = self.user_states[user_id]['prompt']
                r_prompt = self.prompt_generate.generate_prompt()
                prompt = f"{u_prompt} {r_prompt}"
            else:
                prompt = self.user_states[user_id]['prompt']
            
            # Clean up user state
            del self.user_states[user_id]

            await event.answer()
            if generation_type == 'Random':
                response = await self.choose_response_style(
                    context_type='general',
                    user_input=prompt,
                    user_id=user_id
                )
            
                # Use response in your existing handler logic
                await original_event.reply(response)
            else:   
                response = await self.choose_response_style(
                    context_type='image',
                    user_input=prompt,
                    user_id=user_id
                )
            
                # Use response in your existing handler logic
                await original_event.reply(response)
                await self.process_image_prompt(generation_type, original_event, width, height, prompt)

        elif callback_type == 'voice':
            # Handle generation type selection
            voice_type = event.data.decode().split('_')[1]
            prompt = self.user_states[user_id]['prompt']
            original_event = self.user_states[user_id]['original_message']

            del self.user_states[user_id]
            await event.answer()
            await self.handle_speak(original_event,voice_type, prompt)
 
        elif callback_type == 'music':
            file_length = event.data.decode().split('_')[1]
            
            # Get resolution from presets
            original_event = self.user_states[user_id]['original_message']
            prompt = self.user_states[user_id]['prompt']
            
            # Clean up user state
            del self.user_states[user_id]
            
            await event.answer() 
            response = await self.choose_response_style(
                context_type='music',
                user_input=prompt,
                user_id=user_id
            )
        
            # Use response in your existing handler logic
            await original_event.reply(response)
            await self.handle_music(original_event, file_length , prompt)

    def is_valid_resolution(self, width, height):
        return (256 <= width <= 1536 and 
                256 <= height <= 1536)
        
    #-----------------------------------------------------------------------------------------
    #telegram bot
    async def choose_response_style(self, context_type, user_input, user_id=None, user_history=None):
        """
        Choose appropriate response style based on context and input.
        
        Args:
            context_type (str): 'image', 'music', or 'general'
            user_input (str): The user's input text
            user_id (int, optional): User's Telegram ID for tracking history
            user_history (list, optional): Previous interactions
        """
        # Keywords that might trigger different styles
        pretentious_triggers = {'aesthetic', 'artistic', 'sophisticated', 'classical', 'symphony', 'masterpiece'}
        sarcastic_triggers = {'lol', 'meme', 'funny', 'silly', 'weird', 'crazy'}
        
        # Convert input to lowercase for matching
        input_lower = user_input.lower()
        
        # Check input length - longer, more detailed requests might warrant pretentious response
        if len(user_input.split()) > 20:
            style = 'pretentious'
        # Check for trigger words
        elif any(word in input_lower for word in pretentious_triggers):
            style = 'pretentious'
        elif any(word in input_lower for word in sarcastic_triggers):
            style = 'sarcastic'
        # Time-based personality (optional)
        elif user_history and len(user_history) > 3:
            if all("!" in msg for msg in user_history[-3:]):
                style = 'enthusiastic'  # Match user's energy
            else:
                style = 'sarcastic'  # Default to sarcastic for regular users
        else:
            # Default to enthusiastic for new users or simple requests
            style = 'enthusiastic'
        
        # Get appropriate response list
        responses = self.response_styles[style][context_type]
        
        # Return random response from chosen style and context
        return random.choice(responses)
    
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

    async def process_image_prompt(self, i_type, event, width=512, height=512, user_message='', its=1):
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
        if i_type == 'Normal':
            prompt = self.load_json(COMFYUI_PROMPT)
        elif i_type == 'Random':
            prompt = self.load_json(COMFYUI_PROMPT)
        elif i_type == 'Enhanced':
            prompt = self.load_json(COMFYUI_PROMPT_ENHANCE)
            
        # Update the prompt with resolution
        prompt["102"]["inputs"]["text"] = user_message
        prompt["100"]["inputs"]["seed"] = random.randint(1, 4294967294)
        prompt["80"]["inputs"]["width"] = width
        prompt["80"]["inputs"]["height"] = height
        #prompt["80"]["inputs"]["batch_size"] = 2
        
        self.log_queue.put(f"Generating {i_type} Image of: {user_message} at {width}x{height}\n")
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

    async def handle_speak(self, event,v_type, user_message=''):
        self.led_control_queue.put('telegram:' + str(True))

        # TTS settings
        womanA = 'p339'
        womanB = 'p335'
        maleA = 'p313'
        maleB = 'p340'
        SPEAKER_ID = 'p376'  # You can change this or make it configurable
        LANGUAGE_ID = ''  # Leave empty or set as needed

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

        if v_type == 'maleA':
            SPEAKER_ID = 'p313'
        elif v_type == 'maleB':
            SPEAKER_ID = 'p340'
        if v_type == 'womanA':
            SPEAKER_ID = 'p339'
        elif v_type == 'womanB':
            SPEAKER_ID = 'p335'

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

    async def handle_music(self, event, file_length=20, user_message=''):
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
        
        # Load prompt template
        prompt = self.load_json(COMFYUI_MUSIC)
        prompt["11"]["inputs"]["seconds"] = file_length  # Default value

        # Update prompt with user message and random seed
        prompt["6"]["inputs"]["text"] = user_message
        prompt["3"]["inputs"]["seed"] = random.randint(1, 4294967294)

        # Log and start generation
        self.log_queue.put(f"Generating Music File about: {user_message}\n")
        self.led_control_queue.put('monolith:' + str(True))
        
        audio_files, error = comfyui_generation.do_stuff('audio', prompt, client_id)
        self.led_control_queue.put('monolith:' + str(False))

        if audio_files is not None:
            try:
                # Get user info for performer attribute
                user = await event.get_sender()
                performer = user.first_name if user.first_name else user.username
                performer = f"BRAVOLITH feat. {performer}"
                
                # Process each audio file
                for i, audio_data in enumerate(audio_files, 1):
                    try:
                        # Convert FLAC to MP3
                        mp3_data = self.convert_audio_to_mp3(audio_data, "flac")
                        if mp3_data is None or mp3_data.getvalue() == b'':
                            raise ValueError("Converted MP3 data is empty")
                        
                        # Prepare audio file for sending
                        audio_file = io.BytesIO(mp3_data.getvalue())
                        audio_file.name = f'music_sample_{i}.mp3'
                        
                        # Add a small delay between multiple files
                        if i > 1:
                            await asyncio.sleep(0.5)
                        
                        # Send the audio file
                        await event.reply(
                            file=audio_file,
                            attributes=[
                                types.DocumentAttributeAudio(
                                    duration=0,  # You can set the duration if known
                                    title=f"Generated Music Sample {i}",
                                    performer=performer
                                )
                            ],
                            
                        )
                        
                        # Log success
                        self.log_queue.put(f"Successfully sent audio file {i}\n")
                        
                    except Exception as e:
                        error_msg = f"Error processing audio file {i}: {str(e)}"
                        self.log_queue.put(f"{error_msg}\n")
                        await event.reply(error_msg)
                        
            except Exception as e:
                error_msg = f"Error getting user info: {str(e)}"
                self.log_queue.put(f"{error_msg}\n")
                await event.reply(error_msg)
        else:
            error_msg = f"ComfyUI error:\n{error}"
            self.log_queue.put(f"{error_msg}\n")
            await event.reply(error_msg)

        self.led_control_queue.put('telegram:' + str(False))

def start_bot(log_queue, led_control_queue):
    bot = TelegramBot(log_queue, led_control_queue)
    asyncio.run(bot.start())

# If this script is run directly, start the bot
if __name__ == '__main__':
    start_bot(None, None)