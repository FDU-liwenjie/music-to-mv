# Lyrics and rhythm tools

Run these commands from the repository root. Python 3.10+ and the FFmpeg command line tools must be on PATH. The example paths below stand for your own audio and work directory. Source audio is read locally. Lyric and accent times are seconds from the beginning of that exact recording, including the intro. A remix or live recording needs its own review.

### Get a draft

For timed lyrics, import a UTF-8 LRC or SRT. LRC supports repeated line timestamps and a global offset. Line ends follow the next timestamp. Inserting a timestamp with no words ends the previous line and allows a music-only gap. An untimed UTF-8 TXT with one lyric line per row is also accepted. Its initial timestamps are equally spaced placeholders for manual timing.

```sh
python3 tools/lyrics.py import work/song.mp3 work/source.lrc -o work/review.json
```

For an audio-only input, install the optional local recognizer in a Python environment. The first run may download the recognition model. Supply a local model directory or use a cached model and `--offline` for disconnected use. Whisper produces provisional text and line-level timing. For example, a repeated sung line may be missed; review it against the recording.

```sh
python3 -m pip install -r requirements-asr.txt
python3 tools/lyrics.py transcribe work/song.mp3 --model small -o work/review.json
```

Omit `--language` for language detection or supply a code known to your selected model. For example, use `--language zh` for Mandarin. For a user-selected instrumental, create an empty review with `python3 tools/lyrics.py instrumental work/song.mp3 -o work/review.json`. Replacing an existing review requires `--force`.

### Review individual lines

```sh
python3 tools/lyrics.py show work/review.json
python3 tools/lyrics.py listen work/review.json 3 -o work/line-03.wav
python3 tools/lyrics.py edit work/review.json 3 --text "We meet on the last train"
python3 tools/lyrics.py edit work/review.json 3 --start 00:12.450 --end 16.200 --shared-boundaries
python3 tools/lyrics.py show work/review.json
```

`listen` includes half a second of context on either side. Without `-o` it plays with ffplay. Line numbers start at 1. Editing text keeps the line's existing start/end. The optional shared-boundaries flag also moves the adjacent lines' edges if they originally touched this line. Disjoint line timings remain independent. For substantial additions and splits, the user can supply a corrected SRT or edit the draft's local JSON line list and rerun `show`. For a web lookup, let the user find their preferred version and paste their corrections or import the file they provide. Keep each repeated chorus in its actual position.

### Approve and export

Show the text, uncertainties and timings to the user first. Run `approve` only after they accept the current version. It records the reviewed text and times against the source audio hash. Editing a reviewed line invalidates approval. A changed recording requires a new review.

```sh
python3 tools/lyrics.py approve work/review.json
python3 tools/lyrics.py export work/review.json --srt work/captions.srt --project work/project.json
```

At least one of `--srt` and `--project` is required. For project export, create the scene project first and set its `audio` field to an existing path relative to its own JSON. This command writes `lyrics` as an array of `{start, end, text}` cues, and `lyricsReview` records approval provenance. The audio file must match the approved recording. Cropping a preview at render time leaves these source-relative timestamps valid.

### Find accents for actions and cuts

```sh
python3 tools/beats.py work/song.mp3 -o work/accents.json --project work/project.json
```

The detector extracts a mono bass envelope, measures attack strength in 10 ms steps and picks locally prominent peaks. `--spacing 0.30` sets a 300 ms minimum separation. The result is a proposed list of accent times for visual motion. Soft acoustic music may have few such peaks, and bass-heavy songs can include offbeat accents. Listen to the selected part, edit `project.beats` if necessary, and use sung line timing for lyrics. Without `--project` the command writes only a separate analysis file.

### Dependencies

- [FFmpeg / ffprobe](https://ffmpeg.org/) for audio reading, excerpts and bass analysis.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for optional CPU speech recognition.
