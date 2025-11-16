from faster_whisper import WhisperModel
import time

# Choose model size: tiny, base, small, medium, large
model = WhisperModel("small")  # small is faster, medium is more accurate

audio_file = "sample_audio.wav"  # replace with your own recording

start = time.time()
segments, info = model.transcribe(audio_file)
end = time.time()

print(f"Transcription finished in {end - start:.2f} seconds")
for segment in segments:
    print(segment.start, segment.end, segment.text)

