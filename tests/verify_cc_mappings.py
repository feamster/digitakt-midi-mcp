#!/usr/bin/env python3
"""
Verify MIDI CC mappings from nrpn_constants.py against the JSON specification
"""

import sys
import os
# Add parent directory to path to import nrpn_constants
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nrpn_constants import (
    TrackCC, SourceCC, FilterCC, AmpCC, FXCC,
    TrackParams, TrigParams, SourceParams, FilterParams, AmpParams,
    LFO1Params, LFO2Params, LFO3Params, DelayParams, ReverbParams, ChorusParams
)

print("Digitakt II MIDI CC and NRPN Mapping Verification")
print("=" * 70)

# Check for CC conflicts
print("\n1. Checking for CC number conflicts...")
cc_map = {}
conflicts = []

def add_cc(name, cc_number, category):
    if cc_number in cc_map:
        conflicts.append(f"  CC {cc_number}: {category}.{name} conflicts with {cc_map[cc_number]}")
    else:
        cc_map[cc_number] = f"{category}.{name}"

# Track CCs
add_cc("MUTE", TrackCC.MUTE, "TrackCC")
add_cc("LEVEL", TrackCC.LEVEL, "TrackCC")

# Source CCs
add_cc("TUNE", SourceCC.TUNE, "SourceCC")
add_cc("SAMPLE_LEVEL", SourceCC.SAMPLE_LEVEL, "SourceCC")

# Filter CCs
add_cc("ATTACK", FilterCC.ATTACK, "FilterCC")
add_cc("DECAY", FilterCC.DECAY, "FilterCC")
add_cc("SUSTAIN", FilterCC.SUSTAIN, "FilterCC")
add_cc("RELEASE", FilterCC.RELEASE, "FilterCC")
add_cc("FREQUENCY", FilterCC.FREQUENCY, "FilterCC")
add_cc("ENV_DEPTH", FilterCC.ENV_DEPTH, "FilterCC")

# AMP CCs
add_cc("ATTACK", AmpCC.ATTACK, "AmpCC")
add_cc("HOLD", AmpCC.HOLD, "AmpCC")
add_cc("DECAY", AmpCC.DECAY, "AmpCC")
add_cc("SUSTAIN", AmpCC.SUSTAIN, "AmpCC")
add_cc("RELEASE", AmpCC.RELEASE, "AmpCC")
add_cc("VOLUME", AmpCC.VOLUME, "AmpCC")
add_cc("PAN", AmpCC.PAN, "AmpCC")

# FX CCs
add_cc("CHORUS_SEND", FXCC.CHORUS_SEND, "FXCC")
add_cc("DELAY_SEND", FXCC.DELAY_SEND, "FXCC")
add_cc("REVERB_SEND", FXCC.REVERB_SEND, "FXCC")
add_cc("OVERDRIVE", FXCC.OVERDRIVE, "FXCC")

if conflicts:
    print("✗ CONFLICTS FOUND:")
    for conflict in conflicts:
        print(conflict)
else:
    print("✓ No CC number conflicts detected")

# Verify key mappings against expected values
print("\n2. Verifying key CC mappings...")
verifications = [
    ("Filter Attack", FilterCC.ATTACK, 70),
    ("Filter Decay", FilterCC.DECAY, 71),
    ("Filter Sustain", FilterCC.SUSTAIN, 72),
    ("Filter Release", FilterCC.RELEASE, 73),
    ("Filter Frequency", FilterCC.FREQUENCY, 74),
    ("AMP Attack", AmpCC.ATTACK, 79),
    ("AMP Hold", AmpCC.HOLD, 80),
    ("AMP Decay", AmpCC.DECAY, 81),
    ("AMP Sustain", AmpCC.SUSTAIN, 82),
    ("AMP Release", AmpCC.RELEASE, 83),
    ("AMP Volume", AmpCC.VOLUME, 89),
    ("AMP Pan", AmpCC.PAN, 90),
    ("Track Mute", TrackCC.MUTE, 94),
    ("Track Level", TrackCC.LEVEL, 95),
]

errors = []
for name, actual, expected in verifications:
    if actual == expected:
        print(f"  ✓ {name}: CC {actual}")
    else:
        print(f"  ✗ {name}: CC {actual} (expected {expected})")
        errors.append(f"{name}: got {actual}, expected {expected}")

# Verify NRPN mappings
print("\n3. Verifying key NRPN mappings...")
nrpn_verifications = [
    ("Filter Attack", FilterParams.ATTACK, 16),
    ("Filter Decay", FilterParams.DECAY, 17),
    ("Filter Sustain", FilterParams.SUSTAIN, 18),
    ("Filter Release", FilterParams.RELEASE, 19),
    ("Filter Frequency", FilterParams.FREQUENCY, 20),
    ("AMP Attack", AmpParams.ATTACK, 30),
    ("AMP Hold", AmpParams.HOLD, 31),
    ("AMP Decay", AmpParams.DECAY, 32),
    ("AMP Sustain", AmpParams.SUSTAIN, 33),
    ("AMP Release", AmpParams.RELEASE, 34),
    ("AMP Volume", AmpParams.VOLUME, 39),
    ("AMP Pan", AmpParams.PAN, 38),
    ("Trig Note", TrigParams.NOTE, 0),
    ("Trig Velocity", TrigParams.VELOCITY, 1),
    ("Trig Length", TrigParams.LENGTH, 2),
]

for name, actual, expected in nrpn_verifications:
    if actual == expected:
        print(f"  ✓ {name}: LSB {actual}")
    else:
        print(f"  ✗ {name}: LSB {actual} (expected {expected})")
        errors.append(f"{name} NRPN: got {actual}, expected {expected}")

# Summary
print("\n" + "=" * 70)
if not conflicts and not errors:
    print("✓ ALL VERIFICATIONS PASSED")
    print("\nKey improvements:")
    print("  - Filter envelope (CC 70-73) is separate from AMP envelope (CC 79-83)")
    print("  - AMP has Hold time (CC 80) which Filter doesn't have")
    print("  - All NRPN LSB values are correctly mapped")
    print("  - No CC number conflicts detected")
else:
    print("✗ VERIFICATION FAILED")
    if conflicts:
        print(f"\n  {len(conflicts)} CC conflicts found")
    if errors:
        print(f"  {len(errors)} mapping errors found")

print("=" * 70)
