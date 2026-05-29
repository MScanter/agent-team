# Screenshots

These images are referenced by the root `README.md`. Capturing them is the one
thing that can't be automated — a multi-agent **desktop** app lives or dies on
showing what it looks like, so this is high priority.

## What to capture

Run the app (`npm --prefix backend run tauri:dev`), then grab:

| File | Shot | Notes |
|------|------|-------|
| `execution.gif` | A live discussion running | 5–10s loop, agents streaming responses. The hero image. |
| `home.png` | Home / dashboard | Landing screen. |
| `agents.png` | Agents list or the agent editor | Show a couple of configured agents. |
| `debate.png` | A Debate execution mid-round | Pro/con columns + judge — the most visually distinctive mode. |

## Recommended specs

- **Width:** ~1200–1600px (the app window is 1200×800). Retina is fine.
- **Format:** PNG for stills, GIF (or MP4) for the demo. Keep the GIF under ~5 MB.
- **Content:** use placeholder/demo topics — never show real API keys or private data.

## Wiring them in

Once the files are here, uncomment the image block in the root `README.md`
(the `## Screenshots` section) and delete the placeholder note.

> Tip: macOS `Cmd-Shift-5` records a region to video; convert to GIF with
> `ffmpeg -i demo.mov -vf "fps=12,scale=1000:-1" execution.gif`.
