#!/usr/bin/env python3
"""
Test script for filter sweep functionality
Tests the new filter automation tools added to the MCP server
"""

import asyncio
import mido
import sys
import os

# Add parent directory to path to import server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

async def test_linear_sweep():
    """Test 1: Linear sweep from 20 to 127 over 2 seconds"""
    print("\n=== Test 1: Linear Sweep (20 → 127 over 2s) ===")
    print("This should create a smooth, constant-rate filter opening")

    from mcp.types import TextContent

    result = await server.call_tool(
        "send_filter_sweep",
        {
            "start_value": 20,
            "end_value": 127,
            "duration_sec": 2.0,
            "curve": "linear",
            "steps": 50
        }
    )

    print(f"Result: {result[0].text}")
    await asyncio.sleep(0.5)  # Brief pause

async def test_exponential_sweep():
    """Test 2: Exponential sweep that opens quickly then slows"""
    print("\n=== Test 2: Exponential Sweep (0 → 127 over 3s) ===")
    print("This should open the filter quickly at first, then slow down")

    result = await server.call_tool(
        "send_filter_sweep",
        {
            "start_value": 0,
            "end_value": 127,
            "duration_sec": 3.0,
            "curve": "exponential",
            "steps": 60
        }
    )

    print(f"Result: {result[0].text}")
    await asyncio.sleep(0.5)

async def test_logarithmic_sweep():
    """Test 3: Logarithmic sweep that starts slow then speeds up"""
    print("\n=== Test 3: Logarithmic Sweep (127 → 0 over 2.5s) ===")
    print("This should close the filter slowly at first, then speed up")

    result = await server.call_tool(
        "send_filter_sweep",
        {
            "start_value": 127,
            "end_value": 0,
            "duration_sec": 2.5,
            "curve": "logarithmic",
            "steps": 50
        }
    )

    print(f"Result: {result[0].text}")
    await asyncio.sleep(0.5)

async def test_filter_envelope():
    """Test 4: ADSR filter envelope"""
    print("\n=== Test 4: Filter ADSR Envelope ===")
    print("Attack: 0.5s, Decay: 0.3s, Sustain: 64, Release: 1.0s")
    print("This should create a classic filter envelope shape")

    result = await server.call_tool(
        "send_filter_envelope",
        {
            "attack_sec": 0.5,
            "decay_sec": 0.3,
            "sustain_level": 64,
            "release_sec": 1.0,
            "steps_per_stage": 20
        }
    )

    print(f"Result: {result[0].text}")
    await asyncio.sleep(0.5)

async def test_pattern_with_filter_automation():
    """Test 5: Play pattern with multiple filter changes at specific beats"""
    print("\n=== Test 5: Pattern with Filter Automation ===")
    print("4 bars at 120 BPM with kick pattern and filter automation")
    print("Filter will open at beat 0, 4, 8, and 12")

    # Kick on every beat (4/4 time, 4 bars = 16 beats)
    kick_triggers = [[i, 1, 100] for i in range(16)]

    # Filter automation: open at start of each bar, close mid-bar
    filter_events = [
        [0, 127],   # Bar 1 start - fully open
        [2, 40],    # Bar 1 mid - mostly closed
        [4, 127],   # Bar 2 start - fully open
        [6, 40],    # Bar 2 mid - mostly closed
        [8, 127],   # Bar 3 start - fully open
        [10, 40],   # Bar 3 mid - mostly closed
        [12, 127],  # Bar 4 start - fully open
        [14, 40],   # Bar 4 mid - mostly closed
    ]

    result = await server.call_tool(
        "play_with_filter_automation",
        {
            "bars": 4,
            "bpm": 120,
            "track_triggers": kick_triggers,
            "filter_events": filter_events,
            "send_clock": True,
            "send_stop": True
        }
    )

    print(f"Result: {result[0].text}")

async def test_filter_wobble():
    """Test 6: Create a wobble bass effect with rapid filter changes"""
    print("\n=== Test 6: Filter Wobble Effect ===")
    print("Creating a wobble bass by rapidly alternating filter cutoff")

    # Create wobble pattern - 8th note wobble for 2 bars
    filter_events = []
    for i in range(16):  # 16 8th notes in 2 bars
        # Alternate between open (127) and closed (30)
        value = 127 if i % 2 == 0 else 30
        beat = i * 0.5  # 8th notes
        filter_events.append([beat, value])

    result = await server.call_tool(
        "play_with_filter_automation",
        {
            "bars": 2,
            "bpm": 140,
            "filter_events": filter_events,
            "send_clock": True,
            "send_stop": True
        }
    )

    print(f"Result: {result[0].text}")

async def main():
    """Run all tests"""
    print("=" * 60)
    print("DIGITAKT FILTER SWEEP TEST SUITE")
    print("=" * 60)
    print("\nMake sure:")
    print("1. Digitakt II is connected via USB")
    print("2. Digitakt is set to receive MIDI CC on channel 1")
    print("3. A pattern is loaded with a sound that responds to filter")
    print("4. You can hear the output")
    print("\nPress Enter to start tests...")
    input()

    # Connect to MIDI
    server.connect_midi()

    if not server.output_port:
        print("ERROR: Could not connect to Digitakt MIDI port")
        return

    print(f"Connected to: {server.output_port.name}")

    try:
        # Run each test with a pause between
        await test_linear_sweep()
        await asyncio.sleep(1)

        await test_exponential_sweep()
        await asyncio.sleep(1)

        await test_logarithmic_sweep()
        await asyncio.sleep(1)

        await test_filter_envelope()
        await asyncio.sleep(1)

        await test_pattern_with_filter_automation()
        await asyncio.sleep(1)

        await test_filter_wobble()

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Close MIDI connections
        if server.output_port:
            server.output_port.close()
        if server.input_port:
            server.input_port.close()

if __name__ == "__main__":
    asyncio.run(main())
