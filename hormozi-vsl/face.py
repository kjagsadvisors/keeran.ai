"""On-camera VSLs: line the owner's phone footage up with the voice, scene by scene.

  python3 face.py launches/<name> assets/phone.mp4

The phone take is one recording of the whole script (the same file `vo.py import` cut into lines). For every scene
marked "face": true, this sets "src" to the footage and "in" to the second where that scene's first word is spoken
in the take, minus how far into the scene that word lands on the timeline. The footage then plays in sync with the
voice. Run it after `vo.py import` / `vo.py auphonic` / `vo.py build`, and again after any timeline change.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "launch-video"))
import vo  # noqa: E402  (launch-video's voice module: plan parsing, transcription, word alignment)

if len(sys.argv) < 3:
    sys.exit(__doc__)
proj, footage = sys.argv[1], sys.argv[2]
plan_path, tl_path = os.path.join(proj, "plan.json"), os.path.join(proj, "timeline.json")
plan = vo.load_plan(proj)
timeline = json.load(open(tl_path))
src = os.path.relpath(os.path.abspath(footage), os.path.abspath(proj))

us = vo.utterances(plan)
x = vo.read_audio(os.path.join(proj, src))
heard = vo.transcribe(x)
if not heard:
    sys.exit("no words heard in the footage: is faster-whisper installed (pip3 install faster-whisper)?")
script = [w for u in us for w in u["text"].split()]
times = vo.align(script, heard, 0, len(x) / vo.SR)

raw = json.load(open(plan_path))
k, n_set = 0, 0
for u in us:
    for j, n in zip(u["scenes"], u["n"]):
        sc, tl = raw["scenes"][j], timeline["scenes"][j]
        if sc.get("face"):
            lead = tl["vo_start"] - tl["start"]          # where the first word lands inside the scene
            sc["type"], sc["frame"], sc["src"] = "ui", "none", src
            sc["in"] = round(max(0.0, times[k]["s"] - lead), 3)
            sc.setdefault("cam", "still")
            n_set += 1
            print(f"  scene {j:3d}  in {sc['in']:7.2f} s  {u['text'][:60]}")
        k += n
json.dump(raw, open(plan_path, "w"), indent=1, ensure_ascii=False)
print(f"{n_set} face scene(s) synced to {src}")
