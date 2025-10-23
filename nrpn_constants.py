#!/usr/bin/env python3
"""
Digitakt NRPN (Non-Registered Parameter Number) Constants

NRPNs provide access to more parameters than standard MIDI CCs.
Each NRPN requires sending 4 CC messages to set a value.

Structure:
  MSB (CC 99) = Category
  LSB (CC 98) = Parameter
  Data Entry MSB (CC 6) = Value (0-127)
  Data Entry LSB (CC 38) = Fine value (usually 0)
"""

# NRPN MSB Categories
class NRPN_MSB:
    TRACK_TRIG_SOURCE_FILTER_AMP = 1
    FX = 2
    TRIG_NOTE_VEL_LEN = 3

# Track Parameters (MSB 1)
class TrackParams:
    MSB = 1
    LEVEL = 100
    GLOBAL_MUTE = 101
    SOLO = 102
    PATTERN_MUTE = 104

# Trig Parameters (MSB 3 for note/velocity/length)
class TrigParams:
    MSB = 3
    NOTE = 0
    VELOCITY = 1
    LENGTH = 2

# Source Parameters (MSB 1, LSB 0-7)
class SourceParams:
    MSB = 1
    TUNE = 0
    FINE_TUNE = 1
    SAMPLE_SLOT = 2
    SAMPLE_START = 3
    SAMPLE_LENGTH = 4
    SAMPLE_LOOP = 5
    SAMPLE_VOLUME = 6
    SAMPLE_LEVEL = 7

# Filter Parameters (MSB 1, LSB 16-23)
class FilterParams:
    MSB = 1
    ATTACK = 16
    DECAY = 17
    SUSTAIN = 18
    RELEASE = 19
    FREQUENCY = 20
    RESONANCE = 21
    TYPE = 22
    ENVELOPE_DEPTH = 23

# Amp Parameters (MSB 1, LSB 24-31)
class AmpParams:
    MSB = 1
    ATTACK = 24
    HOLD = 25
    DECAY = 26
    OVERDRIVE = 27
    DELAY_SEND = 28
    REVERB_SEND = 29
    PAN = 30
    VOLUME = 31

# LFO Parameters (MSB 1, LSB 32-39)
class LFOParams:
    MSB = 1
    SPEED = 32
    MULTIPLIER = 33
    FADE = 34
    DESTINATION = 35
    WAVEFORM = 36
    PHASE = 37
    TRIG_MODE = 38
    DEPTH = 39

# Delay FX Parameters (MSB 2, LSB 0-7)
class DelayParams:
    MSB = 2
    TIME = 0
    PINGPONG = 1
    STEREO_WIDTH = 2
    FEEDBACK = 3
    HPF = 4
    LPF = 5
    REVERB_SEND = 6
    MIX = 7

# Reverb FX Parameters (MSB 2, LSB 8-15)
class ReverbParams:
    MSB = 2
    PREDELAY = 8
    DECAY = 9
    SHELVING_FREQ = 10
    SHELVING_GAIN = 11
    HPF = 12
    LPF = 13
    MIX = 14

# Helper dictionary for parameter names
NRPN_PARAMS = {
    (1, 100): "Track Level",
    (1, 101): "Global Mute",
    (1, 102): "Solo",
    (1, 104): "Pattern Mute",

    (3, 0): "Trig Note",
    (3, 1): "Trig Velocity",
    (3, 2): "Trig Length",

    (1, 0): "Source Tune",
    (1, 1): "Source Fine Tune",
    (1, 2): "Sample Slot",
    (1, 3): "Sample Start",
    (1, 4): "Sample Length",
    (1, 5): "Sample Loop",
    (1, 6): "Sample Volume",
    (1, 7): "Sample Level",

    (1, 16): "Filter Attack",
    (1, 17): "Filter Decay",
    (1, 18): "Filter Sustain",
    (1, 19): "Filter Release",
    (1, 20): "Filter Frequency",
    (1, 21): "Filter Resonance",
    (1, 22): "Filter Type",
    (1, 23): "Filter Envelope Depth",

    (1, 24): "Amp Attack",
    (1, 25): "Amp Hold",
    (1, 26): "Amp Decay",
    (1, 27): "Amp Overdrive",
    (1, 28): "Delay Send",
    (1, 29): "Reverb Send",
    (1, 30): "Pan",
    (1, 31): "Volume",

    (1, 32): "LFO Speed",
    (1, 33): "LFO Multiplier",
    (1, 34): "LFO Fade",
    (1, 35): "LFO Destination",
    (1, 36): "LFO Waveform",
    (1, 37): "LFO Phase",
    (1, 38): "LFO Trig Mode",
    (1, 39): "LFO Depth",

    (2, 0): "Delay Time",
    (2, 1): "Delay Pingpong",
    (2, 2): "Delay Stereo Width",
    (2, 3): "Delay Feedback",
    (2, 4): "Delay HPF",
    (2, 5): "Delay LPF",
    (2, 6): "Delay Reverb Send",
    (2, 7): "Delay Mix",

    (2, 8): "Reverb Predelay",
    (2, 9): "Reverb Decay",
    (2, 10): "Reverb Shelving Freq",
    (2, 11): "Reverb Shelving Gain",
    (2, 12): "Reverb HPF",
    (2, 13): "Reverb LPF",
    (2, 14): "Reverb Mix",
}

def get_param_name(msb: int, lsb: int) -> str:
    """Get the human-readable name for an NRPN parameter"""
    return NRPN_PARAMS.get((msb, lsb), f"Unknown NRPN {msb}:{lsb}")
