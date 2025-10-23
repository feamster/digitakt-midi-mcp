#!/usr/bin/env python3
"""
Test script for save_last_melody functionality
"""

import mido

# Test data - simulate a melody that was played
test_melody = {
    "bpm": 120,
    "notes": [
        [0, 60, 100, 0.2],    # C
        [1, 62, 100, 0.2],    # D
        [2, 64, 100, 0.2],    # E
        [3, 65, 100, 0.2],    # F
        [4, 67, 100, 0.2],    # G
        [5, 65, 100, 0.2],    # F
        [6, 64, 100, 0.2],    # E
        [7, 60, 100, 0.4],    # C
    ],
    "channel": 1
}

def save_melody_to_midi(melody, filename):
    """Save a melody to a MIDI file"""
    # Create a MIDI file
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    # Set tempo
    bpm = melody["bpm"]
    tempo = mido.bpm2tempo(bpm)
    track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))

    # Add notes
    notes = melody["notes"]
    channel = melody["channel"] - 1  # Convert to 0-based

    # Convert notes to MIDI messages with delta times
    events = []
    for note_data in notes:
        beat = note_data[0]
        note = note_data[1]
        velocity = note_data[2] if len(note_data) > 2 else 100
        duration = note_data[3] if len(note_data) > 3 else 0.1

        # Convert beat to ticks (480 ticks per quarter note)
        tick_start = int(beat * 480)
        tick_duration = int((duration / (60.0 / bpm)) * 480)

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
    mid.save(filename)
    return True

def test_save_melody():
    """Test saving a melody to MIDI file"""
    print("Testing save_last_melody functionality")
    print("=" * 60)

    filename = "test_melody.mid"
    print(f"\nSaving test melody to {filename}...")
    print(f"  BPM: {test_melody['bpm']}")
    print(f"  Notes: {len(test_melody['notes'])}")
    print(f"  Channel: {test_melody['channel']}")

    try:
        save_melody_to_midi(test_melody, filename)
        print(f"✓ Successfully saved to {filename}")

        # Verify by reading it back
        mid = mido.MidiFile(filename)
        print(f"\nVerifying MIDI file:")
        print(f"  Ticks per beat: {mid.ticks_per_beat}")
        print(f"  Number of tracks: {len(mid.tracks)}")

        note_count = 0
        for msg in mid.tracks[0]:
            if msg.type == 'note_on' and msg.velocity > 0:
                note_count += 1
        print(f"  Note on messages: {note_count}")

        if note_count == len(test_melody['notes']):
            print(f"\n✓ Test PASSED - All {note_count} notes saved correctly")
        else:
            print(f"\n✗ Test FAILED - Expected {len(test_melody['notes'])} notes, found {note_count}")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return True

if __name__ == "__main__":
    test_save_melody()
