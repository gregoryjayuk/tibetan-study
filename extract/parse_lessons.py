"""Split repaired textbook text into lessons and sections; keep the parts worth studying.

parse_book() returns one dict per lesson with the Tibetan of every section that is worth drilling:
vocab rows (headword + example), everyday expressions, the grammar pattern and its example, the
sentence-order and fill-the-gap exercises, the teacher's free-talk question, the conversation and
the proverb. Picture, audio, review and column-matching sections are dropped on purpose."""
import re, json, subprocess, sys, os
from collections import Counter

BOOKS = [("A1", 1, "A1 book 1"), ("A1", 2, "A1 book 2"), ("A2", 1, "A2 book 1"),
         ("A2", 2, "A2 book 2"), ("B1", 1, "B1 book 1"), ("B1", 2, "B1 book 2")]
TIB = "༠༡༢༣༤༥༦༧༨༩"
def t2a(s): return "".join(str(TIB.index(c)) if c in TIB else c for c in s)

SECTIONS = [("pics", "པར་རིས་ངོ་སྤྲོད"), ("vocab", "ཚིག་གསར་ངོ་སྤྲོད"), ("pics2", "སླར་ཡང་པར་རིས་ངོ་སྤྲོད"),
            ("order", "ཚིག་གྲུབ་གོ་རིམ"), ("freetalk", "རང་མོས་གླེང་མོལ"), ("review", "བསྐྱར་སྦྱོང"),
            ("audio", "སྒྲ"), ("grammar", "བརྡ་སྤྲོད"), ("match", "མིང་ཚིག་གོ་རིམ"), ("match", "མཐུན་སྦྱོར"), ("drill", "སྦྱོང་བརྡར"),
            ("gaps", "བར་སྟོང"), ("dialogue", "གླེང་མོལ"), ("roleplay", "འཁྲབ་སྟོན"),
            ("proverb", "གོ་སླ་བའི་གཏམ་དཔེ"), ("proverb", "གོ་སླའི་གཏམ་དཔེ")]
SEC_RE = re.compile(r'^\s*([༠-༩]{1,2})\s*(' + "|".join(re.escape(n) for _, n in sorted(SECTIONS, key=lambda x: -len(x[1]))) + r')[་།\s]*(༼|དམིགས་ཡུལ|$)')
NAME2KEY = {n: k for k, n in SECTIONS}
HDR_RE = re.compile(r'གནས་ཚད་[^\s།]*།\s*([༠-༩]{1,2})\s*།\s*([༠-༩]{1,2})')

from tibnorm import norm
from book_config import FOOTER_MARKERS, LABEL_FIXES

def is_footer(l):
    return any(m in l for m in FOOTER_MARKERS) or 'ཤོག་གྲངས' in l

def pages_of(path):
    n = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', path], capture_output=True, text=True).stdout).group(1))
    for p in range(1, n + 1):
        yield p, subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), '-layout', path, '-'], capture_output=True, text=True).stdout

def strip_instructions(lines):
    """drop the 'བྱེད་སྒོ།' teacher-instruction line and its wrapped tail"""
    out, skip = [], False
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith('བྱེད་སྒོ།'):
            skip = not s.endswith('།') or s.endswith('་')
            # a wrapped instruction continues on the next line only if this one does not end a sentence
            skip = not re.search(r'(དགོས|ཆོག|བྱེད་དགོས|དྲིས)།\s*$', s)
            continue
        if skip:
            skip = False
            if len(s) < 40 and not re.match(r'^[༠-༩]', s): continue
        out.append(l)
    return out

GENERIC = ('མིང་ཚིག་གསར་པ་སྦྱོང་བ', 'གླེང་མོལ་ལ་བརྟེན་ནས', 'སོ་སོའི་ཡར་རྒྱས', 'ཆུ་ཚོད་གཅིག་', 'སྐར་མ་༤༥', 'སྐར་མ་༡༥ནི', 'དགེ་རྒན་གྱིས་སློབ་མ་ལ་སྒྲ་གདངས')
def drop_generic(lines):
    out = []
    for l in lines:
        s = l.strip()
        if s == 'སློབ་ཚན་འདིའི་དམིགས་ཡུལ།': continue
        if re.match(r'^[1-9]\.', s): continue
        if any(g in s for g in GENERIC): continue
        out.append(l)
    return out

def parse_vocab(lines):
    rows, exprs, cur = [], [], None
    in_expr = False
    for l in lines:
        s = l.strip()
        if not s: continue
        if s.startswith('རྒྱུན་སྤྱོད་སྐད་ཆ'):
            in_expr = True; s = s.split('།', 1)[1] if '།' in s else ''
        if in_expr:
            exprs.append(s); continue
        indent = len(l) - len(l.lstrip())
        if indent >= 12 and cur is not None:
            cur['ex'] += s; continue
        m = re.match(r'^(.+?[།༔])\s+(.+)$', s) or re.match(r'^(\S+)\s{2,}(.+)$', s)
        if m and (len(m.group(1)) < 40):
            cur = {'bo': m.group(1).strip(), 'ex': m.group(2).strip()}; rows.append(cur)
        elif cur is not None:
            cur['ex'] += s
        else:
            rows.append({'bo': s, 'ex': ''}); cur = rows[-1]
    ex_items = []
    for e in exprs:
        ex_items += [x.strip() + '།' for x in re.split(r'།\s*', e) if x.strip()]
    for r in rows:
        r['ex'] = re.sub(r'\s{2,}', ' ', r['ex'])
    return rows, ex_items

def parse_dialogue(lines):
    lines = [l for l in lines if l.strip()]
    title = None
    # candidate speakers: first token (ending in ། ) of lines, counted
    firsts = Counter()
    for l in lines:
        m = re.match(r'^\s*([^\s།]+།)', l.strip())
        if m: firsts[m.group(1)] += 1
    speakers = {k for k, v in firsts.items() if v >= 2 and len(k) <= 20}
    turns = []
    for l in lines:
        s = l.strip()
        m = re.match(r'^([^\s།]+།)\s*(.*)$', s)
        if m and m.group(1) in speakers:
            turns.append({'who': m.group(1).rstrip('།'), 'bo': m.group(2).strip()})
        elif turns:
            turns[-1]['bo'] = (turns[-1]['bo'] + s) if turns[-1]['bo'].endswith(('་', '།')) or not turns[-1]['bo'] else turns[-1]['bo'] + ' ' + s
        elif title is None:
            title = s
        else:
            title += ' ' + s
    for t in turns: t['bo'] = re.sub(r'\s{2,}', ' ', t['bo'])
    return title, turns

def parse_grammar(lines):
    pats, exs = [], []
    mode = None
    for l in lines:
        s = l.strip()
        if not s: continue
        if s.startswith('བརྡ་སྤྲོད།'):
            pats.append(s.split('།', 1)[1].strip()); mode = 'p'
        elif s.startswith('ཚིག་གྲུབ།'):
            exs.append(s.split('།', 1)[1].strip()); mode = 'e'
        elif mode == 'e': exs.append(s)
        elif mode == 'p': pats[-1] += ' ' + s
    return pats, exs

def parse_order(lines):
    scene, items = [], []
    for l in lines:
        s = l.strip()
        if not s: continue
        m = re.match(r'^([༠-༩]{1,2})\s*(.*)$', s)
        if m and '/' in s: items.append(m.group(2).strip())
        elif items and '/' in s: items[-1] += ' ' + s
        elif not items: scene.append(s)
    return ' '.join(scene), items

def parse_gaps(lines):
    example, bank, items = None, [], []
    for l in lines:
        s = l.strip()
        if not s: continue
        if s.startswith('དཔེར་ན།'): example = s.split('།', 1)[1].strip(); continue
        m = re.match(r'^([༠-༩]{1,2})\s+(.*)$', s)
        if m and '_' in s: items.append(re.sub(r'_{2,}', '＿＿', m.group(2).strip()))
        elif '_' in s and items: items[-1] += ' ' + re.sub(r'_{2,}', '＿＿', s)
        elif not re.match(r'^[༠-༩]', s): bank.append(s)
    words = [w.strip() for b in bank for w in re.split(r'།\s*|\s{2,}', b) if w.strip()]
    return example, words, items

def parse_freetalk(lines):
    qs = []
    for l in lines:
        s = l.strip()
        m = re.match(r'^དགེ་རྒན།\s*(.+)$', s)
        if m: qs.append(m.group(1).strip())
    return qs

def parse_goals(lines):
    conv = gram = None; cur = None
    for l in lines:
        s = l.strip()
        if s.startswith('གླེང་མོལ།'): conv = s.split('།', 1)[1].strip(); cur = 'c'; continue
        if s.startswith('བརྡ་སྤྲོད།'): gram = s.split('།', 1)[1].strip(); cur = 'g'; continue
        if s.startswith('༡') or s.startswith('བྱེད་སྒོ'): cur = None; continue
        if cur == 'c' and s and len(s) < 60: conv += s; cur = None
        elif cur == 'g' and s and len(s) < 60: gram += s; cur = None
    return conv, gram

# A speaker label misprinted once would merge two turns of the conversation, so the label (only) is
# corrected: LABEL_FIXES comes from book_config.py.

def parse_book(level, bookno, name, src):
    lessons, order = {}, []
    cur = None
    for p, text in pages_of(src):
        m = HDR_RE.search(text)
        starts = any(SEC_RE.match(norm(x)) and NAME2KEY.get(SEC_RE.match(norm(x)).group(2)) == 'pics' for x in text.split('\n'))
        if m and (starts or cur is None):
            lid = f"{level}.{t2a(m.group(1)).zfill(2)}.{t2a(m.group(2)).zfill(2)}"
            if cur is not None:
                cc, ll = int(cur.split('.')[1]), int(cur.split('.')[2])
                exp = f"{level}.{cc:02d}.{ll+1:02d}" if ll == 1 else f"{level}.{cc+1:02d}.01"
                if lid != exp:
                    print(f"   ! {name} p{p}: page header says {lid}; the sequence says {exp} — using {exp}")
                    lid = exp
            if lid != cur:
                cur = lid
                if lid not in lessons:
                    lessons[lid] = {'id': lid, 'level': level, 'book': f"{level} book {bookno}", 'pages': [], 'lines': [], 'topic': None, 'title': None}
                    order.append(lid)
        if cur is None: continue
        L = lessons[cur]; L['pages'].append(p)
        for raw in text.split('\n'):
            l = norm(raw)
            if not l.strip() or is_footer(l) or HDR_RE.search(l): continue
            tm = re.match(r'^\s*བརྗོད་གཞི།\s+(\S.*)$', l)
            if tm:
                L['topic'] = L['topic'] or tm.group(1).strip(); continue
            L['lines'].append(l)
    import sections as S
    out = []
    for lid in order:
        L = lessons[lid]
        secs, key, pre = {}, None, []
        for l in L['lines']:
            m = SEC_RE.match(l)
            if m:
                key = NAME2KEY[m.group(2)]
                k2 = key; i = 2
                while k2 in secs: k2 = f"{key}{i}"; i += 1
                key = k2; secs[key] = []; continue
            (secs[key] if key else pre).append(l)
        title = next((l.strip() for l in pre if l.strip()), None)
        gc, gg = S.goals(secs.get('pics', []))
        vocab, exprs = S.vocab(drop_generic(S.body(secs.get('vocab', []))))
        scene, oitems = S.order(S.body(secs.get('order', [])))
        passage = S.passage(S.body(secs.get('order', []))) if not oitems else None
        pats, gex = S.grammar(drop_generic(S.body(secs.get('grammar', []))))
        gx, gsets = S.gaps(drop_generic(S.body(secs.get('gaps', []))))
        dl = secs.get('dialogue', [])
        for a, b in LABEL_FIXES.get(lid, []):
            dl = [l.replace(a, b, 1) if l.strip().startswith(a) else l for l in dl]
        dtitle, turns = S.dialogue(drop_generic(S.body(dl)))
        prov, cap = S.proverb(S.body(secs.get('proverb', [])))
        out.append({'id': lid, 'level': L['level'], 'book': L['book'], 'pages': [min(L['pages']), max(L['pages'])],
                    'topic': L['topic'], 'title': title, 'goal_talk': gc, 'goal_grammar': gg,
                    'vocab': vocab, 'expressions': exprs, 'grammar': {'patterns': pats, 'examples': gex},
                    'order': {'scene': scene, 'items': oitems}, 'passage': passage, 'freetalk': S.freetalk(secs.get('freetalk', [])),
                    'gaps': {'example': gx, 'sets': gsets}, 'dialogue': {'title': dtitle, 'turns': turns},
                    'proverb': prov, 'caption': cap, 'sections_found': list(secs.keys())})
    return out

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('fixed_dir'); ap.add_argument('out_dir')
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    for level, bookno, name in BOOKS:
        res = parse_book(level, bookno, name, os.path.join(a.fixed_dir, name + '.pdf'))
        json.dump(res, open(os.path.join(a.out_dir, name.replace(' ', '_') + '.json'), 'w'), ensure_ascii=False, indent=1)
        print(f"{name}: {len(res)} lessons")
