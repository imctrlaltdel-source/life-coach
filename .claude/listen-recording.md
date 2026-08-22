# Listen to Latest Recording

**Phone-only (Termux/Android).** This skill reads from the phone's local voice-recorder folder — there's no equivalent on other machines, so it only applies when this project is run from the Android device it was built on.

**Path:** `/storage/emulated/0/Recordings/Voice Recorder/`

**Method:**
1. Find latest .m4a file in that folder (usually most recent by timestamp)
2. Convert to WAV: `ffmpeg -i [file.m4a] -ac 1 -ar 16000 [output.wav]`
3. Transcribe using speech_recognition + Google STT (requires FLAC: `apt-get install flac`)
4. Parse transcription, extract key points
5. Log to today's session log

**Quick command:**
```bash
ls -lart /storage/emulated/0/Recordings/Voice\ Recorder/*.m4a | tail -1 | awk '{print $NF}'
```

**Python snippet (ready to use):**
```python
import speech_recognition as sr
import subprocess
import os
from datetime import datetime

# Find latest m4a
folder = "/storage/emulated/0/Recordings/Voice Recorder"
files = sorted([f for f in os.listdir(folder) if f.endswith('.m4a')], 
               key=lambda x: os.path.getmtime(os.path.join(folder, x)))
latest_m4a = os.path.join(folder, files[-1])

# Convert to wav
wav_file = "/storage/emulated/0/Documents/claude/latest_recording.wav"
os.system(f'ffmpeg -i "{latest_m4a}" -ac 1 -ar 16000 "{wav_file}" 2>/dev/null')

# Transcribe
r = sr.Recognizer()
with sr.AudioFile(wav_file) as source:
    audio = r.record(source)
    
try:
    text = r.recognize_google(audio)
    print(f"✅ Transcription:\n{text}")
except Exception as e:
    print(f"Error: {e}")
```

**Dependencies:**
- ffmpeg (already installed)
- flac: `apt-get install flac`
- speech_recognition: `pip install SpeechRecognition`
