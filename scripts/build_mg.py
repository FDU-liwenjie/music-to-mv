"""Compile editable motion.json geometry and keyframes into a native Blender scene."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def blender_binary():
    override = os.environ.get("BLENDER_BIN")
    candidates = (
        [override]
        if override
        else [
            shutil.which("blender"),
            Path.home() / "Applications/Blender.app/Contents/MacOS/Blender",
            Path("/Applications/Blender.app/Contents/MacOS/Blender"),
        ]
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
    raise ValueError(
        "Install Blender 4.5 LTS or set BLENDER_BIN to the Blender executable."
    )


def build(source, output):
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if source == output or output.suffix.lower() != ".blend":
        raise ValueError("Choose a separate .blend output file.")
    binary = blender_binary()
    output.parent.mkdir(parents=True, exist_ok=True)
    adapter = Path(__file__).with_name("mg_scene.py").resolve()
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        temporary = Path(scratch) / "scene.blend"
        result = subprocess.run(
            [
                binary,
                "--background",
                "--factory-startup",
                "--disable-autoexec",
                "--python-exit-code",
                "1",
                "--python",
                str(adapter),
                "--",
                str(source),
                str(temporary),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode or not temporary.is_file():
            raise ValueError(
                f"Could not build {source.name}\n{result.stdout[-5000:].strip()}"
            )
        os.replace(temporary, output)
    return output


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="See scripts/MOTION.md for geometry and timing units.",
    )
    parser.add_argument("motion", type=Path, help="path to motion.json")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="native .blend scene to create or replace",
    )
    args = parser.parse_args()
    print(build(args.motion, args.output))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
