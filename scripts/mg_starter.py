"""Build an editable, beat-aware motion study before a lyric storyboard is approved."""

import math
from bisect import bisect_left, bisect_right
from itertools import pairwise

PALETTE = {
    "night": "#142B36",
    "cream": "#F1E4CC",
    "rust": "#E75C40",
    "gold": "#F2B74B",
    "teal": "#519B98",
    "slate": "#385663",
}


def nearest(values, target, window):
    i = bisect_left(values, target)
    candidates = values[max(0, i - 1) : i + 1]
    match = min(candidates, key=lambda t: abs(t - target), default=target)
    return match if abs(match - target) <= window else target


def phrase(name, start, end, beats, phase, narrative):
    length = end - start
    local = [
        b - start for b in beats[bisect_right(beats, start) : bisect_left(beats, end)]
    ]
    # Snap the turn in each gesture to a measured attack if the recording has one.
    turn = nearest(local, length * 0.54, length * 0.15)
    pale = phase % 2 == 1
    ink = "night" if pale else "cream"
    paper = "cream" if pale else "night"
    sub = "teal" if pale else "slate"
    objects = []

    def add(name, shape, color, **details):
        objects.append({"id": name, "shape": shape, "color": color, **details})

    def key(t, **values):
        return {"t": t, **values}

    def travel(a, b, c):
        return [key(0, position=a), key(turn, position=b), key(length, position=c)]

    def line(name, points, color, stroke, **details):
        add(name, "polyline", color, points=points, stroke=stroke, **details)

    def ring(name, center, radius, color, stroke=0.05, **details):
        add(
            name,
            "ring",
            color,
            radius=radius,
            position=center,
            stroke=stroke,
            **details,
        )

    gesture = phase % 4
    if gesture == 0:
        # A small body follows the two bends of a folded track.
        rail = [[-8, -2.2], [-4.8, -2.2], [-1.7, 0.7], [2.8, 0.7], [6, 3.5]]
        for i in range(5):
            line(f"Contour {i + 1}", [[x, y - i * 0.15] for x, y in rail], sub, 0.026)
        line(
            "Scored route",
            rail,
            "gold",
            0.085,
            keys=[key(0, reveal=0, ease="linear"), key(length, reveal=1)],
        )
        ring("Arrival mark", [2.8, 0.7], 0.54, ink, 0.04)
        add(
            "Signal",
            "disk",
            "rust",
            radius=0.34,
            keys=[
                key(0, position=[-7.5, -2.2]),
                key(turn * 0.5, position=[-4.8, -2.2]),
                key(turn, position=[-1.7, 0.7]),
                key(length, position=[2.8, 0.7]),
            ],
        )
        add("Distant light", "disk", ink, radius=0.13, position=[5.72, 3.25])
    elif gesture == 1:
        # The negative space between two shutters grows wide enough to cross.
        for i in range(8):
            x = -7.6 + 1.3 * i
            line(f"Score {i + 1}", [[x, -4.1], [x + 1.5, -2.6]], sub, 0.027)
        add(
            "Left fold",
            "polygon",
            ink,
            points=[[-8, -4.7], [-8, 4.7], [0.5, 4.7], [-3.7, -4.7]],
            keys=travel([0.8, 0], [-2, 0], [-1, 0]),
        )
        add(
            "Right fold",
            "polygon",
            sub,
            points=[[8, -4.7], [2, -4.7], [6.4, 4.7], [8, 4.7]],
            keys=travel([-1.8, 0], [1.2, 0], [1.6, 0]),
        )
        line("Hinge", [[-2, -3.6], [1.8, 3.6]], "gold", 0.065)
        ring(
            "Passing body",
            [0, 0],
            0.7,
            "rust",
            0.20,
            keys=travel([-4.2, -2], [0.15, 0.1], [4.4, 1.3]),
        )
        add(
            "Core",
            "disk",
            ink,
            radius=0.20,
            keys=travel([-4.2, -2], [0.15, 0.1], [4.4, 1.3]),
        )
    elif gesture == 2:
        # Two bodies rendezvous as partial arcs close around them.
        for i in range(4):
            add(
                f"Orbit {i + 1}",
                "arc",
                sub if i % 2 == 0 else ink,
                radius=1.7 + 0.53 * i,
                position=[-0.75, 0.15],
                startAngle=20 + 33 * i,
                endAngle=240 + 18 * i,
                stroke=0.045,
                keys=[
                    key(0, reveal=0.12, rotation=-25),
                    key(turn, reveal=1, rotation=5),
                    key(length, rotation=38),
                ],
            )
        add(
            "Warm body",
            "disk",
            "rust",
            radius=0.48,
            keys=travel([-6, -1], [-1.25, 0.14], [-0.75, 1.05]),
        )
        add(
            "Bright body",
            "disk",
            "gold",
            radius=0.27,
            keys=travel([5, 1.8], [0.03, 0.14], [-0.75, -0.70]),
        )
        line("Axis", [[1.4, 0.15], [6.1, 0.15]], sub, 0.045)
    else:
        # A stretched ribbon separates into a warm foreground and a cool trail.
        for i in range(7):
            add(
                f"Ribbon {i + 1}",
                "bezier",
                sub if i % 3 else ink,
                stroke=0.038 if i else 0.09,
                points=[
                    [-8, -1.2 + i * 0.18],
                    [-3.1, -1.6 + i * 0.30],
                    [1.7, 2.7 - i * 0.09],
                    [8, 0.7 - i * 0.12],
                ],
                keys=[
                    key(0, reveal=0.18),
                    key(turn, reveal=0.8),
                    key(length, reveal=1),
                ],
            )
        ring(
            "Release",
            [1.5, 2.15],
            0.90,
            "gold",
            0.10,
            keys=[
                key(0, scale=[0.45, 0.45]),
                key(turn, scale=[1, 1]),
                key(length, scale=[1.4, 1.4]),
            ],
        )
        add(
            "Traveller",
            "disk",
            "rust",
            radius=0.36,
            keys=travel([-5, -0.94], [1.5, 2.15], [6.4, 0.88]),
        )

    if not narrative:
        # Give the visual interpretation a stable subject and an animated detail
        # that can later be replaced with a concrete object from a reviewed lyric.
        detail = local[len(local) // 2] if local else turn
        add(
            "Reference mark",
            "rect",
            ink,
            size=[0.12, 0.56],
            position=[-6.8, 2.85],
            keys=[
                key(0, rotation=-90),
                key(detail, rotation=0),
                key(length, rotation=90),
            ],
        )
        line("Reference baseline", [[-6.8, 2.42], [-5.1, 2.42]], sub, 0.035)
    return {
        "name": name,
        "start": start,
        "end": end,
        "background": paper,
        "objects": objects,
    }


def starter_motion(duration, beats, mode):
    count = max(1, math.floor(duration / 11 + 0.5))
    boundaries = [0]
    for i in range(1, count):
        target = i * duration / count
        boundaries.append(nearest(beats, target, min(0.65, duration / count * 0.15)))
    boundaries.append(duration)
    narrative = mode == "narrative"
    names = (
        ["Approach", "Passage", "Rendezvous", "Release"]
        if narrative
        else ["Trace", "Aperture", "Orbit", "Unfold"]
    )
    order = [0, 1, 2, 3] if narrative else [2, 3, 0, 1]
    cues = [
        phrase(
            f"{i + 1:02d} {names[order[i % 4]]}", a, b, beats, order[i % 4], narrative
        )
        for i, (a, b) in enumerate(pairwise(boundaries))
    ]
    return {
        "version": 1,
        "fps": 24,
        "duration": duration,
        "palette": dict(PALETTE),
        "background": "night",
        "camera": {"position": [0, 0], "width": 16},
        "beats": beats,
        "cues": cues,
    }
