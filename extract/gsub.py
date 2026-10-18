import struct
from ttf import tables
def u16(b, o): return struct.unpack_from('>H', b, o)[0]
def i16(b, o): return struct.unpack_from('>h', b, o)[0]
def u32(b, o): return struct.unpack_from('>I', b, o)[0]

def coverage(b, o):
    fmt = u16(b, o)
    if fmt == 1:
        n = u16(b, o+2); return [u16(b, o+4+2*i) for i in range(n)]
    if fmt == 2:
        n = u16(b, o+2); out = []
        for i in range(n):
            s, e, si = struct.unpack_from('>HHH', b, o+4+6*i); out.extend(range(s, e+1))
        return out
    return []

def cmap_map(font):
    t = tables(font); off, ln = t['cmap']; b = font[off:off+ln]
    n = u16(b, 2); best = None
    for i in range(n):
        pid, eid, so = struct.unpack_from('>HHI', b, 4+8*i)
        fmt = u16(b, so)
        if (pid, eid) in ((3,10),(0,4),(0,6)) and fmt == 12: best = so; break
        if (pid, eid) in ((3,1),(0,3),(0,1),(0,0)) and fmt == 4 and best is None: best = so
    m = {}
    fmt = u16(b, best)
    if fmt == 4:
        segX2 = u16(b, best+6); seg = segX2//2
        ends = best+14; starts = ends+segX2+2; deltas = starts+segX2; ros = deltas+segX2
        for i in range(seg):
            e = u16(b, ends+2*i); s = u16(b, starts+2*i); d = i16(b, deltas+2*i); ro = u16(b, ros+2*i)
            for c in range(s, e+1):
                if c == 0xFFFF: continue
                if ro == 0: g = (c + d) & 0xFFFF
                else:
                    go = ros + 2*i + ro + 2*(c - s); g = u16(b, go)
                    if g: g = (g + d) & 0xFFFF
                if g: m[c] = g
    elif fmt == 12:
        ng = u32(b, best+12)
        for i in range(ng):
            s, e, sg = struct.unpack_from('>III', b, best+16+12*i)
            for c in range(s, e+1): m[c] = sg + (c - s)
    return m

def gsub_maps(font):
    """returns (single: out->set(in), lig: out->list of component tuples, mult: in->list(out))"""
    t = tables(font)
    single, lig, mult = {}, {}, {}
    if 'GSUB' not in t: return single, lig, mult
    off, ln = t['GSUB']; b = font[off:off+ln]
    ll = u16(b, 8); nlook = u16(b, ll)
    def sub(st, typ):
        fmt = u16(b, st)
        if typ == 7:
            return sub(st + u32(b, st+4), u16(b, st+2))
        if typ == 1:
            cov = coverage(b, st + u16(b, st+2))
            if fmt == 1:
                d = i16(b, st+4)
                for g in cov: single.setdefault((g + d) & 0xFFFF, set()).add(g)
            else:
                for i, g in enumerate(cov): single.setdefault(u16(b, st+6+2*i), set()).add(g)
        elif typ == 2 or typ == 3:
            cov = coverage(b, st + u16(b, st+2))
            for i, g in enumerate(cov):
                so = st + u16(b, st+6+2*i); n = u16(b, so)
                outs = [u16(b, so+2+2*k) for k in range(n)]
                if typ == 2: mult.setdefault(g, []).append(outs)
                else:
                    for a in outs: single.setdefault(a, set()).add(g)
        elif typ == 4:
            cov = coverage(b, st + u16(b, st+2))
            for i, g in enumerate(cov):
                lso = st + u16(b, st+6+2*i); nl = u16(b, lso)
                for k in range(nl):
                    lo = lso + u16(b, lso+2+2*k)
                    lg = u16(b, lo); cc = u16(b, lo+2)
                    comps = (g,) + tuple(u16(b, lo+4+2*j) for j in range(cc-1))
                    lig.setdefault(lg, []).append(comps)
        elif typ == 8:
            cov = coverage(b, st + u16(b, st+2))
            nb = u16(b, st+4); p = st+6+2*nb; nla = u16(b, p); p += 2+2*nla
            n = u16(b, p)
            for i, g in enumerate(cov[:n]): single.setdefault(u16(b, p+2+2*i), set()).add(g)
    for i in range(nlook):
        lo = ll + u16(b, ll+2+2*i)
        typ = u16(b, lo); nsub = u16(b, lo+4)
        for k in range(nsub):
            try: sub(lo + u16(b, lo+6+2*k), typ)
            except struct.error: pass
    return single, lig, mult

def glyph_unicode(font):
    cm = cmap_map(font)
    rev = {}
    for c, g in sorted(cm.items()):
        # prefer Tibetan block / lowest codepoint for duplicates
        if g not in rev or (0x0F00 <= c <= 0x0FFF and not (0x0F00 <= rev[g] <= 0x0FFF)): rev[g] = c
    single, lig, mult = gsub_maps(font)
    # multiple subst: a precomposed char split into several glyphs; map each piece back if unique
    memo = {}
    def uni(g, depth=0):
        if g in memo: return memo[g]
        if depth > 12: return None
        memo[g] = None
        r = None
        if g in rev: r = chr(rev[g])
        if r is None and g in lig:
            cands = []
            for comps in lig[g]:
                parts = [uni(c, depth+1) for c in comps]
                if all(p is not None for p in parts): cands.append(''.join(parts))
            if cands: r = min(cands, key=len)
        if r is None and g in single:
            cands = [uni(x, depth+1) for x in single[g]]
            cands = [c for c in cands if c is not None]
            if cands: r = min(cands, key=lambda s: (len(s), s))
        memo[g] = r
        return r
    maxp = tables(font)['maxp']; ng = u16(font, maxp[0]+4)
    return {g: uni(g) for g in range(ng)}, (len(cm), len(single), len(lig), len(mult))
