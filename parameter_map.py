#!/usr/bin/env python3
"""
Digitakt II Parameter Mapping for Automation
Maps human-readable parameter names to MIDI CC/NRPN messages
"""

from nrpn_constants import (
    TrackCC, SourceCC, FilterCC, AmpCC, FXCC,
    TrackParams, TrigParams, SourceParams, FilterParams,
    AmpParams, LFO1Params, LFO2Params, LFO3Params,
    DelayParams, ReverbParams, ChorusParams
)

# Parameter mapping: name -> {type: "cc" or "nrpn", cc: X or msb: X, lsb: Y}
PARAMETER_MAP = {
    # FILTER PARAMETERS
    "filter_cutoff": {"type": "cc", "cc": FilterCC.FREQUENCY, "range": (0, 127)},
    "filter_frequency": {"type": "cc", "cc": FilterCC.FREQUENCY, "range": (0, 127)},  # Alias
    "filter_resonance": {"type": "nrpn", "msb": FilterParams.MSB, "lsb": FilterParams.RESONANCE, "range": (0, 127)},
    "filter_type": {"type": "nrpn", "msb": FilterParams.MSB, "lsb": FilterParams.TYPE, "range": (0, 127)},

    # FILTER ENVELOPE
    "filter_attack": {"type": "cc", "cc": FilterCC.ATTACK, "range": (0, 127)},
    "filter_decay": {"type": "cc", "cc": FilterCC.DECAY, "range": (0, 127)},
    "filter_sustain": {"type": "cc", "cc": FilterCC.SUSTAIN, "range": (0, 127)},
    "filter_release": {"type": "cc", "cc": FilterCC.RELEASE, "range": (0, 127)},
    "filter_env_depth": {"type": "cc", "cc": FilterCC.ENV_DEPTH, "range": (0, 127)},
    "filter_envelope_depth": {"type": "cc", "cc": FilterCC.ENV_DEPTH, "range": (0, 127)},  # Alias

    # AMP PARAMETERS
    "amp_volume": {"type": "cc", "cc": AmpCC.VOLUME, "range": (0, 127)},
    "amp_pan": {"type": "cc", "cc": AmpCC.PAN, "range": (0, 127)},
    "volume": {"type": "cc", "cc": AmpCC.VOLUME, "range": (0, 127)},  # Alias
    "pan": {"type": "cc", "cc": AmpCC.PAN, "range": (0, 127)},  # Alias

    # AMP ENVELOPE
    "amp_attack": {"type": "cc", "cc": AmpCC.ATTACK, "range": (0, 127)},
    "amp_hold": {"type": "cc", "cc": AmpCC.HOLD, "range": (0, 127)},
    "amp_decay": {"type": "cc", "cc": AmpCC.DECAY, "range": (0, 127)},
    "amp_sustain": {"type": "cc", "cc": AmpCC.SUSTAIN, "range": (0, 127)},
    "amp_release": {"type": "cc", "cc": AmpCC.RELEASE, "range": (0, 127)},
    "amp_mode": {"type": "nrpn", "msb": AmpParams.MSB, "lsb": AmpParams.MODE, "range": (0, 127)},
    "amp_env_reset": {"type": "nrpn", "msb": AmpParams.MSB, "lsb": AmpParams.ENV_RESET, "range": (0, 127)},

    # SOURCE/SAMPLE PARAMETERS
    "tune": {"type": "cc", "cc": SourceCC.TUNE, "range": (0, 127)},
    "pitch": {"type": "cc", "cc": SourceCC.TUNE, "range": (0, 127)},  # Alias
    "sample_level": {"type": "cc", "cc": SourceCC.SAMPLE_LEVEL, "range": (0, 127)},
    "fine_tune": {"type": "nrpn", "msb": SourceParams.MSB, "lsb": SourceParams.FINE_TUNE, "range": (0, 127)},
    "sample_slot": {"type": "nrpn", "msb": SourceParams.MSB, "lsb": SourceParams.SAMPLE_SLOT, "range": (0, 127)},
    "sample_start": {"type": "nrpn", "msb": SourceParams.MSB, "lsb": SourceParams.SAMPLE_START, "range": (0, 127)},
    "sample_length": {"type": "nrpn", "msb": SourceParams.MSB, "lsb": SourceParams.SAMPLE_LENGTH, "range": (0, 127)},
    "sample_loop": {"type": "nrpn", "msb": SourceParams.MSB, "lsb": SourceParams.SAMPLE_LOOP, "range": (0, 127)},
    "sample_volume": {"type": "nrpn", "msb": SourceParams.MSB, "lsb": SourceParams.SAMPLE_VOLUME, "range": (0, 127)},

    # LFO 1 PARAMETERS
    "lfo1_speed": {"type": "nrpn", "msb": LFO1Params.MSB, "lsb": LFO1Params.SPEED, "range": (0, 127)},
    "lfo1_multiplier": {"type": "nrpn", "msb": LFO1Params.MSB, "lsb": LFO1Params.MULTIPLIER, "range": (0, 127)},
    "lfo1_fade": {"type": "nrpn", "msb": LFO1Params.MSB, "lsb": LFO1Params.FADE, "range": (0, 127)},
    "lfo1_destination": {"type": "nrpn", "msb": LFO1Params.MSB, "lsb": LFO1Params.DESTINATION, "range": (0, 127)},
    "lfo1_waveform": {"type": "nrpn", "msb": LFO1Params.MSB, "lsb": LFO1Params.WAVEFORM, "range": (0, 127)},
    "lfo1_start_phase": {"type": "nrpn", "msb": LFO1Params.MSB, "lsb": LFO1Params.START_PHASE, "range": (0, 127)},
    "lfo1_trig_mode": {"type": "nrpn", "msb": LFO1Params.MSB, "lsb": LFO1Params.TRIG_MODE, "range": (0, 127)},
    "lfo1_depth": {"type": "nrpn", "msb": LFO1Params.MSB, "lsb": LFO1Params.DEPTH, "range": (0, 127)},

    # LFO 2 PARAMETERS
    "lfo2_speed": {"type": "nrpn", "msb": LFO2Params.MSB, "lsb": LFO2Params.SPEED, "range": (0, 127)},
    "lfo2_multiplier": {"type": "nrpn", "msb": LFO2Params.MSB, "lsb": LFO2Params.MULTIPLIER, "range": (0, 127)},
    "lfo2_fade": {"type": "nrpn", "msb": LFO2Params.MSB, "lsb": LFO2Params.FADE, "range": (0, 127)},
    "lfo2_destination": {"type": "nrpn", "msb": LFO2Params.MSB, "lsb": LFO2Params.DESTINATION, "range": (0, 127)},
    "lfo2_waveform": {"type": "nrpn", "msb": LFO2Params.MSB, "lsb": LFO2Params.WAVEFORM, "range": (0, 127)},
    "lfo2_start_phase": {"type": "nrpn", "msb": LFO2Params.MSB, "lsb": LFO2Params.START_PHASE, "range": (0, 127)},
    "lfo2_trig_mode": {"type": "nrpn", "msb": LFO2Params.MSB, "lsb": LFO2Params.TRIG_MODE, "range": (0, 127)},
    "lfo2_depth": {"type": "nrpn", "msb": LFO2Params.MSB, "lsb": LFO2Params.DEPTH, "range": (0, 127)},

    # LFO 3 PARAMETERS
    "lfo3_speed": {"type": "nrpn", "msb": LFO3Params.MSB, "lsb": LFO3Params.SPEED, "range": (0, 127)},
    "lfo3_multiplier": {"type": "nrpn", "msb": LFO3Params.MSB, "lsb": LFO3Params.MULTIPLIER, "range": (0, 127)},
    "lfo3_fade": {"type": "nrpn", "msb": LFO3Params.MSB, "lsb": LFO3Params.FADE, "range": (0, 127)},
    "lfo3_destination": {"type": "nrpn", "msb": LFO3Params.MSB, "lsb": LFO3Params.DESTINATION, "range": (0, 127)},
    "lfo3_waveform": {"type": "nrpn", "msb": LFO3Params.MSB, "lsb": LFO3Params.WAVEFORM, "range": (0, 127)},
    "lfo3_start_phase": {"type": "nrpn", "msb": LFO3Params.MSB, "lsb": LFO3Params.START_PHASE, "range": (0, 127)},
    "lfo3_trig_mode": {"type": "nrpn", "msb": LFO3Params.MSB, "lsb": LFO3Params.TRIG_MODE, "range": (0, 127)},
    "lfo3_depth": {"type": "nrpn", "msb": LFO3Params.MSB, "lsb": LFO3Params.DEPTH, "range": (0, 127)},

    # FX SEND PARAMETERS
    "chorus_send": {"type": "cc", "cc": FXCC.CHORUS_SEND, "range": (0, 127)},
    "delay_send": {"type": "cc", "cc": FXCC.DELAY_SEND, "range": (0, 127)},
    "reverb_send": {"type": "cc", "cc": FXCC.REVERB_SEND, "range": (0, 127)},
    "overdrive": {"type": "cc", "cc": FXCC.OVERDRIVE, "range": (0, 127)},

    # DELAY FX PARAMETERS
    "delay_time": {"type": "nrpn", "msb": DelayParams.MSB, "lsb": DelayParams.TIME, "range": (0, 127)},
    "delay_pingpong": {"type": "nrpn", "msb": DelayParams.MSB, "lsb": DelayParams.PINGPONG, "range": (0, 127)},
    "delay_stereo_width": {"type": "nrpn", "msb": DelayParams.MSB, "lsb": DelayParams.STEREO_WIDTH, "range": (0, 127)},
    "delay_feedback": {"type": "nrpn", "msb": DelayParams.MSB, "lsb": DelayParams.FEEDBACK, "range": (0, 127)},
    "delay_hpf": {"type": "nrpn", "msb": DelayParams.MSB, "lsb": DelayParams.HPF, "range": (0, 127)},
    "delay_lpf": {"type": "nrpn", "msb": DelayParams.MSB, "lsb": DelayParams.LPF, "range": (0, 127)},
    "delay_reverb_send": {"type": "nrpn", "msb": DelayParams.MSB, "lsb": DelayParams.REVERB_SEND, "range": (0, 127)},
    "delay_mix": {"type": "nrpn", "msb": DelayParams.MSB, "lsb": DelayParams.MIX, "range": (0, 127)},

    # REVERB FX PARAMETERS
    "reverb_predelay": {"type": "nrpn", "msb": ReverbParams.MSB, "lsb": ReverbParams.PREDELAY, "range": (0, 127)},
    "reverb_decay": {"type": "nrpn", "msb": ReverbParams.MSB, "lsb": ReverbParams.DECAY, "range": (0, 127)},
    "reverb_shelving_freq": {"type": "nrpn", "msb": ReverbParams.MSB, "lsb": ReverbParams.SHELVING_FREQ, "range": (0, 127)},
    "reverb_shelving_gain": {"type": "nrpn", "msb": ReverbParams.MSB, "lsb": ReverbParams.SHELVING_GAIN, "range": (0, 127)},
    "reverb_hpf": {"type": "nrpn", "msb": ReverbParams.MSB, "lsb": ReverbParams.HPF, "range": (0, 127)},
    "reverb_lpf": {"type": "nrpn", "msb": ReverbParams.MSB, "lsb": ReverbParams.LPF, "range": (0, 127)},
    "reverb_mix": {"type": "nrpn", "msb": ReverbParams.MSB, "lsb": ReverbParams.MIX, "range": (0, 127)},

    # CHORUS FX PARAMETERS
    "chorus_depth": {"type": "nrpn", "msb": ChorusParams.MSB, "lsb": ChorusParams.DEPTH, "range": (0, 127)},
    "chorus_speed": {"type": "nrpn", "msb": ChorusParams.MSB, "lsb": ChorusParams.SPEED, "range": (0, 127)},
    "chorus_hpf": {"type": "nrpn", "msb": ChorusParams.MSB, "lsb": ChorusParams.HPF, "range": (0, 127)},
    "chorus_width": {"type": "nrpn", "msb": ChorusParams.MSB, "lsb": ChorusParams.WIDTH, "range": (0, 127)},
    "chorus_delay_send": {"type": "nrpn", "msb": ChorusParams.MSB, "lsb": ChorusParams.DELAY_SEND, "range": (0, 127)},
    "chorus_reverb_send": {"type": "nrpn", "msb": ChorusParams.MSB, "lsb": ChorusParams.REVERB_SEND, "range": (0, 127)},
    "chorus_mix": {"type": "nrpn", "msb": ChorusParams.MSB, "lsb": ChorusParams.MIX, "range": (0, 127)},

    # TRACK PARAMETERS
    "track_level": {"type": "cc", "cc": TrackCC.LEVEL, "range": (0, 127)},
    "track_mute": {"type": "cc", "cc": TrackCC.MUTE, "range": (0, 127)},

    # TRIG PARAMETERS (for currently selected trig)
    "trig_note": {"type": "nrpn", "msb": TrigParams.MSB, "lsb": TrigParams.NOTE, "range": (0, 127)},
    "trig_velocity": {"type": "nrpn", "msb": TrigParams.MSB, "lsb": TrigParams.VELOCITY, "range": (0, 127)},
    "trig_length": {"type": "nrpn", "msb": TrigParams.MSB, "lsb": TrigParams.LENGTH, "range": (0, 127)},
}


def validate_parameter(param_name: str, value: int) -> tuple[bool, str]:
    """
    Validate a parameter name and value
    Returns: (is_valid, error_message)
    """
    if param_name not in PARAMETER_MAP:
        available = ", ".join(sorted(PARAMETER_MAP.keys()))
        return False, f"Unknown parameter '{param_name}'. Available parameters: {available}"

    param_info = PARAMETER_MAP[param_name]
    min_val, max_val = param_info["range"]

    if not (min_val <= value <= max_val):
        return False, f"Value {value} out of range for '{param_name}' (valid range: {min_val}-{max_val})"

    return True, ""


def get_parameter_info(param_name: str) -> dict:
    """Get parameter mapping info"""
    return PARAMETER_MAP.get(param_name)


def get_all_parameters() -> list[str]:
    """Get list of all available parameter names"""
    return sorted(PARAMETER_MAP.keys())


def get_parameters_by_category() -> dict:
    """Get parameters organized by category"""
    categories = {
        "Filter": [],
        "Filter Envelope": [],
        "Amp": [],
        "Amp Envelope": [],
        "Source/Sample": [],
        "LFO 1": [],
        "LFO 2": [],
        "LFO 3": [],
        "FX Sends": [],
        "Delay FX": [],
        "Reverb FX": [],
        "Chorus FX": [],
        "Track": [],
        "Trig": [],
    }

    for param_name in PARAMETER_MAP.keys():
        if param_name.startswith("filter_") and not any(x in param_name for x in ["attack", "decay", "sustain", "release", "env"]):
            categories["Filter"].append(param_name)
        elif param_name.startswith("filter_") and any(x in param_name for x in ["attack", "decay", "sustain", "release", "env"]):
            categories["Filter Envelope"].append(param_name)
        elif param_name.startswith("amp_") and not any(x in param_name for x in ["attack", "hold", "decay", "sustain", "release", "env", "mode"]):
            categories["Amp"].append(param_name)
        elif param_name.startswith("amp_") and any(x in param_name for x in ["attack", "hold", "decay", "sustain", "release", "env", "mode"]):
            categories["Amp Envelope"].append(param_name)
        elif param_name.startswith("lfo1_"):
            categories["LFO 1"].append(param_name)
        elif param_name.startswith("lfo2_"):
            categories["LFO 2"].append(param_name)
        elif param_name.startswith("lfo3_"):
            categories["LFO 3"].append(param_name)
        elif param_name in ["chorus_send", "delay_send", "reverb_send", "overdrive"]:
            categories["FX Sends"].append(param_name)
        elif param_name.startswith("delay_"):
            categories["Delay FX"].append(param_name)
        elif param_name.startswith("reverb_"):
            categories["Reverb FX"].append(param_name)
        elif param_name.startswith("chorus_") and param_name not in ["chorus_send"]:
            categories["Chorus FX"].append(param_name)
        elif param_name.startswith("track_"):
            categories["Track"].append(param_name)
        elif param_name.startswith("trig_"):
            categories["Trig"].append(param_name)
        elif param_name in ["tune", "pitch", "fine_tune", "sample_slot", "sample_start", "sample_length", "sample_loop", "sample_volume", "sample_level"]:
            categories["Source/Sample"].append(param_name)
        elif param_name in ["volume", "pan"]:
            categories["Amp"].append(param_name)

    # Remove empty categories
    return {k: sorted(v) for k, v in categories.items() if v}
