# ui/speech/piper_tts.py
import logging
import os
import tempfile
import asyncio
from datetime import datetime
import subprocess
import platform
import threading
import queue
import wave
import pyaudio
import time
import numpy as np

logger = logging.getLogger("PiperTTS")

class PiperTTS:
    """Client for Piper text-to-speech synthesis"""
    
    def __init__(self, voice="en_US-amy-medium", model_dir=None):
        self.voice = voice
        self.model_dir = model_dir or os.path.join(os.path.dirname(__file__), "piper_models")
        self.initialized = False
        self.speaking = False
        self.piper_path = None
        
        # Audio playback settings
        self.pyaudio_instance = None
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.is_playing = False
        
        # Initialize the TTS system
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize the Piper TTS system"""
        try:
            # Check if Piper executable exists
            self.piper_path = self._find_piper_executable()
            
            if not self.piper_path:
                logger.warning("Piper executable not found. Using mock TTS.")
                self.initialized = False
                return
            
            # Check if model directory exists
            os.makedirs(self.model_dir, exist_ok=True)
            
            # Check if voice model exists
            voice_file = os.path.join(self.model_dir, f"{self.voice}.onnx")
            if not os.path.exists(voice_file):
                logger.warning(f"Voice model not found: {voice_file}")
                logger.warning("Using mock TTS. Download the model to enable real TTS.")
                self.initialized = False
                return
            
            logger.info(f"Piper TTS initialized with voice '{self.voice}'")
            self.initialized = True
            
            # Start playback thread
            self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.playback_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to initialize Piper TTS: {str(e)}")
            self.initialized = False
    
    def _find_piper_executable(self):
        """Find the Piper executable"""
        # Check common locations based on platform
        if platform.system() == "Windows":
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "piper.exe"),
                os.path.join(os.path.dirname(__file__), "bin", "piper.exe"),
                "piper.exe"
            ]
        else:
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "piper"),
                os.path.join(os.path.dirname(__file__), "bin", "piper"),
                "/usr/local/bin/piper",
                "/usr/bin/piper",
                "piper"
            ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                logger.info(f"Found Piper executable at: {path}")
                return path
        
        return None
    
    def _get_pyaudio(self):
        """Get or create PyAudio instance"""
        if self.pyaudio_instance is None:
            self.pyaudio_instance = pyaudio.PyAudio()
        return self.pyaudio_instance
    
    def _playback_worker(self):
        """Worker function for audio playback"""
        while True:
            try:
                audio_file = self.audio_queue.get()
                if audio_file is None:
                    break
                
                self.is_playing = True
                self._play_audio_file(audio_file)
                self.is_playing = False
                
                # Remove temporary file
                try:
                    os.remove(audio_file)
                except:
                    pass
                
                self.audio_queue.task_done()
            except Exception as e:
                logger.error(f"Error in playback worker: {str(e)}")
                self.is_playing = False
    
    def _play_audio_file(self, audio_file):
        """Play an audio file using PyAudio"""
        try:
            # Open the wave file
            wf = wave.open(audio_file, 'rb')
            
            # Create PyAudio instance
            p = self._get_pyaudio()
            
            # Open stream
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            
            # Read data in chunks
            chunk_size = 1024
            data = wf.readframes(chunk_size)
            
            # Play audio
            while data and self.is_playing:
                stream.write(data)
                data = wf.readframes(chunk_size)
            
            # Close everything
            stream.stop_stream()
            stream.close()
            wf.close()
            
        except Exception as e:
            logger.error(f"Error playing audio: {str(e)}")
    
    def speak(self, text):
        """Convert text to speech and play it"""
        if not text:
            return False
            
        if self.speaking:
            logger.warning("Already speaking, request queued")
            return False
            
        try:
            self.speaking = True
            
            # Generate audio file
            audio_file = self._generate_audio_file_sync(text)
            
            if audio_file:
                # Add to playback queue
                self.audio_queue.put(audio_file)
                logger.info(f"Added speech to playback queue: {text[:50]}...")
                result = True
            else:
                logger.error("Failed to generate audio file")
                result = False
            
            self.speaking = False
            return result
            
        except Exception as e:
            self.speaking = False
            logger.error(f"Failed to speak: {str(e)}")
            return False
    
    async def speak_async(self, text):
        """Async version of the speak method"""
        if not text:
            return {"error": "Empty text"}
            
        try:
            # Create a coroutine to run the synchronous speak method in a thread
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.speak, text)
            
            return {"success": result}
        except Exception as e:
            logger.error(f"Failed to speak asynchronously: {str(e)}")
            return {"error": str(e)}
    
    def _generate_audio_file_sync(self, text):
        """Generate audio file synchronously"""
        if not text:
            return None
            
        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        output_file = os.path.join(temp_dir, f"friday_speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        
        if self.initialized and self.piper_path:
            try:
                # Voice model path
                voice_file = os.path.join(self.model_dir, f"{self.voice}.onnx")
                
                # Run Piper to generate audio
                cmd = [
                    self.piper_path,
                    "--model", voice_file,
                    "--output_file", output_file
                ]
                
                logger.info(f"Running Piper command: {' '.join(cmd)}")
                
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Send text to Piper
                stdout, stderr = process.communicate(input=text)
                
                if process.returncode != 0:
                    logger.error(f"Piper error: {stderr}")
                    return None
                
                logger.info(f"Generated audio file: {output_file}")
                return output_file
                
            except Exception as e:
                logger.error(f"Error generating audio: {str(e)}")
                return None
        else:
            # Mock TTS for testing
            logger.warning("Using mock TTS (Piper not initialized)")
            
            # Create an empty WAV file
            self._create_mock_wav_file(output_file, duration=len(text) / 15)
            
            return output_file
    
    def _create_mock_wav_file(self, filename, duration=1.0, freq=440.0):
        """Create a mock WAV file with a tone for testing"""
        try:
            # Audio parameters
            sample_rate = 16000
            amplitude = 0.5
            
            # Generate audio data
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = amplitude * np.sin(2 * np.pi * freq * t)
            audio = tone * (2**15 - 1) / np.max(np.abs(tone))
            audio = audio.astype(np.int16)
            
            # Write to WAV file
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio.tobytes())
            
            logger.info(f"Created mock WAV file: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error creating mock WAV file: {str(e)}")
            return False
    
    async def generate_audio_file(self, text, output_file=None):
        """Generate an audio file from text without playing it"""
        if not text:
            return {"error": "Empty text"}
            
        try:
            # Create a temporary file if output_file is not specified
            if not output_file:
                temp_dir = tempfile.gettempdir()
                output_file = os.path.join(temp_dir, f"friday_speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
            
            # Run the synchronous file generation in a thread
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, self._generate_audio_file_sync, text)
            
            if file_path:
                # If output_file is different from the generated file, copy it
                if file_path != output_file:
                    import shutil
                    shutil.copy2(file_path, output_file)
                    os.remove(file_path)
                
                return {
                    "success": True,
                    "file_path": output_file,
                    "duration": len(text) / 15  # Rough estimate: 15 characters per second
                }
            else:
                return {"error": "Failed to generate audio file"}
                
        except Exception as e:
            logger.error(f"Failed to generate audio file: {str(e)}")
            return {"error": str(e)}

# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tts = PiperTTS()
    
    def test_tts():
        tts.speak("Hello, I am Friday, your personal AI assistant. How can I help you today?")
        time.sleep(5)  # Wait for playback to complete
    
    test_tts()