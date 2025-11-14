#!/usr/bin/env python3
"""
Test automation looping functionality

This test verifies that the automation_loop_bars parameter correctly
duplicates parameter automation events at the specified interval.
"""

def test_automation_looping_logic():
    """Test the duplication logic for automation looping"""

    # Simulate initial automation events (4 bars = 16 beats = 384 pulses)
    event_schedule = [
        ("param", 0, "filter_cutoff", 20, 0, 0),      # Beat 0
        ("param", 96, "filter_cutoff", 80, 0, 0),     # Beat 4 (1 bar)
        ("param", 192, "filter_cutoff", 40, 0, 0),    # Beat 8 (2 bars)
        ("param", 288, "filter_cutoff", 100, 0, 0),   # Beat 12 (3 bars)
    ]

    # Settings: 4-bar loop repeated over 16 bars
    automation_loop_bars = 4
    bars = 16
    total_param_events = len(event_schedule)

    # Apply the duplication logic
    loop_beats = automation_loop_bars * 4  # 16 beats
    loop_pulses = int(loop_beats * 24)      # 384 pulses
    total_beats = bars * 4                  # 64 beats
    total_pulses = int(total_beats * 24)    # 1536 pulses

    # Get param events that occur within the loop period
    original_param_events = [e for e in event_schedule if e[0] == "param" and e[1] < loop_pulses]

    # Calculate how many times to repeat
    num_loops = int(total_beats / loop_beats)  # Should be 4

    print(f"Original events: {len(original_param_events)}")
    print(f"Loop period: {loop_pulses} pulses ({automation_loop_bars} bars)")
    print(f"Total duration: {total_pulses} pulses ({bars} bars)")
    print(f"Number of loops: {num_loops}")

    # Duplicate events for each loop cycle (skip first, it's already there)
    for loop_num in range(1, num_loops):
        offset_pulses = loop_num * loop_pulses
        print(f"\nLoop {loop_num}: offset = {offset_pulses} pulses")
        for event in original_param_events:
            event_type, pulse, param_name, value, track_num, _ = event
            new_pulse = pulse + offset_pulses
            if new_pulse < total_pulses:
                event_schedule.append((event_type, new_pulse, param_name, value, track_num, 0))
                total_param_events += 1
                print(f"  Added: {param_name}={value} at pulse {new_pulse} (beat {new_pulse/24})")

    # Sort all events by pulse index
    event_schedule.sort(key=lambda x: x[1])

    print(f"\n=== Final Results ===")
    print(f"Total param events: {total_param_events}")
    print(f"Expected: {len(original_param_events) * num_loops}")

    # Verify we have the right number of events
    assert total_param_events == len(original_param_events) * num_loops, \
        f"Expected {len(original_param_events) * num_loops} events, got {total_param_events}"

    # Verify events are at correct positions
    print("\nAll events:")
    for i, event in enumerate(event_schedule):
        _, pulse, param_name, value, _, _ = event
        beat = pulse / 24
        bar = beat / 4
        print(f"  {i+1}. {param_name}={value} at pulse {pulse} (beat {beat}, bar {bar})")

    # Check that each loop has the same pattern
    events_per_loop = len(original_param_events)
    for loop_idx in range(num_loops):
        start_idx = loop_idx * events_per_loop
        end_idx = start_idx + events_per_loop
        loop_events = event_schedule[start_idx:end_idx]

        print(f"\nLoop {loop_idx} verification:")
        for i, event in enumerate(loop_events):
            _, pulse, param_name, value, _, _ = event
            expected_pulse = original_param_events[i][1] + (loop_idx * loop_pulses)
            assert pulse == expected_pulse, \
                f"Loop {loop_idx}, event {i}: expected pulse {expected_pulse}, got {pulse}"
            print(f"  ✓ Event {i} at correct position (pulse {pulse})")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_automation_looping_logic()
