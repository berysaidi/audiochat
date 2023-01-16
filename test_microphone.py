#!/usr/bin/env python3

import json
import os
import sys
import asyncio
import websockets
import logging
import sounddevice as sd
import argparse
import openai
import sys
from gtts import gTTS
import os

print(os.getenv("CHATGPT_API_KEY"))

openai.api_key = os.getenv("CHATGPT_API_KEY")


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

async def run_test():

    with sd.RawInputStream(samplerate=args.samplerate, blocksize = 4000, device=args.device, dtype='int16',
                           channels=1, callback=callback) as device:

        async with websockets.connect(args.uri) as websocket:
            await websocket.send('{ "config" : { "sample_rate" : %d } }' % (device.samplerate))

            while True:
                data = await audio_queue.get()
                await websocket.send(data)
                output_txt = await websocket.recv()
                #print(output_txt)
                output = json.loads(output_txt)
                if "text" in output:
                    if output["text"] is not "":
                        prompt = output["text"]
                        print(prompt)
                        response = openai.Completion.create(engine="text-davinci-002", prompt=prompt, max_tokens=2048, n = 1, stop = None, temperature = 0.5)
                        for i in range(len(response["choices"])):
                            text = response["choices"][i]["text"]
                            lines = text.split("\n")
                            for line in lines:
                                print(line)

                            #print(text)
                            tts = gTTS(text=text, lang='en')
                            # Save the audio file
                            tts.save("response.mp3")
                            os.system("gst-play-1.0 response.mp3")



                #elif "partial" in output:
                #    print(output["partial"])



            await websocket.send('{"eof" : 1}')
            result = await websocket.recv()
            #print(result)

async def main():

    global args
    global loop
    global audio_queue

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-l', '--list-devices', action='store_true',
                        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(description="ASR Server",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     parents=[parser])
    parser.add_argument('-u', '--uri', type=str, metavar='URL',
                        help='Server URL', default='ws://localhost:2700')
    parser.add_argument('-d', '--device', type=int_or_str,
                        help='input device (numeric ID or substring)')
    parser.add_argument('-r', '--samplerate', type=int, help='sampling rate', default=16000)
    args = parser.parse_args(remaining)
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()

    logging.basicConfig(level=logging.INFO)
    await run_test()

if __name__ == '__main__':
    asyncio.run(main())
