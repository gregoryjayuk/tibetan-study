"""The graded readers (one PDF per level, named by book_config.READER_PDF) -> <data>/readers/<level>.json

Each PDF is a run of short stories: a line "<n> <title>" then paragraphs. Pages carry the level
name as a header and a page number. Stories come out sorted by number, each split into sentences
(at the shad) so the reader can show a translation per sentence.

    python3 extract/readers.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixpdf  # noqa: E402
import store  # noqa: E402
from book_config import READER_PDF  # noqa: E402
from tibnorm import norm  # noqa: E402

LEVELS = ('A1', 'A2', 'B1')


def sentences(text):
    """split at shad (keeping it); a ག-final sentence has no shad, so keep those joined to the next"""
    parts = re.findall(r'[^།]+།+|[^།]+$', text)
    out = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    return out


def parse(level, pdf):
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
    stories, cur = [], None
    for raw in txt.split('\n'):
        line = norm(raw)
        s = line.strip()
        if not s or re.fullmatch(r'[0-9༠-༩]+', s) or s.startswith('གནས་ཚད'):
            continue
        m = re.match(r'^([0-9]{1,2})\s+(\S.*)$', s)
        if m and len(m.group(2)) < 60:
            cur = {'n': int(m.group(1)), 'title': m.group(2).strip(), 'lines': []}
            stories.append(cur)
            continue
        if cur is not None:
            cur['lines'].append(s)
    out = []
    for k, st in enumerate(sorted(stories, key=lambda x: x['n']), 1):
        text = ''
        for l in st['lines']:
            text = text + l if (not text or text.endswith('་')) else text + ' ' + l
        text = re.sub(r'\s{2,}', ' ', text).strip()
        out.append({'id': f"{level}-R{k:02d}", 'level': level, 'n': st['n'], 'title': {'bo': st['title'], 'en': None},
                    'sentences': [{'bo': x, 'en': None} for x in sentences(text)]})
    return out


def main():
    work = os.path.join(HERE, 'work', 'fixed')
    os.makedirs(work, exist_ok=True)
    dest = os.path.join(store.DATA, 'readers')
    os.makedirs(dest, exist_ok=True)
    for level in LEVELS:
        src = os.path.join(store.DATA, READER_PDF.format(level=level))
        fixed = os.path.join(work, f'{level} readers.pdf')
        if not os.path.exists(fixed) or os.path.getmtime(fixed) < os.path.getmtime(src):
            fixpdf.main(src, fixed)
        stories = parse(level, fixed)
        path = os.path.join(dest, f'{level}.json')
        old = json.load(open(path)) if os.path.exists(path) else []
        # keep any English already added, story by story, when the Tibetan still lines up
        oldby = {o['id']: o for o in old}
        for st in stories:
            o = oldby.get(st['id'])
            if o and len(o['sentences']) == len(st['sentences']):
                st['title']['en'] = o['title'].get('en')
                for a, b in zip(st['sentences'], o['sentences']):
                    a['en'] = b.get('en')
                if o.get('flags'):
                    st['flags'] = o['flags']
        json.dump(stories, open(path, 'w'), ensure_ascii=False, indent=1)
        print(f"{level}: {len(stories)} stories, {sum(len(s['sentences']) for s in stories)} sentences -> {path}")
        for st in stories:
            print(f"   {st['n']:2d} {st['title']['bo']}  ({len(st['sentences'])} sentences)")


if __name__ == '__main__':
    main()
