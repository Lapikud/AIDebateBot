import sounddevice as sd
import numpy as np
import threading
import time
from faster_whisper import WhisperModel
from colorama import init, Fore

# Initialize colorama
init(autoreset=True)

# ---------------- CONFIG ---------------- #
MODEL_SIZE = "Systran/faster-whisper-medium.en"  # tiny, base, small, medium, large
SAMPLERATE = 16000  # sample rate for recording
CHANNELS = 1  # mono audio
UPDATE_INTERVAL = 5  # seconds between transcript updates
# ---------------------------------------- #

# Logging helper
def log(msg):
    print(Fore.GREEN + "[INFO] " + msg)

log(f"Initializing Faster Whisper model ({MODEL_SIZE})...")
model = WhisperModel(MODEL_SIZE)
log("Model initialized successfully.")

full_transcript = ""
audio_buffer = []
stop_event = threading.Event()

# Ask user before starting
input(Fore.GREEN + "\nPress Enter to start continuous recording...")

# Callback to store audio in buffer
def audio_callback(indata, frames, time_info, status):
    audio_buffer.append(indata.copy())

def transcribe_loop():
    global full_transcript
    last_index = 0
    while not stop_event.is_set():
        if len(audio_buffer) > 0:
            # Concatenate all new audio since last transcription
            audio_data = np.concatenate(audio_buffer[last_index:], axis=0)
            last_index = len(audio_buffer)

            # Transcribe current audio
            segments, _ = model.transcribe(audio_data, beam_size=5)
            chunk_text = " ".join(seg.text for seg in segments)
            full_transcript = chunk_text  # overwrite with current cumulative transcript
            print(Fore.BLUE + f"\n[TRANSCRIPT UPDATE]\n{full_transcript}\n")
        time.sleep(UPDATE_INTERVAL)


# Start transcription thread
transcribe_thread = threading.Thread(target=transcribe_loop, daemon=True)
transcribe_thread.start()

try:
    log("Recording... Press Ctrl+C to stop.")
    with sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, callback=audio_callback):
        while True:
            time.sleep(0.1)
except KeyboardInterrupt:
    log("Stopping recording...")
    stop_event.set()
    transcribe_thread.join()

log("\nFinal transcript:")
print(full_transcript)

