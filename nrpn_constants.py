#!/usr/bin/env python3
"""
Digitakt II MIDI CC and NRPN Constants (OS 1.03)

Source: Digitakt II User Manual OS 1.03, Appendix B

NRPNs provide access to more parameters than standard MIDI CCs.
Each NRPN requires sending 4 CC messages to set a value.

Structure:
  MSB (CC 99) = Category
  LSB (CC 98) = Parameter
  Data Entry MSB (CC 6) = Value (0-127)
  Data Entry LSB (CC 38) = Fine value (usually 0)
"""

# ============================================================================
# MIDI CC CONSTANTS
# ============================================================================

class TrackCC:
    """Track-level CC parameters"""
    MUTE = 94
    LEVEL = 95

class SourceCC:
    """Source/sample CC parameters"""
    TUNE = 16
    PLAY_MODE = 17
    SAMPLE_SLOT = 19
    SAMPLE_START = 20
    SAMPLE_LENGTH = 21
    SAMPLE_LOOP = 22
    SAMPLE_LEVEL = 23
    SAMPLE_BANK = 24

class FilterCC:
    """Filter envelope CC parameters (separate from AMP)"""
    ATTACK = 70
    DECAY = 71
    SUSTAIN = 72
    RELEASE = 73
    FREQUENCY = 74
    ENV_DEPTH = 77

class AmpCC:
    """AMP envelope CC parameters (separate from Filter)"""
    ATTACK = 79
    HOLD = 80    # Unique to AMP envelope
    DECAY = 81
    SUSTAIN = 82
    RELEASE = 83
    VOLUME = 89
    PAN = 90

class FXCC:
    """Effects send CC parameters"""
    CHORUS_SEND = 12
    DELAY_SEND = 84
    REVERB_SEND = 85
    OVERDRIVE = 57

# ============================================================================
# NRPN CONSTANTS
# ============================================================================

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

# Source Parameters (MSB 1, LSB 0-9)
# Based on Digitakt II MIDI Implementation (Oneshot machine)
class SourceParams:
    MSB = 1
    TUNE = 0
    FINE_TUNE = 1
    # Sample Slot = NRPN LSB 8 (full range 0-16383 across banks)
    SAMPLE_START = 4    # Also available as CC 20
    SAMPLE_LENGTH = 5   # Also available as CC 21
    SAMPLE_LOOP = 6     # Also available as CC 22
    SAMPLE_LEVEL = 7    # Also available as CC 23
    SAMPLE_SLOT = 8     # Also available as CC 19
    SAMPLE_BANK = 9     # Also available as CC 24

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

# Amp Parameters (MSB 1, LSB 30-39)
class AmpParams:
    MSB = 1
    ATTACK = 30
    HOLD = 31
    DECAY = 32
    SUSTAIN = 33
    RELEASE = 34
    CHORUS_SEND = 35
    DELAY_SEND = 36
    REVERB_SEND = 37
    PAN = 38
    VOLUME = 39
    MODE = 40
    ENV_RESET = 41

# LFO 1 Parameters (MSB 1, LSB 42-49)
class LFO1Params:
    MSB = 1
    SPEED = 42
    MULTIPLIER = 43
    FADE = 44
    DESTINATION = 45
    WAVEFORM = 46
    START_PHASE = 47
    TRIG_MODE = 48
    DEPTH = 49

# LFO 2 Parameters (MSB 1, LSB 50-57)
class LFO2Params:
    MSB = 1
    SPEED = 50
    MULTIPLIER = 51
    FADE = 52
    DESTINATION = 53
    WAVEFORM = 54
    START_PHASE = 55
    TRIG_MODE = 56
    DEPTH = 57

# LFO 3 Parameters (MSB 1, LSB 58-65 + 70-72)
class LFO3Params:
    MSB = 1
    SPEED = 58
    MULTIPLIER = 59
    FADE = 60
    DESTINATION = 61
    WAVEFORM = 62
    START_PHASE = 70
    TRIG_MODE = 71
    DEPTH = 72

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
    MIX = 15

# Chorus FX Parameters (MSB 2, LSB 41-47)
class ChorusParams:
    MSB = 2
    DEPTH = 41
    SPEED = 42
    HPF = 43
    WIDTH = 44
    DELAY_SEND = 45
    REVERB_SEND = 46
    MIX = 47

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

    (1, 30): "Amp Attack",
    (1, 31): "Amp Hold",
    (1, 32): "Amp Decay",
    (1, 33): "Amp Sustain",
    (1, 34): "Amp Release",
    (1, 35): "Chorus Send",
    (1, 36): "Delay Send",
    (1, 37): "Reverb Send",
    (1, 38): "Pan",
    (1, 39): "Volume",
    (1, 40): "Amp Mode",
    (1, 41): "Amp Env Reset",

    (1, 42): "LFO1 Speed",
    (1, 43): "LFO1 Multiplier",
    (1, 44): "LFO1 Fade",
    (1, 45): "LFO1 Destination",
    (1, 46): "LFO1 Waveform",
    (1, 47): "LFO1 Start Phase",
    (1, 48): "LFO1 Trig Mode",
    (1, 49): "LFO1 Depth",

    (1, 50): "LFO2 Speed",
    (1, 51): "LFO2 Multiplier",
    (1, 52): "LFO2 Fade",
    (1, 53): "LFO2 Destination",
    (1, 54): "LFO2 Waveform",
    (1, 55): "LFO2 Start Phase",
    (1, 56): "LFO2 Trig Mode",
    (1, 57): "LFO2 Depth",

    (1, 58): "LFO3 Speed",
    (1, 59): "LFO3 Multiplier",
    (1, 60): "LFO3 Fade",
    (1, 61): "LFO3 Destination",
    (1, 62): "LFO3 Waveform",
    (1, 70): "LFO3 Start Phase",
    (1, 71): "LFO3 Trig Mode",
    (1, 72): "LFO3 Depth",

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
    (2, 15): "Reverb Mix",

    (2, 41): "Chorus Depth",
    (2, 42): "Chorus Speed",
    (2, 43): "Chorus HPF",
    (2, 44): "Chorus Width",
    (2, 45): "Chorus Delay Send",
    (2, 46): "Chorus Reverb Send",
    (2, 47): "Chorus Mix",
}

def get_param_name(msb: int, lsb: int) -> str:
    """Get the human-readable name for an NRPN parameter"""
    return NRPN_PARAMS.get((msb, lsb), f"Unknown NRPN {msb}:{lsb}")
