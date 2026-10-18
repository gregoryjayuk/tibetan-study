"""The lesson store: one JSON file per lesson under <data>/lessons/<level>/<id>.json.

<data> is the data folder: $TIBETAN_DATA if set, otherwise the default below. Every tool reads it
from here (DATA), so one environment variable points the whole pipeline at another folder.

That JSON is canonical. Tibetan comes from the textbook extraction; every English field starts as
null and is filled by merge_translation() (and later corrected by hand). Re-running the
extraction never discards English: record() carries it over wherever the Tibetan still lines up.
"""
import json
import os
import datetime

SCHEMA = 1
DATA = os.path.expanduser(os.environ.get('TIBETAN_DATA') or '~/tibetan-data')
STORE = os.path.join(DATA, 'lessons')


def path_for(lid):
    return os.path.join(STORE, lid.split('.')[0], lid + '.json')


def load(lid):
    p = path_for(lid)
    return json.load(open(p)) if os.path.exists(p) else None


def save(rec):
    p = path_for(rec['id'])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(tmp, p)


def _bo(x):
    return {'bo': x, 'en': None} if x else None


def record(raw, pdf_name):
    """Build a store record (English all null) from one parsed lesson."""
    today = datetime.date.today().isoformat()
    ex = raw.get('order') or {}
    gaps = raw.get('gaps') or {}
    return {
        'schema': SCHEMA,
        'id': raw['id'],
        'level': raw['level'],
        'book': raw['book'],
        'pdf': pdf_name,
        'pages': raw['pages'],
        'topic': _bo(raw.get('topic')),
        'title': _bo(raw.get('title')),
        'goals': {'talk': _bo(raw.get('goal_talk')), 'grammar': _bo(raw.get('goal_grammar'))},
        'vocab': [{'n': i + 1, 'bo': v['bo'], 'en': None, 'ex': v['ex'], 'ex_en': None, 'note': None}
                  for i, v in enumerate(raw.get('vocab', []))],
        'expressions': [{'n': i + 1, 'bo': e, 'en': None, 'note': None} for i, e in enumerate(raw.get('expressions', []))],
        'grammar': {'patterns': raw['grammar']['patterns'], 'pattern_en': None, 'notes': None,
                    'examples': [{'bo': e, 'en': None} for e in raw['grammar']['examples']]},
        'dialogue': {'title': _bo((raw.get('dialogue') or {}).get('title')),
                     'turns': [{'who': t['who'], 'bo': t['bo'], 'en': None} for t in (raw.get('dialogue') or {}).get('turns', [])]},
        'proverb': [{'bo': p, 'literal': None, 'meaning': None} for p in raw.get('proverb', [])],
        'culture': [{'bo': c, 'en': None} for c in raw.get('caption', [])],
        'exercises': {
            'unscramble': {'scene': _bo(ex.get('scene')),
                           'items': [{'jumbled': j, 'answer': None, 'en': None, 'unsure': None} for j in ex.get('items', [])]},
            'passage': {'bo': raw['passage'], 'note': 'contains deliberate word-order mistakes to find and correct'} if raw.get('passage') else None,
            'gaps': {'example': gaps.get('example'),
                     'sets': [{'bank': s['bank'], 'items': [{'bo': i, 'fill': None, 'en': None, 'unsure': None} for i in s['items']]}
                              for s in gaps.get('sets', [])]},
            'talk': [{'bo': q, 'en': None} for q in raw.get('freetalk', [])],
        },
        'flags': [],
        'status': {'extracted': today, 'translated': None, 'reviewed': None},
    }


def _shape(rec):
    return (len(rec['vocab']), len(rec['expressions']), len(rec['grammar']['examples']), len(rec['dialogue']['turns']),
            len(rec['proverb']), len(rec['culture']), len(rec['exercises']['unscramble']['items']),
            [len(s['items']) for s in rec['exercises']['gaps']['sets']], len(rec['exercises']['talk']))


def carry_english(new, old):
    """Copy every English field from old into new where the structure still matches. Returns list of parts not carried."""
    lost = []
    for k in ('topic', 'title'):
        if new.get(k) and old.get(k):
            new[k]['en'] = old[k].get('en')
    for k in ('talk', 'grammar'):
        if new['goals'].get(k) and old['goals'].get(k):
            new['goals'][k]['en'] = old['goals'][k].get('en')

    def rows(a, b, fields, name):
        if len(a) != len(b):
            lost.append(name)
            return
        for x, y in zip(a, b):
            for f in fields:
                x[f] = y.get(f)
    rows(new['vocab'], old['vocab'], ('en', 'zh', 'ex_en', 'note'), 'vocab')
    rows(new['expressions'], old['expressions'], ('en', 'zh', 'note'), 'expressions')
    new['grammar']['pattern_en'] = old['grammar'].get('pattern_en')
    new['grammar']['notes'] = old['grammar'].get('notes')
    rows(new['grammar']['examples'], old['grammar']['examples'], ('en',), 'grammar examples')
    if new['dialogue'].get('title') and old['dialogue'].get('title'):
        new['dialogue']['title']['en'] = old['dialogue']['title'].get('en')
    rows(new['dialogue']['turns'], old['dialogue']['turns'], ('en',), 'dialogue')
    rows(new['proverb'], old['proverb'], ('literal', 'meaning'), 'proverb')
    rows(new['culture'], old['culture'], ('en',), 'culture')
    ou, nu = old['exercises']['unscramble'], new['exercises']['unscramble']
    if nu.get('scene') and ou.get('scene'):
        nu['scene']['en'] = ou['scene'].get('en')
    rows(nu['items'], ou['items'], ('answer', 'en', 'unsure'), 'unscramble')
    # gap items are matched across sets, so a fix that splits one bank into two keeps the answers
    og = [i for st in old['exercises']['gaps']['sets'] for i in st['items']]
    ng = [i for st in new['exercises']['gaps']['sets'] for i in st['items']]
    rows(ng, og, ('fill', 'en', 'unsure'), 'gaps')
    rows(new['exercises']['talk'], old['exercises']['talk'], ('en',), 'talk')
    new['flags'] = old.get('flags', [])
    new['status'] = dict(old.get('status', {}), extracted=new['status']['extracted'])
    return lost
