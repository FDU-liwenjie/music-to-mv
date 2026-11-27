"""Create a portable, editable MV project from one local audio file."""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from beats import accents, low_end_onsets
from build_mg import build
from media import audio_seconds, write_json
from mg_starter import starter_motion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--mode", required=True, choices=["narrative", "lyric-visual"])
    parser.add_argument(
        "--style",
        default="motion-graphics",
        choices=[
            "motion-graphics",
            "pixel",
            "riso",
            "watercolor",
            "papercut",
            "lowpoly",
            "typography",
            "cinematic",
            "blender",
        ],
    )
    parser.add_argument("--title")
    parser.add_argument(
        "--art",
        type=Path,
        help="copy a JPG or PNG as the first shot's photographic plate",
    )
    parser.add_argument(
        "--blend", type=Path, help="copy a packed Blender scene as the first shot"
    )
    parser.add_argument(
        "--first-frame",
        type=int,
        help="native Blender frame at the start of the shot (default 1)",
    )
    args = parser.parse_args()
    blend = args.blend.expanduser().resolve() if args.blend else None
    if args.style == "blender":
        if not blend or not blend.is_file() or blend.suffix.lower() != ".blend":
            parser.error("--style blender needs --blend PATH to a local .blend scene")
        if args.art:
            parser.error("Use imagery inside the .blend file for Blender shots")
    elif blend or args.first_frame is not None:
        parser.error("--blend and --first-frame require --style blender")
    if args.first_frame is not None and args.first_frame < 1:
        parser.error("--first-frame must be at least 1")
    plate = args.art.expanduser().resolve() if args.art else None
    if args.style == "cinematic" and plate is None:
        parser.error("--style cinematic needs --art PATH to a local JPG or PNG")
    if plate and (
        not plate.is_file() or plate.suffix.lower() not in {".jpg", ".jpeg", ".png"}
    ):
        parser.error("--art must be an existing JPG or PNG photograph")
    if args.style == "motion-graphics" and plate:
        parser.error(
            "Motion graphics uses native shapes; --art expects an image-based style"
        )
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
            "scenes": [
                {
                    "start": 0,
                    "end": duration,
                    "setting": "station",
                    "action": "wait",
                    "motif": "letter",
                    "emotion": "calm",
                }
            ],
        }
        if args.style == "motion-graphics":
            change, hop = low_end_onsets(source)
            timeline = accents(change, hop, 0.24)
            motion = starter_motion(duration, timeline, args.mode)
            write_json(project / "motion.json", motion)
            build(project / "motion.json", project / "scene.blend")
            data.update(
                style="blender",
                beats=timeline,
                scenes=[
                    {
                        "start": 0,
                        "end": duration,
                        "blend": "scene.blend",
                        "firstFrame": 1,
                    }
                ],
            )
        if plate:
            asset_dir = project / "assets"
            asset_dir.mkdir()
            asset = asset_dir / ("shot-01" + plate.suffix.lower())
            shutil.copyfile(plate, asset)
            data["scenes"][0]["art"] = asset.relative_to(project).as_posix()
        if blend:
            asset = project / "assets" / "shot-01.blend"
            asset.parent.mkdir()
            shutil.copyfile(blend, asset)
            data["scenes"][0] = {
                "start": 0,
                "end": duration,
                "blend": asset.relative_to(project).as_posix(),
                "firstFrame": args.first_frame or 1,
            }
        write_json(project / "project.json", data)
        project.rename(dest)
    print(dest / "project.json")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
