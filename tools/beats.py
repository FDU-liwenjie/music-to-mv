#!/usr/bin/env python3
"""Find bass attack times for choreography; keep lyric timing independent."""
import argparse
from array import array
import math
from pathlib import Path
import statistics
import subprocess
import sys

from media import project_for_audio, require_separate, write_json


def low_end_onsets(audio):
    # Reduce audio to a low-frequency mono envelope at 10 ms intervals.
    sr, hop = 2000, 20
    raw = subprocess.check_output(["ffmpeg", "-nostdin", "-v", "error", "-i", str(audio.resolve()),
                                   "-map", "0:a:0", "-af", "highpass=f=35,lowpass=f=185",
                                   "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"])
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    envelope = []
    for offset in range(0, len(samples), hop):
        block = samples[offset:offset+hop]
        rms = math.sqrt(sum(x*x for x in block) / len(block)) / 32768
        envelope.append(math.log1p(40*rms))
    change = [0.0] * len(envelope)
    for i in range(2, len(change)):
        change[i] = max(0.0, envelope[i] - envelope[i-2])
    return change, hop / sr


def accents(change, hop, spacing):
    if len(change) < 5 or max(change, default=0) < 0.04:
        return []
    ordered = sorted(change)
    floor = max(0.035, ordered[int(.90*len(ordered))] * 0.5)
    min_frames = max(1, round(spacing / hop))
    peaks = []
    for i in range(2, len(change)-2):
        val = change[i]
        if val < floor or val != max(change[i-2:i+3]):
            continue
        local = change[max(0, i-40):i+41]
        if val < statistics.median(local)*2 + floor:
            continue
        if peaks and i - peaks[-1] < min_frames:
            if val > change[peaks[-1]]:
                peaks[-1] = i
        else:
            peaks.append(i)
    return [round(i*hop, 3) for i in peaks]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--project", type=Path, help="also set project.beats for this audio recording")
    parser.add_argument("--spacing", type=float, default=.24, help="minimum spacing of accents, in seconds")
    args = parser.parse_args()
    require_separate(args.audio, args.output, args.project)
    if not math.isfinite(args.spacing) or not .05 <= args.spacing <= 5:
        raise ValueError("Choose a minimum separation between 0.05 and 5 seconds.")
    change, hop = low_end_onsets(args.audio)
    beats = accents(change, hop, args.spacing)
    project = project_for_audio(args.project, args.audio) if args.project else None
    write_json(args.output, {"method": "low-frequency attack peaks", "units": "seconds", "beats": beats})
    if project is not None:
        project["beats"] = beats
        write_json(args.project, project)
    print(f"Found {len(beats)} low-frequency accents; review against the song.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
