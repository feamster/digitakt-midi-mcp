#!/usr/bin/env python3
"""
Test script for delayed MIDI Start functionality
Tests playing count-in without MIDI Start, then starting transport at specific beat
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

async def test_delayed_start():
    """Test delayed MIDI Start - count-in then start transport"""
    print("\n" + "="*70)
    print("TEST: Delayed MIDI Start")
    print("="*70)
    print("Workflow:")
    print("  1. Bars 1-4 (beats 0-15): Count-in clicks on track 15")
    print("     - NO MIDI Start sent")
    print("     - NO MIDI Clock sent")
    print("     - Only note triggers")
    print("     - User can arm recording during this time")
    print("  2. Beat 16 (start of bar 5): MIDI Start sent")
    print("     - MIDI Clock begins")
    print("     - Digitakt sequencer/recording starts")
    print("  3. Bars 5-12 (beats 16-47): Melody plays")
    print("     - MIDI Clock continues")
    print("     - Melody gets recorded on Digitakt")
    print()

    bars = 12
    bpm = 120
    midi_start_at_beat = 16  # Start MIDI transport at beat 16 (bar 5)

    # 4-bar count-in on track 15 (beats 0-15)
    track_triggers = []
    for beat in range(16):
        track_triggers.append([beat, 15, 100])

    # 8-bar melody (beats 16-47)
    melody_notes = []
    melody_beats = [
        # Simple repeating 4-note pattern
        60, 64, 67, 64,  # Bar 5
        60, 64, 67, 64,  # Bar 6
        62, 65, 69, 65,  # Bar 7
        62, 65, 69, 65,  # Bar 8
        64, 67, 71, 67,  # Bar 9
        64, 67, 71, 67,  # Bar 10
        65, 69, 72, 69,  # Bar 11
        60, 64, 67, 72,  # Bar 12 (ending)
    ]
    for i, midi_note in enumerate(melody_beats):
        beat = 16 + i  # Start at beat 16
        melody_notes.append([beat, midi_note, 85, 0.4])

    # Calculate timing
    clock_interval = 60.0 / (bpm * 24)
    total_pulses = int(bars * 96)
    start_pulse = int(midi_start_at_beat * 24)

    # Prepare event schedule
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
        event_schedule.append(("melody", pulse_index, note, velocity, duration, 0))

    # Sort all events
    event_schedule.sort(key=lambda x: x[1])

    print(f"Total events scheduled: {len(event_schedule)}")
    print(f"  - Count-in triggers (beats 0-15): {len(track_triggers)}")
    print(f"  - Melody notes (beats 16-47): {len(melody_notes)}")
    print(f"  - MIDI Start will be sent at beat {midi_start_at_beat} (pulse {start_pulse})")
    print()
    print("Starting playback...")
    print()

    start_time = time.time()
    event_idx = 0
    midi_started = False
    pre_start_notes = 0
    post_start_notes = 0

    # Process all pulses
    for i in range(total_pulses):
        # Check if we should send MIDI Start at this pulse
        if i == start_pulse and not midi_started:
            # Send Song Position Pointer if starting mid-sequence
            if midi_start_at_beat > 0:
                spp_position = int(midi_start_at_beat * 4)
                print(f">>> SONG POSITION POINTER set to {spp_position} (beat {midi_start_at_beat})")
                output_port.send(mido.Message('songpos', pos=spp_position))
            print(f">>> MIDI START sent at pulse {i} (beat {i/24:.1f})")
            output_port.send(mido.Message('start'))
            midi_started = True

        # Send MIDI Clock only if we've started
        if midi_started:
            output_port.send(mido.Message('clock'))

        # Check if we need to send any events at this pulse
        while event_idx < len(event_schedule) and event_schedule[event_idx][1] == i:
            event_type, pulse, note, velocity, duration, ch = event_schedule[event_idx]
            output_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=ch))
            asyncio.create_task(_delayed_note_off(note, duration, ch))

            if midi_started:
                post_start_notes += 1
            else:
                pre_start_notes += 1

            event_idx += 1

        # Calculate when next pulse should occur
        next_pulse_time = start_time + (i + 1) * clock_interval
        sleep_duration = next_pulse_time - time.time()

        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)

    # Send Stop
    output_port.send(mido.Message('stop'))
    print(f">>> MIDI STOP sent")
    print()

    print("✓ Playback complete!")
    print(f"  - Notes before MIDI Start: {pre_start_notes}")
    print(f"  - Notes after MIDI Start: {post_start_notes}")
    print(f"  - Total events: {pre_start_notes + post_start_notes}")
    print()

async def main():
    """Run the test"""
    print("Digitakt II Delayed MIDI Start Test")
    print("="*70)
    print("SETUP INSTRUCTIONS:")
    print("  1. Load a sample on track 15 (for count-in clicks)")
    print("  2. Set active track to a melodic sample")
    print("  3. Enable TRANSPORT RECEIVE in MIDI settings")
    print("  4. Enable CLOCK RECEIVE in MIDI settings")
    print("  5. Optionally: Arm live recording on Digitakt during count-in")
    print()
    print("EXPECTED BEHAVIOR:")
    print("  - Bars 1-4: You'll hear count-in clicks (no sequencer start)")
    print("  - Bar 5: Digitakt sequencer starts (MIDI Start sent)")
    print("  - Bars 5-12: Melody plays with MIDI Clock")
    print("  - If recording: melody will be captured to Digitakt")
    print()

    input("Press ENTER to start test...")

    await test_delayed_start()

    print("="*70)
    print("TEST VALIDATION:")
    print("="*70)
    print("Did you observe:")
    print("  ✓ Count-in clicks played WITHOUT starting Digitakt sequencer?")
    print("  ✓ Digitakt sequencer started at bar 5 (after count-in)?")
    print("  ✓ Melody played in sync with MIDI Clock?")
    print("  ✓ If recording armed: melody was recorded?")
    print()

    output_port.close()

if __name__ == "__main__":
    asyncio.run(main())
