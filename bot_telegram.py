import requests,logging,json, os, random, time,io
import asyncio

import urllib.parse
import uuid

from pydub import AudioSegment

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, Application

import comfyui_generation, text_generation, words

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
LOG_FILE = os.getenv('LOG_FILE_TELEGRAM')
TELEGRAM_KEY = os.getenv('TELEGRAM_KEY')
KOBOLD_CONFIG_FILE = os.getenv('KOBOLD_CONFIG_FILE')
COMFYUI_VOICE = os.getenv('COMFYUI_VOICE')
COMFYUI_PROMPT_ENHANCE = os.getenv('COMFYUI_PROMPT_ENHANCE')
COMFYUI_PROMPT = os.getenv('COMFYUI_PROMPT')
COMFYUI_MUSIC = os.getenv('COMFYUI_MUSIC')
TTS_SERVER_URL = os.getenv('TTS_SERVER_URL')

# Set up logging
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

#-----------------------------------------------------------------------------------------
#telegram bot

class TelegramBot:
    def __init__(self, log_queue):
        self.log_queue = log_queue

    async def get_ip(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        ip_address,register = self.get_external_ip()

        self.log_queue.put(f"Ip Address Registration: {register}\n")
        
        await update.message.reply_text(f"The current external IP address is: {ip_address}")

    def get_external_ip(self):
        try:
            response = requests.get('https://api.ipify.org')
            response_register = requests.get('https://freemyip.com/update?token=63a798452ff2d459a7f031cd&domain=bravolabs.freemyip.com')

            if response.status_code == 200:
                return response.text, response_register.text
            else:
                return "Could not fetch IP"
        except Exception as e:
            return f"Error: {str(e)}"

    async def check_services(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(message)

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
        Convert audio data to MP3 format.
        
        :param audio_data: Binary audio data
        :param input_format: String indicating the input format ('flac', 'ogg', or 'wav')
        :return: MP3 audio data as bytes
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
    

    ####################################################################################
    #Text GENERATION

    MAX_BOT_MESSAGE_LENGTH = 4000   #split message at 4000 char

    async def handle_messages(self,update: Update, context: ContextTypes.DEFAULT_TYPE):

        if update.message.text.startswith('/ask'):
            user_message = ' '.join(context.args)
        else:
            user_message = update.message.text
            
        if update.message.reply_to_message:
            original_message = update.message.reply_to_message.text
            if original_message != None:
                user_message = user_message + " " + original_message
        
        self.log_queue.put(f"User Message: {user_message}\n")

        prompt = self.load_json(KOBOLD_CONFIG_FILE)

        prompt["max_length"] = 320
        prompt["temperature"] = 0.75
        prompt["memory"] = "[You are Roleplaying as Bravolith, A Female Artificial Intelligence, You are running on limited hardware, A Raspberry 5 8GB, use concise messages unless specified and use Emoji when appropriate]\n\n"
        prompt["prompt"] = f"<start_of_turn>user\n{user_message}<end_of_turn>\n<start_of_turn>model\n"

        response_texts = text_generation.process_message(prompt)

        for text_segment in response_texts:
            self.log_queue.put(f"Bravo Response: {text_segment}\n")
            await update.message.reply_text(text=text_segment)

    #********************************************************************************************************
    # IMAGE generation


    async def process_image_prompt(self,i_type, update,context):
        client_id = str(uuid.uuid4())
        user_message = ' '.join(context.args)
        
        if update.message.reply_to_message:
            original_message = update.message.reply_to_message.text
            if original_message != None:
                user_message = user_message + " " + original_message

        prompt = {}
        prompt = self.load_json(COMFYUI_PROMPT)
        if i_type == 'normal':
            prompt["50"]["inputs"]["prompt"] = user_message
            prompt["25"]["inputs"]["noise_seed"] = random.randint(1,4294967294)
        elif i_type == 'random':
            user_message = words.fetch_random_prompt()
            prompt["50"]["inputs"]["prompt"] = user_message
            prompt["25"]["inputs"]["noise_seed"] = random.randint(1,4294967294)

        if i_type == 'enhanced':
            prompt = self.load_json(COMFYUI_PROMPT_ENHANCE)
            prompt["50"]["inputs"]["prompt"] = user_message
            prompt["25"]["inputs"]["noise_seed"] = random.randint(1,4294967294)
            prompt["97"]["inputs"]["seed"] = random.randint(1,4294967294)

        self.log_queue.put(f"Generating {i_type} Image of : {user_message}\n")

        img_to_send,error = comfyui_generation.do_stuff('images',prompt,client_id)
        
        if img_to_send != None:
            await update.message.reply_photo(photo=img_to_send)
        else:
            self.log_queue.put(f"Sorry, there was an error generating the image:\n{error}\n")

            await update.message.reply_text(text=f"Sorry, there was an error generating the image:\n{error}")

    async def handle_normal_image(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.process_image_prompt('normal', update, context)
    async def handle_enhanced_image(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.process_image_prompt('enhanced', update, context)
    async def handle_random_image(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.process_image_prompt('random', update, context)

    #------------------------------------------------------------------------------------------
    # voice

    async def handle_speak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # TTS settings
        female_voice = 'p339'
        male_voice = 'p313'
        SPEAKER_ID = 'p376'  # You can change this or make it configurable
        LANGUAGE_ID = ''  # Leave empty or set as needed

        user_message = ' '.join(context.args)
        args = context.args

        voice = user_message[0].lower()
        if voice == 'male':
            SPEAKER_ID = male_voice
            args.pop(0)
            user_message = ' '.join(args)
        elif voice == 'female':
            SPEAKER_ID = female_voice
            args.pop(0)
            user_message = ' '.join(args)
        else:
            voice = 'default'
            user_message = ' '.join(args)

        if update.message.reply_to_message:
            original_message = update.message.reply_to_message.text
            if original_message != None:
                user_message = user_message + " " + original_message

        if not user_message:
            await update.message.reply_text('Please provide some text to speak.')
            return
        
        self.log_queue.put(f"User Message: {user_message}\n")
        encoded_text = urllib.parse.quote(user_message)
        full_url = f'{TTS_SERVER_URL}/api/tts?text={encoded_text}&speaker_id={SPEAKER_ID}&style_wav=&language_id={LANGUAGE_ID}'

        # Send a request to the Coqui TTS server
        try:
            response = requests.get(full_url)

            #response = requests.post(TTS_SERVER_URL, json={'text': text})
            response.raise_for_status()
            
            # The response should contain the audio file in OGG format
            wav_content = response.content
            mp3_content = self.convert_audio_to_mp3(wav_content,"wav")
            mp3_content.name = 'speak_sample.mp3'
            # Send the MP3 audio file back to the Telegram chat
            self.log_queue.put(f'Playing Voice Sample.\n')
            await update.message.reply_audio(mp3_content, performer="Coqui TTS")

        except requests.RequestException as e:
            self.log_queue.put(f'Error communicating with TTS server: {str(e)}\n')
            await update.message.reply_text(f'Error communicating with TTS server: {str(e)}')

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        client_id = str(uuid.uuid4())
        user_message = ' '.join(context.args)
        args = user_message.split(' ')
        prompt = self.load_json(COMFYUI_VOICE)
        prompt["95"]["inputs"]["speaker"] = 'None'
        voice = args[0].lower()
        if voice == 'old':
            prompt["95"]["inputs"]["speaker"] = "Pigston_Banker_ill.ogg" 
            args.pop(0)
            user_message = ' '.join(args)
        elif voice == 'gabe':
            prompt["95"]["inputs"]["speaker"] = "gabe_voice.ogg"
            args.pop(0)
            user_message = ' '.join(args)

        if update.message.reply_to_message:
            original_message = update.message.reply_to_message.text
            if original_message != None:
                user_message = user_message + " " + original_message

        prompt["95"]["inputs"]["text"] = user_message

        if not user_message:
            await update.message.reply_text('Please provide some text to speak.')
            return

        self.log_queue.put(f"Generate Voice Saying: {user_message}\n")
        
        mp3_name = f"voice_sample.mp3"
        raw_flac,error = comfyui_generation.do_stuff('audio',prompt,client_id)
        if raw_flac != None:
            performer = f"BRAVOLITH"
            try:
                mp3_data = self.convert_audio_to_mp3(raw_flac,"flac")
                mp3_data.name = mp3_name
                self.log_queue.put(f"voice_generated.\n")
                await update.message.reply_audio(audio=mp3_data,performer=performer)
            except Exception as e:
                error=f"Sorry, there was an error converting the audio:\n{str(e)}"
                self.log_queue.put(f"{error}\n")
                await update.message.reply_text(text=f"{error}")
        else:
            c_error = f"ComfyUI error:\n{error}"
            self.log_queue.put(f"{c_error}\n")
            await update.message.reply_text(text=f"{c_error}")

    #**********************************************************************************************************

    async def handle_music(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        client_id = str(uuid.uuid4())
        user_message = ' '.join(context.args)
        args = user_message.split(' ')

        prompt = self.load_json(COMFYUI_MUSIC)
        prompt["11"]["inputs"]["seconds"] = 20
        file_length = args[0]
        
        if file_length.isdigit():
            prompt["11"]["inputs"]["seconds"] = file_length
            args.pop(0)
            user_message = ' '.join(args)

        if update.message.reply_to_message:
            original_message = update.message.reply_to_message.text
            if original_message != None:
                user_message = user_message + " " + original_message

        if not user_message:
            await update.message.reply_text('Please provide some text to convert to music.')
            return
        
        prompt["6"]["inputs"]["text"] = user_message
        prompt["3"]["inputs"]["seed"] = random.randint(1,4294967294)

        self.log_queue.put(f"Generating Music File about: {user_message}\n")
        
        mp3_name = f"music_sample.mp3"
        raw_flac,error = comfyui_generation.do_stuff('audio',prompt,client_id)
        if raw_flac != None:
            user = update.effective_user
            performer = user.first_name if user.first_name else user.username
            performer = f"BRAVOLITH feat. {performer}"
            try:
                mp3_data = self.convert_audio_to_mp3(raw_flac,"flac")
                mp3_data.name = mp3_name
                self.log_queue.put("Music Sample Generated.\n")
                await update.message.reply_audio(audio=mp3_data,performer=performer)

            except Exception as e:
                error=f"Sorry, there was an error converting the audio: {str(e)}"
                self.log_queue.put(f"{error}\n")
                await update.message.reply_text(text=f"{error}")
        else:
            c_error = f"ComfyUI error:\n{error}"
            self.log_queue.put(f"{c_error}\n")
            await update.message.reply_text(text=f"{c_error}")

    #**********************************************************************************************************

    async def run(self):
        application = ApplicationBuilder().token(TELEGRAM_KEY).read_timeout(60).write_timeout(60).build()
        
        application.add_handler(CommandHandler('ask', self.handle_messages))
        application.add_handler(CommandHandler("getip", self.get_ip))
        application.add_handler(CommandHandler("checkservices", self.check_services))
        application.add_handler(CommandHandler("image", self.handle_enhanced_image))
        application.add_handler(CommandHandler("normal", self.handle_normal_image))
        application.add_handler(CommandHandler("random", self.handle_random_image))
        application.add_handler(CommandHandler("speak", self.handle_speak))
        application.add_handler(CommandHandler("voice", self.handle_voice))
        application.add_handler(CommandHandler("music", self.handle_music))

        application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, self.handle_messages))

    # Start the bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling()

        # Keep the main coroutine running
        try:
            await asyncio.Future()  # This will run forever until cancelled
        finally:
            await application.stop()

def start_bot(log_queue):
    bot = TelegramBot(log_queue)
    asyncio.run(bot.run())
