"""Create a portable, editable MV project from one local audio file."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from media import audio_seconds, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--mode", required=True, choices=["narrative", "lyric-visual"])
    parser.add_argument("--style", required=True, choices=[
        "pixel", "riso", "watercolor", "papercut", "lowpoly", "typography"
    ])
    parser.add_argument("--title")
    args = parser.parse_args()
    source = args.audio.expanduser().resolve()
    dest = args.directory.expanduser().resolve()
    if not source.is_file() or dest.exists():
        parser.error("Choose an existing audio file and a new project directory.")
    try:
        duration = audio_seconds(source)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError) as error:
        parser.error(f"Cannot read this audio file with ffprobe: {error}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as scratch:
        project = Path(scratch) / "project"
        project.mkdir()
        filename = "song" + source.suffix.lower()
        shutil.copyfile(source, project / filename)
        data = {
            "title": args.title or source.stem,
            "audio": filename,
            "mode": args.mode,
            "style": args.style,
            "lyrics": [],
            "beats": [],
            "scenes": [{
                "start": 0, "end": duration,
                "setting": "station", "action": "wait", "motif": "letter", "emotion": "calm",
            }],
        }
        write_json(project / "project.json", data)
        project.rename(dest)
    print(dest / "project.json")


if __name__ == "__main__":
    main()
