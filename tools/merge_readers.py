"""Merge the English for the graded stories into <data>/readers/<level>.json (data folder: see extract/store.py).

    python3 tools/merge_readers.py path/to/A2.en.json [...]

Each input is a list of {"id", "title_en", "sentences_en": [one per Tibetan sentence], "flags": [...]}.
Only fills English and flags; the Tibetan is never touched. A story whose sentence count differs from the store is refused.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract'))
import store  # noqa: E402


def main(paths):
    for p in paths:
        en = json.load(open(p))
        level = en[0]['id'].split('-')[0]
        path = os.path.join(store.DATA, 'readers', f'{level}.json')
        stories = json.load(open(path))
        by = {s['id']: s for s in stories}
        done = 0
        for t in en:
            s = by.get(t['id'])
            if s is None:
                print(f"{t['id']}: not in {path}, skipped")
                continue
            if len(t['sentences_en']) != len(s['sentences']):
                print(f"{t['id']}: {len(t['sentences_en'])} English lines for {len(s['sentences'])} sentences, refused")
                continue
            s['title']['en'] = t.get('title_en')
            for x, e in zip(s['sentences'], t['sentences_en']):
                x['en'] = e
            s['flags'] = t.get('flags') or []
            done += 1
        json.dump(stories, open(path, 'w'), ensure_ascii=False, indent=1)
        print(f"{level}: English merged for {done} of {len(stories)} stories, "
              f"{sum(len(s.get('flags') or []) for s in stories)} flags -> {path}")


if __name__ == '__main__':
    main(sys.argv[1:])
