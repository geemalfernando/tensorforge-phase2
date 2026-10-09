"""Build the walkthrough video: narration (macOS say) + HTML slides + live dashboard capture -> MP4 + SRT.

usage: python3 build.py <work_dir> <output.mp4> [--only-slides]
env:   FFMPEG, BASE_URL (dashboard), VOICE, RATE
"""
import html
import json
import os
import re
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scenes import SCENES  # noqa: E402

FF = os.environ.get("FFMPEG", "ffmpeg")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8765")
VOICE = os.environ.get("VOICE", "Daniel")
RATE = os.environ.get("RATE", "192")
GAP, LEAD, TAIL, FPS = 0.45, 0.5, 0.7, 30
WORK = OUT = None

# ------------------------------------------------------------------ text
SPEECH = [("SQLite", "sequel lite"), ("OpenAPI", "Open A P I"), ("FastAPI", "Fast A P I"), ("RideEat", "Ride Eat"),
          ("n-grams", "en grams"), ("n-gram", "en gram"), ("JSON", "jason"), ("Fresh Desk", "Fresh Desk")]
CAPTION = [("four hundred and eighty five", "485"), ("T F I D F", "TF-IDF"), ("SHA two fifty six", "SHA-256"),
           ("W W W Authenticate", "WWW-Authenticate"), ("X API Key", "X-API-Key"), ("Retry After", "Retry-After"),
           ("Idempotency Key", "Idempotency-Key"), ("draft twenty twenty", "draft 2020-12"), ("macro F 1", "macro-F1"),
           ("I Ds", "IDs"), (" I D", " ID"), ("A I ", "AI "), ("four oh one", "401"), ("four oh nine", "409"),
           ("four oh four", "404"), ("two oh two", "202"), ("four twenty two", "422"), ("four fifteen", "415"),
           ("four hundred", "400"), ("two hundred straight", "200 straight"), ("API key environment variable", "API_KEY environment variable")]


def speech(text):
    for a, b in SPEECH:
        text = text.replace(a, b)
    return text


def caption(text):
    for a, b in CAPTION:
        text = text.replace(a, b)
    return text


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def wav_seconds(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


# ------------------------------------------------------------------ narration
def tts():
    for s in SCENES:
        for i, b in enumerate(s["beats"]):
            out = WORK / "audio" / f"{s['id']}-{i}.wav"
            txt = WORK / "audio" / f"{s['id']}-{i}.txt"
            spoken = speech(b["say"])
            if not out.exists() or txt.read_text() != spoken:
                txt.write_text(spoken)
                run(["say", "-v", VOICE, "-r", RATE, "--file-format=WAVE", "--data-format=LEI16@48000",
                     "-o", str(out), "-f", str(txt)])
            b["dur"] = wav_seconds(out)
            b["wav"] = out


# ------------------------------------------------------------------ slides
CSS = """
:root{--ink:#0f2a25;--deep:#133d36;--teal:#0f9f8a;--lime:#b7e35a;--muted:#5b6f6a;--line:#dbe7e2;--bg:#f5faf7;--bad:#c2410c;--warn:#b7791f}
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;overflow:hidden;font-family:-apple-system,"SF Pro Display","Helvetica Neue",Arial,sans-serif;color:var(--ink);
 background:radial-gradient(1200px 700px at 85% -10%,#dff3ea 0,transparent 60%),radial-gradient(900px 600px at -10% 110%,#eef8d9 0,transparent 55%),var(--bg)}
.frame{position:absolute;inset:0;padding:96px 120px 80px}
.brand{position:absolute;left:120px;bottom:44px;font-size:20px;color:var(--muted);letter-spacing:.02em}
.brand b{color:var(--deep)}
.kicker{font-size:22px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:var(--teal);display:flex;align-items:center;gap:14px}
.kicker:before{content:"";width:12px;height:12px;border-radius:50%;background:var(--lime);box-shadow:0 0 0 6px #b7e35a33}
h1{font-size:68px;line-height:1.05;letter-spacing:-.035em;margin:22px 0 46px;font-weight:800;max-width:1500px}
.hide{opacity:0}
ul.items{list-style:none;display:flex;flex-direction:column;gap:26px}
ul.items li{font-size:36px;line-height:1.3;padding-left:46px;position:relative;color:#1d3a34}
ul.items li:before{content:"";position:absolute;left:0;top:15px;width:18px;height:18px;border-radius:6px;background:var(--teal)}
.card{background:#fff;border:1px solid var(--line);border-radius:28px;box-shadow:0 24px 60px -40px #133d3655}
.dark{background:linear-gradient(135deg,#133d36,#0c2823);color:#eaf6f1;border:none}
code,.mono{font-family:"SF Mono",Menlo,monospace}
"""


def page(body):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}" \
           f"<div class='brand'><b>Fresh Desk</b> · TensorForge 2.0 Phase 2</div></body></html>"


def vis(i, show):
    return "" if i < show else " hide"


def esc(x):
    return html.escape(str(x))


def slide_title(s, show):
    chips = "".join(f"<span class='chip{vis(i, show)}'>{esc(t)}</span>" for i, t in enumerate(s["items"]))
    return page(f"""<style>.hero{{position:absolute;inset:70px;border-radius:44px;padding:120px 110px;overflow:hidden}}
 .hero:after{{content:"";position:absolute;right:-180px;top:-180px;width:760px;height:760px;border-radius:50%;border:1px solid #ffffff22;box-shadow:0 0 0 90px #ffffff07,0 0 0 180px #ffffff05}}
 .hero .kicker{{color:var(--lime)}} .hero h1{{font-size:150px;margin:36px 0 24px;color:#fff}}
 .sub{{font-size:44px;color:#cfe7df;max-width:1300px;line-height:1.25}}
 .chips{{display:flex;flex-wrap:wrap;gap:18px;margin-top:80px;max-width:1500px}}
 .chip{{font-size:28px;padding:16px 28px;border-radius:999px;border:1px solid #ffffff33;color:#eaf6f1;background:#ffffff0d}}
 .chip.mono{{font-family:"SF Mono",Menlo,monospace}}</style>
 <div class='hero dark card'><div class='kicker'>{esc(s['kicker'])}</div><h1>{esc(s['title'])}</h1>
 <p class='sub'>{esc(s['subtitle'])}</p><div class='chips'>{chips}</div></div>""")


def slide_bullets(s, show):
    li = "".join(f"<li class='{vis(i, show)}'>{esc(t)}</li>" for i, t in enumerate(s["items"]))
    return page(f"<div class='frame'><div class='kicker'>{esc(s['kicker'])}</div><h1>{esc(s['title'])}</h1>"
                f"<ul class='items'>{li}</ul></div>")


def slide_table(s, show):
    li = "".join(f"<li class='{vis(i, show)}'>{t.split(' — ')[0] and '<code>' + esc(t.split(' — ')[0]) + '</code> — ' + esc(t.split(' — ')[1])}</li>"
                 for i, t in enumerate(s["items"]))
    rows = "".join(f"<tr><td><code>{esc(c)}</code></td><td>{esc(t)}</td></tr>" for c, t in s["table"])
    return page(f"""<style>.cols{{display:grid;grid-template-columns:1fr 760px;gap:70px}} ul.items li{{font-size:32px}}
 ul.items code{{color:var(--deep);font-weight:700}} table{{width:100%;border-collapse:collapse;font-size:25px}}
 td{{padding:13px 26px;border-bottom:1px solid var(--line)}} tr:last-child td{{border:none}} td code{{color:var(--teal);font-size:23px}}
 th{{text-align:left;padding:18px 26px;font-size:20px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}</style>
 <div class='frame'><div class='kicker'>{esc(s['kicker'])}</div><h1>{esc(s['title'])}</h1>
 <div class='cols'><ul class='items'>{li}</ul><div class='card' style='padding:10px 0'><table><tr><th>category</th><th>team</th></tr>{rows}</table></div></div></div>""")


def slide_architecture(s, show):
    def box(i, cls, title, body):
        return f"<div class='box {cls}{vis(i, show)}'><h3>{title}</h3>{body}</div>"
    steps = "".join(f"<span>{a}<b>{c}</b></span>" for a, c in
                    (("auth", "401"), ("content-type", "415"), ("size", "413"), ("JSON", "400"), ("validation", "422")))
    return page(f"""<style>
 .arch{{position:relative;height:740px;margin-top:-10px}}
 .box{{position:absolute;background:#fff;border:2px solid var(--line);border-radius:26px;padding:26px 30px;box-shadow:0 24px 60px -40px #133d3666}}
 .box h3{{font-size:31px;margin-bottom:12px;letter-spacing:-.01em}} .box p{{font-size:23px;color:var(--muted);line-height:1.4}}
 .judges{{left:0;top:70px;width:440px}} .browser{{left:0;top:390px;width:440px}}
 .api{{left:590px;top:120px;width:560px;height:500px;border-color:var(--teal)}} .api h3{{font-size:28px}}
 .model{{left:1250px;top:40px;width:410px}} .jobs{{left:1250px;top:420px;width:410px}}
 .chain{{display:flex;flex-direction:column;gap:12px;margin-top:20px}}
 .chain span{{display:flex;justify-content:space-between;font-size:25px;padding:10px 18px;border-radius:14px;background:#eef7f3}}
 .chain b{{font-family:"SF Mono",Menlo,monospace;color:var(--bad)}}
 .docker{{position:absolute;left:555px;top:0;width:1125px;height:740px;border:3px dashed var(--teal);border-radius:40px;background:#0f9f8a08}}
 .docker .tag{{position:absolute;bottom:18px;right:34px;font-size:24px;font-weight:700;color:var(--teal)}}
 .arrow{{position:absolute;height:4px;background:var(--deep);border-radius:4px}}
 .arrow:after{{content:"";position:absolute;right:-4px;top:-9px;border:11px solid transparent;border-left:16px solid var(--deep)}}
 </style>
 <div class='frame' style='padding-top:80px'><div class='kicker'>{esc(s['kicker'])}</div><h1 style='margin-bottom:40px'>{esc(s['title'])}</h1>
 <div class='arch'>
 <div class='docker{vis(5, show)}'><div class='tag'>Docker image · --network none · API_KEY from env</div></div>
 {box(0, 'judges', "Judges' harness", "<p>Calls the API directly<br><code>X-API-Key</code> or <code>Authorization: Bearer</code></p>")}
 {box(1, 'browser', 'Fresh Desk dashboard', "<p>Same-origin <code>/dashboard/api</code><br>server adds the key — never in the browser</p>")}
 {box(2, 'api', 'FastAPI · checks in contract order', f"<div class='chain'>{steps}</div>")}
 {box(3, 'model', 'Ticket model', "<p>3 trained pipelines<br>+ fixed category → team map<br>+ consistency rules</p>")}
 {box(4, 'jobs', 'Async batch jobs', "<p>Background worker<br>SQLite job + result store<br>≤ 5,000 tickets per job</p>")}
 <div class='arrow{vis(0, show)}' style='left:445px;top:175px;width:135px'></div>
 <div class='arrow{vis(1, show)}' style='left:445px;top:495px;width:135px'></div>
 <div class='arrow{vis(3, show)}' style='left:1155px;top:200px;width:85px'></div>
 <div class='arrow{vis(4, show)}' style='left:1155px;top:520px;width:85px'></div>
 </div></div>""")


def slide_stats(s, show):
    cards = "".join(f"<div class='card st'><b>{esc(a)}</b><span>{esc(b)}</span></div>" for a, b in s["stats"])
    li = "".join(f"<li class='{vis(i, show)}'>{esc(t)}</li>" for i, t in enumerate(s["items"]))
    return page(f"""<style>.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:28px;margin-bottom:56px}}
 .st{{padding:34px 38px}} .st b{{display:block;font-size:64px;letter-spacing:-.03em;color:var(--deep)}} .st span{{font-size:26px;color:var(--muted)}}
 ul.items li{{font-size:32px}}</style>
 <div class='frame'><div class='kicker'>{esc(s['kicker'])}</div><h1>{esc(s['title'])}</h1><div class='stats'>{cards}</div><ul class='items'>{li}</ul></div>""")


def slide_models(s, show):
    cards = "".join(
        f"<div class='card m{vis(i, show)}'><div class='n'>MODEL 0{i + 1}</div><h3>{esc(n)}</h3><p class='algo'>{esc(a)}</p>"
        + "".join(f"<p class='d mono'>{esc(x)}</p>" for x in d) + "</div>"
        for i, (n, a, d) in enumerate(s["models"]))
    li = "".join(f"<li class='{vis(i + 3, show)}'>{esc(t)}</li>" for i, t in enumerate(s["items"]))
    return page(f"""<style>.ms{{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;margin-bottom:54px}}
 .m{{padding:36px 38px}} .n{{font-size:19px;letter-spacing:.24em;color:var(--teal);font-weight:700}}
 .m h3{{font-size:40px;margin:16px 0 6px}} .algo{{font-size:27px;color:var(--muted);margin-bottom:22px}}
 .d{{font-size:19px;padding:10px 14px;background:#eef7f3;border-radius:12px;margin-top:10px}} ul.items li{{font-size:30px}}</style>
 <div class='frame'><div class='kicker'>{esc(s['kicker'])}</div><h1>{esc(s['title'])}</h1><div class='ms'>{cards}</div><ul class='items'>{li}</ul></div>""")


def slide_timeline(s, show):
    color = {"neutral": "var(--muted)", "warn": "var(--warn)", "bad": "var(--bad)", "good": "var(--teal)"}
    rows = "".join(
        f"<div class='row{vis(i, show)}'><i style='background:{color[k]}'></i><b>{esc(a)}</b><span>{esc(b)}</span></div>"
        for i, (a, b, k) in enumerate(s["steps"]))
    return page(f"""<style>.tl{{display:flex;flex-direction:column;gap:22px;position:relative;padding-left:10px}}
 .tl:before{{content:"";position:absolute;left:24px;top:30px;bottom:30px;width:3px;background:var(--line)}}
 .row{{display:grid;grid-template-columns:32px 460px 1fr;align-items:center;gap:30px;background:#fff;border:1px solid var(--line);border-radius:22px;padding:24px 30px;position:relative}}
 .row i{{width:26px;height:26px;border-radius:50%;margin-left:-14px}} .row b{{font-size:32px}} .row span{{font-size:30px;color:#2c4842}}</style>
 <div class='frame'><div class='kicker'>{esc(s['kicker'])}</div><h1>{esc(s['title'])}</h1><div class='tl'>{rows}</div></div>""")


def slide_results(s, show):
    cards = "".join(f"<div class='card st'><b>{esc(a)}</b><span>{esc(b)}</span><em>{esc(c)}</em></div>" for a, b, c in s["stats"])
    bars = "".join(f"<div class='bar'><code>{esc(n)}</code><div><i style='width:{v * 100:.0f}%'></i></div><b>{v:.2f}</b></div>"
                   for n, v in s["bars"])
    langs = "".join(f"<div class='bar'><code>{esc(n)}</code><div><i class='l' style='width:{v * 100:.0f}%'></i></div><b>{v * 100:.0f}%</b></div>"
                    for n, v in s["langs"])
    return page(f"""<style>.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:26px;margin:-10px 0 40px}}
 .st{{padding:26px 32px}} .st b{{display:block;font-size:54px;letter-spacing:-.03em;color:var(--deep)}} .st span{{font-size:24px;display:block}} .st em{{font-size:21px;color:var(--muted);font-style:normal}}
 .two{{display:grid;grid-template-columns:1.25fr 1fr;gap:40px}} .panel{{padding:28px 34px}}
 .panel h4{{font-size:20px;letter-spacing:.2em;text-transform:uppercase;color:var(--teal);margin-bottom:14px}}
 .bar{{display:grid;grid-template-columns:270px 1fr 70px;align-items:center;gap:16px;margin:7px 0;font-size:21px}}
 .bar div{{height:16px;background:#edf3f0;border-radius:8px;overflow:hidden}} .bar i{{display:block;height:100%;background:linear-gradient(90deg,#0f9f8a,#b7e35a)}}
 .bar i.l{{background:linear-gradient(90deg,#133d36,#0f9f8a)}} .bar b{{text-align:right}} h1{{margin-bottom:34px}}</style>
 <div class='frame' style='padding-top:80px'><div class='kicker'>{esc(s['kicker'])}</div><h1>{esc(s['title'])}</h1>
 <div class='stats{vis(0, show)}'>{cards}</div>
 <div class='two'><div class='card panel{vis(1, show)}'><h4>Category F1 by class</h4>{bars}</div>
 <div class='card panel{vis(2, show)}'><h4>Category accuracy by language</h4>{langs}</div></div></div>""")


def terminal_blocks(path):
    blocks, cur = [], []
    for line in Path(path).read_text().splitlines():
        if line.startswith("$ ") and cur:
            blocks.append(cur)
            cur = []
        if line.strip() or cur:
            cur.append(line)
    if cur:
        blocks.append(cur)
    return [[l for l in b] for b in blocks]


def slide_terminal(s, show, term_dir):
    blocks = terminal_blocks(term_dir / s["file"])
    lines = sum(len(b) + 1 for b in blocks)
    size = max(15, min(25, int(760 / (lines * 1.42))))
    out = []
    for i, b in enumerate(blocks):
        body = []
        for line in b:
            e = esc(line)
            if line.startswith("$ "):
                e = re.sub(r"(\s#\s.*)$", r"<span class='cm'>\1</span>", e)
                body.append(f"<div class='cmd'>{e}</div>")
            else:
                e = re.sub(r"(→ HTTP (\d)\d\d|HTTP/1\.1 \d\d\d [A-Za-z ]+)",
                           lambda m: f"<span class='st s{(m.group(2) or m.group(1)[9])}'>{m.group(1)}</span>", e)
                body.append(f"<div>{e}</div>")
        out.append(f"<div class='blk{vis(i, show)}'>{''.join(body)}</div>")
    return page(f"""<style>.term{{margin-top:-6px;border-radius:24px;background:#0d1f1b;box-shadow:0 30px 80px -40px #000a;overflow:hidden}}
 .bar3{{height:52px;background:#16302a;display:flex;align-items:center;gap:12px;padding:0 24px}} .bar3 i{{width:15px;height:15px;border-radius:50%;background:#ff5f57}}
 .bar3 i:nth-child(2){{background:#febc2e}} .bar3 i:nth-child(3){{background:#28c840}} .bar3 span{{margin-left:16px;color:#8fb5aa;font-size:19px;font-family:"SF Mono",Menlo,monospace}}
 .tb{{padding:26px 34px;font-family:"SF Mono",Menlo,monospace;font-size:{size}px;line-height:1.42;color:#cfe2dc;white-space:pre-wrap;word-break:break-all;height:{int(1080 - 330)}px}}
 .blk{{margin-bottom:{size * 0.75:.0f}px}} .cmd{{color:#b7e35a}} .cm{{color:#7f9c94}} .st{{font-weight:700;padding:0 6px;border-radius:6px}}
 .s2{{background:#14532d;color:#bbf7d0}} .s4{{background:#7c2d12;color:#fed7aa}} h1{{font-size:54px;margin:16px 0 30px}}</style>
 <div class='frame' style='padding-top:70px'><div class='kicker'>{esc(s['kicker'])}</div><h1>{esc(s['title'])}</h1>
 <div class='term'><div class='bar3'><i></i><i></i><i></i><span>zsh — URL=http://localhost:8765 · key from $API_KEY (not shown)</span></div><div class='tb'>{''.join(out)}</div></div></div>""")


LAYOUTS = dict(title=slide_title, bullets=slide_bullets, table=slide_table, architecture=slide_architecture,
               stats=slide_stats, models=slide_models, timeline=slide_timeline, results=slide_results)


def render_slides():
    jobs = []
    for s in SCENES:
        if s["kind"] == "live":
            continue
        for i, b in enumerate(s["beats"]):
            h = (slide_terminal(s, b["show"], HERE / "term") if s["kind"] == "terminal"
                 else LAYOUTS[s["layout"]](s, b["show"]))
            hp = WORK / "html" / f"{s['id']}-{i}.html"
            hp.write_text(h, encoding="utf-8")
            b["png"] = WORK / "slides" / f"{s['id']}-{i}.png"
            jobs.append([str(hp), str(b["png"])])
    (WORK / "render.json").write_text(json.dumps(jobs))
    run(["node", str(HERE / "render.cjs"), str(WORK / "render.json")])


# ------------------------------------------------------------------ segments
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def scene_audio(s, offsets, total, out):
    """Mix beat wavs at given offsets (seconds) into one track of length total."""
    inputs, filters = [], []
    for i, (b, off) in enumerate(zip(s["beats"], offsets)):
        inputs += ["-i", str(b["wav"])]
        filters.append(f"[{i}:a]aresample=48000,adelay={int(off * 1000)}|{int(off * 1000)}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(s["beats"])))
    filters.append(f"{mix}amix=inputs={len(s['beats'])}:normalize=0,apad,atrim=0:{total:.3f}[out]")
    run([FF, "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]",
         "-ac", "2", "-ar", "48000", str(out)])


def slide_segment(s, idx):
    offsets, t = [], LEAD
    lines = ["ffconcat version 1.0"]
    for i, b in enumerate(s["beats"]):
        offsets.append(t)
        d = b["dur"] + GAP + (LEAD if i == 0 else 0) + (TAIL if i == len(s["beats"]) - 1 else 0)
        lines += [f"file '{b['png']}'", f"duration {d:.3f}"]
        t += b["dur"] + GAP
    lines.append(f"file '{s['beats'][-1]['png']}'")
    total = t - GAP + TAIL + GAP
    cc = WORK / "segments" / f"{idx:02d}-{s['id']}.ffconcat"
    cc.write_text("\n".join(lines))
    wav = WORK / "segments" / f"{idx:02d}-{s['id']}.wav"
    scene_audio(s, offsets, total, wav)
    out = WORK / "segments" / f"{idx:02d}-{s['id']}.mp4"
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(cc), "-i", str(wav),
         "-vf", f"fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.35,fade=t=out:st={total - 0.35:.3f}:d=0.35",
         "-t", f"{total:.3f}", *ENC, str(out)])
    return out, offsets, total


def record_live():
    durs = {s["id"]: [b["dur"] for b in s["beats"]] for s in SCENES if s["kind"] == "live"}
    (WORK / "live_durations.json").write_text(json.dumps(durs))
    live_dir = WORK / "live"
    if not (live_dir / "timeline.json").exists():
        run(["node", str(HERE / "live.cjs"), BASE_URL, str(WORK / "live_durations.json"), str(live_dir)])
    return json.loads((live_dir / "timeline.json").read_text())


def live_segment(s, idx, rec):
    beats = rec["timeline"][s["id"]]
    t0 = beats[0]["start"] - LEAD
    t1 = beats[-1]["end"] + TAIL
    frames = [f for f in rec["frames"] if f["t"] <= t1]
    # Frame shown at t0 is the last one emitted at or before t0.
    first = max([i for i, f in enumerate(frames) if f["t"] <= t0] or [0])
    use = frames[first:]
    lines = ["ffconcat version 1.0"]
    for i, f in enumerate(use):
        start = max(f["t"], t0)
        end = use[i + 1]["t"] if i + 1 < len(use) else t1
        if end - start <= 0:
            continue
        lines += [f"file '{WORK / 'live' / 'frames' / f['name']}'", f"duration {end - start:.4f}"]
    lines.append(f"file '{WORK / 'live' / 'frames' / use[-1]['name']}'")
    total = t1 - t0
    cc = WORK / "segments" / f"{idx:02d}-{s['id']}.ffconcat"
    cc.write_text("\n".join(lines))
    offsets = [b["start"] - t0 for b in beats]
    wav = WORK / "segments" / f"{idx:02d}-{s['id']}.wav"
    scene_audio(s, offsets, total, wav)
    out = WORK / "segments" / f"{idx:02d}-{s['id']}.mp4"
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(cc), "-i", str(wav),
         "-vf", f"scale=1920:1080:flags=lanczos,fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.35,fade=t=out:st={total - 0.35:.3f}:d=0.35",
         "-t", f"{total:.3f}", *ENC, str(out)])
    return out, offsets, total


# ------------------------------------------------------------------ captions
def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def captions(timeline):
    cues = []
    for s, start, offsets in timeline:
        for b, off in zip(s["beats"], offsets):
            text = caption(b["say"])
            parts = [p.strip() for p in re.split(r"(?<=[.!?:])\s+", text) if p.strip()]
            # split long sentences at commas so each cue stays readable
            chunks = []
            for p in parts:
                while len(p) > 110:
                    cut = p.rfind(", ", 0, 100)
                    cut = cut if cut > 30 else p.rfind(" ", 0, 100)
                    chunks.append(p[:cut + 1].strip())
                    p = p[cut + 1:].strip()
                chunks.append(p)
            total_chars = sum(len(c) for c in chunks)
            t = start + off
            for c in chunks:
                d = b["dur"] * len(c) / total_chars
                cues.append((t, t + d, c))
                t += d
    return "\n".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{c}\n" for i, (a, b, c) in enumerate(cues, 1))


def main():
    global WORK, OUT
    WORK, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    for d in ("audio", "slides", "html", "segments", "live"):
        (WORK / d).mkdir(parents=True, exist_ok=True)
    tts()
    render_slides()
    if "--only-slides" in sys.argv:
        return
    rec = record_live()
    segs, timeline, clock = [], [], 0.0
    for idx, s in enumerate(SCENES):
        out, offsets, total = (live_segment(s, idx, rec) if s["kind"] == "live" else slide_segment(s, idx))
        dur = total
        segs.append(out)
        timeline.append((s, clock, offsets))
        clock += dur
        print(f"{idx:02d} {s['id']:<14} {total:6.1f}s  (t={clock / 60:5.2f} min)", flush=True)
    lst = WORK / "segments" / "all.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
         "-movflags", "+faststart", str(OUT)])
    OUT.with_suffix(".srt").write_text(captions(timeline), encoding="utf-8")
    print(f"done: {OUT}  {clock / 60:.2f} min")


if __name__ == "__main__":
    main()
