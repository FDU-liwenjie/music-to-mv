---
name: music-to-mv
description: Make an editable motion-graphics music video from a local song. Use when a user wants a narrative MV or a direct lyric visual, needs to review sung words and timing, or wants to direct shapes, colors, camera framing and rhythm in Blender. Supports instrumental tracks and lyrics in the recording's original language.
---

# Music to MV

Use Blender-native motion graphics for new productions. Build timed cues from paths, fills, masks or foreground occlusion, changes of scale, grouping, rotation and reveals. Make the primary action legible with the sound muted. Keep the recording, its language, the chosen mode and the user's style decisions across revisions. Conduct the conversation in the user's language.

Work from this skill's installation directory. Keep the user's media and work files in a separate production directory. Check for Node.js 20+, Python 3.10+, Blender 4.5 LTS, FFmpeg and ffprobe. Install the bundled Node dependencies with `npm ci` on first use.

## Listen and review the lyrics

- Locate the exact recording. Confirm its length and where the singing starts. Prefer the user's LRC or SRT when available. For audio alone, use the local recognizer. Imported plain text starts with evenly spaced placeholder times that need listening and correction.
- Show the complete numbered, timed review with `python3 tools/lyrics.py show path/to/review.json`. A long song can have a separate readable review file. Flag uncertain lines, preserve repeats and language, and offer to play individual lines. Let the user paste corrections or lyrics they found online. Keep timing intact for word-only corrections.
- Run `approve` only after the user accepts the current draft. Then export an SRT and the lyric cues into the project. During review, a picture-only test is useful. For an instrumental, use an empty lyric track and continue with the art discussion. [Lyric review commands](tools/README.md)

**The only visible words in an MV are the original lyrics at their sung times.** Keep titles, interpretations, style labels, version marks and shot descriptions in the project or conversation. Check the artwork itself for incidental characters. Publish sample prompts, labels, narration and captions in English; preserve the requested language on a specific production.

## Offer two interpretations of one passage

Give the user two short treatments of the same phrase unless they have already chosen. A narrative MV follows a character or recurring object through a decision with a visible consequence. A lyric visual depicts the object, action and relationship in a line. For example, two hands on separate dials can move apart to make lost synchrony visible. Mood does not determine the mode.

Ask about what materially changes the picture. A sports or business setting establishes the world; devotion, calm or restlessness establishes the emotional arc. Pixel, print, watercolor or paper can guide the surface. Translate those choices into two concrete treatments with a dominant color, a physical gesture and a change in pace. Respect a selection already made. [Visual direction](references/direction.md)

## Author the motion score

1. Create the project with `python3 scripts/new_project.py "/path/song.wav" "/path/my-mv" --mode narrative`, or select `lyric-visual`. The default produces a motion score and a Blender scene. Record the actual copied audio filename. Export the reviewed lyrics to `project.json`. Use `tools/beats.py` when accent candidates would help, and listen before choosing which ones deserve motion.
2. Describe each cue in terms of its subject, starting state, action, ending state and musical or lyrical trigger. Keep a recognizable element across a cut. Use a hold before a reveal, a shared pivot to show connection or an occluding shape to carry an exit. A repeated chorus should advance the action.
3. Replace the starter cues with artwork for this song. Edit `motion.json` using the documented score fields. Object-key times are local to each cue. Choose a framing that makes each action visible. For a handoff, establish the distance between the people, come close enough to see who grips the fabric, then return to the platform when the train clears. For a comparison, a held camera can keep both subjects legible. Compare the opening, the strongest beat and a quiet interval at phone size. Check silhouettes, overlaps and color contrast. [Score fields and examples](scripts/MOTION.md)
4. Run `python3 scripts/build_mg.py /path/my-mv/motion.json --output /path/my-mv/scene.blend` after editing the score. Use the native scene directly for final refinements when practical. Preserve hand-edited .blend variants independently of generated outputs. Previously authored projects with an explicit renderer or supplied native scene keep their own path. [Blender details](references/blender.md)

## Preview and deliver

Render 8–15 seconds from an expressive passage, or a shorter complete phrase when appropriate. The range must fit the audio and the score. For example:

```sh
node render/cli.mjs /path/my-mv/project.json /path/my-mv/preview.mp4 --start 12 --duration 8 --width 960 --height 540 --fps 24
```

Share the playable excerpt, its source range and one concrete decision the user can change. Once directed to finish, cover the remaining recording and export the complete piece. Verify the streams and duration with ffprobe. Inspect the frames around cuts, large movements, sung entrances and lyric gaps. Listen across a repeated line. Deliver the MP4, subtitle file when applicable, the motion score, the song project, and the editable Blender scene with any required assets. Keep public examples and their media separate from personal recordings.
