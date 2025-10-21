#!/usr/bin/env python3
"""
Helper script to analyze SysEx (.syx) files from Elektron Transfer
Usage: python analyze_sysex.py <file.syx>
"""

import sys
import mido

def analyze_sysex_file(filepath):
    """Analyze a SysEx file and display its contents"""
    print(f"Analyzing: {filepath}")
    print("=" * 80)

    try:
        # Read the MIDI file
        mid = mido.MidiFile(filepath)

        sysex_count = 0

        for i, track in enumerate(mid.tracks):
            print(f"\nTrack {i}: {track.name}")
            print("-" * 80)

            for msg in track:
                if msg.type == 'sysex':
                    sysex_count += 1
                    data = msg.data

                    print(f"\nSysEx Message #{sysex_count}:")
                    print(f"  Length: {len(data)} bytes")

                    # Check if it's an Elektron message
                    if len(data) >= 3 and data[0:3] == [0x00, 0x20, 0x3C]:
                        print(f"  Manufacturer: Elektron (00 20 3C)")

                        if len(data) >= 4:
                            device_id = data[3]
                            print(f"  Device ID: 0x{device_id:02X}")

                        if len(data) >= 5:
                            command = data[4]
                            print(f"  Command: 0x{command:02X}")
                    else:
                        print(f"  Manufacturer: {' '.join([f'{b:02X}' for b in data[0:3]])}")

                    # Display first 32 bytes in hex
                    print(f"\n  Data (hex):")
                    for i in range(0, min(len(data), 64), 16):
                        chunk = data[i:i+16]
                        hex_str = " ".join([f"{b:02X}" for b in chunk])
                        ascii_str = "".join([chr(b) if 32 <= b < 127 else "." for b in chunk])
                        print(f"    {i:04X}: {hex_str:<48}  {ascii_str}")

                    if len(data) > 64:
                        print(f"    ... ({len(data) - 64} more bytes)")

                    # Full hex dump
                    print(f"\n  Full hex: F0 {' '.join([f'{b:02X}' for b in data])} F7")

        print(f"\n{'=' * 80}")
        print(f"Total SysEx messages: {sysex_count}")

    except Exception as e:
        print(f"Error reading file: {e}")
        print("\nTrying to read as raw SysEx file...")

        # Try reading as raw .syx file
        try:
            with open(filepath, 'rb') as f:
                data = f.read()

            print(f"File size: {len(data)} bytes")

            # Look for SysEx messages (F0 ... F7)
            i = 0
            msg_count = 0

            while i < len(data):
                if data[i] == 0xF0:  # SysEx start
                    # Find end
                    end = i + 1
                    while end < len(data) and data[end] != 0xF7:
                        end += 1

                    if end < len(data):
                        msg_count += 1
                        sysex_data = data[i+1:end]  # Exclude F0 and F7

                        print(f"\nSysEx Message #{msg_count}:")
                        print(f"  Offset: 0x{i:04X}")
                        print(f"  Length: {len(sysex_data)} bytes")

                        # Check manufacturer
                        if len(sysex_data) >= 3 and sysex_data[0:3] == bytes([0x00, 0x20, 0x3C]):
                            print(f"  Manufacturer: Elektron (00 20 3C)")
                            if len(sysex_data) >= 4:
                                print(f"  Device ID: 0x{sysex_data[3]:02X}")
                            if len(sysex_data) >= 5:
                                print(f"  Command: 0x{sysex_data[4]:02X}")

                        # Display first 64 bytes
                        print(f"\n  Data (hex):")
                        for j in range(0, min(len(sysex_data), 64), 16):
                            chunk = sysex_data[j:j+16]
                            hex_str = " ".join([f"{b:02X}" for b in chunk])
                            ascii_str = "".join([chr(b) if 32 <= b < 127 else "." for b in chunk])
                            print(f"    {j:04X}: {hex_str:<48}  {ascii_str}")

                        if len(sysex_data) > 64:
                            print(f"    ... ({len(sysex_data) - 64} more bytes)")

                        i = end + 1
                    else:
                        i += 1
                else:
                    i += 1

            print(f"\n{'=' * 80}")
            print(f"Total SysEx messages: {msg_count}")

        except Exception as e2:
            print(f"Error: {e2}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_sysex.py <file.syx>")
        print("\nThis script analyzes SysEx files saved from Elektron Transfer")
        print("and displays their structure to help understand the format.")
        sys.exit(1)

    analyze_sysex_file(sys.argv[1])
