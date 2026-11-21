#!/usr/bin/env python3
"""Local lyric drafts, timing corrections, line previews and approved caption export."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

from media import audio_seconds, digest_file, project_for_audio, read_json, require_separate, write_json, write_text


def seconds(value):
    fields = str(value).strip().replace(",", ".").split(":")
    if not 1 <= len(fields) <= 3 or any(not re.fullmatch(r"\d+(?:\.\d+)?", f) for f in fields):
        raise ValueError(f"Invalid time: {value}")
    result = 0.0
    for i, field in enumerate(fields):
        number = float(field)
        if not math.isfinite(number) or (i and number >= 60) or (i < len(fields)-1 and "." in field):
            raise ValueError(f"Invalid time: {value}")
        result = result * 60 + number
    return result


def stamp(t, separator="."):
    total, fraction = divmod(round(t * 1000), 1000)
    total, secs = divmod(total, 60)
    hours, mins = divmod(total, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}{separator}{fraction:03d}"


def cue(start, end, text, note=None):
    result = {"start": round(start, 3), "end": round(end, 3), "text": text.strip()}
    if note:
        result["note"] = note
    return result


def validate(draft):
    duration = draft["duration"]
    last_end = 0.0
    for i, line in enumerate(draft["lyrics"], 1):
        start, end = float(line["start"]), float(line["end"])
        if not (last_end <= start < end <= duration + 0.002):
            raise ValueError(f"Line {i}: check its order, overlap, or audio bounds.")
        if not isinstance(line["text"], str) or not line["text"].strip():
            raise ValueError(f"Line {i}: empty text.")
        last_end = end
    if not draft["lyrics"] and draft["source"] != "instrumental":
        raise ValueError("No lyric lines. Supply an LRC/SRT, or explicitly choose instrumental.")
    if draft["lyrics"] and draft["source"] == "instrumental":
        raise ValueError("An instrumental review must have an empty lyric track.")


def parse_import(path, duration):
    content = path.read_text(encoding="utf-8-sig").strip()
    if path.suffix.lower() == ".srt":
        rows = []
        for i, block in enumerate(re.split(r"\n\s*\n", content), 1):
            lines = block.strip().splitlines()
            if lines and lines[0].strip().isdigit():
                lines = lines[1:]
            if len(lines) < 2 or "-->" not in lines[0]:
                raise ValueError(f"Malformed SRT block {i}")
            a, b = lines[0].split("-->", 1)
            rows.append(cue(seconds(a), seconds(b), " ".join(lines[1:])))
        return rows, "srt"
    if path.suffix.lower() == ".lrc":
        events = []
        offset = re.search(r"(?im)^\s*\[offset:\s*([+-]?\d+)\s*\]", content)
        # A positive LRC offset advances lyric display.
        shift = -int(offset[1]) / 1000 if offset else 0.0
        pattern = re.compile(r"\[(\d+:\d{1,2}(?:[.,]\d+)?)\]")
        for i, row in enumerate(content.splitlines(), 1):
            times = pattern.findall(row)
            words = pattern.sub("", row).strip()
            if times:
                events.extend((round(max(0, seconds(t) + shift), 3), words) for t in times)
            elif words and not re.fullmatch(r"\[[\w-]+:[^\]]*\]", words):
                raise ValueError(f"Line {i} has no LRC timestamp. Use .txt for untimed lyrics.")
        events.sort(key=lambda item: item[0])
        rows = []
        for i, (start, words) in enumerate(events):
            end = events[i+1][0] if i + 1 < len(events) else duration
            if words:
                rows.append(cue(start, end, words, "Line ends inferred from next LRC timestamp"))
        return rows, "lrc"
    if path.suffix.lower() == ".txt":
        lines = [row.strip() for row in content.splitlines() if row.strip()]
        return [cue(i * duration / len(lines), (i+1) * duration / len(lines), words,
                    "Approximate timing: evenly spaced placeholder")
                for i, words in enumerate(lines)], "untimed-text"
    raise ValueError("Supported lyric formats are .srt, .lrc, and .txt")


def transcribe(args, duration):
    try:
        from faster_whisper import WhisperModel
        import numpy as np
    except ImportError as err:
        raise ValueError("Install the optional packages in requirements-asr.txt.") from err
    model = WhisperModel(args.model, device="cpu", compute_type="int8",
                         local_files_only=args.offline, cpu_threads=args.threads)
    pcm = subprocess.check_output(["ffmpeg", "-nostdin", "-v", "error", "-i", str(args.audio.resolve()),
                                   "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"])
    waveform = np.frombuffer(pcm, dtype="<f4")
    segments, info = model.transcribe(waveform, language=args.language,
                                      beam_size=5, vad_filter=False, condition_on_previous_text=False)
    result = []
    last_end = 0.0
    for segment in segments:
        start = max(last_end, 0.0, round(segment.start, 3))
        end = min(duration, round(segment.end, 3))
        if end <= start or not segment.text.strip():
            continue
        note = "Listen closely" if segment.avg_logprob < -0.8 or segment.no_speech_prob > 0.55 else "ASR draft"
        result.append(cue(start, end, segment.text, note))
        last_end = end
    print(f"Detected language: {info.language}", file=sys.stderr)
    return result


def referenced_audio(review_path, draft):
    return (review_path.resolve().parent / draft["audio"]).resolve(strict=True)


def approval_hash(draft):
    data = {key: draft[key] for key in ("duration", "source", "lyrics", "audio_sha256")}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def checked_audio(review, draft):
    path = referenced_audio(review, draft)
    if digest_file(path) != draft["audio_sha256"]:
        raise ValueError("The recording has changed since this draft was created.")
    return path


def create_review(args):
    audio = args.audio.resolve(strict=True)
    require_separate(audio, args.output, getattr(args, "captions", None))
    if args.output.exists() and not args.force:
        raise ValueError(f"Review exists: {args.output}. Use --force to replace it.")
    duration = round(audio_seconds(audio), 3)
    if args.command == "import":
        lines, source = parse_import(args.captions, duration)
    elif args.command == "transcribe":
        lines, source = transcribe(args, duration), "asr"
    else:
        lines, source = [], "instrumental"
    try:
        audio_ref = os.path.relpath(audio, args.output.resolve().parent)
    except ValueError:  # Windows volumes can differ.
        audio_ref = str(audio)
    draft = {"version": 1, "audio": audio_ref, "audio_sha256": digest_file(audio), "duration": duration,
             "source": source, "status": "draft", "lyrics": lines}
    validate(draft)
    write_json(args.output, draft)
    print(f"Wrote {args.output} ({len(lines)} lines, awaiting lyric review).")


def pick_line(draft, number):
    if not 1 <= number <= len(draft["lyrics"]):
        raise ValueError(f"No lyric line {number}.")
    return draft["lyrics"][number - 1]


def use_review(args):
    d = read_json(args.review)
    validate(d)
    if args.command == "show":
        approved = d.get("status") == "approved" and d.get("approval") == approval_hash(d)
        print(f"{'approved' if approved else 'draft'} | {d['source']} | {d['duration']:.3f}s")
        for i, line in enumerate(d["lyrics"], 1):
            print(f"{i:03d}  {stamp(line['start'])} – {stamp(line['end'])}  "
                  f"{line['text']}  [{line.get('note', 'review')}]")
        return
    if args.command == "edit":
        line = pick_line(d, args.line)
        old_start, old_end = line["start"], line["end"]
        changes = {"text": args.text, "start": args.start, "end": args.end}
        if all(value is None for value in changes.values()):
            raise ValueError("Set --text, --start, or --end.")
        for key, value in changes.items():
            if value is not None:
                line[key] = value.strip() if key == "text" else round(seconds(value), 3)
        if args.shared_boundaries:
            i = args.line - 1
            if i and d["lyrics"][i-1]["end"] == old_start:
                d["lyrics"][i-1]["end"] = line["start"]
            if i+1 < len(d["lyrics"]) and d["lyrics"][i+1]["start"] == old_end:
                d["lyrics"][i+1]["start"] = line["end"]
        line["note"] = "Edited locally"
        validate(d)
        d["status"] = "draft"
        d.pop("approval", None)
        write_json(args.review, d)
        return
    audio = checked_audio(args.review, d)
    if args.command == "listen":
        line = pick_line(d, args.line)
        if not math.isfinite(args.pad) or args.pad < 0:
            raise ValueError("--pad must be zero or greater.")
        start = max(0, line["start"] - args.pad)
        end = min(d["duration"], line["end"] + args.pad)
        times = ["-ss", f"{start:.3f}", "-t", f"{end-start:.3f}"]
        if args.output:
            require_separate(audio, args.review, args.output)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-n", *times, "-i", str(audio),
                            "-map", "0:a:0", "-vn", "-c:a", "pcm_s16le", str(args.output)], check=True)
        else:
            subprocess.run(["ffplay", "-loglevel", "error", "-nodisp", "-autoexit", *times, str(audio)],
                           check=True)
        return
    if args.command == "approve":
        d["status"] = "approved"
        d["approval"] = approval_hash(d)
        write_json(args.review, d)
        print("Saved approval for this recording, text and timing.")
        return
    if d.get("status") != "approved" or d.get("approval") != approval_hash(d):
        raise ValueError("Show the current lyrics to the user and obtain approval before export.")
    if not args.srt and not args.project:
        raise ValueError("Select --project or --srt (or both).")
    require_separate(audio, args.review, args.project, args.srt)
    project = project_for_audio(args.project, audio) if args.project else None
    if args.srt:
        subs = [f"{i}\n{stamp(row['start'], ',')} --> {stamp(row['end'], ',')}\n{row['text']}\n"
                for i, row in enumerate(d["lyrics"], 1)]
        write_text(args.srt, "\n".join(subs))
    if project is not None:
        project["lyrics"] = [{key: row[key] for key in ("start", "end", "text")} for row in d["lyrics"]]
        project["lyricsReview"] = {"status": "approved", "source": d["source"], "digest": d["approval"]}
        write_json(args.project, project)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("transcribe", "import", "instrumental"):
        cmd = sub.add_parser(name)
        cmd.add_argument("audio", type=Path)
        cmd.add_argument("-o", "--output", type=Path, required=True)
        cmd.add_argument("--force", action="store_true", help="replace an existing draft")
        if name == "import":
            cmd.add_argument("captions", type=Path)
        if name == "transcribe":
            cmd.add_argument("--language", help="language code (omit to detect)")
            cmd.add_argument("--model", default="small", help="faster-whisper model name or local directory")
            cmd.add_argument("--offline", action="store_true", help="use locally cached models only")
            cmd.add_argument("--threads", type=int, default=4)
    for name in ("show", "edit", "listen", "approve", "export"):
        cmd = sub.add_parser(name)
        cmd.add_argument("review", type=Path)
        if name in ("edit", "listen"):
            cmd.add_argument("line", type=int, help="1-based line number from show")
        if name == "edit":
            cmd.add_argument("--text")
            cmd.add_argument("--start")
            cmd.add_argument("--end")
            cmd.add_argument("--shared-boundaries", action="store_true",
                             help="move touching edges of immediately adjacent lines with this one")
        if name == "listen":
            cmd.add_argument("--pad", type=float, default=0.5, help="context around each end in seconds")
            cmd.add_argument("-o", "--output", type=Path, help="write to a new WAV instead of playing")
        if name == "export":
            cmd.add_argument("--srt", type=Path)
            cmd.add_argument("--project", type=Path)
    args = parser.parse_args()
    if args.command in ("import", "transcribe", "instrumental"):
        create_review(args)
    else:
        use_review(args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
