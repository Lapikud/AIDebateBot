import requests
import base64
import soundfile as sf
import sounddevice as sd
from colorama import Fore


def send_text_to_tts(ai_reply: str):
    print(Fore.GREEN + "\nSending AI reply to Kokoro TTS...")

    try:
        tts_payload = {
            "text": ai_reply,
            "voice": "af_heart",      # pick your Kokoro voice
            "format": "wav",
            "speed": 1.0
        }

        r = requests.post("http://localhost:8880/tts", json=tts_payload, timeout=60)

        if r.status_code != 200:
            print(Fore.RED + f"Kokoro error: {r.text}")
        else:
            data = r.json()
            audio_base64 = data["audio"]
            audio_bytes = base64.b64decode(audio_base64)

            output_audio = "ai_reply.wav"
            with open(output_audio, "wb") as f:
                f.write(audio_bytes)

            print(Fore.GREEN + f"Kokoro audio saved as: {output_audio}")

            # Play audio using sounddevice
            audio_data, sr = sf.read(output_audio)
            print(Fore.GREEN + "Playing AI response...")
            sd.play(audio_data, sr)
            sd.wait()

    except Exception as e:
        print(Fore.RED + f"Error during Kokoro TTS: {e}")

if __name__ == '__main__':
    text = "Hello, my name is kokoro. What is your name?"
    send_text_to_tts(text)