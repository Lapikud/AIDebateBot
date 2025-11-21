import sounddevice as sd
import soundfile as sf
import queue
import threading
import time
from faster_whisper import WhisperModel
import os
from colorama import init, Fore, Style
from controller import send_text_to_ai
from texttospeech import send_text_to_tts

# Initialize colorama
init(autoreset=True)

# ---------------- CONFIG ---------------- #
MODEL_SIZE = "Systran/faster-whisper-medium.en"  # tiny, base, small, medium, large
CHUNK_DURATION = 10  # seconds per audio chunk
SAMPLERATE = 16000  # sample rate for recording
CHANNELS = 1  # mono audio
OUTPUT_DIR = "audio_chunks"  # where temporary chunks will be stored
MAX_CHUNKS = 2
# MAX_CHUNKS = 18
HUMANITY_SPEECH_COUNT = 1
AI_SPEECH_COUNT = 1


# ---------------------------------------- #

# Logging helper
def log(msg):
    print(Fore.GREEN + "[INFO] " + msg)


log("Initializing audio chunk directory...")
os.makedirs(OUTPUT_DIR, exist_ok=True)

log(f"Initializing Faster Whisper model ({MODEL_SIZE})...")
model = WhisperModel(MODEL_SIZE)
log("Model initialized successfully.")

log("Initializing audio queue...")
audio_queue = queue.Queue()
current_full_transcript = ""
log("Audio queue ready.")

log("Initializing speech files...")
# open("humanity_speeches", "a").close()
# open("ai_speeches", "a").close()
open("speeches", "a").close()
open("prompt", "a").close()
log("Speech files made.")


def record_chunk(filename, duration=CHUNK_DURATION):
    log(f"Starting recording chunk: {filename} ({duration}s)")
    recording = sd.rec(int(duration * SAMPLERATE), samplerate=SAMPLERATE, channels=CHANNELS, dtype='int16')

    # Live countdown
    for remaining in range(duration, 0, -1):
        print(Fore.GREEN + f"\rTime left: {remaining:2d}s", end="")
        time.sleep(1)
    sd.wait()
    print(Fore.GREEN + "\rTime left:  0s")  # overwrite last countdown

    sf.write(filename, recording, SAMPLERATE)
    log(f"Saved chunk: {filename}")
    audio_queue.put(filename)


def transcribe_worker():
    global current_full_transcript
    log("Transcription worker started.")
    while True:
        filename = audio_queue.get()
        if filename is None:
            log("Transcription worker stopping.")
            break
        log(f"Transcribing: {filename} ...")
        start = time.time()
        segments, _ = model.transcribe(filename)
        chunk_text = " ".join([seg.text for seg in segments])
        current_full_transcript += " " + chunk_text
        end = time.time()
        log(f"Chunk transcription done in {end - start:.1f}s")
        print(Fore.BLUE + f"Current full transcript:\n{current_full_transcript}\n")
        # Optionally delete chunk to save disk
        os.remove(filename)


def write_to_file(file_name: str, text: str, mode: str):
    with open(file_name, mode, encoding="utf8") as f:
        f.write("\n")
        f.write(text)
        f.write("\n")


while True:
    # Ask user before starting
    input(Fore.YELLOW + "\nPress Enter to start recording audio...")
    start_time = time.time()

    # Start transcription thread
    t = threading.Thread(target=transcribe_worker, daemon=True)
    t.start()

    try:
        chunk_index = 1
        while chunk_index <= MAX_CHUNKS:
            chunk_file = os.path.join(OUTPUT_DIR, f"chunk_{chunk_index}.wav")
            record_chunk(chunk_file, CHUNK_DURATION)
            chunk_index += 1
    except KeyboardInterrupt:
        print(Fore.RED + "\nStopping recording...")
    finally:
        # Signal transcription thread to stop
        audio_queue.put(None)
        t.join()
        log("\n***************************************:")
        print(current_full_transcript)
        end_time = time.time()
        print("Full recording + transcription took:")
        print(end_time - start_time)
        write_to_file("speeches", f"Humanity speech number {HUMANITY_SPEECH_COUNT}:\n{current_full_transcript}", "a")
        HUMANITY_SPEECH_COUNT += 1

        # API sending part
        print(Fore.YELLOW + "\nPress ENTER to send transcript to GPT...")
        input()
        start_time = time.time()
        # Load prompt from file
        try:
            with open("prompt", "r", encoding="utf8") as f:
                system_prompt = f.read().strip()
        except FileNotFoundError:
            print(Fore.RED + "prompt not found! Create the file first.")
            exit()
        try:
            with open("speeches", "r", encoding="utf8") as f:
                all_speeches = f.read().strip()
        except FileNotFoundError:
            print(Fore.RED + "speeches not found! Create the file first.")
            exit()

        # Send to AI
        ai_reply = send_text_to_ai(system_prompt, all_speeches)
        end_time = time.time()
        print("Full ai response sending and retrieval took:")
        print(end_time - start_time)

        write_to_file("speeches", f"AI speech number {AI_SPEECH_COUNT}:\n{ai_reply}", "a")
        AI_SPEECH_COUNT += 1
        print(Fore.CYAN + "\n========== AI RESPONSE ==========\n")
        print(ai_reply)
        print("\n=================================\n")

        # Send to text-to-speech
        # print(Fore.YELLOW + "\nPress ENTER so AI could give their speech...")
        # input()
        # send_text_to_tts(ai_reply)

        user_input = input(Fore.YELLOW + "\nPress ENTER for next round"
                                         "\nq to quit")
        if user_input.lower() == "q":
            print("DEBATE OVER")
            break
