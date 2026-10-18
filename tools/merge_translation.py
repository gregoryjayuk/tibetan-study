"""Merge an English layer (<id>.en.json, the shape checked by extract/trans_schema_check.py) into the lesson store.

    python3 tools/merge_translation.py path/to/A2.01.01.en.json [...]

Only fills fields; the Tibetan is never touched. Counts must line up with the store record or the file is refused.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract'))
import store  # noqa: E402


def _tibetan_text(rec):
    return json.dumps(rec, ensure_ascii=False)


def _still_there(flag, rec):
    """a flag about text the extraction has since cleaned up (e.g. a stray space) is dropped"""
    txt = (flag.get('text') or '').strip()
    tib = ''.join(ch for ch in txt if '\u0F00' <= ch <= '\u0FFF' or ch == ' ')
    return not tib.strip() or tib.strip() in _tibetan_text(rec)


def merge(t, rec):
    def need(a, b, what):
        if len(a) != len(b):
            raise ValueError(f"{rec['id']}: {what} count {len(a)} != store {len(b)}")
    rec['topic'] and rec['topic'].update(en=t.get('topic_en'))
    rec['title'] and rec['title'].update(en=t.get('title_en'))
    if rec['goals']['talk']:
        rec['goals']['talk']['en'] = t.get('goal_talk_en')
    if rec['goals']['grammar']:
        rec['goals']['grammar']['en'] = t.get('goal_grammar_en')
    need(t['vocab'], rec['vocab'], 'vocab')
    for v, e in zip(rec['vocab'], t['vocab']):
        v['en'], v['ex_en'], v['note'] = e.get('en'), e.get('ex_en'), e.get('note') or None
        if e.get('zh'):
            v['zh'] = e['zh']
    need(t['expressions'], rec['expressions'], 'expressions')
    for v, e in zip(rec['expressions'], t['expressions']):
        v['en'], v['note'] = e.get('en'), e.get('note') or None
        if e.get('zh'):
            v['zh'] = e['zh']
    g = t.get('grammar', {})
    rec['grammar']['pattern_en'], rec['grammar']['notes'] = g.get('pattern_en'), g.get('notes')
    need(g.get('examples_en', []), rec['grammar']['examples'], 'grammar examples')
    for v, e in zip(rec['grammar']['examples'], g.get('examples_en', [])):
        v['en'] = e
    d = t.get('dialogue', {})
    if rec['dialogue']['title']:
        rec['dialogue']['title']['en'] = d.get('title_en')
    need(d.get('turns_en', []), rec['dialogue']['turns'], 'dialogue turns')
    for v, e in zip(rec['dialogue']['turns'], d.get('turns_en', [])):
        v['en'] = e
    need(t.get('proverb', []), rec['proverb'], 'proverb')
    for v, e in zip(rec['proverb'], t.get('proverb', [])):
        v['literal'], v['meaning'] = e.get('literal'), e.get('meaning')
    for v, e in zip(rec['culture'], t.get('caption_en', [])):
        v['en'] = e
    o = t.get('order') or {}
    u = rec['exercises']['unscramble']
    if u['scene'] and o.get('scene_en'):
        u['scene']['en'] = o.get('scene_en')
    if o.get('answers'):
        need(o['answers'], u['items'], 'unscramble answers')
    for v, e in zip(u['items'], o.get('answers', [])):
        v['answer'], v['en'], v['unsure'] = e.get('bo'), e.get('en'), bool(e.get('unsure'))
    answers = [a for st in t.get('gaps', {}).get('sets', []) for a in st.get('answers', [])]
    items = [i for st in rec['exercises']['gaps']['sets'] for i in st['items']]
    need(answers, items, 'gap answers')
    for v, a in zip(items, answers):
        v['fill'], v['en'], v['unsure'] = a.get('fill'), a.get('en'), bool(a.get('unsure'))
    need(t.get('freetalk_en', []), rec['exercises']['talk'], 'talk questions')
    for v, e in zip(rec['exercises']['talk'], t.get('freetalk_en', [])):
        v['en'] = e
    rec['flags'] = [f for f in t.get('flags', []) if _still_there(f, rec)]
    rec['status']['translated'] = datetime.date.today().isoformat() + ' (machine translation — unreviewed; check with a teacher)'


if __name__ == '__main__':
    for p in sys.argv[1:]:
        t = json.load(open(p))
        rec = store.load(t['id'])
        if rec is None:
            print(f"{t['id']}: not in the store — run extract/run.py first")
            continue
        merge(t, rec)
        store.save(rec)
        print(f"{t['id']}: merged ({len(rec['vocab'])} words, {len(rec['dialogue']['turns'])} conversation lines, {len(rec['flags'])} flags)")
