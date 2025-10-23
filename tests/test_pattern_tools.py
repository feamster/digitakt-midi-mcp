#!/usr/bin/env python3
"""
Test script for the new pattern + MIDI tools
Tests play_pattern_with_tracks, play_pattern_with_melody, play_pattern_with_loop
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

async def test_pattern_with_tracks():
    """Test play_pattern_with_tracks - trigger specific tracks at specific times"""
    print("\n" + "="*60)
    print("TEST 1: play_pattern_with_tracks")
    print("="*60)
    print("Playing 2 bars at 120 BPM with kick on beats 1 and 3")

    bars = 2
    bpm = 120
    # Triggers: [beat, track, velocity]
    # Beat 0 = start, Beat 1 = second quarter note, etc.
    triggers = [
        [0, 1, 100],   # Kick on beat 1
        [1, 1, 100],   # Kick on beat 2
        [2, 1, 100],   # Kick on beat 3
        [3, 1, 100],   # Kick on beat 4
        [4, 1, 100],   # Kick on beat 1 of bar 2
        [5, 1, 100],   # Kick on beat 2 of bar 2
        [6, 1, 100],   # Kick on beat 3 of bar 2
        [7, 1, 100],   # Kick on beat 4 of bar 2
    ]

    clock_interval = 60.0 / (bpm * 24)
    total_pulses = int(bars * 96)

    # Prepare trigger schedule
    trigger_schedule = []
    for trigger in triggers:
        beat = trigger[0]
        track = trigger[1]
        velocity = trigger[2]
        pulse_index = int(beat * 24)
        trigger_schedule.append((pulse_index, track, velocity))

    trigger_schedule.sort(key=lambda x: x[0])

    # Send Start
    output_port.send(mido.Message('start'))

    start_time = time.time()
    trigger_idx = 0

    # Send clock + triggers
    for i in range(total_pulses):
        output_port.send(mido.Message('clock'))

        while trigger_idx < len(trigger_schedule) and trigger_schedule[trigger_idx][0] == i:
            pulse, track, velocity = trigger_schedule[trigger_idx]
            note = track - 1
            output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=0))
            asyncio.create_task(_delayed_note_off(note, 0.05, 0))
            trigger_idx += 1

        next_pulse_time = start_time + (i + 1) * clock_interval
        sleep_duration = next_pulse_time - time.time()
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)

    output_port.send(mido.Message('stop'))
    print(f"✓ Played {bars} bars with {len(triggers)} track triggers")

async def test_pattern_with_melody():
    """Test play_pattern_with_melody - play melodic sequence on active track"""
    print("\n" + "="*60)
    print("TEST 2: play_pattern_with_melody")
    print("="*60)
    print("Playing 2 bars at 120 BPM with a simple melody")

    bars = 2
    bpm = 120
    channel = 0
    # Notes: [beat, note, velocity, duration]
    notes = [
        [0, 60, 100, 0.2],    # C
        [1, 62, 100, 0.2],    # D
        [2, 64, 100, 0.2],    # E
        [3, 65, 100, 0.2],    # F
        [4, 67, 100, 0.2],    # G
        [5, 65, 100, 0.2],    # F
        [6, 64, 100, 0.2],    # E
        [7, 60, 100, 0.4],    # C
    ]

    clock_interval = 60.0 / (bpm * 24)
    total_pulses = int(bars * 96)

    # Prepare note schedule
    note_schedule = []
    for note_data in notes:
        beat = note_data[0]
        note = note_data[1]
        velocity = note_data[2]
        duration = note_data[3]
        pulse_index = int(beat * 24)
        note_schedule.append((pulse_index, note, velocity, duration))

    note_schedule.sort(key=lambda x: x[0])

    # Send Start
    output_port.send(mido.Message('start'))

    start_time = time.time()
    note_idx = 0

    # Send clock + notes
    for i in range(total_pulses):
        output_port.send(mido.Message('clock'))

        while note_idx < len(note_schedule) and note_schedule[note_idx][0] == i:
            pulse, note, velocity, duration = note_schedule[note_idx]
            output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=channel))
            asyncio.create_task(_delayed_note_off(note, duration, channel))
            note_idx += 1

        next_pulse_time = start_time + (i + 1) * clock_interval
        sleep_duration = next_pulse_time - time.time()
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)

    output_port.send(mido.Message('stop'))
    print(f"✓ Played {bars} bars with {len(notes)} melody notes")

async def test_pattern_with_loop():
    """Test play_pattern_with_loop - continuously trigger notes on a loop"""
    print("\n" + "="*60)
    print("TEST 3: play_pattern_with_loop")
    print("="*60)
    print("Playing 4 bars at 120 BPM with a 1-bar loop")

    bars = 4
    bpm = 120
    loop_length = 1
    channel = 0
    # Loop notes: [beat_offset, note, velocity]
    # This creates a simple hi-hat pattern on track 3
    loop_notes = [
        [0, 2, 80],      # 8th notes on track 3
        [0.5, 2, 60],
        [1, 2, 80],
        [1.5, 2, 60],
        [2, 2, 80],
        [2.5, 2, 60],
        [3, 2, 80],
        [3.5, 2, 60],
    ]

    clock_interval = 60.0 / (bpm * 24)
    total_pulses = int(bars * 96)
    loop_pulses = int(loop_length * 96)

    # Prepare loop schedule
    loop_schedule = []
    for note_data in loop_notes:
        beat_offset = note_data[0]
        note = note_data[1]
        velocity = note_data[2]
        pulse_offset = int(beat_offset * 24)
        loop_schedule.append((pulse_offset, note, velocity))

    loop_schedule.sort(key=lambda x: x[0])

    # Send Start
    output_port.send(mido.Message('start'))

    start_time = time.time()

    # Send clock + looped notes
    for i in range(total_pulses):
        output_port.send(mido.Message('clock'))

        loop_position = i % loop_pulses

        for pulse_offset, note, velocity in loop_schedule:
            if pulse_offset == loop_position:
                output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=channel))
                asyncio.create_task(_delayed_note_off(note, 0.05, channel))

        next_pulse_time = start_time + (i + 1) * clock_interval
        sleep_duration = next_pulse_time - time.time()
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)

    output_port.send(mido.Message('stop'))
    num_loops = bars / loop_length
    print(f"✓ Played {bars} bars with {len(loop_notes)} notes looping every {loop_length} bar(s) ({num_loops:.1f} loops)")

async def main():
    """Run all tests"""
    print("Digitakt II Pattern + MIDI Tools Test")
    print("="*60)
    print("Make sure your Digitakt II has:")
    print("  - Samples loaded on tracks 1-3")
    print("  - TRANSPORT RECEIVE enabled")
    print("  - CLOCK RECEIVE enabled")
    print()

    await test_pattern_with_tracks()
    await asyncio.sleep(1)

    await test_pattern_with_melody()
    await asyncio.sleep(1)

    await test_pattern_with_loop()

    print("\n" + "="*60)
    print("✓ All tests complete!")
    print("="*60)

    output_port.close()

if __name__ == "__main__":
    asyncio.run(main())
