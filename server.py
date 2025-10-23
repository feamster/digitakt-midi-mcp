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
from nrpn_constants import (
    NRPN_MSB, TrackParams, TrigParams, SourceParams,
    FilterParams, AmpParams, LFOParams, DelayParams, ReverbParams,
    get_param_name
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("digitakt-midi-server")

# MIDI port name - will be auto-detected
DIGITAKT_PORT_NAME = "Elektron Digitakt II"

# Create server instance
server = Server("digitakt-midi-server")

# Global MIDI port references
output_port: Optional[mido.ports.BaseOutput] = None
input_port: Optional[mido.ports.BaseInput] = None

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
                        "default": true
                    }
                }
            }
        )
    ]

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

            # Send clock pulses
            for i in range(total_pulses):
                output_port.send(mido.Message('clock'))
                await asyncio.sleep(clock_interval)

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
