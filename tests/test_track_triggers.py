#!/usr/bin/env python3
"""
Test script to verify track triggering on Digitakt II
Sends MIDI notes 0-7 to trigger tracks 1-8
"""

import mido
import time

def test_track_triggers():
    """Test triggering each track individually"""

    # Find Digitakt output port
    output_port = None
    for port_name in mido.get_output_names():
        if "Elektron Digitakt II" in port_name:
            output_port = mido.open_output(port_name)
            print(f"✓ Connected to MIDI output: {port_name}")
            break

    if not output_port:
        print("✗ Could not find Digitakt MIDI output port")
        return False

    try:
        print("\nTesting track triggers (MIDI notes 0-15)...")
        print("Make sure your Digitakt II has samples loaded on tracks 1-16!")
        print()

        # Test each track
        for track in range(1, 17):
            note = track - 1  # Track 1 = note 0, Track 2 = note 1, etc.

            print(f"Triggering Track {track:2d} (MIDI note {note:2d})...")

            # Send note on
            note_on = mido.Message('note_on', note=note, velocity=100)
            output_port.send(note_on)

            time.sleep(0.05)

            # Send note off
            note_off = mido.Message('note_off', note=note)
            output_port.send(note_off)

            time.sleep(0.3)  # Wait between triggers

        print("\n✓ Test complete!")
        print("\nDid you hear all 16 tracks trigger?")
        print("If not, check:")
        print("  - Tracks have samples loaded (or MIDI devices connected for MIDI tracks)")
        print("  - Track MIDI channels are set correctly (or use AUTO CHANNEL)")
        print("  - Digitakt II volume is up")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    finally:
        output_port.close()
        print("\nMIDI port closed.")

if __name__ == "__main__":
    print("Digitakt II Track Trigger Test")
    print("=" * 60)
    test_track_triggers()
