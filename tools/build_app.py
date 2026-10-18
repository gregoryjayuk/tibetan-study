"""Build the study app's data and publish the app into the data folder.

    python3 tools/build_app.py                          # data folder: $TIBETAN_DATA, or store.DATA's default
    TIBETAN_DATA=demo python3 tools/build_app.py        # build the bundled demo

Reads   <data>/lessons/<level>/<id>.json   (the textbook, canonical)
        <data>/class/<date>.json           (class notes, canonical)
        <data>/readers/<level>.json        (graded stories)
Writes  <data>/app/content.json            (everything the app shows, in one file)
        <data>/app/index.html              (copied from app/web/index.html)

Both the desktop server (app/server.py) and the phone (the Android shell) load the app and its data
from that app/ folder, so when the folder is synced a rebuild reaches the phone with no reinstall.
"""
import datetime
import glob
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'extract'))
import store  # noqa: E402

DATA = store.DATA
OUT = os.path.join(DATA, 'app')
COURSE_LEVELS = ('A2', 'B1')      # the path he is made to walk, in order
EXTRA_LEVELS = ('A1',)            # available, not enforced

LETTER = r'[ཀ-ྼ]'


def fill_gap(sentence, fill):
    parts = [p.strip() for p in fill.split('…')]
    s = sentence
    for p in parts:
        if '＿＿' not in s:
            break
        s = re.sub(r'\s*＿＿\s*', '\x00' + p + '\x01', s, count=1)
    if '＿＿' in s:
        return None
    # glue the filled word to its neighbours with a tsheg where a syllable boundary needs one
    s = re.sub(r'(' + LETTER + r')\x00', r'\1་', s)
    s = re.sub(r'\x00', '', s)
    s = re.sub(r'(' + LETTER + r')\x01(?=' + LETTER + ')', r'\1་', s)
    s = s.replace('\x01', '')
    return re.sub(r'་་+', '་', s)


def lesson_out(r):
    tr = bool(r['status'].get('translated'))
    pats = []
    for st in r['exercises']['gaps']['sets']:
        for it in st['items']:
            if it.get('fill') and it.get('en') and not it.get('unsure'):
                full = fill_gap(it['bo'], it['fill'])
                if full:
                    pats.append({'bo': full, 'en': it['en']})
    g = r['grammar']
    return {
        'id': r['id'], 'level': r['level'], 'book': r['book'], 'pages': r['pages'], 'ready': tr,
        'title': r['title'], 'topic': r['topic'], 'goals': r['goals'],
        'vocab': [{k: v.get(k) for k in ('n', 'bo', 'en', 'zh', 'ex', 'ex_en', 'note')} for v in r['vocab']],
        'phrases': [{k: v.get(k) for k in ('n', 'bo', 'en', 'zh', 'note')} for v in r['expressions']],
        'grammar': {'patterns': g['patterns'], 'en': g.get('pattern_en'), 'notes': g.get('notes'), 'examples': g['examples']},
        'patterns': pats,
        'dialogue': r['dialogue'],
        'proverb': r['proverb'],
        'culture': r['culture'],
        'talk': r['exercises']['talk'],
    }


def main():
    lessons, course, extra = {}, [], []
    for p in sorted(glob.glob(os.path.join(store.STORE, '*', '*.json'))):
        r = json.load(open(p))
        lessons[r['id']] = lesson_out(r)
    order = sorted(lessons)
    course = [i for lv in COURSE_LEVELS for i in order if i.startswith(lv + '.')]
    extra = [i for lv in EXTRA_LEVELS for i in order if i.startswith(lv + '.')]
    classes = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(DATA, 'class', '*.json')))]
    readers = {}
    for p in sorted(glob.glob(os.path.join(DATA, 'readers', '*.json'))):
        readers[os.path.basename(p)[:-5]] = json.load(open(p))
    content = {
        'built': datetime.datetime.now().isoformat(timespec='seconds'),
        'course': course, 'extra': extra, 'lessons': lessons, 'classes': classes, 'readers': readers,
    }
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, 'content.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(content, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, os.path.join(OUT, 'content.json'))
    shutil.copyfile(os.path.join(ROOT, 'app', 'web', 'index.html'), os.path.join(OUT, 'index.html'))
    for d in ('progress', 'inbox'):
        os.makedirs(os.path.join(DATA, d), exist_ok=True)
    ready = sum(1 for i in course if lessons[i]['ready'])
    items = sum(len(c['items']) for c in classes)
    size = os.path.getsize(os.path.join(OUT, 'content.json')) // 1024
    print(f"content.json: {len(course)} course lessons ({ready} with English), {len(extra)} A1, "
          f"{len(classes)} classes ({items} items), {sum(len(v) for v in readers.values())} stories — {size} KB")


if __name__ == '__main__':
    main()
