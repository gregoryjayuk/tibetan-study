"""Textbook PDFs -> lesson store.

    python3 extract/run.py            # repair the six books, parse, write any lesson not yet in the store
    python3 extract/run.py --refresh  # also rewrite lessons already in the store, carrying their English over

Step 1 (fixpdf) rewrites each PDF's ToUnicode maps from the embedded fonts' own cmap+GSUB tables, so
pdftotext yields correct Tibetan stacks. Step 2 (parse_lessons) splits the text into lessons and
sections. Step 3 writes store records (store.py). The repaired PDFs and raw JSON live in extract/work/.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixpdf  # noqa: E402
import parse_lessons  # noqa: E402
import store  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=store.DATA, help='folder holding the textbook PDFs (default: the data folder)')
    ap.add_argument('--work', default=os.path.join(HERE, 'work'))
    ap.add_argument('--refresh', action='store_true', help='rewrite existing store records (English is carried over)')
    a = ap.parse_args()
    fixed = os.path.join(a.work, 'fixed')
    raw = os.path.join(a.work, 'raw')
    os.makedirs(fixed, exist_ok=True)
    os.makedirs(raw, exist_ok=True)
    wrote = kept = 0
    for level, bookno, name in parse_lessons.BOOKS:
        src_pdf = os.path.join(a.src, name + '.pdf')
        fixed_pdf = os.path.join(fixed, name + '.pdf')
        if not os.path.exists(fixed_pdf) or os.path.getmtime(fixed_pdf) < os.path.getmtime(src_pdf):
            fixpdf.main(src_pdf, fixed_pdf)
        lessons = parse_lessons.parse_book(level, bookno, name, fixed_pdf)
        json.dump(lessons, open(os.path.join(raw, name.replace(' ', '_') + '.json'), 'w'), ensure_ascii=False, indent=1)
        for L in lessons:
            new = store.record(L, name + '.pdf')
            old = store.load(L['id'])
            if old is None:
                store.save(new)
                wrote += 1
            elif a.refresh:
                lost = store.carry_english(new, old)
                if lost and old.get('status', {}).get('translated'):
                    print(f"  ! {L['id']}: structure changed in {', '.join(lost)} — English for those parts NOT carried; kept the old record")
                    continue
                store.save(new)
                wrote += 1
            else:
                kept += 1
        print(f"{name}: {len(lessons)} lessons")
    print(f"store: {wrote} written, {kept} left as they were ({store.STORE})")


if __name__ == '__main__':
    main()
