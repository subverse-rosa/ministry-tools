"""Self-test with the bundled invented song: handoff import, draft gate, stale-export guard and every
library-check status. No church template or private files needed.

    python3 selftest.py
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(HERE, "..", "examples", "handoff")


def run(*args):
    return subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, encoding="utf-8")


def check(lib):
    r = run(os.path.join(HERE, "check_library.py"), lib, "--json")
    return json.loads(r.stdout), r.returncode


def main():
    tmp = tempfile.mkdtemp(prefix="worship-slides-selftest-")
    try:
        song = os.path.join(tmp, "晨光小径")
        os.makedirs(os.path.join(song, "music")); os.makedirs(os.path.join(song, "slides"))
        shutil.copy(os.path.join(EX, "morning-path.mei"), os.path.join(song, "music", "score.mei"))
        shutil.copy(os.path.join(EX, "morning-path.events.json"), os.path.join(song, "music", "events.json"))
        yaml = os.path.join(song, "slides", "song.yaml")
        open(yaml, "w", encoding="utf-8").write(
            "profile: oxblood-library\nservice:\n  - {type: jianpu, handoff: ../music/events.json, score: ../music/score.mei}\n")
        deck = os.path.join(song, "slides", "晨光小径（简谱）.pptx")
        build = os.path.join(HERE, "build_service.py")
        r = run(build, yaml, deck)
        assert r.returncode == 0, r.stderr
        data, code = check(tmp)
        assert code == 0 and [s["status"] for s in data["songs"]] == ["current"], data

        # 1. deck edited by hand -> EDITED
        from pptx import Presentation
        p = Presentation(deck)
        for s in p.slides:
            for sh in s.shapes:
                if sh.has_text_frame and sh.text_frame.text == "路":
                    sh.text_frame.paragraphs[0].runs[0].text = "道"
        edited = deck.replace(".pptx", "-edited.pptx")
        p.save(edited)
        data, code = check(tmp)
        assert code == 1 and sorted(s["status"] for s in data["songs"]) == ["EDITED", "current"], data
        os.remove(edited)

        # 2. score changed, events not re-exported -> EXPORT-OLD, and the build refuses the old export
        score = os.path.join(song, "music", "score.mei")
        text = open(score, encoding="utf-8").read().replace('lyric-version="0.3"', 'lyric-version="0.4"')
        open(score, "w", encoding="utf-8").write(text)
        data, code = check(tmp)
        assert data["songs"][0]["status"] == "EXPORT-OLD", data
        r = run(build, yaml, deck.replace(".pptx", "-x.pptx"))
        assert r.returncode != 0 and "older" in r.stderr, r.stderr

        # 3. events re-exported (simulated) -> STALE until the deck is rebuilt, then current
        ev = os.path.join(song, "music", "events.json")
        h = json.load(open(ev, encoding="utf-8"))
        h["source_sha256"] = hashlib.sha256(open(score, "rb").read()).hexdigest(); h["lyric_version"] = "0.4"
        json.dump(h, open(ev, "w", encoding="utf-8"), ensure_ascii=False)
        data, code = check(tmp)
        assert data["songs"][0]["status"] == "STALE", data
        os.remove(deck)
        assert run(build, yaml, deck).returncode == 0
        data, code = check(tmp)
        assert code == 0 and data["songs"][0]["status"] == "current", data

        # 4. draft lyrics are refused unless allow_draft
        h["lyric_status"] = "draft"
        json.dump(h, open(ev, "w", encoding="utf-8"), ensure_ascii=False)
        r = run(build, yaml, deck.replace(".pptx", "-draft.pptx"))
        assert r.returncode != 0 and "draft" in r.stderr, r.stderr
        print("selftest OK: handoff import, draft gate, old-export guard, current / EDITED / EXPORT-OLD / STALE")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
