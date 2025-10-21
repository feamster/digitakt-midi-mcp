#!/usr/bin/env python3
"""
Simple test script to verify MIDI connectivity with Digitakt II
"""

import mido
import time

def test_digitakt_connection():
    """Test basic MIDI connection and send a test note"""

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
        # Send a test note (C3 = note 60 = Track 1 on Digitakt)
        print("\nSending test note to Track 1 (kick)...")
        note_on = mido.Message('note_on', note=60, velocity=100)
        output_port.send(note_on)

        time.sleep(0.1)

        note_off = mido.Message('note_off', note=60)
        output_port.send(note_off)

        print("✓ Test note sent successfully!")
        print("\nIf you heard a sound from your Digitakt, the connection is working!")

        # Send a simple pattern
        print("\nSending a simple 4-step pattern...")
        for i in range(4):
            note_on = mido.Message('note_on', note=60, velocity=100)
            output_port.send(note_on)
            time.sleep(0.05)
            note_off = mido.Message('note_off', note=60)
            output_port.send(note_off)
            time.sleep(0.2)

        print("✓ Pattern sent successfully!")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    finally:
        output_port.close()
        print("\nMIDI port closed.")

if __name__ == "__main__":
    print("Digitakt II MIDI Test")
    print("=" * 40)
    test_digitakt_connection()
