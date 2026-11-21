"""Compose a tiny instrumental recording for the downloadable demo (stdlib only)."""
from array import array
from math import exp, pi, sin
from pathlib import Path
import sys
import wave

RATE = 24000
DURATION = 12
BEAT = 0.5
CHORDS = [(50, 57, 62, 65), (46, 53, 58, 62), (48, 55, 60, 64), (45, 52, 57, 61)]


def hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def synth():
    samples = array("h")
    for index in range(RATE * DURATION):
        time = index / RATE
        beat = int(time / BEAT)
        since = time - beat * BEAT
        chord = CHORDS[(beat // 6) % len(CHORDS)]
        bell = 0.0
        for back in range(min(3, beat + 1)):
            previous = beat - back
            note = CHORDS[previous // 6 % 4][(previous * 3) % 4] + 12
            elapsed = since + back * BEAT
            phase = 2 * pi * hz(note) * elapsed
            bell += (sin(phase) + .19 * sin(2 * phase)) * min(elapsed / .013, 1) * exp(-3.2 * elapsed) * .23
        bar_time = time % (6 * BEAT)
        pad = sum(sin(2 * pi * hz(n) * time) for n in chord) * .042 * min(bar_time * 2, 1, (3 - bar_time) * 3)
        kick = .15 * sin(2 * pi * (49 * since + 4 * (1 - exp(-18 * since)))) * exp(-14 * since) if beat % 2 == 0 else 0
        env = max(0, min(1, time * 6, (DURATION - time) * 1.8))
        samples.append(round((bell + pad + kick) * env * 30000))
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


if __name__ == "__main__":
    path = Path(__file__).with_name("song.wav")
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        output.writeframes(synth())
    print(path)
