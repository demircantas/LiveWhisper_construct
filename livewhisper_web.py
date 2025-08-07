#!/usr/bin/env python3
import whisper, os, numpy as np, sounddevice as sd, asyncio, threading, websockets
import pyttsx3, requests, soundfile as sf
import torch

# Whisper device setup
if torch.cuda.is_available():
    print("\033[92mUsing GPU for Whisper model.\033[0m")
else:
    print("\033[93mUsing CPU for Whisper model.\033[0m")

Model = 'base'
English = True
Translate = False
SampleRate = 44100
BlockSize = 30
Threshold = 0.025
Vocals = [70, 3000]
EndBlocks = 40

# WebSocket server
clients = set()

async def websocket_handler(websocket):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)

def start_websocket_server():
    async def server_main():
        async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
            print("✅ WebSocket server started on ws://0.0.0.0:8765")
            await asyncio.Future()  # run forever
    asyncio.run(server_main())

threading.Thread(target=start_websocket_server, daemon=True).start()

class StreamHandler:
    def __init__(self, assist=None):
        if assist is None:
            class fakeAsst(): running, talking, analyze = True, False, None
            self.asst = fakeAsst()
        else:
            self.asst = assist

        self.running = True
        self.padding = 0
        self.prevblock = self.buffer = np.zeros((0,1))
        self.fileready = False
        print("\033[96mLoading Whisper Model..\033[0m", end='', flush=True)
        self.model = whisper.load_model(f'{Model}{".en" if English else ""}')
        print("\033[90m Done.\033[0m")
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 1)

    def callback(self, indata, frames, time, status):
        if not any(indata):
            print('\033[31m.\033[0m', end='', flush=True)
            return

        freq = np.argmax(np.abs(np.fft.rfft(indata[:, 0]))) * SampleRate / frames

        if np.sqrt(np.mean(indata**2)) > Threshold and Vocals[0] <= freq <= Vocals[1] and not self.asst.talking:
            print('.', end='', flush=True)

            async def send_dot():
                for ws in clients:
                    try:
                        await ws.send("[dot]")
                    except:
                        pass
            asyncio.run(send_dot())

            if self.padding < 1: self.buffer = self.prevblock.copy()
            self.buffer = np.concatenate((self.buffer, indata))
            self.padding = EndBlocks
        else:
            self.padding -= 1
            if self.padding > 1:
                self.buffer = np.concatenate((self.buffer, indata))
            elif self.padding < 1 < self.buffer.shape[0] > SampleRate:
                self.fileready = True
                sf.write('dictate.wav', self.buffer, SampleRate, format='WAV', subtype='PCM_16')
                self.buffer = np.zeros((0,1))
            elif self.padding < 1 < self.buffer.shape[0] < SampleRate:
                self.buffer = np.zeros((0,1))
                print("\033[2K\033[0G", end='', flush=True)
            else:
                self.prevblock = indata.copy()

    def speak(self, message):
        self.tts_engine.say(message)
        self.tts_engine.runAndWait()

    def process(self):
        if self.fileready:
            print("\n\033[90mTranscribing..\033[0m")
            result = self.model.transcribe('dictate.wav',
                                           fp16=False,
                                           language='en' if English else '',
                                           task='translate' if Translate else 'transcribe')
            transcribed_text = result['text']
            print(f"\033[1A\033[2K\033[0G{transcribed_text}")

            async def send_to_clients(text):
                for ws in clients:
                    try:
                        await ws.send(text)
                    except:
                        pass

            asyncio.run(send_to_clients(transcribed_text))
            self.fileready = False

    def listen(self):
        print("\033[32mListening.. \033[37m(Ctrl+C to Quit)\033[0m")
        with sd.InputStream(channels=1, callback=self.callback,
                            blocksize=int(SampleRate * BlockSize / 1000),
                            samplerate=SampleRate):
            while self.running and self.asst.running:
                self.process()

def main():
    try:
        handler = StreamHandler()
        handler.listen()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        print("\n\033[93mQuitting..\033[0m")
        if os.path.exists('dictate.wav'):
            os.remove('dictate.wav')

if __name__ == '__main__':
    main()
