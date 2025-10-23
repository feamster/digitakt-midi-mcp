#!/usr/bin/env python3
"""
Test script to verify MIDI transport controls on Digitakt II
Tests Start, Stop, Continue, and Song Position messages
"""

import mido
import time

def test_transport_controls():
    """Test MIDI transport control messages"""

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
        print("\nTesting MIDI Transport Controls...")
        print("Make sure TRANSPORT RECEIVE is enabled in Digitakt MIDI SYNC settings!")
        print()

        # Test MIDI Start
        print("1. Sending MIDI Start...")
        msg = mido.Message('start')
        output_port.send(msg)
        print("   → Digitakt should start playing from the beginning")
        time.sleep(3)

        # Test MIDI Stop
        print("\n2. Sending MIDI Stop...")
        msg = mido.Message('stop')
        output_port.send(msg)
        print("   → Digitakt should stop playing")
        time.sleep(2)

        # Test Song Position (jump to bar 2)
        print("\n3. Sending Song Position to bar 2 (position 32)...")
        msg = mido.Message('songpos', pos=32)  # 32 16th notes = 2 bars in 4/4
        output_port.send(msg)
        print("   → Digitakt playhead should jump to bar 2")
        time.sleep(1)

        # Test MIDI Continue
        print("\n4. Sending MIDI Continue...")
        msg = mido.Message('continue')
        output_port.send(msg)
        print("   → Digitakt should resume playing from bar 2")
        time.sleep(3)

        # Test MIDI Stop again
        print("\n5. Sending MIDI Stop...")
        msg = mido.Message('stop')
        output_port.send(msg)
        print("   → Digitakt should stop playing")
        time.sleep(1)

        # Reset to beginning
        print("\n6. Sending Song Position to beginning (position 0)...")
        msg = mido.Message('songpos', pos=0)
        output_port.send(msg)
        print("   → Digitakt playhead should return to start")

        print("\n✓ Test complete!")
        print("\nDid the Digitakt respond to the transport messages?")
        print("If not, check:")
        print("  - TRANSPORT RECEIVE is enabled in Settings > MIDI Config > Sync")
        print("  - The Digitakt has a pattern loaded")
        print("  - You're listening for playback changes")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    finally:
        output_port.close()
        print("\nMIDI port closed.")

if __name__ == "__main__":
    print("Digitakt II MIDI Transport Control Test")
    print("=" * 60)
    test_transport_controls()
