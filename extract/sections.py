import re
def indent(l): return len(l) - len(l.lstrip())
def join(a, b):
    a, b = a.rstrip(), b.strip()
    if not a: return b
    if a.endswith('་'): return a + b
    return a + ' ' + b
def is_instr(s): return s.startswith('བྱེད་སྒོ།')
LABEL = re.compile(r'^(བརྡ་སྤྲོད།|ཚིག་གྲུབ།|དཔེར་ན།|དགེ་རྒན།|རྒྱུན་སྤྱོད་(ཀྱི་)?སྐད|[༠-༩])')
def body(lines):
    """drop instruction line + its wrapped tail (first following line at col 0 that ends with དགོས། / ཆོག)"""
    out, i = [], 0
    while i < len(lines):
        s = lines[i].strip()
        if is_instr(s):
            nxt = lines[i+1].strip() if i + 1 < len(lines) else ''
            if not re.search(r'(དགོས|ཆོག|དྲིས)།?\s*$', s) and nxt and len(nxt) < 50 and not LABEL.match(nxt):
                i += 1
            i += 1; continue
        out.append(lines[i]); i += 1
    return [l for l in out if l.strip()]

def split_items(text):
    """split a run of short phrases separated by ། or by a space after ག/ཀ"""
    parts = re.split(r'(?<=།)\s*|(?<=[གཀ])\s+', text)
    out = []
    for p in parts:
        p = p.strip()
        if not p or p == '།': continue
        out.append(p)
    return out

def vocab(lines):
    rows, expr_txt, in_expr = [], '', False
    base = min((indent(l) for l in lines if l.strip()), default=0)
    for l in lines:
        s = l.strip()
        if re.match(r'^རྒྱུན་སྤྱོད་(ཀྱི་)?སྐད', s):   # also written རྒྱུན་སྤྱོད་ཀྱི་སྐད་ཆ། and རྒྱུན་སྤྱོད་སྐད།
            in_expr = True; expr_txt = s.split('།', 1)[1].strip() if '།' in s else ''; continue
        if in_expr:
            expr_txt = join(expr_txt, s); continue
        if indent(l) >= base + 8 and rows:
            rows[-1]['ex'] = join(rows[-1]['ex'], s); continue
        m = re.match(r'^(\S+?།)\s+(.+)$', s) or re.match(r'^(\S+)\s+(.+)$', s)
        if m: rows.append({'bo': m.group(1), 'ex': re.sub(r'\s{2,}', ' ', m.group(2).strip())})
        else: rows.append({'bo': s, 'ex': ''})
    return rows, split_items(expr_txt)

NOT_NAMES = {'རེད', 'ཡིན', 'འདུག', 'ཡོད', 'མེད', 'དགོས', 'སོང་', 'ལགས', 'ལགས་སོ', 'ཡ་ཡ', 'འོ', 'དཔེར་ན'}
def _lead(s):
    """leading speaker-like token: up to the first shad, or up to a run of 2+ spaces"""
    m = re.match(r'^([^\s།]{1,24})།\s*(.*)$', s)
    if m: return m.group(1), m.group(2)
    m = re.match(r'^([^\s།]{1,24})\s{2,}(.*)$', s)
    if m: return m.group(1), m.group(2)
    return None, s
def dialogue(lines):
    lines = [l for l in lines if l.strip()]
    if not lines: return None, []
    base = min(indent(l) for l in lines)
    cand = {}
    for l in lines:
        if indent(l) <= base + 6:
            who, _ = _lead(l.strip())
            # a name is sometimes printed with a stray tsheg before the shad (A2.08.02); it is the same speaker
            if who: cand[who.rstrip('་')] = cand.get(who.rstrip('་'), 0) + 1
    speakers = {k for k, v in cand.items() if v >= 2 and k.strip('་') not in NOT_NAMES}
    title, turns = None, []
    for l in lines:
        s = l.strip()
        who, rest = _lead(s)
        if who and who.rstrip('་') in speakers and indent(l) <= base + 6:
            turns.append({'who': who.rstrip('་'), 'bo': re.sub(r'\s{2,}', ' ', rest.strip())})
        elif turns:
            turns[-1]['bo'] = join(turns[-1]['bo'], s)
        else:
            title = join(title or '', s)
    return title, turns

def passage(lines):
    """B1's section 4 is a short passage seeded with word-order mistakes to find and fix"""
    return ' '.join(l.strip() for l in lines if l.strip()).replace('་ ', '་')

def grammar(lines):
    pats, exs, mode = [], [], None
    for l in lines:
        s = l.strip()
        if s.startswith('བརྡ་སྤྲོད།'): pats.append(s.split('།', 1)[1].strip()); mode = 'p'
        elif s.startswith('ཚིག་གྲུབ།'): exs.append(s.split('།', 1)[1].strip()); mode = 'e'
        elif mode == 'e': exs.append(s)
        elif mode == 'p' and pats: pats[-1] = join(pats[-1], s)
    return [p for p in pats if p], [e for e in exs if e]

def order(lines):
    pre, items = [], []
    for l in lines:
        s = l.strip()
        m = re.match(r'^([༠-༩]{1,2})\s*(.*)$', s)
        if m and '/' in s: items.append(m.group(2).strip())
        elif items and ('/' in s or indent(l) >= 4): items[-1] = join(items[-1], s)
        elif not items: pre.append(s)
    return (pre[-1] if pre else ''), [re.sub(r'\s*/\s*', ' / ', i).strip(' /') for i in items]

def gaps(lines):
    example, sets = None, []
    for l in lines:
        s = l.strip()
        if s.startswith('དཔེར་ན།'): example = s.split('།', 1)[1].strip(); continue
        m = re.match(r'^([༠-༩]{1,2})\s*(.*)$', s)   # the space after the number is sometimes missing (A2.07.01 ༥)
        if m and ('_' in s or '＿' in s):
            if not sets: sets.append({'bank': [], 'items': [], '_bank': ''})
            sets[-1]['items'].append(m.group(2).strip()); continue
        looks_like_bank = '_' not in s and '＿' not in s and len([w for w in re.split(r'།\s*', s) if w.strip()]) >= 3
        still_open = bool(sets and sets[-1]['items']) and not sets[-1]['items'][-1].rstrip().endswith('།')
        if sets and sets[-1]['items'] and indent(l) >= 4 and not re.match(r'^[༠-༩]', s) and still_open and not looks_like_bank:
            sets[-1]['items'][-1] = join(sets[-1]['items'][-1], s); continue
        if not re.match(r'^[༠-༩]', s):
            if not sets or sets[-1]['items']: sets.append({'bank': [], 'items': [], '_bank': ''})
            sets[-1]['_bank'] = join(sets[-1].get('_bank', ''), s)   # a bank word can wrap onto the next line
    for st in sets:
        st['bank'] = [w for w in re.split(r'།\s*|\s+', st.pop('_bank', '')) if w.strip()] or st['bank']
        st['items'] = [re.sub(r'\s*[_＿]{2,}\s*', ' ＿＿ ', i).replace('  ', ' ').strip() for i in st['items']]
    return example, [st for st in sets if st['items'] or st['bank']]

def freetalk(lines):
    """the teacher's questions; a question can wrap onto the next line (A2.09.02)"""
    qs, open_q = [], False
    for l in lines:
        s = l.strip()
        m = re.match(r'^དགེ་རྒན།\s*(.+)$', s)
        if m:
            qs.append(m.group(1).strip()); open_q = True
        elif open_q and s and not s.startswith(('སློབ་ཕྲུག', 'དཔེར་ན', 'བྱེད་སྒོ')) and not re.search(r'-\s*-', s):
            qs[-1] = join(qs[-1], re.sub(r'^[\u0f71-\u0f84་\s]+', '', s))   # a vowel sign can be displaced onto the next line
        else:
            open_q = False
    return qs

def goals(lines):
    conv = gram = None; cur = None
    for l in lines:
        s = l.strip()
        if s.startswith('གླེང་མོལ།'): conv = s.split('།', 1)[1].strip(); cur = 'c'; continue
        if s.startswith('བརྡ་སྤྲོད།'): gram = s.split('།', 1)[1].strip(); cur = 'g'; continue
        if cur and s and len(s) < 60 and not s.startswith(('༡', 'བྱེད་སྒོ', 'དགེ་རྒན་གྱིས')) and not re.search(r'(དུས་ཚོད་ཡིན།)$', s):
            if cur == 'c' and not conv.endswith('དགོས།'): conv = join(conv, s)
            elif cur == 'g' and not gram.endswith('དགོས།'): gram = join(gram, s)
        cur = None
    return conv, gram

def proverb(lines):
    prov, cap = [], []
    for l in lines:
        s = l.strip()
        if not s or re.fullmatch(r'[0-9༠-༩]+', s) or is_instr(s): continue
        clauses = [c for c in re.split(r'།+', s) if c.strip()]
        if '།།' in s or (len(clauses) >= 2 and len(s) > 14): prov.append(s)
        else: cap.append(s)
    # a one-clause proverb reads like a caption; it is printed first, under the heading (A2.10.01)
    if not prov and len(cap) >= 2 and cap[0].count('་') >= 5: prov.append(cap.pop(0))
    return prov, cap
