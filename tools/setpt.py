# -*- coding: utf-8 -*-
"""Merge translations from a JSON patch file into units/*.pt.json.

Patch format: {"NNNN_cat": {"item_index": "pt text", ...}, ...}
Every index must exist in the matching units/NNNN_cat.en.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sstr as s  # noqa: E402


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        patch = json.load(f)
    for stem, mapping in patch.items():
        with open(os.path.join(s.UNITS, stem + ".en.json"), encoding="utf-8") as f:
            valid = {str(it["i"]) for it in json.load(f)["items"]}
        path = os.path.join(s.UNITS, stem + ".pt.json")
        cur = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                cur = json.load(f)
        for k, v in mapping.items():
            if k not in valid:
                raise SystemExit(f"{stem}: item {k} does not exist")
            cur[k] = v
        cur = dict(sorted(cur.items(), key=lambda kv: int(kv[0])))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"{stem}: {len(mapping)} updated, {len(cur)} total")


if __name__ == "__main__":
    main()
