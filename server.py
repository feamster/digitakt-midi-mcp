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
            description="Send a MIDI note on/off message to the Digitakt. Can play drums on specific tracks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note": {
                        "type": "integer",
                        "description": "MIDI note number (0-127). For Digitakt drums: 60=C3 (Track 1), 61=C#3 (Track 2), etc.",
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
