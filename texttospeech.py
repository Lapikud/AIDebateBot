from openai import OpenAI
import base64
import requests
import soundfile as sf
import sounddevice as sd
from playsound import playsound  # fallback for mp3 playback
from pathlib import Path
from typing import Optional

def send_text_to_kokoro_tts(text: str,
                            host: str = "http://localhost:8880",
                            endpoints: Optional[list] = None,
                            prefer_format: str = "wav"):
    """
    Send text to Kokoro-style TTS and play/save the resulting audio.
    - Tries endpoints in order until one returns 200.
    - Handles raw audio bytes or JSON with base64 audio (key guesses).
    - Saves file with extension based on returned Content-Type or prefer_format.
    """
    if endpoints is None:
        # try the endpoint you used earlier plus a couple common variants
        endpoints = [
            "/v1/audio/speech",   # your earlier attempt
            "/v1/generate",       # some forks use this
            "/v1/tts",            # other variants
        ]

    payload = {
        "text": text,
        "voice": "af_heart",
        "format": prefer_format,
        "speed": 1.0
    }

    last_error = None
    for ep in endpoints:
        url = host.rstrip("/") + ep
        try:
            # prefer streaming for potentially large audio
            r = requests.post(url, json=payload, timeout=60, stream=True)
        except Exception as e:
            last_error = f"Request to {url} failed: {e}"
            continue

        if r.status_code != 200:
            last_error = f"{url} -> HTTP {r.status_code}: {r.text[:200]}"
            continue

        # We have a 200 — inspect headers & body
        ctype = r.headers.get("content-type", "").lower()
        # If the server returned JSON (explicit content-type), parse JSON
        audio_bytes = None
        filename = None

        if "application/json" in ctype or "json" in ctype:
            try:
                data = r.json()
            except Exception as e:
                last_error = f"{url} returned JSON content-type but json() failed: {e}"
                continue

            # common fields that might contain base64 audio
            for key in ("audio", "audio_base64", "data", "base64"):
                if key in data:
                    maybe = data[key]
                    if isinstance(maybe, str):
                        try:
                            audio_bytes = base64.b64decode(maybe)
                        except Exception:
                            # maybe it's already raw bytes in a different format
                            pass
                        break

            # some APIs return {"download_url": "..."} etc. If you get that, you must fetch it.
            if audio_bytes is None:
                # if the JSON contains a download link
                for key in ("download_url", "url", "link"):
                    if key in data and isinstance(data[key], str):
                        dl = data[key]
                        try:
                            rr = requests.get(dl, timeout=30)
                            if rr.status_code == 200:
                                audio_bytes = rr.content
                                break
                        except Exception:
                            pass

        else:
            # Not JSON content-type. Likely raw audio bytes.
            # We'll stream-write to avoid loading huge blobs into memory.
            # Decide extension from content-type
            if "wav" in ctype or "wave" in ctype:
                ext = ".wav"
            elif "mpeg" in ctype or "mp3" in ctype:
                ext = ".mp3"
            elif "ogg" in ctype:
                ext = ".ogg"
            else:
                # fallback to prefer_format
                ext = f".{prefer_format}" if not prefer_format.startswith(".") else prefer_format

            filename = f"ai_reply{ext}"
            # Stream to disk
            try:
                with open(filename, "wb") as out_f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            out_f.write(chunk)
                audio_bytes = None  # we saved to filename directly
            except Exception as e:
                last_error = f"Failed to write streamed audio from {url}: {e}"
                continue

        # If we ended up with audio_bytes (in-memory), save to file
        if audio_bytes is not None:
            # try to infer extension from prefer_format or header
            ext = ".wav" if prefer_format == "wav" else f".{prefer_format}"
            filename = f"ai_reply{ext}"
            try:
                Path(filename).write_bytes(audio_bytes)
            except Exception as e:
                last_error = f"Failed to write audio bytes to {filename}: {e}"
                continue

        # At this point `filename` should exist on disk
        if not filename or not Path(filename).exists():
            last_error = f"No audio file produced by {url}"
            continue

        print(f"Saved audio to: {filename}")

        # Play it: prefer soundfile+sounddevice for WAV; fallback to playsound for mp3
        try:
            if filename.lower().endswith(".wav"):
                audio_data, sr = sf.read(filename)
                sd.play(audio_data, sr)
                sd.wait()
            elif filename.lower().endswith(".mp3"):
                # soundfile doesn't natively support mp3; playsound is simpler here
                playsound(filename)
            else:
                # try soundfile, if it fails fallback to playsound
                try:
                    audio_data, sr = sf.read(filename)
                    sd.play(audio_data, sr)
                    sd.wait()
                except Exception:
                    playsound(filename)
        except Exception as e:
            print(f"Saved audio but playback failed: {e}")

        # success — return filename
        return filename

    # if loop finishes, nothing succeeded
    raise RuntimeError(f"All endpoints failed. Last error: {last_error}")



def send_text_to_openai_tts(text: str, ai_speech_count: int):
    client = OpenAI()

    audio = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input="Hello! This should play immediately."
    )

    filename = f"speech{ai_speech_count}.mp3"

    with open(filename, "wb") as f:
        f.write(audio)

    return filename


if __name__ == '__main__':
    # while True:
    #     tts_payload = {
    #         "text": "hello",
    #         "voice": "af_heart",  # pick your Kokoro voice
    #         "format": "wav",
    #         "speed": 1.0
    #     }
    #     r = requests.get("http://localhost:8880/health", timeout=60)
    #
    #     code = r.status_code
    #     if code != 200:
    #         print(Fore.RED + f"Kokoro error, status code: {code}: {r.text}")
    #         time.sleep(5)
    #         continue
    #     print(Fore.GREEN + f"Kokoro success: {r.text}")
    #     break
    text = "Hello, my name is kokoro. What is your name?"
    send_text_to_kokoro_tts(text)
