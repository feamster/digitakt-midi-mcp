#!/usr/bin/env python3
"""
MCP Server for Digitakt II MIDI Control
Provides tools to send MIDI messages to the Elektron Digitakt II
"""

import asyncio
import mido
from typing import Optional
from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
import mcp.server.stdio
import logging
import json
import os
from pathlib import Path
from nrpn_constants import (
    NRPN_MSB, TrackParams, TrigParams, SourceParams,
    FilterParams, AmpParams, LFO1Params, LFO2Params, LFO3Params,
    DelayParams, ReverbParams, ChorusParams,
    get_param_name
)
from parameter_map import (
    PARAMETER_MAP, validate_parameter, get_parameter_info,
    get_all_parameters, get_parameters_by_category
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("digitakt-midi-server")

# MIDI port name - will be auto-detected
DIGITAKT_PORT_NAME = "Elektron Digitakt II"

# Preset directory
PRESET_DIR = Path.home() / ".digitakt-mcp" / "presets"
PRESET_DIR.mkdir(parents=True, exist_ok=True)

# Create server instance
server = Server("digitakt-midi-server")

# Global MIDI port references
output_port: Optional[mido.ports.BaseOutput] = None
input_port: Optional[mido.ports.BaseInput] = None

# Global history for last played melody/pattern
last_melody = None  # Stores: {"bpm": int, "notes": [...], "channel": int}
last_tracks = None  # Stores: {"bpm": int, "triggers": [...]}
last_loop = None    # Stores: {"bpm": int, "loop_notes": [...], "loop_length": float, "channel": int}

def connect_midi():
    """Connect to Digitakt MIDI ports"""
    global output_port, input_port
    
    try:
        # Find and connect to Digitakt output port
        output_ports = mido.get_output_names()
        for port_name in output_ports:
            if DIGITAKT_PORT_NAME in port_name:
                output_port = mido.open_output(port_name)
                logger.info(f"Connected to MIDI output: {port_name}")
                break

        # Find and connect to Digitakt input port
        input_ports = mido.get_input_names()
        for port_name in input_ports:
            if DIGITAKT_PORT_NAME in port_name:
                input_port = mido.open_input(port_name)
                logger.info(f"Connected to MIDI input: {port_name}")
                break

        if not output_port:
            logger.warning(f"Could not find MIDI output port for {DIGITAKT_PORT_NAME}")
        if not input_port:
            logger.warning(f"Could not find MIDI input port for {DIGITAKT_PORT_NAME}")

    except Exception as e:
        logger.error(f"Error connecting to MIDI: {e}")

def send_parameter_change(param_name: str, value: int, channel: int = 0):
    """
    Send a parameter change via CC or NRPN
    channel: 0-indexed MIDI channel
    """
    param_info = get_parameter_info(param_name)
    if not param_info:
        raise ValueError(f"Unknown parameter: {param_name}")

    if param_info["type"] == "cc":
        # Send CC message
        msg = mido.Message('control_change', control=param_info["cc"], value=value, channel=channel)
        output_port.send(msg)
    elif param_info["type"] == "nrpn":
        # Send NRPN message (4 CC messages)
        output_port.send(mido.Message('control_change', control=99, value=param_info["msb"], channel=channel))
        output_port.send(mido.Message('control_change', control=98, value=param_info["lsb"], channel=channel))
        output_port.send(mido.Message('control_change', control=6, value=value, channel=channel))
        output_port.send(mido.Message('control_change', control=38, value=0, channel=channel))

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MIDI control tools"""
    return [
        Tool(
            name="send_note",
            description="Send a MIDI note on/off message to the Digitakt. To trigger one-shots on specific tracks, use notes 0-7 (Track 1-8). To play the active track chromatically, use notes 12-84.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note": {
                        "type": "integer",
                        "description": "MIDI note number (0-127). Track triggers: 0-7 (Track 1-8). Chromatic: 12-84 (plays active track). Examples: 0=Track 1 kick, 1=Track 2 snare, 60=C3 on active track.",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "velocity": {
                        "type": "integer",
                        "description": "Note velocity (1-127). 0 = note off. Default is 100.",
                        "minimum": 0,
                        "maximum": 127,
                        "default": 100
                    },
                    "duration": {
                        "type": "number",
                        "description": "How long to hold the note in seconds. Default is 0.1 seconds.",
                        "minimum": 0.001,
                        "default": 0.1
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1 (auto channel on Digitakt).",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["note"]
            }
        ),
        Tool(
            name="trigger_track",
            description="Trigger a one-shot sample on a specific Digitakt II track (1-16). This is a convenience wrapper that sends the correct MIDI note (0-15) to trigger the track.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track": {
                        "type": "integer",
                        "description": "Track number (1-16). Tracks 1-16 correspond to MIDI notes 0-15.",
                        "minimum": 1,
                        "maximum": 16
                    },
                    "velocity": {
                        "type": "integer",
                        "description": "Note velocity (1-127). Default is 100.",
                        "minimum": 1,
                        "maximum": 127,
                        "default": 100
                    },
                    "duration": {
                        "type": "number",
                        "description": "How long to hold the note in seconds. Default is 0.1 seconds.",
                        "minimum": 0.001,
                        "default": 0.1
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1 (AUTO CHANNEL).",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["track"]
            }
        ),
        Tool(
            name="send_cc",
            description="Send a MIDI Control Change (CC) message to control Digitakt parameters like filter, envelope, LFO, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cc_number": {
                        "type": "integer",
                        "description": "CC number (0-127). Common CCs: 74=Filter Freq, 71=Filter Res, 73=Attack, 75=Decay, etc.",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "value": {
                        "type": "integer",
                        "description": "CC value (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["cc_number", "value"]
            }
        ),
        Tool(
            name="send_program_change",
            description="Send a MIDI Program Change message to switch patterns on the Digitakt",
            inputSchema={
                "type": "object",
                "properties": {
                    "program": {
                        "type": "integer",
                        "description": "Program number (0-127). Patterns are numbered 0-127 across banks.",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["program"]
            }
        ),
        Tool(
            name="send_note_sequence",
            description="Send a sequence of MIDI notes with timing. Useful for creating rhythms or melodies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "notes": {
                        "type": "array",
                        "description": "Array of note events. Each event is [note, velocity, duration_sec]",
                        "items": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {"type": "number"}
                        }
                    },
                    "delay": {
                        "type": "number",
                        "description": "Delay between notes in seconds. Default is 0.25 (quarter note at 120 BPM)",
                        "minimum": 0,
                        "default": 0.25
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["notes"]
            }
        ),
        Tool(
            name="send_sysex",
            description="Send a System Exclusive (SysEx) message to the Digitakt. SysEx messages can be used for advanced control, pattern programming, and device configuration. Elektron manufacturer ID is 0x00 0x20 0x3C.",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "description": "Array of bytes to send as SysEx data (excluding F0 start and F7 end bytes, which are added automatically). Example: [0x00, 0x20, 0x3C, ...]. For Elektron devices, messages typically start with manufacturer ID [0x00, 0x20, 0x3C].",
                        "items": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 127
                        }
                    },
                    "hex_string": {
                        "type": "string",
                        "description": "Alternative to 'data': provide SysEx data as a hex string (e.g., '00203C...'). Spaces are ignored."
                    }
                }
            }
        ),
        Tool(
            name="request_sysex_dump",
            description="Request a SysEx data dump from the Digitakt (pattern, sound, kit, or project data). Note: You'll need to capture the response separately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dump_type": {
                        "type": "string",
                        "description": "Type of data to request: 'pattern', 'sound', 'kit', or 'project'",
                        "enum": ["pattern", "sound", "kit", "project"]
                    },
                    "bank": {
                        "type": "integer",
                        "description": "Bank number (0-15 for patterns). Optional.",
                        "minimum": 0,
                        "maximum": 15
                    },
                    "pattern_number": {
                        "type": "integer",
                        "description": "Pattern number within bank (0-15). Optional.",
                        "minimum": 0,
                        "maximum": 15
                    }
                },
                "required": ["dump_type"]
            }
        ),
        Tool(
            name="send_nrpn",
            description="Send an NRPN (Non-Registered Parameter Number) message to control Digitakt parameters. NRPNs provide access to more parameters than standard CCs, including per-trig control (note, velocity, length), filter, amp, LFO, and effects parameters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "msb": {
                        "type": "integer",
                        "description": "NRPN MSB (Most Significant Byte). 1=Track/Trig/Source/Filter/Amp, 2=FX, 3=Trig Note/Velocity/Length",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "lsb": {
                        "type": "integer",
                        "description": "NRPN LSB (Least Significant Byte) - the specific parameter number",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "value": {
                        "type": "integer",
                        "description": "Parameter value (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["msb", "lsb", "value"]
            }
        ),
        Tool(
            name="set_trig_note",
            description="Set the note/pitch for a trig (step). This is a convenience wrapper for NRPN MSB=3, LSB=0.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note": {
                        "type": "integer",
                        "description": "MIDI note number (0-127). For Digitakt: 60=C3",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["note"]
            }
        ),
        Tool(
            name="set_trig_velocity",
            description="Set the velocity for a trig (step). This is a convenience wrapper for NRPN MSB=3, LSB=1.",
            inputSchema={
                "type": "object",
                "properties": {
                    "velocity": {
                        "type": "integer",
                        "description": "Velocity (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["velocity"]
            }
        ),
        Tool(
            name="set_trig_length",
            description="Set the note length for a trig (step). This is a convenience wrapper for NRPN MSB=3, LSB=2.",
            inputSchema={
                "type": "object",
                "properties": {
                    "length": {
                        "type": "integer",
                        "description": "Note length (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["length"]
            }
        ),
        Tool(
            name="send_midi_start",
            description="Send MIDI Start message to start the Digitakt's sequencer from the beginning. This is a standard MIDI transport control message.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="send_midi_stop",
            description="Send MIDI Stop message to stop the Digitakt's sequencer. This is a standard MIDI transport control message.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="send_midi_continue",
            description="Send MIDI Continue message to resume the Digitakt's sequencer from its current position. This is a standard MIDI transport control message.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="send_song_position",
            description="Send MIDI Song Position Pointer to jump to a specific position in the sequence. Position is measured in MIDI beats (16th notes).",
            inputSchema={
                "type": "object",
                "properties": {
                    "position": {
                        "type": "integer",
                        "description": "Song position in MIDI beats (16th notes). 0 = start, 16 = 1 bar at 4/4 time.",
                        "minimum": 0,
                        "maximum": 16383
                    }
                },
                "required": ["position"]
            }
        ),
        Tool(
            name="play_with_clock",
            description="Start the Digitakt sequencer and send MIDI clock for a specified duration. The Digitakt requires receiving MIDI clock to play when externally controlled.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {
                        "type": "number",
                        "description": "Number of bars to play (in 4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "send_stop": {
                        "type": "boolean",
                        "description": "Send MIDI Stop after duration. Default is true.",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="play_pattern_with_tracks",
            description="Start the Digitakt pattern and trigger specific tracks at specific times. Sends MIDI Start + Clock while also sending note triggers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {
                        "type": "number",
                        "description": "Number of bars to play (in 4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "triggers": {
                        "type": "array",
                        "description": "Array of [beat, track, velocity] where beat is 0-based quarter note (0=start, 1=beat 2, etc), track is 1-16, velocity is 1-127.",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 3
                        }
                    },
                    "send_stop": {
                        "type": "boolean",
                        "description": "Send MIDI Stop after duration. Default is true.",
                        "default": True
                    }
                },
                "required": ["triggers"]
            }
        ),
        Tool(
            name="play_pattern_with_melody",
            description="Start the Digitakt pattern and play a melodic sequence on the active track. Sends MIDI Start + Clock while also sending notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {
                        "type": "number",
                        "description": "Number of bars to play (in 4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "notes": {
                        "type": "array",
                        "description": "Array of [beat, note, velocity, duration] where beat is 0-based quarter note, note is MIDI note 12-127, velocity is 1-127, duration is in seconds.",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 4
                        }
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1 (auto channel).",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    },
                    "send_stop": {
                        "type": "boolean",
                        "description": "Send MIDI Stop after duration. Default is true.",
                        "default": True
                    }
                },
                "required": ["notes"]
            }
        ),
        Tool(
            name="play_pattern_with_loop",
            description="Start the Digitakt pattern and continuously trigger notes on a loop. Sends MIDI Start + Clock while looping note triggers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {
                        "type": "number",
                        "description": "Number of bars to play (in 4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "loop_notes": {
                        "type": "array",
                        "description": "Array of [beat_offset, note_or_track, velocity] where beat_offset is relative to loop start (0-3.99 for 1 bar loop), note/track can be 0-15 for tracks or 12+ for melody, velocity is 1-127.",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 3
                        }
                    },
                    "loop_length": {
                        "type": "number",
                        "description": "Length of the loop in bars (in 4/4 time). Default is 1 bar.",
                        "minimum": 0.25,
                        "default": 1
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1 (auto channel).",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    },
                    "send_stop": {
                        "type": "boolean",
                        "description": "Send MIDI Stop after duration. Default is true.",
                        "default": True
                    }
                },
                "required": ["loop_notes"]
            }
        ),
        Tool(
            name="play_pattern_with_tracks_and_melody",
            description="Start the Digitakt pattern and play both track triggers and melody simultaneously. Combines MIDI transport control with both drum triggers and chromatic notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {
                        "type": "number",
                        "description": "Number of bars to play (in 4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "track_triggers": {
                        "type": "array",
                        "description": "Array of [beat, track, velocity] or [beat, track, velocity, note] where beat is 0-based quarter note, track is 1-16, velocity is 1-127, and optional note is MIDI note 0-127 for chromatic triggering (if omitted, uses track number as note for standard triggering).",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 4
                        },
                        "default": []
                    },
                    "melody_notes": {
                        "type": "array",
                        "description": "Array of [beat, note, velocity, duration] where beat is 0-based quarter note, note is MIDI note 12-127, velocity is 1-127, duration is in seconds.",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 4
                        },
                        "default": []
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel for melody notes (1-16). Track triggers always use channel 1. Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    },
                    "midi_start_at_beat": {
                        "type": "number",
                        "description": "Beat number (0-based) to send MIDI Start and begin MIDI Clock. Before this beat, only note triggers are sent (no transport control). When starting mid-sequence (beat > 0), a MIDI Song Position Pointer message is sent before MIDI Start to ensure the Digitakt sequencer aligns with the correct beat position. Default is 0 (send MIDI Start immediately). Use this for count-in workflows where you want to arm recording during count-in, then start Digitakt sequencer at a specific beat.",
                        "minimum": 0,
                        "default": 0
                    },
                    "preroll_bars": {
                        "type": "number",
                        "description": "Number of bars to delay melody notes (not track triggers). Track triggers play immediately, melody notes start after preroll. Use for live recording: set preroll_bars to the loop length, arm recording during preroll, then melody notes get recorded. Default is 0 (no preroll).",
                        "minimum": 0,
                        "default": 0
                    },
                    "send_stop": {
                        "type": "boolean",
                        "description": "Send MIDI Stop after duration. Default is true.",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="play_pattern_with_multi_channel_midi",
            description="Play patterns with MIDI notes on multiple channels simultaneously. Send drums to Digitakt tracks while also sending MIDI notes to multiple external instruments on different channels (e.g., chords on channel 9, pad melody on channel 12) all synchronized together.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {
                        "type": "number",
                        "description": "Number of bars to play (in 4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "track_triggers": {
                        "type": "array",
                        "description": "Array of [beat, track, velocity] or [beat, track, velocity, note] for Digitakt drum tracks where beat is 0-based quarter note, track is 1-16, velocity is 1-127, and optional note is MIDI note 0-127 for chromatic triggering (if omitted, uses track number as note for standard triggering).",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 4
                        },
                        "default": []
                    },
                    "midi_channels": {
                        "type": "object",
                        "description": "Dictionary mapping MIDI channel numbers (1-16) to arrays of [beat, note, velocity, duration]. Each channel can have independent note sequences. Example: {'9': [[0, 54, 75, 3.9], [0.01, 57, 75, 3.9]], '12': [[0, 69, 70, 1.9], [2, 73, 65, 1.9]]}",
                        "additionalProperties": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 4
                            }
                        },
                        "default": {}
                    },
                    "send_clock": {
                        "type": "boolean",
                        "description": "Send MIDI Clock messages for transport sync. Default is true.",
                        "default": True
                    },
                    "midi_start_at_beat": {
                        "type": "number",
                        "description": "Beat number (0-based) to send MIDI Start and begin MIDI Clock. Before this beat, only note triggers are sent (no transport control). When starting mid-sequence (beat > 0), a MIDI Song Position Pointer message is sent before MIDI Start to ensure the Digitakt sequencer aligns with the correct beat position. Default is 0 (send MIDI Start immediately).",
                        "minimum": 0,
                        "default": 0
                    },
                    "preroll_bars": {
                        "type": "number",
                        "description": "Number of bars to delay MIDI channel notes (not track triggers). Track triggers play immediately, MIDI notes start after preroll. Use for live recording: set preroll_bars to the loop length, arm recording during preroll, then MIDI notes get recorded. Default is 0 (no preroll).",
                        "minimum": 0,
                        "default": 0
                    },
                    "send_stop": {
                        "type": "boolean",
                        "description": "Send MIDI Stop after duration. Default is true.",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="save_last_melody",
            description="Save the last played melody from play_pattern_with_melody to a MIDI file. The melody is saved with the original tempo and timing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename for the MIDI file (e.g., 'my_melody.mid'). Will be saved in the current directory."
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="send_filter_sweep",
            description="Smoothly sweep the filter cutoff from one value to another over a specified duration. Useful for creating dynamic filter movements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_value": {
                        "type": "integer",
                        "description": "Starting filter cutoff value (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "end_value": {
                        "type": "integer",
                        "description": "Ending filter cutoff value (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "duration_sec": {
                        "type": "number",
                        "description": "Duration of the sweep in seconds",
                        "minimum": 0.1
                    },
                    "curve": {
                        "type": "string",
                        "description": "Sweep curve shape: 'linear' (constant rate), 'exponential' (fast start, slow end), 'logarithmic' (slow start, fast end)",
                        "enum": ["linear", "exponential", "logarithmic"],
                        "default": "linear"
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of CC messages to send (more = smoother). Default is 50.",
                        "minimum": 2,
                        "maximum": 200,
                        "default": 50
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["start_value", "end_value", "duration_sec"]
            }
        ),
        Tool(
            name="send_filter_envelope",
            description="Apply an ADSR-style envelope to the filter cutoff. Creates organic filter movements with attack, decay, sustain, and release stages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "attack_sec": {
                        "type": "number",
                        "description": "Attack time in seconds - time to reach peak (127)",
                        "minimum": 0.01
                    },
                    "decay_sec": {
                        "type": "number",
                        "description": "Decay time in seconds - time to drop from peak to sustain level",
                        "minimum": 0.01
                    },
                    "sustain_level": {
                        "type": "integer",
                        "description": "Sustain filter cutoff value (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "release_sec": {
                        "type": "number",
                        "description": "Release time in seconds - time to return to 0",
                        "minimum": 0.01
                    },
                    "steps_per_stage": {
                        "type": "integer",
                        "description": "Number of CC messages per stage (more = smoother). Default is 20.",
                        "minimum": 2,
                        "maximum": 100,
                        "default": 20
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["attack_sec", "decay_sec", "sustain_level", "release_sec"]
            }
        ),
        Tool(
            name="play_with_filter_automation",
            description="Play a pattern with automated filter cutoff changes at specific beats. Combines transport control, track triggers, and precise filter automation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {
                        "type": "number",
                        "description": "Number of bars to play (in 4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "track_triggers": {
                        "type": "array",
                        "description": "Optional array of [beat, track, velocity] where beat is 0-based quarter note, track is 1-16, velocity is 1-127.",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 3
                        },
                        "default": []
                    },
                    "filter_events": {
                        "type": "array",
                        "description": "Array of [beat, cutoff_value] for timed filter cutoff changes. Beat is 0-based quarter note, cutoff is 0-127.",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2
                        }
                    },
                    "send_clock": {
                        "type": "boolean",
                        "description": "Send MIDI Start and Clock messages. Default is true.",
                        "default": True
                    },
                    "send_stop": {
                        "type": "boolean",
                        "description": "Send MIDI Stop after duration. Default is true.",
                        "default": True
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["filter_events"]
            }
        ),
        Tool(
            name="send_parameter_sweep",
            description="Smoothly sweep any parameter from one value to another over a specified duration. Works with all parameters including filter, amp, LFO, sample, and FX parameters. Use this for creating dynamic parameter movements like filter sweeps, pitch bends, LFO depth fades, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "parameter": {
                        "type": "string",
                        "description": "Parameter name to sweep. Examples: 'filter_cutoff', 'filter_resonance', 'amp_attack', 'lfo1_depth', 'sample_start', 'pitch'. Use list_parameters tool to see all available parameters."
                    },
                    "start_value": {
                        "type": "integer",
                        "description": "Starting parameter value (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "end_value": {
                        "type": "integer",
                        "description": "Ending parameter value (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "duration_sec": {
                        "type": "number",
                        "description": "Duration of the sweep in seconds",
                        "minimum": 0.1
                    },
                    "curve": {
                        "type": "string",
                        "description": "Sweep curve shape: 'linear' (constant rate), 'exponential' (fast start, slow end), 'logarithmic' (slow start, fast end)",
                        "enum": ["linear", "exponential", "logarithmic"],
                        "default": "linear"
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of messages to send (more = smoother). Default is 50.",
                        "minimum": 2,
                        "maximum": 200,
                        "default": 50
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["parameter", "start_value", "end_value", "duration_sec"]
            }
        ),
        Tool(
            name="send_parameter_envelope",
            description="Apply an ADSR-style envelope to any parameter. Creates organic parameter movements with attack, decay, sustain, and release stages. Great for filter envelopes, amp envelopes, LFO depth modulation, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "parameter": {
                        "type": "string",
                        "description": "Parameter name to modulate. Examples: 'filter_cutoff', 'amp_volume', 'lfo1_depth', 'sample_start'."
                    },
                    "attack_sec": {
                        "type": "number",
                        "description": "Attack time in seconds - time to reach peak (127)",
                        "minimum": 0.01
                    },
                    "decay_sec": {
                        "type": "number",
                        "description": "Decay time in seconds - time to drop from peak to sustain level",
                        "minimum": 0.01
                    },
                    "sustain_level": {
                        "type": "integer",
                        "description": "Sustain parameter value (0-127)",
                        "minimum": 0,
                        "maximum": 127
                    },
                    "release_sec": {
                        "type": "number",
                        "description": "Release time in seconds - time to return to 0",
                        "minimum": 0.01
                    },
                    "steps_per_stage": {
                        "type": "integer",
                        "description": "Number of messages per stage (more = smoother). Default is 20.",
                        "minimum": 2,
                        "maximum": 100,
                        "default": 20
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["parameter", "attack_sec", "decay_sec", "sustain_level", "release_sec"]
            }
        ),
        Tool(
            name="play_pattern_with_parameter_automation",
            description="Play a pattern with automated parameter changes at specific beats. Supports multiple parameters simultaneously. This is the main tool for creating complex, evolving sounds with filter, amp, LFO, and FX automation. Note: automation is sent in real-time and not saved to Digitakt patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bars": {
                        "type": "number",
                        "description": "Number of bars to play (in 4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "track_triggers": {
                        "type": "array",
                        "description": "Optional array of [beat, track, velocity] where beat is 0-based quarter note, track is 1-16, velocity is 1-127.",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 3
                        },
                        "default": []
                    },
                    "parameter_automation": {
                        "type": "object",
                        "description": "Object mapping parameter names to arrays of [beat, value] pairs. Example: {'filter_cutoff': [[0, 20], [4, 80]], 'filter_resonance': [[0, 40], [8, 100]], 'lfo1_depth': [[0, 0], [8, 127]]}"
                    },
                    "send_clock": {
                        "type": "boolean",
                        "description": "Send MIDI Start and Clock messages. Default is true.",
                        "default": True
                    },
                    "send_stop": {
                        "type": "boolean",
                        "description": "Send MIDI Stop after duration. Default is true.",
                        "default": True
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["parameter_automation"]
            }
        ),
        Tool(
            name="save_automation_preset",
            description=f"Save parameter automation as a reusable JSON preset file. Presets are stored in {PRESET_DIR} and can be loaded later.",
            inputSchema={
                "type": "object",
                "properties": {
                    "preset_name": {
                        "type": "string",
                        "description": "Name for the preset (without .json extension). Example: 'wobble_bass', 'filter_build'"
                    },
                    "automation": {
                        "type": "object",
                        "description": "Automation data including parameter_automation, bars, bpm, etc."
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of what this preset does"
                    }
                },
                "required": ["preset_name", "automation"]
            }
        ),
        Tool(
            name="load_automation_preset",
            description=f"Load and optionally play a saved automation preset from {PRESET_DIR}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "preset_name": {
                        "type": "string",
                        "description": "Name of the preset to load (without .json extension)"
                    },
                    "play": {
                        "type": "boolean",
                        "description": "If true, immediately play the loaded preset. Default is false (just load and return the data).",
                        "default": False
                    }
                },
                "required": ["preset_name"]
            }
        ),
        Tool(
            name="list_automation_presets",
            description=f"List all available automation presets stored in {PRESET_DIR}.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="export_automation_to_midi",
            description="Export parameter automation to a standard MIDI file that can be imported into any DAW.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Output MIDI filename (will add .mid extension if not present)"
                    },
                    "automation": {
                        "type": "object",
                        "description": "Automation data including parameter_automation, bars, bpm, etc."
                    },
                    "channel": {
                        "type": "integer",
                        "description": "MIDI channel (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["filename", "automation"]
            }
        ),
        Tool(
            name="export_pattern_to_midi",
            description="Export a Digitakt pattern to a standard MIDI file (.mid). Creates a multi-track MIDI file with drums on channel 1 and melody on specified channel. Supports chromatic track triggers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Output filename (will add .mid extension if not present)"
                    },
                    "bpm": {
                        "type": "number",
                        "description": "Tempo in beats per minute. Default is 120 BPM.",
                        "minimum": 20,
                        "maximum": 300,
                        "default": 120
                    },
                    "bars": {
                        "type": "number",
                        "description": "Total length in bars (4/4 time). Default is 4 bars.",
                        "minimum": 0.25,
                        "default": 4
                    },
                    "track_triggers": {
                        "type": "array",
                        "description": "Array of [beat, track, velocity] or [beat, track, velocity, note] for drum/sample triggers",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 4
                        },
                        "default": []
                    },
                    "melody_notes": {
                        "type": "array",
                        "description": "Array of [beat, note, velocity, duration] for melody notes",
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 4
                        },
                        "default": []
                    },
                    "melody_channel": {
                        "type": "integer",
                        "description": "MIDI channel for melody notes (1-16). Default is 1.",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="list_parameters",
            description="List all available parameters that can be automated, organized by category (Filter, Amp, LFO, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional: filter by category name. If not specified, shows all categories."
                    }
                }
            }
        )
    ]

# Helper function for delayed note off
async def _delayed_note_off(note: int, duration: float, channel: int = 0):
    """Send note off after a delay"""
    await asyncio.sleep(duration)
    if output_port:
        output_port.send(mido.Message('note_off', note=note, velocity=0, channel=channel))

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a MIDI tool"""
    if not output_port:
        return [TextContent(
            type="text",
            text="Error: Not connected to Digitakt MIDI output port"
        )]

    try:
        if name == "send_note":
            note = arguments["note"]
            velocity = arguments.get("velocity", 100)
            duration = arguments.get("duration", 0.1)
            channel = arguments.get("channel", 1) - 1  # Convert to 0-indexed

            # Send note on
            msg_on = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            output_port.send(msg_on)

            # Wait for duration
            await asyncio.sleep(duration)

            # Send note off
            msg_off = mido.Message('note_off', note=note, velocity=0, channel=channel)
            output_port.send(msg_off)

            return [TextContent(
                type="text",
                text=f"Sent note {note} (velocity {velocity}) on channel {channel+1} for {duration}s"
            )]

        elif name == "trigger_track":
            track = arguments["track"]
            velocity = arguments.get("velocity", 100)
            duration = arguments.get("duration", 0.1)
            channel = arguments.get("channel", 1) - 1  # Convert to 0-indexed

            # Convert track number (1-8) to MIDI note (0-7)
            note = track - 1

            # Send note on
            msg_on = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            output_port.send(msg_on)

            # Wait for duration
            await asyncio.sleep(duration)

            # Send note off
            msg_off = mido.Message('note_off', note=note, velocity=0, channel=channel)
            output_port.send(msg_off)

            return [TextContent(
                type="text",
                text=f"Triggered Track {track} (note {note}, velocity {velocity}) on channel {channel+1} for {duration}s"
            )]

        elif name == "send_cc":
            cc_number = arguments["cc_number"]
            value = arguments["value"]
            channel = arguments.get("channel", 1) - 1

            msg = mido.Message('control_change', control=cc_number, value=value, channel=channel)
            output_port.send(msg)

            return [TextContent(
                type="text",
                text=f"Sent CC {cc_number} = {value} on channel {channel+1}"
            )]

        elif name == "send_program_change":
            program = arguments["program"]
            channel = arguments.get("channel", 1) - 1

            msg = mido.Message('program_change', program=program, channel=channel)
            output_port.send(msg)

            return [TextContent(
                type="text",
                text=f"Sent Program Change to {program} on channel {channel+1}"
            )]

        elif name == "send_note_sequence":
            notes = arguments["notes"]
            delay = arguments.get("delay", 0.25)
            channel = arguments.get("channel", 1) - 1

            for i, (note, velocity, duration) in enumerate(notes):
                # Send note on
                msg_on = mido.Message('note_on', note=int(note), velocity=int(velocity), channel=channel)
                output_port.send(msg_on)

                # Wait for note duration
                await asyncio.sleep(duration)

                # Send note off
                msg_off = mido.Message('note_off', note=int(note), velocity=0, channel=channel)
                output_port.send(msg_off)

                # Wait before next note (if not the last note)
                if i < len(notes) - 1:
                    await asyncio.sleep(delay)

            return [TextContent(
                type="text",
                text=f"Sent sequence of {len(notes)} notes on channel {channel+1}"
            )]

        elif name == "send_sysex":
            # Get SysEx data from either data array or hex string
            sysex_data = None

            if "data" in arguments and arguments["data"]:
                sysex_data = arguments["data"]
            elif "hex_string" in arguments and arguments["hex_string"]:
                hex_str = arguments["hex_string"].replace(" ", "").replace("0x", "")
                # Convert hex string to byte array
                sysex_data = [int(hex_str[i:i+2], 16) for i in range(0, len(hex_str), 2)]

            if not sysex_data:
                return [TextContent(
                    type="text",
                    text="Error: Must provide either 'data' array or 'hex_string'"
                )]

            # Send SysEx message
            msg = mido.Message('sysex', data=sysex_data)
            output_port.send(msg)

            # Format output
            hex_display = " ".join([f"{b:02X}" for b in sysex_data[:16]])
            if len(sysex_data) > 16:
                hex_display += f"... ({len(sysex_data)} bytes total)"

            return [TextContent(
                type="text",
                text=f"Sent SysEx message: F0 {hex_display} F7"
            )]

        elif name == "request_sysex_dump":
            dump_type = arguments["dump_type"]

            # Elektron manufacturer ID: 0x00 0x20 0x3C
            # Note: The exact format for dump requests is not publicly documented
            # This is a placeholder that sends a basic dump request structure
            # You may need to adjust based on actual Digitakt protocol

            # Basic structure (this may need adjustment based on actual protocol):
            # F0 00 20 3C [device_id] [command] [parameters...] F7

            ELEKTRON_MFG_ID = [0x00, 0x20, 0x3C]
            DIGITAKT_DEVICE_ID = 0x0E  # Placeholder - may need verification

            sysex_data = ELEKTRON_MFG_ID + [DIGITAKT_DEVICE_ID]

            # Add dump request command (placeholder - needs verification)
            if dump_type == "pattern":
                bank = arguments.get("bank", 0)
                pattern_num = arguments.get("pattern_number", 0)
                # Command 0x67 might be pattern dump request (unverified)
                sysex_data.extend([0x67, bank, pattern_num])
            elif dump_type == "sound":
                sysex_data.extend([0x68, 0x00])  # Placeholder
            elif dump_type == "kit":
                sysex_data.extend([0x69, 0x00])  # Placeholder
            elif dump_type == "project":
                sysex_data.extend([0x6A, 0x00])  # Placeholder

            msg = mido.Message('sysex', data=sysex_data)
            output_port.send(msg)

            hex_display = " ".join([f"{b:02X}" for b in sysex_data])

            return [TextContent(
                type="text",
                text=f"Sent SysEx dump request for {dump_type}: F0 {hex_display} F7\n\nNote: The exact SysEx format for Digitakt dump requests is not publicly documented. This sends a basic request structure that may need adjustment. You may need to use Elektron Transfer software or capture actual dump requests to determine the correct format."
            )]

        elif name == "send_nrpn":
            msb = arguments["msb"]
            lsb = arguments["lsb"]
            value = arguments["value"]
            channel = arguments.get("channel", 1) - 1  # Convert to 0-indexed

            # Send NRPN message (requires 4 CC messages)
            # 1. CC 99 (NRPN MSB)
            msg1 = mido.Message('control_change', control=99, value=msb, channel=channel)
            output_port.send(msg1)

            # 2. CC 98 (NRPN LSB)
            msg2 = mido.Message('control_change', control=98, value=lsb, channel=channel)
            output_port.send(msg2)

            # 3. CC 6 (Data Entry MSB)
            msg3 = mido.Message('control_change', control=6, value=value, channel=channel)
            output_port.send(msg3)

            # 4. CC 38 (Data Entry LSB) - typically 0
            msg4 = mido.Message('control_change', control=38, value=0, channel=channel)
            output_port.send(msg4)

            param_name = get_param_name(msb, lsb)

            return [TextContent(
                type="text",
                text=f"Sent NRPN: {param_name} (MSB={msb}, LSB={lsb}) = {value} on channel {channel+1}"
            )]

        elif name == "set_trig_note":
            note = arguments["note"]
            channel = arguments.get("channel", 1) - 1

            # NRPN MSB=3, LSB=0 for trig note
            output_port.send(mido.Message('control_change', control=99, value=3, channel=channel))
            output_port.send(mido.Message('control_change', control=98, value=0, channel=channel))
            output_port.send(mido.Message('control_change', control=6, value=note, channel=channel))
            output_port.send(mido.Message('control_change', control=38, value=0, channel=channel))

            return [TextContent(
                type="text",
                text=f"Set trig note to {note} on channel {channel+1}"
            )]

        elif name == "set_trig_velocity":
            velocity = arguments["velocity"]
            channel = arguments.get("channel", 1) - 1

            # NRPN MSB=3, LSB=1 for trig velocity
            output_port.send(mido.Message('control_change', control=99, value=3, channel=channel))
            output_port.send(mido.Message('control_change', control=98, value=1, channel=channel))
            output_port.send(mido.Message('control_change', control=6, value=velocity, channel=channel))
            output_port.send(mido.Message('control_change', control=38, value=0, channel=channel))

            return [TextContent(
                type="text",
                text=f"Set trig velocity to {velocity} on channel {channel+1}"
            )]

        elif name == "set_trig_length":
            length = arguments["length"]
            channel = arguments.get("channel", 1) - 1

            # NRPN MSB=3, LSB=2 for trig length
            output_port.send(mido.Message('control_change', control=99, value=3, channel=channel))
            output_port.send(mido.Message('control_change', control=98, value=2, channel=channel))
            output_port.send(mido.Message('control_change', control=6, value=length, channel=channel))
            output_port.send(mido.Message('control_change', control=38, value=0, channel=channel))

            return [TextContent(
                type="text",
                text=f"Set trig length to {length} on channel {channel+1}"
            )]

        elif name == "send_midi_start":
            # Send MIDI Start message (0xFA)
            msg = mido.Message('start')
            output_port.send(msg)

            return [TextContent(
                type="text",
                text="Sent MIDI Start - sequencer should start from beginning"
            )]

        elif name == "send_midi_stop":
            # Send MIDI Stop message (0xFC)
            msg = mido.Message('stop')
            output_port.send(msg)

            return [TextContent(
                type="text",
                text="Sent MIDI Stop - sequencer should stop"
            )]

        elif name == "send_midi_continue":
            # Send MIDI Continue message (0xFB)
            msg = mido.Message('continue')
            output_port.send(msg)

            return [TextContent(
                type="text",
                text="Sent MIDI Continue - sequencer should resume from current position"
            )]

        elif name == "send_song_position":
            position = arguments["position"]

            # Send MIDI Song Position Pointer (0xF2)
            # Position is in MIDI beats (16th notes)
            msg = mido.Message('songpos', pos=position)
            output_port.send(msg)

            return [TextContent(
                type="text",
                text=f"Sent Song Position Pointer to position {position} (16th note: {position}, bar: {position/16:.2f})"
            )]

        elif name == "play_with_clock":
            bars = arguments.get("bars", 4)
            bpm = arguments.get("bpm", 120)
            send_stop = arguments.get("send_stop", True)

            # Calculate timing
            # MIDI clock: 24 pulses per quarter note
            # At 4/4 time: 96 pulses per bar
            # Time between pulses = 60 / (bpm * 24)
            clock_interval = 60.0 / (bpm * 24)
            total_pulses = int(bars * 96)  # 96 pulses per bar in 4/4

            # Send Start message
            output_port.send(mido.Message('start'))

            # Use absolute timing to prevent drift
            import time
            start_time = time.time()

            # Send clock pulses with precise timing
            for i in range(total_pulses):
                output_port.send(mido.Message('clock'))

                # Calculate when next pulse should occur
                next_pulse_time = start_time + (i + 1) * clock_interval
                sleep_duration = next_pulse_time - time.time()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

            # Optionally send Stop
            if send_stop:
                output_port.send(mido.Message('stop'))
                status = "and stopped"
            else:
                status = "(still running)"

            return [TextContent(
                type="text",
                text=f"Played {bars} bars at {bpm} BPM {status}"
            )]

        elif name == "play_pattern_with_tracks":
            bars = arguments.get("bars", 4)
            bpm = arguments.get("bpm", 120)
            triggers = arguments["triggers"]
            send_stop = arguments.get("send_stop", True)

            # Calculate timing
            clock_interval = 60.0 / (bpm * 24)
            total_pulses = int(bars * 96)
            beat_duration = 60.0 / bpm  # Duration of one quarter note

            # Prepare trigger schedule: convert beats to pulse indices
            trigger_schedule = []
            for trigger in triggers:
                beat = trigger[0]
                track = trigger[1]
                velocity = trigger[2] if len(trigger) > 2 else 100
                pulse_index = int(beat * 24)  # 24 pulses per quarter note
                trigger_schedule.append((pulse_index, track, velocity))

            # Sort by pulse index
            trigger_schedule.sort(key=lambda x: x[0])

            # Send Start message
            output_port.send(mido.Message('start'))

            import time
            start_time = time.time()
            trigger_idx = 0

            # Send clock pulses and triggers
            for i in range(total_pulses):
                output_port.send(mido.Message('clock'))

                # Check if we need to send any triggers at this pulse
                while trigger_idx < len(trigger_schedule) and trigger_schedule[trigger_idx][0] == i:
                    pulse, track, velocity = trigger_schedule[trigger_idx]
                    note = track - 1  # Track 1-16 = note 0-15
                    output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=0))
                    # Schedule note off after short duration
                    asyncio.create_task(_delayed_note_off(note, 0.05, 0))
                    trigger_idx += 1

                # Calculate when next pulse should occur
                next_pulse_time = start_time + (i + 1) * clock_interval
                sleep_duration = next_pulse_time - time.time()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

            # Optionally send Stop
            if send_stop:
                output_port.send(mido.Message('stop'))
                status = "and stopped"
            else:
                status = "(still running)"

            return [TextContent(
                type="text",
                text=f"Played {bars} bars at {bpm} BPM with {len(triggers)} track triggers {status}"
            )]

        elif name == "play_pattern_with_melody":
            global last_melody
            bars = arguments.get("bars", 4)
            bpm = arguments.get("bpm", 120)
            notes = arguments["notes"]
            channel = arguments.get("channel", 1) - 1
            send_stop = arguments.get("send_stop", True)

            # Save to history for later export
            last_melody = {
                "bpm": bpm,
                "notes": notes,
                "channel": channel + 1  # Store as 1-based
            }

            # Calculate timing
            clock_interval = 60.0 / (bpm * 24)
            total_pulses = int(bars * 96)

            # Prepare note schedule: convert beats to pulse indices
            note_schedule = []
            for note_data in notes:
                beat = note_data[0]
                note = note_data[1]
                velocity = note_data[2] if len(note_data) > 2 else 100
                duration = note_data[3] if len(note_data) > 3 else 0.1
                pulse_index = int(beat * 24)
                note_schedule.append((pulse_index, note, velocity, duration))

            # Sort by pulse index
            note_schedule.sort(key=lambda x: x[0])

            # Send Start message
            output_port.send(mido.Message('start'))

            import time
            start_time = time.time()
            note_idx = 0

            # Send clock pulses and notes
            for i in range(total_pulses):
                output_port.send(mido.Message('clock'))

                # Check if we need to send any notes at this pulse
                while note_idx < len(note_schedule) and note_schedule[note_idx][0] == i:
                    pulse, note, velocity, duration = note_schedule[note_idx]
                    output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=channel))
                    # Schedule note off after duration
                    asyncio.create_task(_delayed_note_off(note, duration, channel))
                    note_idx += 1

                # Calculate when next pulse should occur
                next_pulse_time = start_time + (i + 1) * clock_interval
                sleep_duration = next_pulse_time - time.time()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

            # Optionally send Stop
            if send_stop:
                output_port.send(mido.Message('stop'))
                status = "and stopped"
            else:
                status = "(still running)"

            return [TextContent(
                type="text",
                text=f"Played {bars} bars at {bpm} BPM with {len(notes)} melody notes {status}"
            )]

        elif name == "play_pattern_with_loop":
            bars = arguments.get("bars", 4)
            bpm = arguments.get("bpm", 120)
            loop_notes = arguments["loop_notes"]
            loop_length = arguments.get("loop_length", 1)
            channel = arguments.get("channel", 1) - 1
            send_stop = arguments.get("send_stop", True)

            # Calculate timing
            clock_interval = 60.0 / (bpm * 24)
            total_pulses = int(bars * 96)
            loop_pulses = int(loop_length * 96)

            # Prepare loop schedule
            loop_schedule = []
            for note_data in loop_notes:
                beat_offset = note_data[0]
                note = note_data[1]
                velocity = note_data[2] if len(note_data) > 2 else 100
                pulse_offset = int(beat_offset * 24)
                loop_schedule.append((pulse_offset, note, velocity))

            # Sort by pulse offset
            loop_schedule.sort(key=lambda x: x[0])

            # Send Start message
            output_port.send(mido.Message('start'))

            import time
            start_time = time.time()

            # Send clock pulses and looped notes
            for i in range(total_pulses):
                output_port.send(mido.Message('clock'))

                # Calculate position within loop
                loop_position = i % loop_pulses

                # Check if we need to send any notes at this position in the loop
                for pulse_offset, note, velocity in loop_schedule:
                    if pulse_offset == loop_position:
                        output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=channel))
                        # Schedule note off after short duration
                        asyncio.create_task(_delayed_note_off(note, 0.05, channel))

                # Calculate when next pulse should occur
                next_pulse_time = start_time + (i + 1) * clock_interval
                sleep_duration = next_pulse_time - time.time()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

            # Optionally send Stop
            if send_stop:
                output_port.send(mido.Message('stop'))
                status = "and stopped"
            else:
                status = "(still running)"

            num_loops = bars / loop_length
            return [TextContent(
                type="text",
                text=f"Played {bars} bars at {bpm} BPM with {len(loop_notes)} notes looping every {loop_length} bar(s) ({num_loops:.1f} loops) {status}"
            )]

        elif name == "play_pattern_with_tracks_and_melody":
            bars = arguments.get("bars", 4)
            bpm = arguments.get("bpm", 120)
            track_triggers = arguments.get("track_triggers", [])
            melody_notes = arguments.get("melody_notes", [])
            channel = arguments.get("channel", 1) - 1
            midi_start_at_beat = arguments.get("midi_start_at_beat", 0)
            preroll_bars = arguments.get("preroll_bars", 0)
            send_stop = arguments.get("send_stop", True)

            # Calculate timing
            clock_interval = 60.0 / (bpm * 24)
            beat_duration = 60.0 / bpm
            total_pulses = int(bars * 96)
            start_pulse = int(midi_start_at_beat * 24)  # Pulse index for MIDI Start
            preroll_beats = preroll_bars * 4  # Convert bars to beats (4/4 time)

            # Prepare combined event schedule with all notes
            event_schedule = []

            # Add track triggers to schedule
            # Track triggers are NOT affected by preroll
            for trigger_data in track_triggers:
                beat = trigger_data[0]
                track = trigger_data[1]
                velocity = trigger_data[2] if len(trigger_data) > 2 else 100
                # Check if chromatic note is specified (4th parameter)
                if len(trigger_data) > 3:
                    note = trigger_data[3]  # Use chromatic note
                else:
                    note = track - 1  # Standard: Track 1-16 = note 0-15
                pulse_index = int(beat * 24)
                # Track triggers use channel 0 and default 0.05s duration
                event_schedule.append(("track", pulse_index, note, velocity, 0.05, 0))

            # Add melody notes to schedule
            # Melody notes ARE delayed by preroll
            for note_data in melody_notes:
                beat = note_data[0] + preroll_beats  # Add preroll offset
                note = note_data[1]
                velocity = note_data[2] if len(note_data) > 2 else 100
                duration = note_data[3] if len(note_data) > 3 else 0.1
                pulse_index = int(beat * 24)
                # Melody notes use specified channel
                event_schedule.append(("melody", pulse_index, note, velocity, duration, channel))

            # Sort all events by pulse index
            event_schedule.sort(key=lambda x: x[1])

            import time
            start_time = time.time()
            event_idx = 0
            midi_started = False

            # Process all pulses/beats
            for i in range(total_pulses):
                # Check if we should send MIDI Start at this pulse
                if i == start_pulse and not midi_started:
                    # Send Song Position Pointer if starting mid-sequence
                    if midi_start_at_beat > 0:
                        # SPP is in "MIDI beats" (16th notes), so 1 quarter note = 4 MIDI beats
                        spp_position = int(midi_start_at_beat * 4)
                        output_port.send(mido.Message('songpos', pos=spp_position))
                    output_port.send(mido.Message('start'))
                    midi_started = True

                # Send MIDI Clock only if we've started
                if midi_started:
                    output_port.send(mido.Message('clock'))

                # Check if we need to send any events at this pulse
                while event_idx < len(event_schedule) and event_schedule[event_idx][1] == i:
                    event_type, pulse, note, velocity, duration, ch = event_schedule[event_idx]
                    output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=ch))
                    # Schedule note off after duration
                    asyncio.create_task(_delayed_note_off(note, duration, ch))
                    event_idx += 1

                # Calculate when next pulse should occur
                next_pulse_time = start_time + (i + 1) * clock_interval
                sleep_duration = next_pulse_time - time.time()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

            # Optionally send Stop (only if we actually started)
            if send_stop and midi_started:
                output_port.send(mido.Message('stop'))
                status = "and stopped"
            elif midi_started:
                status = "(still running)"
            else:
                status = "(no MIDI Start sent - all notes before midi_start_at_beat)"

            count_in_info = f" (MIDI Start at beat {midi_start_at_beat})" if midi_start_at_beat > 0 else ""
            return [TextContent(
                type="text",
                text=f"Played {bars} bars at {bpm} BPM with {len(track_triggers)} track triggers and {len(melody_notes)} melody notes{count_in_info} {status}"
            )]

        elif name == "play_pattern_with_multi_channel_midi":
            bars = arguments.get("bars", 4)
            bpm = arguments.get("bpm", 120)
            track_triggers = arguments.get("track_triggers", [])
            midi_channels = arguments.get("midi_channels", {})
            send_clock = arguments.get("send_clock", True)
            midi_start_at_beat = arguments.get("midi_start_at_beat", 0)
            preroll_bars = arguments.get("preroll_bars", 0)
            send_stop = arguments.get("send_stop", True)

            # Calculate timing
            clock_interval = 60.0 / (bpm * 24)
            beat_duration = 60.0 / bpm
            total_pulses = int(bars * 96)
            start_pulse = int(midi_start_at_beat * 24)  # Pulse index for MIDI Start
            preroll_beats = preroll_bars * 4  # Convert bars to beats (4/4 time)

            # Prepare combined event schedule with all notes from all channels
            event_schedule = []

            # Add track triggers to schedule
            # Track triggers are NOT affected by preroll
            for trigger_data in track_triggers:
                beat = trigger_data[0]
                track = trigger_data[1]
                velocity = trigger_data[2] if len(trigger_data) > 2 else 100
                # Check if chromatic note is specified (4th parameter)
                if len(trigger_data) > 3:
                    note = trigger_data[3]  # Use chromatic note
                else:
                    note = track - 1  # Standard: Track 1-16 = note 0-15
                pulse_index = int(beat * 24)
                # Track triggers use channel 0 and default 0.05s duration
                event_schedule.append(("track", pulse_index, note, velocity, 0.05, 0))

            # Add MIDI notes from each channel
            # MIDI notes ARE delayed by preroll
            total_midi_notes = 0
            for channel_str, notes in midi_channels.items():
                channel = int(channel_str) - 1  # Convert to 0-based MIDI channel
                if channel < 0 or channel > 15:
                    continue  # Skip invalid channels

                for note_data in notes:
                    beat = note_data[0] + preroll_beats  # Add preroll offset
                    note = note_data[1]
                    velocity = note_data[2] if len(note_data) > 2 else 100
                    duration = note_data[3] if len(note_data) > 3 else 0.1
                    pulse_index = int(beat * 24)
                    event_schedule.append(("midi", pulse_index, note, velocity, duration, channel))
                    total_midi_notes += 1

            # Sort all events by pulse index
            event_schedule.sort(key=lambda x: x[1])

            import time
            start_time = time.time()
            event_idx = 0
            midi_started = False

            # Process all pulses/beats
            for i in range(total_pulses):
                # Check if we should send MIDI Start at this pulse
                if i == start_pulse and not midi_started:
                    # Send Song Position Pointer if starting mid-sequence
                    if midi_start_at_beat > 0:
                        # SPP is in "MIDI beats" (16th notes), so 1 quarter note = 4 MIDI beats
                        spp_position = int(midi_start_at_beat * 4)
                        output_port.send(mido.Message('songpos', pos=spp_position))
                    output_port.send(mido.Message('start'))
                    midi_started = True

                # Send MIDI Clock only if we've started and send_clock is True
                if midi_started and send_clock:
                    output_port.send(mido.Message('clock'))

                # Check if we need to send any events at this pulse
                while event_idx < len(event_schedule) and event_schedule[event_idx][1] == i:
                    event_type, pulse, note, velocity, duration, ch = event_schedule[event_idx]
                    output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=ch))
                    # Schedule note off after duration
                    asyncio.create_task(_delayed_note_off(note, duration, ch))
                    event_idx += 1

                # Calculate when next pulse should occur
                next_pulse_time = start_time + (i + 1) * clock_interval
                sleep_duration = next_pulse_time - time.time()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

            # Optionally send Stop (only if we actually started)
            if send_stop and midi_started:
                output_port.send(mido.Message('stop'))
                status = "and stopped"
            elif midi_started:
                status = "(still running)"
            else:
                status = "(no MIDI Start sent - all notes before midi_start_at_beat)"

            num_channels = len(midi_channels)
            count_in_info = f" (MIDI Start at beat {midi_start_at_beat})" if midi_start_at_beat > 0 else ""
            return [TextContent(
                type="text",
                text=f"Played {bars} bars at {bpm} BPM with {len(track_triggers)} track triggers and {total_midi_notes} MIDI notes across {num_channels} channels{count_in_info} {status}"
            )]

        elif name == "save_last_melody":
            filename = arguments["filename"]

            if not last_melody:
                return [TextContent(
                    type="text",
                    text="Error: No melody to save. Use play_pattern_with_melody first."
                )]

            # Create a MIDI file
            mid = mido.MidiFile(ticks_per_beat=480)
            track = mido.MidiTrack()
            mid.tracks.append(track)

            # Set tempo
            bpm = last_melody["bpm"]
            tempo = mido.bpm2tempo(bpm)
            track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))

            # Add notes
            notes = last_melody["notes"]
            channel = last_melody["channel"] - 1  # Convert back to 0-based

            # Convert notes to MIDI messages with delta times
            # Notes format: [beat, note, velocity, duration]
            events = []
            for note_data in notes:
                beat = note_data[0]
                note = note_data[1]
                velocity = note_data[2] if len(note_data) > 2 else 100
                duration = note_data[3] if len(note_data) > 3 else 0.1

                # Convert beat to ticks (480 ticks per quarter note)
                tick_start = int(beat * 480)
                tick_duration = int((duration / (60.0 / bpm)) * 480)  # Convert seconds to ticks

                events.append(("on", tick_start, note, velocity, channel))
                events.append(("off", tick_start + tick_duration, note, 0, channel))

            # Sort events by time
            events.sort(key=lambda x: x[1])

            # Convert absolute times to delta times
            current_time = 0
            for event_type, tick_time, note, velocity, ch in events:
                delta_time = tick_time - current_time

                if event_type == "on":
                    track.append(mido.Message('note_on', note=note, velocity=velocity, channel=ch, time=delta_time))
                else:
                    track.append(mido.Message('note_off', note=note, velocity=velocity, channel=ch, time=delta_time))

                current_time = tick_time

            # Add end of track
            track.append(mido.MetaMessage('end_of_track', time=0))

            # Save to file
            try:
                mid.save(filename)
                return [TextContent(
                    type="text",
                    text=f"Saved melody to {filename} ({len(notes)} notes at {bpm} BPM)"
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error saving MIDI file: {str(e)}"
                )]

        elif name == "send_filter_sweep":
            import math

            start_value = arguments["start_value"]
            end_value = arguments["end_value"]
            duration_sec = arguments["duration_sec"]
            curve = arguments.get("curve", "linear")
            steps = arguments.get("steps", 50)
            channel = arguments.get("channel", 1) - 1

            # Calculate step interval
            interval = duration_sec / steps

            # Generate sweep values based on curve type
            values = []
            for i in range(steps + 1):
                # Normalized position (0.0 to 1.0)
                t = i / steps

                if curve == "linear":
                    # Linear interpolation
                    value = start_value + (end_value - start_value) * t
                elif curve == "exponential":
                    # Exponential curve (fast start, slow end)
                    value = start_value + (end_value - start_value) * (1 - math.exp(-3 * t))
                elif curve == "logarithmic":
                    # Logarithmic curve (slow start, fast end)
                    value = start_value + (end_value - start_value) * math.exp(3 * (t - 1))

                values.append(int(round(value)))

            # Send CC messages with timing
            import time
            start_time = time.time()

            for i, value in enumerate(values):
                # Send CC 74 (filter cutoff)
                msg = mido.Message('control_change', control=74, value=value, channel=channel)
                output_port.send(msg)

                # Calculate when next message should be sent
                if i < len(values) - 1:
                    next_time = start_time + (i + 1) * interval
                    sleep_duration = next_time - time.time()
                    if sleep_duration > 0:
                        await asyncio.sleep(sleep_duration)

            return [TextContent(
                type="text",
                text=f"Sent filter sweep from {start_value} to {end_value} over {duration_sec}s ({curve} curve, {steps} steps) on channel {channel+1}"
            )]

        elif name == "send_filter_envelope":
            attack_sec = arguments["attack_sec"]
            decay_sec = arguments["decay_sec"]
            sustain_level = arguments["sustain_level"]
            release_sec = arguments["release_sec"]
            steps_per_stage = arguments.get("steps_per_stage", 20)
            channel = arguments.get("channel", 1) - 1

            # Build envelope stages
            stages = []

            # Attack: 0 -> 127
            attack_interval = attack_sec / steps_per_stage
            for i in range(steps_per_stage + 1):
                t = i / steps_per_stage
                value = int(round(127 * t))
                stages.append((attack_interval, value))

            # Decay: 127 -> sustain_level
            decay_interval = decay_sec / steps_per_stage
            for i in range(1, steps_per_stage + 1):
                t = i / steps_per_stage
                value = int(round(127 + (sustain_level - 127) * t))
                stages.append((decay_interval, value))

            # Sustain: hold at sustain_level (no delay, just one message)
            stages.append((0, sustain_level))

            # Release: sustain_level -> 0
            release_interval = release_sec / steps_per_stage
            for i in range(1, steps_per_stage + 1):
                t = i / steps_per_stage
                value = int(round(sustain_level * (1 - t)))
                stages.append((release_interval, value))

            # Send CC messages with timing
            import time
            start_time = time.time()
            current_time = 0

            for i, (interval, value) in enumerate(stages):
                # Send CC 74 (filter cutoff)
                msg = mido.Message('control_change', control=74, value=value, channel=channel)
                output_port.send(msg)

                # Wait for interval
                if interval > 0 and i < len(stages) - 1:
                    current_time += interval
                    next_time = start_time + current_time
                    sleep_duration = next_time - time.time()
                    if sleep_duration > 0:
                        await asyncio.sleep(sleep_duration)

            total_time = attack_sec + decay_sec + release_sec
            return [TextContent(
                type="text",
                text=f"Sent filter ADSR envelope: A={attack_sec}s D={decay_sec}s S={sustain_level} R={release_sec}s (total {total_time:.2f}s) on channel {channel+1}"
            )]

        elif name == "play_with_filter_automation":
            bars = arguments.get("bars", 4)
            bpm = arguments.get("bpm", 120)
            track_triggers = arguments.get("track_triggers", [])
            filter_events = arguments["filter_events"]
            send_clock = arguments.get("send_clock", True)
            send_stop = arguments.get("send_stop", True)
            channel = arguments.get("channel", 1) - 1

            # Calculate timing
            clock_interval = 60.0 / (bpm * 24)
            total_pulses = int(bars * 96)

            # Prepare track trigger schedule
            trigger_schedule = []
            for trigger in track_triggers:
                beat = trigger[0]
                track = trigger[1]
                velocity = trigger[2] if len(trigger) > 2 else 100
                pulse_index = int(beat * 24)
                note = track - 1  # Track 1-16 = note 0-15
                trigger_schedule.append((pulse_index, note, velocity))
            trigger_schedule.sort(key=lambda x: x[0])

            # Prepare filter event schedule
            filter_schedule = []
            for event in filter_events:
                beat = event[0]
                cutoff = event[1]
                pulse_index = int(beat * 24)
                filter_schedule.append((pulse_index, cutoff))
            filter_schedule.sort(key=lambda x: x[0])

            # Send Start if requested
            if send_clock:
                output_port.send(mido.Message('start'))

            import time
            start_time = time.time()
            trigger_idx = 0
            filter_idx = 0

            # Send clock pulses, triggers, and filter automation
            for i in range(total_pulses):
                # Send clock if requested
                if send_clock:
                    output_port.send(mido.Message('clock'))

                # Check for track triggers at this pulse
                while trigger_idx < len(trigger_schedule) and trigger_schedule[trigger_idx][0] == i:
                    pulse, note, velocity = trigger_schedule[trigger_idx]
                    output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=0))
                    asyncio.create_task(_delayed_note_off(note, 0.05, 0))
                    trigger_idx += 1

                # Check for filter events at this pulse
                while filter_idx < len(filter_schedule) and filter_schedule[filter_idx][0] == i:
                    pulse, cutoff = filter_schedule[filter_idx]
                    output_port.send(mido.Message('control_change', control=74, value=cutoff, channel=channel))
                    filter_idx += 1

                # Calculate when next pulse should occur
                next_pulse_time = start_time + (i + 1) * clock_interval
                sleep_duration = next_pulse_time - time.time()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

            # Send Stop if requested
            if send_clock and send_stop:
                output_port.send(mido.Message('stop'))
                status = "and stopped"
            elif send_clock:
                status = "(still running)"
            else:
                status = "(no transport control)"

            return [TextContent(
                type="text",
                text=f"Played {bars} bars at {bpm} BPM with {len(track_triggers)} track triggers and {len(filter_events)} filter events {status}"
            )]

        elif name == "send_parameter_sweep":
            import math

            parameter = arguments["parameter"]
            start_value = arguments["start_value"]
            end_value = arguments["end_value"]
            duration_sec = arguments["duration_sec"]
            curve = arguments.get("curve", "linear")
            steps = arguments.get("steps", 50)
            channel = arguments.get("channel", 1) - 1

            # Validate parameter
            is_valid, error_msg = validate_parameter(parameter, start_value)
            if not is_valid:
                return [TextContent(type="text", text=f"Error: {error_msg}")]
            is_valid, error_msg = validate_parameter(parameter, end_value)
            if not is_valid:
                return [TextContent(type="text", text=f"Error: {error_msg}")]

            # Calculate step interval
            interval = duration_sec / steps

            # Generate sweep values based on curve type
            values = []
            for i in range(steps + 1):
                t = i / steps

                if curve == "linear":
                    value = start_value + (end_value - start_value) * t
                elif curve == "exponential":
                    value = start_value + (end_value - start_value) * (1 - math.exp(-3 * t))
                elif curve == "logarithmic":
                    value = start_value + (end_value - start_value) * math.exp(3 * (t - 1))

                values.append(int(round(value)))

            # Send parameter changes with timing
            import time
            start_time = time.time()

            for i, value in enumerate(values):
                send_parameter_change(parameter, value, channel)

                if i < len(values) - 1:
                    next_time = start_time + (i + 1) * interval
                    sleep_duration = next_time - time.time()
                    if sleep_duration > 0:
                        await asyncio.sleep(sleep_duration)

            return [TextContent(
                type="text",
                text=f"Sent {parameter} sweep from {start_value} to {end_value} over {duration_sec}s ({curve} curve, {steps} steps) on channel {channel+1}"
            )]

        elif name == "send_parameter_envelope":
            parameter = arguments["parameter"]
            attack_sec = arguments["attack_sec"]
            decay_sec = arguments["decay_sec"]
            sustain_level = arguments["sustain_level"]
            release_sec = arguments["release_sec"]
            steps_per_stage = arguments.get("steps_per_stage", 20)
            channel = arguments.get("channel", 1) - 1

            # Validate parameter
            is_valid, error_msg = validate_parameter(parameter, sustain_level)
            if not is_valid:
                return [TextContent(type="text", text=f"Error: {error_msg}")]

            # Build envelope stages
            stages = []

            # Attack: 0 -> 127
            attack_interval = attack_sec / steps_per_stage
            for i in range(steps_per_stage + 1):
                t = i / steps_per_stage
                value = int(round(127 * t))
                stages.append((attack_interval, value))

            # Decay: 127 -> sustain_level
            decay_interval = decay_sec / steps_per_stage
            for i in range(1, steps_per_stage + 1):
                t = i / steps_per_stage
                value = int(round(127 + (sustain_level - 127) * t))
                stages.append((decay_interval, value))

            # Sustain: hold at sustain_level
            stages.append((0, sustain_level))

            # Release: sustain_level -> 0
            release_interval = release_sec / steps_per_stage
            for i in range(1, steps_per_stage + 1):
                t = i / steps_per_stage
                value = int(round(sustain_level * (1 - t)))
                stages.append((release_interval, value))

            # Send parameter changes with timing
            import time
            start_time = time.time()
            current_time = 0

            for i, (interval, value) in enumerate(stages):
                send_parameter_change(parameter, value, channel)

                if interval > 0 and i < len(stages) - 1:
                    current_time += interval
                    next_time = start_time + current_time
                    sleep_duration = next_time - time.time()
                    if sleep_duration > 0:
                        await asyncio.sleep(sleep_duration)

            total_time = attack_sec + decay_sec + release_sec
            return [TextContent(
                type="text",
                text=f"Sent {parameter} ADSR envelope: A={attack_sec}s D={decay_sec}s S={sustain_level} R={release_sec}s (total {total_time:.2f}s) on channel {channel+1}"
            )]

        elif name == "play_pattern_with_parameter_automation":
            bars = arguments.get("bars", 4)
            bpm = arguments.get("bpm", 120)
            track_triggers = arguments.get("track_triggers", [])
            parameter_automation = arguments["parameter_automation"]
            send_clock = arguments.get("send_clock", True)
            send_stop = arguments.get("send_stop", True)
            channel = arguments.get("channel", 1) - 1

            # Validate all parameters
            for param_name, events in parameter_automation.items():
                param_info = get_parameter_info(param_name)
                if not param_info:
                    return [TextContent(type="text", text=f"Error: Unknown parameter '{param_name}'")]
                for beat, value in events:
                    is_valid, error_msg = validate_parameter(param_name, value)
                    if not is_valid:
                        return [TextContent(type="text", text=f"Error: {error_msg}")]

            # Calculate timing
            clock_interval = 60.0 / (bpm * 24)
            total_pulses = int(bars * 96)

            # Prepare track trigger schedule
            trigger_schedule = []
            for trigger in track_triggers:
                beat = trigger[0]
                track = trigger[1]
                velocity = trigger[2] if len(trigger) > 2 else 100
                pulse_index = int(beat * 24)
                note = track - 1
                trigger_schedule.append((pulse_index, note, velocity))
            trigger_schedule.sort(key=lambda x: x[0])

            # Prepare parameter automation schedules (one per parameter)
            param_schedules = {}
            for param_name, events in parameter_automation.items():
                schedule = []
                for beat, value in events:
                    pulse_index = int(beat * 24)
                    schedule.append((pulse_index, value))
                schedule.sort(key=lambda x: x[0])
                param_schedules[param_name] = schedule

            # Send Start if requested
            if send_clock:
                output_port.send(mido.Message('start'))

            import time
            start_time = time.time()
            trigger_idx = 0
            param_indices = {param_name: 0 for param_name in param_schedules.keys()}

            # Send clock pulses, triggers, and parameter automation
            for i in range(total_pulses):
                # Send clock if requested
                if send_clock:
                    output_port.send(mido.Message('clock'))

                # Check for track triggers at this pulse
                while trigger_idx < len(trigger_schedule) and trigger_schedule[trigger_idx][0] == i:
                    pulse, note, velocity = trigger_schedule[trigger_idx]
                    output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=0))
                    asyncio.create_task(_delayed_note_off(note, 0.05, 0))
                    trigger_idx += 1

                # Check for parameter events at this pulse
                for param_name, schedule in param_schedules.items():
                    param_idx = param_indices[param_name]
                    while param_idx < len(schedule) and schedule[param_idx][0] == i:
                        pulse, value = schedule[param_idx]
                        send_parameter_change(param_name, value, channel)
                        param_idx += 1
                    param_indices[param_name] = param_idx

                # Calculate when next pulse should occur
                next_pulse_time = start_time + (i + 1) * clock_interval
                sleep_duration = next_pulse_time - time.time()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

            # Send Stop if requested
            if send_clock and send_stop:
                output_port.send(mido.Message('stop'))
                status = "and stopped"
            elif send_clock:
                status = "(still running)"
            else:
                status = "(no transport control)"

            total_events = sum(len(events) for events in parameter_automation.values())
            param_list = ", ".join(parameter_automation.keys())
            return [TextContent(
                type="text",
                text=f"Played {bars} bars at {bpm} BPM with {len(track_triggers)} track triggers and {total_events} parameter events ({param_list}) {status}"
            )]

        elif name == "save_automation_preset":
            preset_name = arguments["preset_name"]
            automation = arguments["automation"]
            description = arguments.get("description", "")

            # Ensure preset name doesn't have .json extension
            if preset_name.endswith('.json'):
                preset_name = preset_name[:-5]

            preset_file = PRESET_DIR / f"{preset_name}.json"

            preset_data = {
                "name": preset_name,
                "description": description,
                "automation": automation
            }

            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)

            return [TextContent(
                type="text",
                text=f"Saved automation preset '{preset_name}' to {preset_file}"
            )]

        elif name == "load_automation_preset":
            preset_name = arguments["preset_name"]
            play = arguments.get("play", False)

            # Ensure preset name doesn't have .json extension
            if preset_name.endswith('.json'):
                preset_name = preset_name[:-5]

            preset_file = PRESET_DIR / f"{preset_name}.json"

            if not preset_file.exists():
                return [TextContent(
                    type="text",
                    text=f"Error: Preset '{preset_name}' not found at {preset_file}"
                )]

            with open(preset_file, 'r') as f:
                preset_data = json.load(f)

            automation = preset_data.get("automation", {})

            if play:
                # Play the loaded preset
                result_text = f"Loaded and playing preset '{preset_name}'\n"
                result_text += f"Description: {preset_data.get('description', 'N/A')}\n"

                # Call play_pattern_with_parameter_automation recursively
                play_result = await call_tool("play_pattern_with_parameter_automation", automation)
                result_text += play_result[0].text

                return [TextContent(type="text", text=result_text)]
            else:
                return [TextContent(
                    type="text",
                    text=f"Loaded preset '{preset_name}'\nDescription: {preset_data.get('description', 'N/A')}\nAutomation data: {json.dumps(automation, indent=2)}"
                )]

        elif name == "list_automation_presets":
            preset_files = list(PRESET_DIR.glob("*.json"))

            if not preset_files:
                return [TextContent(
                    type="text",
                    text=f"No presets found in {PRESET_DIR}"
                )]

            result = f"Available automation presets ({len(preset_files)}):\n\n"

            for preset_file in sorted(preset_files):
                try:
                    with open(preset_file, 'r') as f:
                        preset_data = json.load(f)
                    name = preset_data.get("name", preset_file.stem)
                    description = preset_data.get("description", "No description")
                    result += f"- {name}: {description}\n"
                except Exception as e:
                    result += f"- {preset_file.stem}: (Error loading: {e})\n"

            result += f"\nPresets stored in: {PRESET_DIR}"

            return [TextContent(type="text", text=result)]

        elif name == "export_automation_to_midi":
            filename = arguments["filename"]
            automation = arguments["automation"]
            channel = arguments.get("channel", 1) - 1

            # Ensure filename has .mid extension
            if not filename.endswith('.mid'):
                filename += '.mid'

            parameter_automation = automation.get("parameter_automation", {})
            bars = automation.get("bars", 4)
            bpm = automation.get("bpm", 120)

            # Create MIDI file
            mid = mido.MidiFile()
            track = mido.MidiTrack()
            mid.tracks.append(track)

            # Set tempo
            tempo = mido.bpm2tempo(bpm)
            track.append(mido.MetaMessage('set_tempo', tempo=tempo))

            # Convert parameter automation to MIDI messages
            # Collect all events with their timing
            events = []

            for param_name, param_events in parameter_automation.items():
                param_info = get_parameter_info(param_name)
                if not param_info:
                    continue

                for beat, value in param_events:
                    # Convert beat to ticks (480 ticks per beat is standard)
                    ticks = int(beat * 480)

                    if param_info["type"] == "cc":
                        events.append((ticks, 'cc', param_info["cc"], value))
                    elif param_info["type"] == "nrpn":
                        events.append((ticks, 'nrpn', param_info["msb"], param_info["lsb"], value))

            # Sort events by time
            events.sort(key=lambda x: x[0])

            # Add events to track with delta times
            last_ticks = 0
            for event in events:
                if event[1] == 'cc':
                    ticks, _, cc, value = event
                    delta = ticks - last_ticks
                    track.append(mido.Message('control_change', control=cc, value=value, channel=channel, time=delta))
                    last_ticks = ticks
                elif event[1] == 'nrpn':
                    ticks, _, msb, lsb, value = event
                    delta = ticks - last_ticks
                    # NRPN requires 4 CC messages
                    track.append(mido.Message('control_change', control=99, value=msb, channel=channel, time=delta))
                    track.append(mido.Message('control_change', control=98, value=lsb, channel=channel, time=0))
                    track.append(mido.Message('control_change', control=6, value=value, channel=channel, time=0))
                    track.append(mido.Message('control_change', control=38, value=0, channel=channel, time=0))
                    last_ticks = ticks

            # Save MIDI file
            mid.save(filename)

            return [TextContent(
                type="text",
                text=f"Exported automation to MIDI file: {filename}\nBars: {bars}, BPM: {bpm}, Parameters: {', '.join(parameter_automation.keys())}"
            )]

        elif name == "export_pattern_to_midi":
            filename = arguments.get("filename")
            bpm = arguments.get("bpm", 120)
            bars = arguments.get("bars", 4)
            track_triggers = arguments.get("track_triggers", [])
            melody_notes = arguments.get("melody_notes", [])
            melody_channel = arguments.get("melody_channel", 1)

            try:
                if not filename.endswith('.mid'):
                    filename += '.mid'

                # Create MIDI file
                mid = mido.MidiFile()

                # Tempo track
                tempo_track = mido.MidiTrack()
                mid.tracks.append(tempo_track)
                tempo_track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
                tempo_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))

                # Convert beat duration to ticks (480 ticks per beat is standard)
                ticks_per_beat = mid.ticks_per_beat

                # Track 1: Drum triggers (on channel 1)
                if track_triggers:
                    drum_track = mido.MidiTrack()
                    mid.tracks.append(drum_track)
                    drum_track.append(mido.MetaMessage('track_name', name='Digitakt Drums'))

                    # Sort by beat time
                    sorted_triggers = sorted(track_triggers, key=lambda x: x[0])

                    current_tick = 0
                    for trigger in sorted_triggers:
                        beat = trigger[0]
                        track_num = trigger[1]
                        velocity = trigger[2]

                        # Check if chromatic (4th parameter is note)
                        if len(trigger) == 4:
                            note = trigger[3]  # Use provided note for chromatic
                        else:
                            note = track_num - 1  # Track triggers: Track 1 = note 0, etc.

                        # Calculate tick position
                        tick = int(beat * ticks_per_beat)
                        delta_time = tick - current_tick

                        # Note on
                        drum_track.append(mido.Message('note_on', channel=0, note=note, velocity=velocity, time=delta_time))
                        # Note off (100ms later)
                        note_off_ticks = int(0.1 * ticks_per_beat * bpm / 60)
                        drum_track.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=note_off_ticks))

                        current_tick = tick + note_off_ticks

                    # End of track
                    drum_track.append(mido.MetaMessage('end_of_track', time=0))

                # Track 2: Melody/chords
                if melody_notes:
                    melody_track = mido.MidiTrack()
                    mid.tracks.append(melody_track)
                    melody_track.append(mido.MetaMessage('track_name', name=f'Melody Ch{melody_channel}'))

                    # Sort by beat time
                    sorted_notes = sorted(melody_notes, key=lambda x: x[0])

                    current_tick = 0
                    for note_data in sorted_notes:
                        beat = note_data[0]
                        note = note_data[1]
                        velocity = note_data[2]
                        duration = note_data[3] if len(note_data) > 3 else 0.5

                        # Calculate tick positions
                        tick = int(beat * ticks_per_beat)
                        delta_time = tick - current_tick
                        duration_ticks = int(duration * ticks_per_beat * bpm / 60)

                        # Note on
                        melody_track.append(mido.Message('note_on', channel=melody_channel-1, note=note, velocity=velocity, time=delta_time))
                        # Note off
                        melody_track.append(mido.Message('note_off', channel=melody_channel-1, note=note, velocity=0, time=duration_ticks))

                        current_tick = tick + duration_ticks

                    # End of track
                    melody_track.append(mido.MetaMessage('end_of_track', time=0))

                # Save file
                mid.save(filename)

                track_count = (1 if track_triggers else 0) + (1 if melody_notes else 0)
                return [TextContent(
                    type="text",
                    text=f"Exported pattern to {filename}\n{bars} bars at {bpm} BPM\n{len(track_triggers)} drum triggers, {len(melody_notes)} melody notes\n{track_count} MIDI tracks created"
                )]

            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error exporting MIDI: {str(e)}"
                )]

        elif name == "list_parameters":
            category_filter = arguments.get("category")

            categories = get_parameters_by_category()

            if category_filter:
                if category_filter in categories:
                    params = categories[category_filter]
                    result = f"Parameters in category '{category_filter}' ({len(params)}):\n\n"
                    for param in params:
                        result += f"- {param}\n"
                else:
                    result = f"Error: Unknown category '{category_filter}'\n"
                    result += f"Available categories: {', '.join(categories.keys())}"
            else:
                result = "Available parameters by category:\n\n"
                for cat_name, params in categories.items():
                    result += f"{cat_name} ({len(params)}):\n"
                    for param in params:
                        result += f"  - {param}\n"
                    result += "\n"

                result += f"Total: {len(get_all_parameters())} parameters\n"
                result += f"\nUse 'category' parameter to filter by category."

            return [TextContent(type="text", text=result)]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="midi://ports",
            name="MIDI Ports",
            mimeType="application/json",
            description="List all available MIDI input and output ports"
        ),
        Resource(
            uri="midi://digitakt/status",
            name="Digitakt Connection Status",
            mimeType="text/plain",
            description="Current connection status to Digitakt MIDI ports"
        )
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource"""
    if uri == "midi://ports":
        import json
        ports = {
            "inputs": mido.get_input_names(),
            "outputs": mido.get_output_names()
        }
        return json.dumps(ports, indent=2)

    elif uri == "midi://digitakt/status":
        status = []
        status.append(f"Digitakt Port Name: {DIGITAKT_PORT_NAME}")
        status.append(f"Output Connected: {output_port is not None}")
        status.append(f"Input Connected: {input_port is not None}")

        if output_port:
            status.append(f"Output Port: {output_port.name}")
        if input_port:
            status.append(f"Input Port: {input_port.name}")

        return "\n".join(status)

    return f"Unknown resource: {uri}"

async def main():
    """Main entry point"""
    # Connect to MIDI first
    connect_midi()

    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
