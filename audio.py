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
    def get_beginning_phase_angle(self, phase_angle = -1):
        if phase_angle == -1:
            phase_angle = int(self.beginning_phase_angle_randomness * random.random() * 2**32)
        return phase_angle

class Voice:
    def __init__(self, freq, voice_settings: VoiceSettings, env_settings: GlobalEnvelopeSettings, wt: WaveTable, phase_angle):
        self.amplitude = 0.5
        self.phase_max = 1<<32
        self.phase = voice_settings.get_beginning_phase_angle(phase_angle)
        self.step_size = (self.phase_max / voice_settings.sample_rate) * freq
        self.time_remaining = 400

    def increase_time(self):
        if self.time_remaining < 200:
            self.time_remaining = 200
    def get_sample(self):
        int_phase = int(self.phase) >> 21
        sample = wt.wave_table[int_phase]
        self.phase += self.step_size
        if self.phase >= self.phase_max:
            self.phase -= self.phase_max

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

    def handle_keyboard_input(self):
        id = voice_queue.get()
        if id in self.voice_dict:
            self.voice_dict[id].increase_time()
        else:
                self.add_voice(random.random()*1000,id)

    def add_voice(self, freq, name, phase_angle = -1):
        self.voice_dict[name] = Voice(freq, voice_settings = self.voice_settings, env_settings = self.envelope_settings, wt = self.wt, phase_angle = phase_angle)
        self.samples.append(0)
        self.voice_number +=1
        self.scaler = math.sqrt(self.voice_number) if self.voice_number > 1 else 1
        print("added:{0}, scaler set to:{1}".format(name,self.scaler))

    def get_sample(self):
        for i in range(len(self.voice_dict)):
            self.samples[i] = self.voice_dict[i].get_sample() * self.scaler
        output = sum(self.samples) / self.scaler
        return output

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

if __name__ == '__main__':
    wt = WaveTable()
    glob_env_sett = GlobalEnvelopeSettings()
    voice_settings = VoiceSettings()
    mixer = Mixer(voice_settings, glob_env_sett, wt)
    samples = []
    #mixer.add_voice(69,voice_settings,glob_env_sett,wt, 0)
    #mixer.add_voice(440,voice_settings,glob_env_sett,wt, 20000000)
    #mixer.add_voice(130.813,voice_settings,glob_env_sett,wt)
    #mixer.add_voice(150,voice_settings,glob_env_sett,wt)
    #mixer.add_voice(14,voice_settings,glob_env_sett,wt)
    start = time.perf_counter()
    for i in range(88100):
        samples.append(mixer.get_sample())
    end = time.perf_counter()
    print(f"took {end - start:.4} seconds")
    samples = np.array(samples)
    #np.clip(samples, 1, -1, out=samples)

    sd.default.samplerate = 44100
    sd.play(samples)

    while True:
        if not voice_queue.empty():
            mixer.handle_keyboard_input()
    time = np.arange(len(samples))
    x = np.arange(len(wt.wave_table))
   # plt.plot(time, samples)
    #plt.plot(x, wt.wave_table)
   # plt.show()
