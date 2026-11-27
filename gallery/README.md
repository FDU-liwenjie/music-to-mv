# Gallery and credits

These frames come from music videos the project author made before the Blender motion-graphics examples. The two treatments of *Last Summer* use the same song and different visual materials.

| Still | Work | Look for |
| --- | --- | --- |
| [Pixel art](fuji-pixel.jpg) | *Under Mount Fuji* | Two people meet on a snowy street. The wordless crop retains the mountain and the space between them. |
| [Risograph](summer-riso.jpg) | *Last Summer*, DJ remix | Hanging heart posters and overlapping spot colors on warm paper frame the figure. |
| [Watercolor](summer-watercolor.jpg) | *Last Summer*, the same remix | A figure carries an envelope while red letters rise across a line drawing. |

The author created the imagery for the two *Last Summer* studies. Their print and watercolor techniques draw on Lemo-Opuscar. The earlier songs appear here as visual excerpts. The music, fonts and upstream tools retain their respective licenses. [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar)

## Two illustrated studies

Both silent GIFs run for 12 seconds at 480 × 270 and eight frames per second. Their projects use a short original instrumental that can be synthesized locally. The scene notes record the intended meaning of each shot.

- In *Rain Station*, a red coat passes between two people before a train crosses the platform. The station sign uses an arrow. [Watch the loop](rain-station.gif) · [Open the cut-paper project](../examples/rain-station/project.json)
- In *Out of Time*, a spring compresses, a heart-shaped token changes hands and a flight of birds gives way to two clocks that fall out of step. [Watch the loop](out-of-time.gif) · [Open the lyric-visual project](../examples/out-of-time/project.json)

To render the projects with their music, run these commands from the repository root.

```sh
python3 examples/night-train/make_audio.py
node render/cli.mjs examples/rain-station/project.json outputs/rain-station.mp4
node render/cli.mjs examples/out-of-time/project.json outputs/out-of-time.mp4
```

## Photographic and three-dimensional studies

The photographic *Rain Station* uses AI-generated keyframes. The train body, headlight reflections and foreground window frame move independently over the station plate. [Watch the photographic cut](rain-cinema.webp) · [Open the project](../examples/rain-cinema/)

*Last Train After the Rain* follows a modeled train through a three-camera Blender sequence. The three-dimensional *Out of Time* uses two pocket watches whose second hands move at different speeds. Both can render with the original practice instrumental. [Watch the train sequence](blender-station.webp) · [Open the station scene](../examples/blender-station/) · [View the pocket watches](blender-clocks.jpg) · [Open the watch scene](../examples/blender-clocks/)
