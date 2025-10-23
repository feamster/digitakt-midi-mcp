# Digitakt MIDI MCP Server

An MCP (Model Context Protocol) server for controlling the Elektron Digitakt II via MIDI.

## Features

- **Send MIDI Notes**: Trigger drum sounds on specific tracks
- **Control Parameters**: Adjust filters, envelopes, and other parameters via CC messages
- **Program Changes**: Switch between patterns
- **Note Sequences**: Send rhythmic patterns programmatically
- **NRPN Support**: Advanced parameter control including per-trig note, velocity, and length
- **Transport Control**: Start/Stop/Continue sequencer playback and jump to positions
- **SysEx Support**: Send raw SysEx messages for advanced control and pattern programming

## Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure your Digitakt II is connected via USB with Overbridge

## Usage

### Running the Server Manually

```bash
source venv/bin/activate
python server.py
```

### Configuring with Claude Desktop

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "digitakt-midi": {
      "command": "/Users/feamster/src/digitakt-midi-mcp/venv/bin/python",
      "args": ["/Users/feamster/src/digitakt-midi-mcp/server.py"]
    }
  }
}
```

Then restart Claude Desktop.

## Available Tools

### send_note
Send a MIDI note to trigger drums on the Digitakt.

**Parameters:**
- `note` (required): MIDI note number (0-127). Notes 0-7 trigger tracks 1-8. Notes 12-84 play active track chromatically.
- `velocity` (optional): Note velocity (1-127), default 100
- `duration` (optional): How long to hold the note in seconds, default 0.1
- `channel` (optional): MIDI channel (1-16), default 1

**Examples:**
```
Play note 0 to trigger track 1
Play note 60 on the active track
```

### trigger_track
Trigger a one-shot sample on a specific Digitakt II track (convenience wrapper).

**Parameters:**
- `track` (required): Track number (1-16)
- `velocity` (optional): Note velocity (1-127), default 100
- `duration` (optional): How long to hold the note in seconds, default 0.1
- `channel` (optional): MIDI channel (1-16), default 1

**Examples:**
```
Trigger track 1 (kick)
Trigger track 9 with velocity 127
Trigger track 16
```

### send_cc
Send a Control Change message to adjust Digitakt parameters.

**Parameters:**
- `cc_number` (required): CC number (0-127)
- `value` (required): CC value (0-127)
- `channel` (optional): MIDI channel (1-16), default 1

**Common CC Numbers for Digitakt:**
- 74: Filter Frequency
- 71: Filter Resonance
- 73: Attack
- 75: Decay
- 16-23: Track levels (16=Track 1, 17=Track 2, etc.)

**Example:**
```
Set filter frequency to maximum on track 1
```

### send_program_change
Switch to a different pattern on the Digitakt.

**Parameters:**
- `program` (required): Pattern number (0-127)
- `channel` (optional): MIDI channel (1-16), default 1

**Example:**
```
Switch to pattern 5
```

### send_note_sequence
Send a sequence of notes with timing.

**Parameters:**
- `notes` (required): Array of [note, velocity, duration] triplets
- `delay` (optional): Time between notes in seconds, default 0.25
- `channel` (optional): MIDI channel (1-16), default 1

**Example:**
```
Play a simple 4-on-the-floor kick pattern
```

### send_nrpn
Send an NRPN (Non-Registered Parameter Number) message for advanced parameter control.

**Parameters:**
- `msb` (required): NRPN MSB (1=Track/Trig/Source/Filter/Amp, 2=FX, 3=Trig Note/Velocity/Length)
- `lsb` (required): NRPN LSB (parameter number)
- `value` (required): Parameter value (0-127)
- `channel` (optional): MIDI channel (1-16), default 1

**Example:**
```
Set filter frequency using NRPN
```

**Common NRPNs:**
- MSB=3, LSB=0: Trig Note
- MSB=3, LSB=1: Trig Velocity
- MSB=3, LSB=2: Trig Length
- MSB=1, LSB=20: Filter Frequency
- MSB=1, LSB=21: Filter Resonance

### set_trig_note
Convenience tool to set the note for a trig (step).

**Parameters:**
- `note` (required): MIDI note number (0-127)
- `channel` (optional): MIDI channel (1-16), default 1

**Example:**
```
Set the current trig to C3 (note 60)
```

### set_trig_velocity
Convenience tool to set the velocity for a trig (step).

**Parameters:**
- `velocity` (required): Velocity (0-127)
- `channel` (optional): MIDI channel (1-16), default 1

### set_trig_length
Convenience tool to set the length for a trig (step).

**Parameters:**
- `length` (required): Note length (0-127)
- `channel` (optional): MIDI channel (1-16), default 1

### send_midi_start
Send MIDI Start message to start the Digitakt's sequencer from the beginning.

**Parameters:** None

**Example:**
```
Start the Digitakt sequencer
```

**Important:** The Digitakt requires MIDI Clock to actually play when externally controlled. Use `play_with_clock` instead for reliable playback, or ensure you're sending clock pulses separately. Requires TRANSPORT RECEIVE and CLOCK RECEIVE enabled in MIDI SYNC settings.

### send_midi_stop
Send MIDI Stop message to stop the Digitakt's sequencer.

**Parameters:** None

**Example:**
```
Stop the Digitakt sequencer
```

### send_midi_continue
Send MIDI Continue message to resume the Digitakt's sequencer from its current position.

**Parameters:** None

**Example:**
```
Resume the Digitakt sequencer
```

### send_song_position
Send MIDI Song Position Pointer to jump to a specific position in the sequence.

**Parameters:**
- `position` (required): Song position in MIDI beats (16th notes). 0 = start, 16 = 1 bar in 4/4 time.

**Examples:**
```
Jump to the beginning (position 0)
Jump to bar 2 (position 32)
Jump to the 3rd 16th note (position 2)
```

### play_with_clock
Start the Digitakt sequencer and send MIDI clock for a specified duration. This is the recommended way to control Digitakt playback remotely.

**Parameters:**
- `bars` (optional): Number of bars to play in 4/4 time. Default is 4 bars.
- `bpm` (optional): Tempo in beats per minute. Default is 120 BPM.
- `send_stop` (optional): Send MIDI Stop after duration. Default is true.

**Examples:**
```
Play for 4 bars at 120 BPM
Play for 8 bars at 140 BPM
Play for 2 bars and keep running (send_stop=false)
```

**Use case:** This tool sends MIDI Start + Clock pulses + Stop, which the Digitakt needs to actually play when externally controlled. You can use this to play the Digitakt's sequencer while also sending notes or CC messages.

### play_pattern_with_tracks
Start the Digitakt pattern and trigger specific tracks at specific times. Combines MIDI transport control with precise track triggering.

**Parameters:**
- `bars` (optional): Number of bars to play in 4/4 time. Default is 4 bars.
- `bpm` (optional): Tempo in beats per minute. Default is 120 BPM.
- `triggers` (required): Array of `[beat, track, velocity]` where beat is 0-based quarter note (0=start, 1=beat 2, etc), track is 1-16, velocity is 1-127.
- `send_stop` (optional): Send MIDI Stop after duration. Default is true.

**Examples:**
```
Play 4 bars with kick on every beat
triggers: [[0, 1, 100], [1, 1, 100], [2, 1, 100], [3, 1, 100]]

Play 2 bars with kick and snare pattern
triggers: [[0, 1, 100], [1, 2, 80], [2, 1, 100], [3, 2, 80]]
```

**Use case:** Perfect for layering additional drum hits on top of your Digitakt's pattern. You can trigger specific tracks at precise times while the pattern plays.

### play_pattern_with_melody
Start the Digitakt pattern and play a melodic sequence on the active track. Combines MIDI transport control with melodic note sequences.

**Parameters:**
- `bars` (optional): Number of bars to play in 4/4 time. Default is 4 bars.
- `bpm` (optional): Tempo in beats per minute. Default is 120 BPM.
- `notes` (required): Array of `[beat, note, velocity, duration]` where beat is 0-based quarter note, note is MIDI note 12-127, velocity is 1-127, duration is in seconds.
- `channel` (optional): MIDI channel (1-16). Default is 1 (auto channel).
- `send_stop` (optional): Send MIDI Stop after duration. Default is true.

**Examples:**
```
Play a C major scale over 2 bars
notes: [[0, 60, 100, 0.2], [1, 62, 100, 0.2], [2, 64, 100, 0.2], [3, 65, 100, 0.2],
        [4, 67, 100, 0.2], [5, 69, 100, 0.2], [6, 71, 100, 0.2], [7, 72, 100, 0.4]]

Play a simple melody
notes: [[0, 60, 100, 0.3], [1.5, 64, 100, 0.3], [3, 67, 100, 0.5]]
```

**Use case:** Add melodic elements or basslines on top of your Digitakt pattern. The active track will play chromatically while the pattern runs.

### play_pattern_with_loop
Start the Digitakt pattern and continuously trigger notes on a loop. Combines MIDI transport control with looping note patterns.

**Parameters:**
- `bars` (optional): Number of bars to play in 4/4 time. Default is 4 bars.
- `bpm` (optional): Tempo in beats per minute. Default is 120 BPM.
- `loop_notes` (required): Array of `[beat_offset, note_or_track, velocity]` where beat_offset is relative to loop start (0-3.99 for 1 bar loop), note/track can be 0-15 for tracks or 12+ for melody, velocity is 1-127.
- `loop_length` (optional): Length of the loop in bars (in 4/4 time). Default is 1 bar.
- `channel` (optional): MIDI channel (1-16). Default is 1 (auto channel).
- `send_stop` (optional): Send MIDI Stop after duration. Default is true.

**Examples:**
```
Play a 1-bar hi-hat pattern that loops for 4 bars
loop_notes: [[0, 2, 80], [0.5, 2, 60], [1, 2, 80], [1.5, 2, 60],
             [2, 2, 80], [2.5, 2, 60], [3, 2, 80], [3.5, 2, 60]]
loop_length: 1
bars: 4

Play a 2-bar melodic ostinato
loop_notes: [[0, 60, 100], [1, 64, 100], [2, 67, 100], [3, 64, 100],
             [4, 60, 100], [5, 67, 100], [6, 64, 100], [7, 60, 100]]
loop_length: 2
bars: 8
```

**Use case:** Create repeating rhythmic or melodic patterns that play continuously while your Digitakt pattern runs. Perfect for hi-hats, percussion loops, or ostinato basslines.

### save_last_melody
Save the last played melody from `play_pattern_with_melody` to a standard MIDI file. Perfect for capturing generated melodies you like.

**Parameters:**
- `filename` (required): Filename for the MIDI file (e.g., 'my_melody.mid'). Will be saved in the current directory.

**Examples:**
```
Save the last melody to a file
filename: "cool_melody.mid"

Save with a descriptive name
filename: "bassline_120bpm.mid"
```

**Use case:** After using `play_pattern_with_melody` to generate or play a melody, you can save it to a MIDI file for use in your DAW, other hardware, or for archival. The MIDI file includes the original tempo and timing.

**Note:** This only works after you've used `play_pattern_with_melody` at least once. The melody is saved with the exact BPM, notes, velocities, and durations from the last playback.

### send_sysex
Send a System Exclusive (SysEx) message to the Digitakt for advanced control and pattern programming.

**Parameters:**
- `data` (optional): Array of bytes (0-127) to send as SysEx data. F0 and F7 bytes are added automatically.
- `hex_string` (optional): Alternative to `data` - provide SysEx as hex string (e.g., "00203C...")

**Elektron Manufacturer ID:** `0x00 0x20 0x3C`

**Example:**
```
Send a custom SysEx message to the Digitakt
```

**Note:** The exact SysEx format for Digitakt pattern programming is not publicly documented by Elektron. You can:
- Use this tool to send raw SysEx data you've captured or reverse-engineered
- Capture SysEx dumps from Elektron Transfer software
- Experiment with the format by analyzing saved .syx files

### request_sysex_dump
Request a SysEx data dump from the Digitakt (pattern, sound, kit, or project).

**Parameters:**
- `dump_type` (required): Type of dump - "pattern", "sound", "kit", or "project"
- `bank` (optional): Bank number (0-15)
- `pattern_number` (optional): Pattern number within bank (0-15)

**Example:**
```
Request a pattern dump from bank 0, pattern 0
```

**Important:** This sends a best-guess dump request format. The exact protocol is not publicly documented. You may need to:
- Monitor SysEx responses using MIDI monitoring software
- Use Elektron Transfer for official dumps
- Adjust the command bytes based on experimentation

## Resources

### midi://ports
Lists all available MIDI input and output ports on the system.

### midi://digitakt/status
Shows the current connection status to the Digitakt MIDI ports.

## Digitakt MIDI Reference

### Note Numbers for Tracks

**To trigger one-shots on specific tracks (regardless of active track):**
- Track 1: MIDI note **0** (C-2 / C0)
- Track 2: MIDI note **1** (C#-2 / C#0)
- Track 3: MIDI note **2** (D-2 / D0)
- Track 4: MIDI note **3** (D#-2 / D#0)
- Track 5: MIDI note **4** (E-2 / E0)
- Track 6: MIDI note **5** (F-2 / F0)
- Track 7: MIDI note **6** (F#-2 / F#0)
- Track 8: MIDI note **7** (G-2 / G0)
- Track 9: MIDI note **8** (G#-2 / G#0)
- Track 10: MIDI note **9** (A-2 / A0)
- Track 11: MIDI note **10** (A#-2 / A#0)
- Track 12: MIDI note **11** (B-2 / B0)
- Track 13: MIDI note **12** (C-1 / C1)
- Track 14: MIDI note **13** (C#-1 / C#1)
- Track 15: MIDI note **14** (D-1 / D1)
- Track 16: MIDI note **15** (D#-1 / D#1)

**To play the currently active track chromatically:**
- MIDI notes **12 and above** (C1+) will play the active track at different pitches
- Note: This overlaps with track 13-16 triggers, so if you want chromatic playback, use notes higher than 15

**Note:** MIDI channels 1-16 can be assigned to tracks 1-16, or use AUTO CHANNEL to control the currently active track.

### Common CC Parameters
Check the Digitakt manual for the full CC map. Some common ones:
- 16-23: Track levels
- 71: Filter Resonance
- 74: Filter Frequency
- 73: Attack
- 75: Decay

### NRPN Parameters

NRPNs (Non-Registered Parameter Numbers) provide access to more parameters than standard CCs. The server includes a complete `nrpn_constants.py` file with all parameter definitions.

**NRPN Structure:**
- MSB (CC 99): Category (1, 2, or 3)
- LSB (CC 98): Specific parameter
- Data Entry MSB (CC 6): Value (0-127)
- Data Entry LSB (CC 38): Fine value (usually 0)

**Categories:**
- **MSB 1**: Track, Source, Filter, Amp, LFO parameters
- **MSB 2**: FX (Delay and Reverb) parameters
- **MSB 3**: Trig parameters (Note, Velocity, Length)

**Key Trig Parameters (MSB=3):**
- LSB 0: Trig Note (pitch per step)
- LSB 1: Trig Velocity (velocity per step)
- LSB 2: Trig Length (note length per step)

**Filter Parameters (MSB=1):**
- LSB 16: Attack
- LSB 17: Decay
- LSB 18: Sustain
- LSB 19: Release
- LSB 20: Frequency
- LSB 21: Resonance
- LSB 22: Type
- LSB 23: Envelope Depth

**Amp Parameters (MSB=1):**
- LSB 24: Attack
- LSB 25: Hold
- LSB 26: Decay
- LSB 27: Overdrive
- LSB 28: Delay Send
- LSB 29: Reverb Send
- LSB 30: Pan
- LSB 31: Volume

See `nrpn_constants.py` for the complete parameter list.

## Troubleshooting

**MIDI device not found:**
- Make sure the Digitakt is connected via USB
- Check that Overbridge is properly installed
- Verify the device shows up in Audio MIDI Setup (macOS)

**Permission errors:**
- On macOS, you may need to grant microphone permissions to Terminal/iTerm
- Check System Preferences > Security & Privacy > Privacy > Microphone

## Working with SysEx

The Digitakt supports SysEx for advanced operations, but Elektron hasn't published the detailed protocol specification. Here are some approaches to work with SysEx:

### Capturing SysEx Data

1. **Using Elektron Transfer:**
   - Use Elektron Transfer to save patterns/sounds as .syx files
   - Analyze these files to understand the format
   - Use `send_sysex` with the captured data

2. **MIDI Monitoring:**
   - Use tools like MIDI Monitor (macOS) or MIDI-OX (Windows)
   - Capture SysEx dumps from the device
   - Analyze the byte structure

3. **Reverse Engineering:**
   - Study community projects like the Analog Rytm SysEx library
   - Experiment with sending modified SysEx data
   - Document your findings

### SysEx Structure

All Elektron SysEx messages follow this basic structure:
```
F0                    - SysEx start byte
00 20 3C              - Elektron manufacturer ID
[device_id]           - Device identifier
[command]             - Command byte
[data...]             - Message-specific data
F7                    - SysEx end byte
```

### Tips for Pattern Programming

- Start by capturing existing patterns via Transfer
- Compare multiple patterns to identify fields
- Test modifications carefully to avoid corrupting device memory
- Always backup your projects before experimenting

## License

MIT
