# Walkthrough video

`fresh-desk-walkthrough.mp4` (1080p, 13:50) is the Phase 2 walkthrough with machine narration. `fresh-desk-walkthrough.srt` holds its subtitles; upload both to YouTube as an unlisted video. The narration text, with timestamps, is in [docs/video-script.md](../docs/video-script.md). The MP4 is git-ignored.

## Rebuild after editing the narration

The build needs macOS (`say`), Node with the frontend's Playwright install, and ffmpeg.

1. Start a demo server with a throwaway key so no real key appears on screen:
   `API_KEY=demo-video-key SUPPORT_PASSWORD=demo-support JOB_DB_PATH=/tmp/demo.sqlite3 python -m uvicorn app.main:app --port 8765`
2. Optional: refresh the terminal captures in `term/` with `./capture_terminal.sh term`. This covers the auth, error and job captures; the Docker and test captures were recorded by hand.
3. Edit `scenes.py`, then run `SUPPORT_PASSWORD=demo-support python3 build.py work fresh-desk-walkthrough.mp4`. The `VOICE` and `RATE` environment variables change the narrator, and `FFMPEG` points at a specific ffmpeg binary.
4. Regenerate the script with `python3 script_md.py work/segments ffmpeg ../docs/video-script.md`.

Delete `work/live` to record the dashboard again. Otherwise the existing recording is reused.
