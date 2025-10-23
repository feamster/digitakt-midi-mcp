#!/usr/bin/env python3
"""
Test script for play_pattern_with_tracks_and_melody function
Tests combining track triggers and melody notes in a single MIDI clock session
"""

import asyncio
import mido
import time

# Find Digitakt output port
output_port = None
for port_name in mido.get_output_names():
    if "Elektron Digitakt II" in port_name:
        output_port = mido.open_output(port_name)
        print(f"✓ Connected to MIDI output: {port_name}")
        break

if not output_port:
    print("✗ Could not find Digitakt MIDI output port")
    exit(1)

# Helper function for delayed note off
async def _delayed_note_off(note: int, duration: float, channel: int = 0):
    """Send note off after a delay"""
    await asyncio.sleep(duration)
    if output_port:
        output_port.send(mido.Message('note_off', note=note, velocity=0, channel=channel))

async def test_tracks_and_melody():
    """Test combining track triggers and melody notes"""
    print("\n" + "="*70)
    print("TEST: play_pattern_with_tracks_and_melody")
    print("="*70)
    print("Playing 5 bars at 120 BPM:")
    print("  - 1-bar count-in on track 15 (beats 0-3)")
    print("  - 4-bar melody (beats 4-19)")
    print()

    bars = 5
    bpm = 120

    # 1-bar count-in on track 15 (click track)
    track_triggers = [
        [0, 15, 100],   # beat 0, track 15, velocity 100
        [1, 15, 100],   # beat 1
        [2, 15, 100],   # beat 2
        [3, 15, 100],   # beat 3
    ]

    # 4-bar melody (simple ascending scale)
    melody_notes = [
        # Bar 2 (beats 4-7)
        [4, 60, 85, 0.4],    # C
        [5, 62, 80, 0.4],    # D
        [6, 64, 85, 0.4],    # E
        [7, 65, 80, 0.4],    # F
        # Bar 3 (beats 8-11)
        [8, 67, 85, 0.4],    # G
        [9, 69, 80, 0.4],    # A
        [10, 71, 85, 0.4],   # B
        [11, 72, 90, 0.4],   # C (octave)
        # Bar 4 (beats 12-15)
        [12, 71, 85, 0.4],   # B
        [13, 69, 80, 0.4],   # A
        [14, 67, 85, 0.4],   # G
        [15, 65, 80, 0.4],   # F
        # Bar 5 (beats 16-19)
        [16, 64, 85, 0.4],   # E
        [17, 62, 80, 0.4],   # D
        [18, 60, 85, 0.4],   # C
        [19, 60, 90, 0.8],   # C (longer)
    ]

    # Calculate timing
    clock_interval = 60.0 / (bpm * 24)
    total_pulses = int(bars * 96)
    channel = 0  # Use channel 0 for melody

    # Prepare combined event schedule
    event_schedule = []

    # Add track triggers
    for trigger_data in track_triggers:
        beat = trigger_data[0]
        track = trigger_data[1]
        velocity = trigger_data[2]
        pulse_index = int(beat * 24)
        note = track - 1  # Track 15 = note 14
        event_schedule.append(("track", pulse_index, note, velocity, 0.05, 0))

    # Add melody notes
    for note_data in melody_notes:
        beat = note_data[0]
        note = note_data[1]
        velocity = note_data[2]
        duration = note_data[3]
        pulse_index = int(beat * 24)
        event_schedule.append(("melody", pulse_index, note, velocity, duration, channel))

    # Sort all events by pulse index
    event_schedule.sort(key=lambda x: x[1])

    print(f"Total events scheduled: {len(event_schedule)}")
    print(f"  - Track triggers: {len(track_triggers)}")
    print(f"  - Melody notes: {len(melody_notes)}")
    print()

    # Send Start message
    output_port.send(mido.Message('start'))

    start_time = time.time()
    event_idx = 0
    trigger_count = 0
    melody_count = 0

    # Send clock pulses and all scheduled events
    for i in range(total_pulses):
        output_port.send(mido.Message('clock'))

        # Check if we need to send any events at this pulse
        while event_idx < len(event_schedule) and event_schedule[event_idx][1] == i:
            event_type, pulse, note, velocity, duration, ch = event_schedule[event_idx]
            output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=ch))
            asyncio.create_task(_delayed_note_off(note, duration, ch))

            if event_type == "track":
                trigger_count += 1
            else:
                melody_count += 1

            event_idx += 1

        # Calculate when next pulse should occur
        next_pulse_time = start_time + (i + 1) * clock_interval
        sleep_duration = next_pulse_time - time.time()

        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)

    # Send Stop
    output_port.send(mido.Message('stop'))

    print(f"✓ Playback complete!")
    print(f"  - Sent {trigger_count} track triggers")
    print(f"  - Sent {melody_count} melody notes")
    print(f"  - Total events: {trigger_count + melody_count}")
    print()

async def main():
    """Run the test"""
    print("Digitakt II play_pattern_with_tracks_and_melody Test")
    print("="*70)
    print("Make sure your Digitakt II has:")
    print("  - Sample loaded on track 15 (for count-in)")
    print("  - Active track set to a melodic sample")
    print("  - TRANSPORT RECEIVE enabled")
    print("  - CLOCK RECEIVE enabled")
    print()

    await test_tracks_and_melody()

    print("="*70)
    print("✓ Test complete!")
    print("="*70)
    print()
    print("Did you hear:")
    print("  1. Four count-in clicks on track 15?")
    print("  2. An ascending and descending scale melody?")
    print("  3. Both overlapping correctly?")
    print()

    output_port.close()

if __name__ == "__main__":
    asyncio.run(main())
