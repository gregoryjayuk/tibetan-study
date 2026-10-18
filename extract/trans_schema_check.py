"""usage: python3 trans_schema_check.py A2.01.01  -> validates trans/<id>.en.json against lessons_in/<id>.json"""
import json, sys
lid = sys.argv[1]
src = json.load(open(f'lessons_in/{lid}.json'))
t = json.load(open(f'trans/{lid}.en.json'))
errs = []
def need(cond, msg):
    if not cond: errs.append(msg)
need(t.get('id') == lid, 'id mismatch')
for k in ['topic_en', 'title_en', 'goal_talk_en', 'goal_grammar_en']: need(isinstance(t.get(k), str) and t[k].strip(), f'missing {k}')
need(len(t.get('vocab', [])) == len(src['vocab']), f"vocab count {len(t.get('vocab', []))} != {len(src['vocab'])}")
for i, v in enumerate(t.get('vocab', [])):
    need(v.get('en') and v.get('ex_en'), f'vocab {i+1} missing en/ex_en')
need(len(t.get('expressions', [])) == len(src['expressions']), 'expressions count')
g = t.get('grammar', {})
need(g.get('pattern_en') and g.get('notes'), 'grammar pattern_en/notes')
need(len(g.get('examples_en', [])) == len(src['grammar']['examples']), 'grammar examples count')
need(len(t.get('dialogue', {}).get('turns_en', [])) == len(src['dialogue']['turns']), f"dialogue turns {len(t.get('dialogue', {}).get('turns_en', []))} != {len(src['dialogue']['turns'])}")
need(len(t.get('proverb', [])) == len(src['proverb']), 'proverb count')
if t.get('order', {}).get('answers'): need(len(t['order']['answers']) == len(src['order']['items']), 'order answers count')
gs = t.get('gaps', {}).get('sets', [])
need(len(gs) == len(src['gaps']['sets']), 'gap sets count')
for a, b in zip(gs, src['gaps']['sets']): need(len(a.get('answers', [])) == len(b['items']), 'gap answers count')
need(len(t.get('freetalk_en', [])) == len(src['freetalk']), 'freetalk count')
print('OK' if not errs else 'ERRORS:\n  ' + '\n  '.join(errs))
