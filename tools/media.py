"""Shared file handling for local MV tools (Python 3.10+, FFmpeg / ffprobe)."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as source:
        return json.load(source)


def write_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             delete=False, newline="\n")
    temp = Path(temporary.name)
    try:
        with temporary as target:
            target.write(content)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def write_json(path, obj):
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        while chunk := source.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def require_separate(*paths):
    resolved = [Path(p).resolve() for p in paths if p]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Input and output paths must be different.")


def audio_seconds(path):
    path = Path(path).resolve(strict=True)
    raw = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a:0",
                                   "-show_entries", "stream=duration:format=duration",
                                   "-of", "json", str(path)])
    metadata = json.loads(raw)
    streams = metadata.get("streams", [])
    if not streams:
        raise ValueError(f"No audio track found in {path.name}")
    duration = None
    for value in [streams[0].get("duration"), metadata.get("format", {}).get("duration")]:
        if value not in (None, "N/A"):
            duration = float(value)
            break
    if not duration or not math.isfinite(duration) or duration <= 0:
        raise ValueError("The audio needs a finite, positive duration.")
    return duration


def project_for_audio(project_path, audio_path):
    project = read_json(project_path)
    name = project.get("audio")
    if not isinstance(name, str) or not name:
        raise ValueError("Set the project audio path before importing a timeline.")
    target = (Path(project_path).resolve().parent / name).resolve(strict=True)
    source = Path(audio_path).resolve(strict=True)
    if target != source and digest_file(target) != digest_file(source):
        raise ValueError("The project audio differs from the reviewed recording.")
    return project
