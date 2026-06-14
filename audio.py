#python
import numpy as np
import random
import math
import time
import sounddevice as sd
import threading
from pynput import keyboard
import queue


import matplotlib.pyplot as plt

voice_queue = queue.Queue()

sample_buffer_size = 2**10
sample_buffer = np.zeros(sample_buffer_size, dtype=float)
samples_written = 0
samples_used = 2**10

class WaveTable:
    def __init__(self):
        self.length = 2048
        self.wave_table = np.sin(2 * np.pi * np.arange(self.length) / self.length).astype(np.float32)

class GlobalEnvelopeSettings:
    def __init__(self):
        self.attack_ms: float = 100.0
        self.decay_ms: float = 150.0
        self.sustain_level: float = 0.7
        self.release_ms: float = 300.0

    def update(self, attack=None, decay=None, sustain=None, release=None):
        if attack is not None:  self.attack_ms = attack
        if decay is not None:   self.decay_ms = decay
        if sustain is not None: self.sustain_level = sustain
        if release is not None: self.release_ms = release

class VoiceSettings:
    def __init__(self):
        self.detune = 0.0
        self.beginning_phase_angle_randomness = 1
        self.sample_rate = 44100
        self.minimum_samples = 22050
    def get_beginning_phase_angle(self, phase_angle = -1):
        if phase_angle == -1:
            phase_angle = int(self.beginning_phase_angle_randomness * random.random() * 2**32)
        return phase_angle

class Voice:
    def __init__(self, parent: Mixer, freq, voice_settings: VoiceSettings, env_settings: GlobalEnvelopeSettings, wt: WaveTable, phase_angle):
        self.amplitude = 0.5
        self.ms_to_samples_scaler= voice_settings.sample_rate/1000
        self.phase_max = 1<<32
        self.phase = voice_settings.get_beginning_phase_angle(phase_angle)
        self.step_size = (self.phase_max / voice_settings.sample_rate) * freq
        self.samples_played = 0
        self.samples_remaining = voice_settings.minimum_samples
        self.parent = parent
        self.flags = 0

    def increase_time(self):
        if self.samples_remaining < 1 * self.ms_to_samples_scaler:
            self.samples_remaining = 1 * self.ms_to_samples_scaler
    def get_sample(self):
        int_phase = int(self.phase) >> 21
        sample = wt.wave_table[int_phase]
        self.phase += self.step_size
        if self.phase >= self.phase_max:
            self.phase -= self.phase_max
        if self.samples_remaining - self.samples_played < 1:
            if self not in self.parent.flags:
                self.parent.flags.append(self)
                print("appended ")
                print(self)
            return 0
        self.samples_played += 1
        #print("{0}: {1}".format(self, self.samples_played))
        return sample

class Mixer:
    def __init__(self, voice_settings: VoiceSettings, envelope_settings: GlobalEnvelopeSettings,wt: WaveTable):
        self.voice_settings = voice_settings
        self.envelope_settings = envelope_settings
        self.wt = wt
        self.voice_number = 0
        self.scaler = math.sqrt(self.voice_number) if self.voice_number > 1 else 1
        self.voice_dict = {}
        self.samples = []
        self.last_output = 0
        self.flags = []

    def handle_keyboard_input(self):
        id = voice_queue.get()
        if id in self.voice_dict:
            self.voice_dict[id].increase_time()
            print("increased time")
        else:
            self.add_voice(random.random()*1000,id)

    def add_voice(self, freq, name, phase_angle = -1):
        self.voice_dict[name] = Voice(self, freq, voice_settings = self.voice_settings, env_settings = self.envelope_settings, wt = self.wt, phase_angle = phase_angle)
        self.samples.append(0)
        self.voice_number +=1
        self.scaler = math.sqrt(self.voice_number) if self.voice_number > 1 else 1
        print("added:{0} -> {2}, @ {3}Hz scaler set to:{1}".format(name,self.scaler,self,freq))

    def get_sample(self):
        if len(self.voice_dict) > 0:
            for i ,(key,value) in enumerate(self.voice_dict.items()):
                #print(i)
                self.samples[i] = value.get_sample() / self.scaler
            output = sum(self.samples)
            return output
        else:
            return 0
    def handle_flags(self):
        for i in self.flags:
            for key in self.voice_dict.keys():
                if self.voice_dict[key] is i:
                    del self.voice_dict[key]
                    self.flags.remove(i)
                    self.voice_number -=1
                    break
            print("removed a voice\n")

def on_press(key):
    if str(key) == 'key.esc':
        listener.stop()
    try:
        if hasattr(key, 'char') and key.char is not None:
            if key.char.isalpha():
                voice_queue.put(key.char)
        #print("\nkey pressed:{0}".format(key.char))
    except AttributeError:
        pass
listener = keyboard.Listener(on_press)
listener.start()

def output_callback(outdata: numpy.ndarray, frames: int,
                    time: CData, status: CallbackFlags):
    global sample_buffer_size
    global sample_buffer
    global samples_used

    position = samples_used % sample_buffer_size

    #print(frames)
    #print(type(outdata))
    for i in range(len(outdata)):
        #print(i)
        outdata[i][:] = sample_buffer[position]
    #print(outdata)
    samples_used += frames

if __name__ == '__main__':
    wt = WaveTable()
    glob_env_sett = GlobalEnvelopeSettings()
    voice_settings = VoiceSettings()
    mixer = Mixer(voice_settings, glob_env_sett, wt)
    samples = []
#    start = time.perf_counter()
#    for i in range(88100):
#        samples.append(mixer.get_sample())
#    end = time.perf_counter()
#    print(f"took {end - start:.4} seconds")
#    samples = np.array(samples)
    #np.clip(samples, 1, -1, out=samples)

    sd.default.samplerate = 44100
    #sd.play(samples)
    #print(sd.query_devices())
    stream = sd.OutputStream(blocksize=64,callback=output_callback,device=None, channels=2)
    stream.start()
    while stream.active:
        if len(mixer.flags) > 0:
            mixer.handle_flags()
        if not voice_queue.empty():
            mixer.handle_keyboard_input()
        if samples_used - samples_written > 1:
            #print("get_sample")
            sample_buffer[samples_written % 1024] = mixer.get_sample()
            samples_written +=1
    time = np.arange(len(samples))
    x = np.arange(len(wt.wave_table))
   # plt.plot(time, samples)
    #plt.plot(x, wt.wave_table)
   # plt.show()
