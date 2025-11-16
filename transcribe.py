import sounddevice as sd
import soundfile as sf
import queue
import threading
import time
from faster_whisper import WhisperModel
import os
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# ---------------- CONFIG ---------------- #
MODEL_SIZE = "Systran/faster-whisper-medium.en"  # tiny, base, small, medium, large
CHUNK_DURATION = 10  # seconds per audio chunk
SAMPLERATE = 16000  # sample rate for recording
CHANNELS = 1  # mono audio
OUTPUT_DIR = "audio_chunks"  # where temporary chunks will be stored
MAX_CHUNKS = 3
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
full_transcript = ""
log("Audio queue ready.")

# Ask user before starting
input(Fore.GREEN + "\nPress Enter to start recording audio chunks...")

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
    global full_transcript
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
        full_transcript += " " + chunk_text
        end = time.time()
        log(f"Chunk transcription done in {end - start:.1f}s")
        print(Fore.BLUE + f"Current full transcript:\n{full_transcript}\n")
        # Optionally delete chunk to save disk
        os.remove(filename)


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
    print(full_transcript)
