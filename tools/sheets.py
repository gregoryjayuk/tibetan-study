"""Render the lesson store as readable study sheets (one Markdown file per lesson, plus an index).

    python3 tools/sheets.py

Writes <data>/lessons/<level>/<id>.md next to each <id>.json, and lessons/README.md (data folder: see extract/store.py).
The .md files are generated: edit the .json and re-run, never the other way round.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract'))
import store  # noqa: E402


def en(x, key='en'):
    return (x or {}).get(key) or ''


def dash(bo, e):
    return f"{bo} — {e}" if e else bo


def videos_for(r):
    """lesson videos sit in <data>/videos/<level>/ named '<id> part N.mkv'"""
    folder = os.path.join(store.DATA, 'videos', r['level'])
    if not os.path.isdir(folder):
        return []
    found = [f for f in os.listdir(folder) if f.startswith(r['id'] + ' ') and f.lower().endswith(('.mkv', '.mp4', '.webm', '.mp3', '.m4a'))]
    return sorted(found, key=lambda f: (0 if ' part ' in f else 1, f))


def sheet(r):
    L = []
    title_en = en(r['title'])
    L.append(f"# {r['id']} · {r['title']['bo'] if r['title'] else ''}" + (f" — {title_en}" if title_en else ''))
    L.append('')
    L.append(f"_Generated from {r['id']}.json — edit the JSON, not this file._")
    L.append('')
    topic = r['topic']['bo'] if r['topic'] else ''
    L.append(f"{r['book'].replace('book', 'Book')}, pages {r['pages'][0]}–{r['pages'][1]} · Topic: {topic}" + (f" ({en(r['topic'])})" if en(r['topic']) else ''))
    if r['status'].get('translated'):
        L.append('')
        L.append('English is a machine translation, not yet checked by a teacher: ask about anything that sounds off.')
    else:
        L.append('')
        L.append('English not added yet.')
    g = r['goals']
    if g.get('talk') or g.get('grammar'):
        L.append('')
        L.append('## Goals')
        if g.get('talk'):
            L.append(f"- Talk: {g['talk']['en'] or g['talk']['bo']}")
        if g.get('grammar'):
            L.append(f"- Grammar: {g['grammar']['en'] or g['grammar']['bo']}")
    vids = videos_for(r)
    if vids:
        L.append('')
        L.append('## Videos')
        L.append('Videos for this lesson:')
        for v in vids:
            label = v[len(r['id']) + 1:].rsplit('.', 1)[0]
            L.append(f"- [{label}](<../../videos/{r['level']}/{v}>)")
    L.append('')
    L.append('## New words')
    for v in r['vocab']:
        L.append(f"{v['n']}. **{v['bo']}**" + (f" — {v['en']}" if v['en'] else ''))
        if v['ex']:
            L.append(f"    - {dash(v['ex'], v['ex_en'])}")
        if v.get('note'):
            L.append(f"    - _{v['note']}_")
    if r['expressions']:
        L.append('')
        L.append('## Everyday expressions')
        for x in r['expressions']:
            L.append(f"- **{x['bo']}**" + (f" — {x['en']}" if x['en'] else '') + (f" _({x['note']})_" if x.get('note') else ''))
    gr = r['grammar']
    if gr['patterns'] or gr['examples']:
        L.append('')
        L.append('## Grammar: ' + (gr['pattern_en'] or ' / '.join(gr['patterns'])))
        if gr.get('notes'):
            L.append('')
            L.append(gr['notes'])
        L.append('')
        for e in gr['examples']:
            L.append(f"- {dash(e['bo'], e['en'])}")
    d = r['dialogue']
    if d['turns']:
        L.append('')
        L.append('## Conversation: ' + (d['title']['bo'] if d['title'] else '') + (f" — {en(d['title'])}" if en(d['title']) else ''))
        for t in d['turns']:
            L.append('')
            L.append(f"**{t['who']}།** {t['bo']}")
            if t['en']:
                L.append(f"_{t['en']}_")
    if r['proverb']:
        L.append('')
        L.append('## Proverb')
        for p in r['proverb']:
            L.append('')
            L.append(p['bo'])
            if p.get('literal'):
                L.append(f"_Literally:_ {p['literal']}")
            if p.get('meaning'):
                L.append(f"_Meaning:_ {p['meaning']}")
    ex = r['exercises']
    answers = []
    L.append('')
    L.append('## Exercises')
    sets = ex['gaps']['sets']
    if sets:
        L.append('')
        L.append('### Fill the gap')
        k = 0
        for s in sets:
            L.append('')
            L.append('Words: ' + ' · '.join(s['bank']))
            for it in s['items']:
                k += 1
                L.append(f"{k}. {it['bo']}")
                if it.get('fill'):
                    answers.append(f"Gap {k}: {it['fill']}" + (f" — {it['en']}" if it.get('en') else '') + (' _(unsure)_' if it.get('unsure') else ''))
    un = ex['unscramble']
    if un['items']:
        L.append('')
        L.append('### Put in order' + (f" — {un['scene']['bo']}" if un.get('scene') else '') + (f" ({un['scene']['en']})" if un.get('scene') and un['scene'].get('en') else ''))
        for i, it in enumerate(un['items'], 1):
            L.append(f"{i}. {it['jumbled']}")
            if it.get('answer'):
                answers.append(f"Order {i}: {it['answer']}" + (f" — {it['en']}" if it.get('en') else '') + (' _(unsure)_' if it.get('unsure') else ''))
    if ex.get('passage'):
        L.append('')
        L.append('### Find the mistakes')
        L.append(f"_{ex['passage']['note']}_")
        L.append('')
        L.append(ex['passage']['bo'])
    if ex['talk']:
        L.append('')
        L.append('### Talk about it')
        for q in ex['talk']:
            L.append(f"- {dash(q['bo'], q['en'])}")
    if answers:
        L.append('')
        L.append('### Answers')
        for a in answers:
            L.append(f"- {a}")
    if r.get('culture'):
        L.append('')
        L.append('## Culture picture')
        for c in r['culture']:
            L.append(f"- {dash(c['bo'], c['en'])}")
    if r['flags']:
        L.append('')
        L.append("## Possible typos in the book")
        for f in r['flags']:
            L.append(f"- {f.get('where', '')}: {f.get('text', '')} → {f.get('suggest', '')}" + (f" ({f['why']})" if f.get('why') else ''))
    return '\n'.join(L) + '\n'


def main():
    rows = []
    for p in sorted(glob.glob(os.path.join(store.STORE, '*', '*.json'))):
        r = json.load(open(p))
        open(p[:-5] + '.md', 'w').write(sheet(r))
        rows.append(r)
    idx = ['# Tibetan lessons', '', '_Generated by tools/sheets.py from the lesson JSON files. One file per lesson; the .md is for reading, the .json is the data._', '']
    for level in ('A1', 'A2', 'B1'):
        idx.append(f"## {level}")
        idx.append('')
        for r in [x for x in rows if x['level'] == level]:
            t = r['title']['bo'] if r['title'] else ''
            e = en(r['title'])
            mark = '' if r['status'].get('translated') else ' _(Tibetan only so far)_'
            idx.append(f"- [{r['id']}]({level}/{r['id']}.md) {t}" + (f" — {e}" if e else '') + f" · {len(r['vocab'])} words{mark}")
        idx.append('')
    open(os.path.join(store.STORE, 'README.md'), 'w').write('\n'.join(idx))
    print(f"{len(rows)} sheets written; index at {os.path.join(store.STORE, 'README.md')}")


if __name__ == '__main__':
    main()
