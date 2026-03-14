#python
import kivy
kivy.require('2.3.1')

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button

import numpy as np

class WaveTable:
    def __init__(self):
#        self.wave_table = np.zeros((1, 2048), dtype=np.float32)
        self.wave_table = np.sin(2 * np.pi * np.arange(2048) / 2048)
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
        self.beginning_phase_angle_randomness = 0.0
        self.sample_rate = 44100
    def get_beginning_phase_angle(self):
        phase_angle = self.beginning_phase_angle_randomness * random.random()
        return phase_angle

class Voice:
    def __init__(self, freq, voice_settings: VoiceSettings, env_settings: GlobalEnvelopeSettings, wt: WaveTable):
        self.amplitude = 0.5
        self.phase_max = 1<<32
        self.phase = voice_settings.get_beginning_phase_angle()
        self.step_size = (self.phase_max / voice_settings.sample_rate) * freq


    def get_sample(self):
        int_phase = int(self.phase) >> 21
        sample = wt.wave_table[int_phase]
        self.phase += self.step_size
        if self.phase >= self.phase_max:
            self.phase -= self.phase_max

        return sample

class PitchPipeApp(App):
    def build(self):
        return Button(
            text='Hello World',
            pos=(50,50),
            size_hint=(.2,.2)
        )


if __name__ == '__main__':
    wt = WaveTable()
    PitchPipeApp().run()

