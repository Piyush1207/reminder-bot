import sounddevice as sd
import numpy as np
import time
from collections import deque
import threading

class ClapDetector:
    def __init__(self, on_clap, sensitivity=0.05, timeout=1.0):
        self.on_clap = on_clap
        self.sensitivity = sensitivity
        self.timeout = timeout
        self.clap_times = deque()
        self.listening = False
        self.stream = None
        self.lock = threading.Lock()
        self.last_trigger_time = 0
        self.trigger_cooldown = 3.0  # Don't trigger more than once every 3 seconds
        
    def audio_callback(self, indata, frames, time_info, status):
        if status:
            return
        
        try:
            # Calculate volume (RMS)
            volume = np.sqrt(np.mean(indata**2))
            
            # Detect clap (sudden loud sound)
            if volume > self.sensitivity:
                current_time = time.time()
                
                # Check cooldown to prevent rapid re-triggering
                if current_time - self.last_trigger_time < self.trigger_cooldown:
                    return
                
                with self.lock:
                    self.clap_times.append(current_time)
                    
                    # Remove old claps
                    while self.clap_times and current_time - self.clap_times[0] > self.timeout:
                        self.clap_times.popleft()
                    
                    # Check for two claps within timeout period
                    if len(self.clap_times) >= 2:
                        time_diff = self.clap_times[-1] - self.clap_times[-2]
                        if time_diff < self.timeout:
                            self.last_trigger_time = current_time
                            self.clap_times.clear()
                            # Use threading to avoid callback blocking
                            threading.Thread(target=self.on_clap, daemon=True).start()
        except Exception as e:
            print(f"Clap detection error: {e}")
    
    def start(self):
        """Start listening for claps"""
        self.listening = True
        try:
            self.stream = sd.InputStream(
                callback=self.audio_callback,
                channels=1,
                samplerate=44100,
                blocksize=2048,
                latency='low'
            )
            self.stream.start()
            print("🎤 Clap detector started. Listening for two claps...")
        except Exception as e:
            print(f"Failed to start microphone: {e}")
    
    def stop(self):
        """Stop listening"""
        self.listening = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass