"""Where the learner is: read the study app's progress logs and print a short report.

    python3 tools/progress.py          # human summary
    python3 tools/progress.py --json   # the same, as JSON (for scripts)

Data folder: $TIBETAN_DATA if set, otherwise the default below (same as extract/store.py).

Replays every progress/<device>.jsonl exactly as the app does (same FSRS-4.5 constants, same
4am day boundary), so "due today" here matches what the app shows.
"""
import datetime
import glob
import json
import math
import os
import sys

DATA = os.path.expanduser(os.environ.get('TIBETAN_DATA') or '~/tibetan-data')
W = [0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031, 1.6474, 0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755]
DAY = 86400000


def day_index(t):
    d = datetime.datetime.fromtimestamp((t - 4 * 3600 * 1000) / 1000)
    return (datetime.date(d.year, d.month, d.day) - datetime.date(1970, 1, 1)).days


def clamp(d):
    return min(10, max(1, d))


def schedule(st, t, g):
    day = day_index(t)
    ivl = lambda S: max(1, min(365, round(S)))
    if st is None:
        S = W[g - 1]
        return {'S': S, 'D': clamp(W[4] - (g - 3) * W[5]), 'last': t, 'lastDay': day, 'due': day + ivl(S)}
    if st['lastDay'] == day:
        if g == 1 and st['due'] > day + 1:
            st['due'] = day + 1
        return st
    R = (1 + max(0, (t - st['last']) / DAY) / (9 * st['S'])) ** -1
    if g == 1:
        S = W[11] * st['D'] ** -W[12] * ((st['S'] + 1) ** W[13] - 1) * math.exp(W[14] * (1 - R))
    else:
        S = st['S'] * (math.exp(W[8]) * (11 - st['D']) * st['S'] ** -W[9] * (math.exp(W[10] * (1 - R)) - 1) * (W[16] if g == 4 else 1) + 1)
    D0 = clamp(W[4] - (4 - 3) * W[5])
    D = clamp(W[7] * D0 + (1 - W[7]) * (st['D'] - W[6] * (g - 3)))
    return {'S': S, 'D': D, 'last': t, 'lastDay': day, 'due': day + ivl(S)}


def one_way(item_id, C):
    """sentences and grammar points are reviewed one way only (Tibetan first), as in the app"""
    if ':ge' in item_id or ':gp' in item_id or item_id.endswith(':g'):
        return True
    for c in C['classes']:
        for x in c['items']:
            if x['id'] == item_id:
                return x['kind'] in ('sentence', 'grammar')
    return False


def report():
    C = json.load(open(os.path.join(DATA, 'app', 'content.json')))
    ev = []
    for f in glob.glob(os.path.join(DATA, 'progress', '*.jsonl')):
        for line in open(f, encoding='utf-8'):
            line = line.strip()
            if line:
                try:
                    ev.append(json.loads(line))
                except ValueError:
                    pass
    ev.sort(key=lambda e: e['t'])
    cards, intro, steps, done, skipped, days, last = {}, {}, set(), set(), set(), set(), {}
    for e in ev:
        last[e.get('d', '?')] = max(last.get(e.get('d', '?'), 0), e['t'])
        k = e['k']
        if k == 'intro':
            intro.setdefault(e['i'], e['t'])
        elif k == 'r':
            intro.setdefault(e['c'].split('|')[0], e['t'])
            cards[e['c']] = schedule(cards.get(e['c']), e['t'], e['g'])
            days.add(day_index(e['t']))
        elif k == 'step':
            steps.add((e['l'], e['s']))
        elif k == 'lesson':
            done.add(e['l'])
        elif k == 'skip':
            skipped.add(e['l'])
    now = int(datetime.datetime.now().timestamp() * 1000)
    today = day_index(now)
    due = sum(1 for c, st in cards.items() if st['due'] <= today)
    # production cards not yet seen fall due the day after the item was learned
    for i, t in intro.items():
        if not one_way(i, C) and (i + '|p') not in cards and day_index(t) < today:
            due += 1
    current = next((l for l in C['course'] if l not in done and l not in skipped), None)
    streak, d = 0, today if today in days else today - 1
    while d in days:
        streak += 1
        d -= 1
    cls_total = sum(len(c['items']) for c in C['classes'])
    cls_learned = sum(1 for c in C['classes'] for x in c['items'] if x['id'] in intro)
    inbox = sorted(os.path.basename(p) for p in glob.glob(os.path.join(DATA, 'inbox', '*.txt')))
    nxt = None
    if current:
        for s in ('words', 'phrases', 'grammar', 'conversation'):
            if (current, s) not in steps:
                nxt = s
                break
    return {
        'current_lesson': current, 'current_title': (C['lessons'][current]['title'] or {}).get('en') if current else None,
        'next_step': nxt, 'lessons_done': sorted(done | skipped), 'items_learned': len(intro),
        'learned_today': sum(1 for t in intro.values() if day_index(t) == today), 'due_today': due, 'streak_days': streak,
        'class_items': {'learned': cls_learned, 'total': cls_total},
        'last_activity': {k: datetime.datetime.fromtimestamp(v / 1000).isoformat(timespec='minutes') for k, v in last.items()},
        'inbox_waiting': inbox, 'content_built': C['built'],
    }


if __name__ == '__main__':
    r = report()
    if '--json' in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"Textbook: {r['current_lesson']} ({r['current_title']}) — next step: {r['next_step']}; done: {', '.join(r['lessons_done']) or 'none yet'}")
        print(f"Learned: {r['items_learned']} items ({r['learned_today']} today); due today: {r['due_today']}; streak: {r['streak_days']} days")
        print(f"Class notes: {r['class_items']['learned']} of {r['class_items']['total']} learned")
        print(f"Last activity: {', '.join(f'{k} {v}' for k, v in r['last_activity'].items()) or 'none yet'}")
        if r['inbox_waiting']:
            print(f"Pasted notes waiting to be tidied: {', '.join(r['inbox_waiting'])}")
