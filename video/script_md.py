"""Write docs/video-script.md from scenes.py, with start times taken from the built segment lengths."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import caption  # noqa: E402
from scenes import SCENES  # noqa: E402

seg_dir, ffmpeg, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
SHOW = {"slide": "Slide", "terminal": "Terminal capture", "live": "Live dashboard"}


def seconds(mp4):
    err = subprocess.run([ffmpeg, "-i", str(mp4)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


lines = ["# Video walkthrough script", "",
         "Narration for the Phase 2 walkthrough video, one section per scene. The start times match the generated "
         "MP4. To record the video in your own voice, read each section while its scene is on screen.", "",
         "| Start | Scene | On screen |", "| --- | --- | --- |"]
clock, rows, body = 0.0, [], []
for idx, s in enumerate(SCENES):
    mp4 = seg_dir / f"{idx:02d}-{s['id']}.mp4"
    stamp = f"{int(clock // 60):02d}:{int(clock % 60):02d}"
    title = s.get("title") or s["id"].replace("demo_", "Demo: ").replace("_", " ")
    lines.append(f"| {stamp} | {title} | {SHOW[s['kind']]} |")
    body += [f"## {stamp} — {title}", "", *(caption(b["say"]) + "\n" for b in s["beats"])]
    clock += seconds(mp4)
lines += ["", f"Total length: {int(clock // 60)}:{int(clock % 60):02d}.", ""] + body
out.write_text("\n".join(lines), encoding="utf-8")
print(out, f"{clock / 60:.2f} min")
