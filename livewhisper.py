#!/usr/bin/env python3
import whisper, os
import numpy as np
import sounddevice as sd
# import requests # for sending to api
# import curses
import pyttsx3
import requests
from scipy.io.wavfile import write

# This is my attempt to make psuedo-live transcription of speech using Whisper.
# Since my system can't use pyaudio, I'm using sounddevice instead.
# This terminal implementation can run standalone or imported for assistant.py
# by Nik Stromberg - nikorasu85@gmail.com - MIT 2022 - copilot

# dtt

# Model = 'medium.en'     # Whisper model size (tiny, base, small, medium, large)
Model = 'tiny.en'     # Whisper model size (tiny, base, small, medium, large)
English = True      # Use English-only model?
Translate = False   # Translate non-English to English?
SampleRate = 44100  # Stream device recording frequency
BlockSize = 30      # Block size in milliseconds
Threshold = 0.05     # Minimum volume threshold to activate listening
Vocals = [50, 1000] # Frequency range to detect sounds that could be speech
EndBlocks = 40      # Number of blocks to wait before sending to Whisper



class StreamHandler:
    def __init__(self, assist=None):
        if assist == None:  # If not being run by my assistant, just run as terminal transcriber.
            class fakeAsst(): running, talking, analyze = True, False, None
            self.asst = fakeAsst()  # anyone know a better way to do this?
        else: self.asst = assist
        self.running = True
        self.padding = 0
        self.prevblock = self.buffer = np.zeros((0,1))
        self.fileready = False
        print("\033[96mLoading Whisper Model..\033[0m", end='', flush=True)
        self.model = whisper.load_model(f'{Model}')
        # self.model = whisper.load_model(f'{Model}{".en" if English else ""}')
        print("\033[90m Done.\033[0m")

        # Initialize the TTS engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)  # Set speech rate
        self.tts_engine.setProperty('volume', 1)  # Set volume level


    def callback(self, indata, frames, time, status):
        #if status: print(status) # for debugging, prints stream errors.
        if not any(indata):
            print('\033[31m.\033[0m', end='', flush=True) # if no input, prints red dots
            #print("\033[31mNo input or device is muted.\033[0m") #old way
            #self.running = False  # used to terminate if no input
            return
        # A few alternative methods exist for detecting speech.. #indata.max() > Threshold
        #zero_crossing_rate = np.sum(np.abs(np.diff(np.sign(indata)))) / (2 * indata.shape[0]) # threshold 20
        freq = np.argmax(np.abs(np.fft.rfft(indata[:, 0]))) * SampleRate / frames
        if np.sqrt(np.mean(indata**2)) > Threshold and Vocals[0] <= freq <= Vocals[1] and not self.asst.talking:
            print('.', end='', flush=True)
            if self.padding < 1: self.buffer = self.prevblock.copy()
            self.buffer = np.concatenate((self.buffer, indata))
            self.padding = EndBlocks
        else:
            self.padding -= 1
            if self.padding > 1:
                self.buffer = np.concatenate((self.buffer, indata))
            elif self.padding < 1 < self.buffer.shape[0] > SampleRate: # if enough silence has passed, write to file.
                self.fileready = True
                write('dictate.wav', SampleRate, self.buffer) # I'd rather send data to Whisper directly..
                self.buffer = np.zeros((0,1))
            elif self.padding < 1 < self.buffer.shape[0] < SampleRate: # if recording not long enough, reset buffer.
                self.buffer = np.zeros((0,1))
                print("\033[2K\033[0G", end='', flush=True)
            else:
                self.prevblock = indata.copy() #np.concatenate((self.prevblock[-int(SampleRate/10):], indata)) # SLOW

    def speak(self, message):
        """Speaks the given message using TTS."""
        self.tts_engine.say(message)
        self.tts_engine.runAndWait()

    # def send_command_to_windows(command):
    def send_command_to_windows(self, command):
        """Sends a JSON request to the Windows server to execute the command."""
        WINDOWS_IP = "172.21.224.1"  # Replace with your Windows IP
        url = f"http://{WINDOWS_IP}:5000/execute"
        # url = "http://localhost:5000/execute"  # Ensure this matches the Windows server

        payload = {"command": command}
        try:
            response = requests.post(url, json=payload, timeout=2)
            print(f"\033[94mServer Response: {response.text}\033[0m")
        except requests.exceptions.RequestException as e:
            print(f"\033[91mError sending command: {e}\033[0m")

    def process(self):
        if self.fileready:
            print("\n\033[90mTranscribing..\033[0m")
            result = self.model.transcribe('dictate.wav', fp16=False, language='en' if English else '', task='translate' if Translate else 'transcribe')
            transcribed_text = result['text']
            print(f"\033[1A\033[2K\033[0G{transcribed_text}")

            lowercase_text = transcribed_text.lower()
            if "hello" in lowercase_text:
                response = "Hi there! How can I help you today?"
                print(f"\033[94mResponse: {response}\033[0m")
                self.speak(response)
            elif "how are you" in lowercase_text:
                response = "I'm just a program, but I'm functioning perfectly. Thanks for asking!"
                print(f"\033[94mResponse: {response}\033[0m")
                self.speak(response)
            elif "stop listening" in lowercase_text:
                response = "Stopping the transcription. Goodbye!"
                print(f"\033[94mResponse: {response}\033[0m")
                self.speak(response)
                self.running = False
            elif "urban typologies" in lowercase_text:
                hcResponse = "The Urban Metabolism Group (UMG) categorizes data into five distinct typologies, each focusing on different aspects of urban environments. The typologies are: Urban Morphology Typology, Metabolic Typology, Urban Resource Use, Vegetation and Land Characteristics Typology, Climate Risks Typology, Urbanization Impacts Typology."
                print(f"\33[94mResponse: {hcResponse}]")
                self.speak(hcResponse)

            # commands for creating geometry
            elif "create a cube" in lowercase_text:
                print("\033[94mSending command: create_cube\033[0m")
                self.send_command_to_windows("create_cube")
            elif "create a cylinder" in lowercase_text:
                self.send_command_to_windows("create_cylinder")
            elif "create a sphere" in lowercase_text:
                self.send_command_to_windows("create_sphere")
            elif "create a cone" in lowercase_text:
                self.send_command_to_windows("create_cone")

            # if 'construct' in lowercase_text:
            #     construct_index = lowercase_text.index('construct')
            #     sentence = transcribed_text[construct_index + len('construct'):].strip()
            #     print(f"\033[94mCONSTRUCT({sentence})\033[0m")
            #     self.send_to_api(sentence)

            # if 'make' in lowercase_text:
            #     construct_index = lowercase_text.index('make')
            #     sentence = transcribed_text[construct_index + len('make'):].strip()
            #     print(f"\033[94mMAKE({sentence})\033[0m")
            #     self.send_to_api(sentence)

            if self.asst.analyze is not None:
                self.asst.analyze(result['text'])

            self.fileready = False

    def listen(self):
        print("\033[32mListening.. \033[37m(Ctrl+C to Quit)\033[0m")
        with sd.InputStream(channels=1, callback=self.callback, blocksize=int(SampleRate * BlockSize / 1000), samplerate=SampleRate):
            while self.running and self.asst.running: self.process()

    # send api request to construct sentence
    def send_to_api(self, sentence):
        payload = {'sentence': sentence}
        response = requests.post('http://localhost:5000/construct', data=payload)

def main():
    try:
        handler = StreamHandler()
        handler.listen()
    except (KeyboardInterrupt, SystemExit): pass
    finally:
        print("\n\033[93mQuitting..\033[0m")
        if os.path.exists('dictate.wav'): os.remove('dictate.wav')

if __name__ == '__main__':
    main()  # by Nik
