# -*- coding: utf-8 -*-
"""QA for PT-BR units: coverage, identical-to-English entries, leftover English, OR-line structure."""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sstr as s  # noqa: E402

EN_STOP = re.compile(r"\b(the|and|you|your|with|this|that|will|are|is|of|to|from|into|have|has|can)\b", re.I)


def main():
    total = done = same = empty = leftover = orbad = 0
    report = []
    for p in sorted(glob.glob(os.path.join(s.UNITS, "*.en.json"))):
        name = os.path.basename(p)[:-8]
        ptp = p[:-8] + ".pt.json"
        with open(p, encoding="utf-8") as f:
            items = json.load(f)["items"]
        pt = {}
        if os.path.exists(ptp):
            with open(ptp, encoding="utf-8") as f:
                pt = json.load(f)
        for it in items:
            total += 1
            t = pt.get(str(it["i"]))
            if t is None:
                continue
            done += 1
            if t.strip() == "" and it["en"].strip() != "":
                empty += 1
                report.append(f"EMPTY {name}#{it['i']}")
            elif t == it["en"]:
                same += 1
                report.append(f"SAME  {name}#{it['i']}: {it['en'][:90]}")
            elif len(EN_STOP.findall(t)) >= 3:
                leftover += 1
                report.append(f"ENG?  {name}#{it['i']}: {t[:90]}")
            if s.or_lines(it["en"]) != s.or_lines(t):
                orbad += 1
                report.append(f"OR    {name}#{it['i']}")
    print(f"items={total} translated={done} same_as_en={same} empty={empty} "
          f"english_suspects={leftover} or_mismatch={orbad}")
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    for r in report[:limit]:
        print(r)


if __name__ == "__main__":
    main()
