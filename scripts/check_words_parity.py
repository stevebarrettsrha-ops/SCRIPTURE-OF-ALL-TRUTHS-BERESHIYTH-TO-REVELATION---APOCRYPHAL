#!/usr/bin/env python3
"""
check_words_parity.py

assets/words.js repairs a verse in the browser; scripts/sweep_text.py
repairs the same verse on disk. They are two implementations of one set of
rules, so this runs both over every verse of every book and fails if they
ever disagree — the only way to be sure the page and the data stay in step.

Needs node on PATH (only for this check; the site itself never does).

Usage:
    python3 scripts/check_words_parity.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sweep_text  # noqa: E402  (imported for its repair pipeline)

JS_DRIVER = r"""
const fs = require('fs');
global.window = global;
eval(fs.readFileSync(process.argv[2], 'utf8'));
const verses = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
process.stdout.write(JSON.stringify(verses.map(v => BesorahWords.repair(v))));
"""


def main():
    verses, labels = [], []
    for path in sorted((ROOT / "assets" / "text").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for cn, ch in data["chapters"].items():
            for v in ch.get("verses", []):
                verses.append(v["t"])
                labels.append(f"{path.stem} {cn}:{v['n']}")

    tmp_in = ROOT / "scripts" / ".parity-input.json"
    tmp_js = ROOT / "scripts" / ".parity-driver.js"
    tmp_in.write_text(json.dumps(verses, ensure_ascii=False), encoding="utf-8")
    tmp_js.write_text(JS_DRIVER, encoding="utf-8")
    try:
        out = subprocess.run(
            ["node", str(tmp_js), str(ROOT / "assets" / "words.js"), str(tmp_in)],
            capture_output=True, text=True, check=True)
        js = json.loads(out.stdout)
    except FileNotFoundError:
        print("node is not installed — cannot compare the two implementations.")
        return 2
    except subprocess.CalledProcessError as e:
        print("the JavaScript side failed:\n" + e.stderr[:2000])
        return 2
    finally:
        tmp_in.unlink(missing_ok=True)
        tmp_js.unlink(missing_ok=True)

    mismatches = []
    for label, raw, js_out in zip(labels, verses, js):
        py_out = sweep_text.repair(raw)
        if py_out != js_out:
            mismatches.append((label, py_out, js_out))

    print(f"Compared {len(verses)} verses.")
    if not mismatches:
        print("words.js and sweep_text.py agree on every one.")
        return 0
    print(f"{len(mismatches)} disagreements:")
    for label, py_out, js_out in mismatches[:20]:
        print(f"  {label}\n    py: {py_out[:160]!r}\n    js: {js_out[:160]!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
