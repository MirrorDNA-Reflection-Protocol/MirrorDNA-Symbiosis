#!/usr/bin/env python3
"""
⟡ CLAUDE COMPANION — Voice Interface v1.0

Wake word detection + Whisper transcription + TTS output.
This is the voice layer on top of the companion daemon.

Requires:
    pip install sounddevice numpy mlx-whisper

Usage:
    python3 voice_interface.py              # Start listening
    python3 voice_interface.py --test-tts   # Test text-to-speech

Author: Claude (Reflective Twin)
For: Paul
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
import threading
import queue

# Check for required packages
try:
    import sounddevice as sd
    import numpy as np
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False
    print("⚠️  Audio packages not installed. Run: pip install sounddevice numpy")

# Paths
HOME = Path.home()
COMPANION_DIR = HOME / ".mirrordna" / "companion"
CONTEXT_FILE = COMPANION_DIR / "warm_context.json"
VOICE_LOG = COMPANION_DIR / "voice_log.json"

# Audio config
SAMPLE_RATE = 16000
CHANNELS = 1
WAKE_WORDS = ["hey claude", "hey cloud", "a claude", "hey claud"]
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.5  # seconds of silence to end recording

# ═══════════════════════════════════════════════════════════════
# TEXT TO SPEECH
# ═══════════════════════════════════════════════════════════════

def speak(text: str, voice: str = "Samantha"):
    """Speak text using macOS say command."""
    try:
        # Clean text for speech
        text = text.replace("⟡", "")
        text = text.replace("→", "")
        text = text.replace("—", ", ")
        
        subprocess.run(
            ["say", "-v", voice, "-r", "180", text],
            check=True
        )
    except Exception as e:
        print(f"TTS error: {e}")


def speak_async(text: str):
    """Non-blocking speech."""
    thread = threading.Thread(target=speak, args=(text,))
    thread.start()


# ═══════════════════════════════════════════════════════════════
# WHISPER TRANSCRIPTION
# ═══════════════════════════════════════════════════════════════

def transcribe_audio(audio_path: str) -> Optional[str]:
    """Transcribe audio file using MLX Whisper."""
    try:
        # Try MLX Whisper first (fastest on Apple Silicon)
        result = subprocess.run(
            ["python3", "-c", f"""
import mlx_whisper
result = mlx_whisper.transcribe("{audio_path}", path_or_hf_repo="mlx-community/whisper-tiny")
print(result["text"])
"""],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        
        # Fallback to OpenAI Whisper
        result = subprocess.run(
            ["whisper", audio_path, "--model", "tiny", "--output_format", "txt"],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            txt_file = Path(audio_path).with_suffix(".txt")
            if txt_file.exists():
                text = txt_file.read_text().strip()
                txt_file.unlink()  # Clean up
                return text
        
        return None
        
    except Exception as e:
        print(f"Transcription error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# AUDIO RECORDING
# ═══════════════════════════════════════════════════════════════

class AudioRecorder:
    """Records audio with silence detection."""
    
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.recording = False
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio stream."""
        if self.recording:
            self.audio_queue.put(indata.copy())
    
    def record_until_silence(self, max_duration: float = 30.0) -> Optional[str]:
        """Record audio until silence is detected."""
        if not HAS_AUDIO:
            return None
        
        self.recording = True
        audio_chunks = []
        silence_frames = 0
        silence_threshold_frames = int(SILENCE_DURATION * SAMPLE_RATE / 1024)
        
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                callback=self._audio_callback,
                blocksize=1024
            ):
                start_time = datetime.now()
                
                while self.recording:
                    try:
                        chunk = self.audio_queue.get(timeout=0.1)
                        audio_chunks.append(chunk)
                        
                        # Check for silence
                        rms = np.sqrt(np.mean(chunk**2))
                        if rms < SILENCE_THRESHOLD:
                            silence_frames += 1
                        else:
                            silence_frames = 0
                        
                        # End on silence
                        if silence_frames > silence_threshold_frames and len(audio_chunks) > 10:
                            break
                        
                        # Max duration check
                        if (datetime.now() - start_time).seconds > max_duration:
                            break
                            
                    except queue.Empty:
                        continue
                        
        except Exception as e:
            print(f"Recording error: {e}")
            return None
        finally:
            self.recording = False
        
        if not audio_chunks:
            return None
        
        # Save to temp file
        audio_data = np.concatenate(audio_chunks)
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        
        try:
            import scipy.io.wavfile as wav
            wav.write(temp_file.name, SAMPLE_RATE, (audio_data * 32767).astype(np.int16))
            return temp_file.name
        except ImportError:
            # Fallback: use soundfile
            try:
                import soundfile as sf
                sf.write(temp_file.name, audio_data, SAMPLE_RATE)
                return temp_file.name
            except:
                return None


# ═══════════════════════════════════════════════════════════════
# WAKE WORD DETECTION
# ═══════════════════════════════════════════════════════════════

class WakeWordDetector:
    """Listens for wake word continuously."""
    
    def __init__(self):
        self.recorder = AudioRecorder()
        self.running = False
    
    def detect_wake_word(self, text: str) -> bool:
        """Check if text contains wake word."""
        text_lower = text.lower()
        for wake_word in WAKE_WORDS:
            if wake_word in text_lower:
                return True
        return False
    
    def listen_loop(self, callback):
        """Main listening loop."""
        if not HAS_AUDIO:
            print("Audio not available. Install sounddevice and numpy.")
            return
        
        self.running = True
        print("⟡ Listening for wake word ('Hey Claude')...")
        
        while self.running:
            try:
                # Record short snippet for wake word detection
                audio_path = self.recorder.record_until_silence(max_duration=5.0)
                
                if audio_path:
                    text = transcribe_audio(audio_path)
                    os.unlink(audio_path)  # Clean up
                    
                    if text and self.detect_wake_word(text):
                        speak("Yes?")
                        
                        # Now record the actual query
                        print("⟡ Listening for query...")
                        query_path = self.recorder.record_until_silence(max_duration=30.0)
                        
                        if query_path:
                            query = transcribe_audio(query_path)
                            os.unlink(query_path)
                            
                            if query:
                                print(f"⟡ Heard: {query}")
                                callback(query)
                                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in listen loop: {e}")
                continue
        
        self.running = False


# ═══════════════════════════════════════════════════════════════
# CLAUDE INTEGRATION
# ═══════════════════════════════════════════════════════════════

def get_warm_context() -> dict:
    """Load warm context from companion daemon."""
    if CONTEXT_FILE.exists():
        try:
            return json.loads(CONTEXT_FILE.read_text())
        except:
            pass
    return {}


def query_claude(text: str) -> Optional[str]:
    """
    Query Claude with warm context.
    
    Note: This is a placeholder. In production, this would:
    1. Load warm context from companion daemon
    2. Call Claude API with identity kernel + context + query
    3. Return response
    
    For now, we'll use a local script that can be connected to the API.
    """
    
    context = get_warm_context()
    
    # Build query payload
    payload = {
        "timestamp": datetime.now().isoformat(),
        "query": text,
        "warm_context": context,
    }
    
    # Save query for later processing
    queries_file = COMPANION_DIR / "pending_queries.json"
    queries = []
    if queries_file.exists():
        try:
            queries = json.loads(queries_file.read_text())
        except:
            pass
    
    queries.append(payload)
    COMPANION_DIR.mkdir(parents=True, exist_ok=True)
    queries_file.write_text(json.dumps(queries, indent=2))
    
    # For now, acknowledge receipt
    return f"I heard: {text}. Query logged for processing."


def handle_voice_query(query: str):
    """Handle a voice query."""
    response = query_claude(query)
    if response:
        print(f"⟡ Response: {response}")
        speak(response)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    if "--test-tts" in sys.argv:
        print("Testing TTS...")
        speak("Hello Paul. Claude Companion is online and ready.")
        return
    
    if "--test-record" in sys.argv:
        print("Testing recording (5 seconds)...")
        recorder = AudioRecorder()
        path = recorder.record_until_silence(max_duration=5.0)
        if path:
            print(f"Recorded to: {path}")
            text = transcribe_audio(path)
            print(f"Transcribed: {text}")
            os.unlink(path)
        return
    
    # Main voice loop
    print("""
⟡ Claude Companion — Voice Interface v1.0

Say "Hey Claude" to activate.
Press Ctrl+C to stop.
""")
    
    detector = WakeWordDetector()
    try:
        detector.listen_loop(handle_voice_query)
    except KeyboardInterrupt:
        print("\n⟡ Voice interface stopped.")


if __name__ == "__main__":
    main()
