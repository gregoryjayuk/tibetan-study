"""Merge Chinese glosses ({"id", "vocab_zh", "expressions_zh"}) into the lesson store.

    python3 tools/merge_zh.py extract/work/translate/zh/*.zh.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract'))
import store  # noqa: E402

for p in sys.argv[1:]:
    z = json.load(open(p))
    rec = store.load(z['id'])
    if len(z['vocab_zh']) != len(rec['vocab']) or len(z['expressions_zh']) != len(rec['expressions']):
        print(f"{z['id']}: counts differ — skipped")
        continue
    for v, c in zip(rec['vocab'], z['vocab_zh']):
        v['zh'] = c
    for v, c in zip(rec['expressions'], z['expressions_zh']):
        v['zh'] = c
    store.save(rec)
    print(f"{z['id']}: {len(z['vocab_zh'])} words, {len(z['expressions_zh'])} phrases")
