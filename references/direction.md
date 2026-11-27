# Directing movement for a song

Start with one sung phrase. In a narrative treatment, a passenger keeps a paper ticket through three departures, then finally lets go. In a lyric visual for the same feeling, a loop tightens each time the refrain returns and opens on the last sustained note. Both can feel sad. Ask which change the listener wants to watch.

## Turn a preference into a visible choice

| Ask the listener | Try it on screen |
| --- | --- |
| What world does the song inhabit? | For a sports setting, use curved tracks, lane markings and a moving viewpoint. An office can use a glass grid, an access card and the repeating rhythm of closing doors. |
| Where does the feeling begin and end? | For growing restlessness, let a single level line vibrate, split, then cross the frame on the chorus. For devotion giving way to acceptance, return to the same clasped shape and open it a little further each time. |
| Whose attention are we following? | A distant observer can see two figures and the gap between them. A first-person shot can fill the frame with a sleeve, a hand and the corner of the coat it is holding. |
| When should the gesture land? | Time a release to the vocal consonant, an impact to the kick, or a cut to the silence after the phrase. Pick the moment by listening to that particular recording. |
| What should the surface feel like? | A pixel treatment can step through positions on a grid. A risograph print can let two flat inks make a third color where they overlap. A watercolor treatment can spread a wash around a dry center. |
| How should the words appear? | Reserve a legible part of the frame for the approved sung line. A lyric visual can communicate the hook with changing geometry even during a wordless refrain. |

## Score a short sequence in Blender

Give each cue one subject, an initial state, an action and a final pose. For a handoff, establish the coat's color before the second hand enters. Hold both hands on it for a moment, release the first hand, and carry that color through the cut. For a direct reading of “out of time,” keep a stationary tick mark visible beside each moving hand so the difference in speed is easy to read.

- **Silhouette and layers.** Block the subject with a small number of shapes. Place an occluding window frame above a passenger to reveal the face as the train moves. Parent details to the subject that carries them.
- **Rhythm.** Give a strong pose enough screen time to register before the next cut. To build persistence, repeat the action with a shorter pause or greater reach at each return of the chorus.
- **Color.** Give a recurring object one recognizable hue. Change the background or surrounding shapes when the location changes. Test the strongest pose as a small still.
- **Camera.** Hold the framing when relative motion between subjects carries the meaning. A slow push or lateral move serves a shot when it reveals a second object, a change of scale or a new relationship.
- **Editing.** Shape geometry, grouping, motion and color belong in the score. The project places shots, audio and approved lyrics on the original recording's clock. The `meaning` field can hold production notes, including what the audience should notice. [Motion score reference](../scripts/MOTION.md) · [Blender workflow](blender.md)

## Reopening earlier projects

The earlier studies use the same song-relative seconds in UTF-8 JSON. Each `project.json` includes `title`, a project-relative `audio` path, `style`, `mode`, ordered `scenes`, timed `lyrics` and a list of `beats`. The lyric tool writes reviewed cues with `start`, `end` and `text`. Bass analysis suggests beat times for the editor. Trimming a preview preserves the original time coordinates. [Two starter projects](../examples/night-train/) · [Lyric and rhythm tools](../tools/README.md)

| Existing style | What is editable |
| --- | --- |
| `blender` | Geometry, materials, lights, camera and animation in the native Blender file |
| `cinematic` | The photographic plate, crop, masked image layers and optional rain |
| `pixel` | Limited steps in value and edges aligned to a pixel grid |
| `riso` | Spot colors, halftone dots and misregistered ink layers |
| `watercolor` | Transparent washes, wet edges and exposed paper |
| `papercut` | Silhouettes, foreground cutouts, occlusion and cast shadows |
| `lowpoly` | Faceted geometry, perspective and camera movement |
| `typography` | Placement, scale and timing of the active lyric |

For an illustrated scene, use the built-in composition or add project-relative SVG/PNG artwork. Choose `artMode: "background"` for a backdrop and `"foreground"` for an overlay. For example, this four-second shot can be inserted into the scene list of an illustrated project that contains the referenced file.

```json
{
  "start": 8,
  "end": 12,
  "setting": "bridge",
  "action": "release",
  "motif": "boat",
  "emotion": "calm",
  "meaning": "A paper boat leaves an open palm.",
  "art": "art/paper-boat.svg",
  "artMode": "foreground"
}
```

| Illustrated scene field | Values |
| --- | --- |
| `setting` | `station`, `street`, `coast`, `room`, `bridge`, `mountain`, `stage` |
| `action` | `wait`, `walk`, `offer`, `release`, `return`, `reach`, `depart`, `unfold` |
| `motif` | `letter`, `boat`, `flower`, `train`, `umbrella`, `light`, `clock`, `leaf`, `mountain` |
| `emotion` | `calm`, `romantic`, `sad`, `restless`, `determined`, `wild` |

A scene can override the project style. Its `camera` can be `still`, `push`, `pan-left` or `pan-right`. Its `intensity` ranges from 0 to 1. A `palette` of three to five six-digit hex colors can apply to the project or to one scene. In `layers`, each item has a `src` and optional `from` and `to` transforms. The three values give horizontal offset, vertical offset and scale. The default screen coordinates are based on a 960 × 540 frame. For example, `{"src":"art/coat.svg","from":[-80,0,1],"to":[20,0,1.04]}` moves an isolated coat to the right while bringing it slightly closer. [Paper-cut example](../examples/rain-station/) · [Illustrated lyric visual](../examples/out-of-time/)

For a photographic shot, use a JPG or PNG plate in `art`. Its optional `framing.from` and `framing.to` arrays give normalized horizontal center, normalized vertical center and zoom. Centers range from 0 to 1 and zoom starts at 1. Omitting the transform leaves the camera stationary. `rain` ranges from 0 to 1. For a moving train, composite the masked train over an empty platform. A layer with `space: "plate"` uses source pixels and follows the camera crop. A layer with `space: "screen"` can supply a passing window frame. The mask's alpha selects the visible pixels. Set `ease: "perspective"` on a rigid object approaching the camera, and align its translation and scale to the vanishing point. [Photographic example](../examples/rain-cinema/project.json)
