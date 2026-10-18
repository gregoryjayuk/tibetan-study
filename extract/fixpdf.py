"""Rebuild correct ToUnicode maps for Tibetan fonts in Word/Acrobat PDFs, write an incremental update.
The PDFs' own ToUnicode maps split each shaped cluster's characters unevenly across glyphs (stacks lose
subjoined letters, vowel glyphs gain stray ones). Each embedded font still carries cmap+GSUB, so the true
string of every glyph is recomputed by walking the ligature/single substitutions back to nominal glyphs."""
import os, re, sys, zlib, struct
from pdfobj import PDF
from gsub import cmap_map, gsub_maps
from ttf import tables

# the full Microsoft Himalaya font (not shipped here): Word for Mac bundles it; HIMALAYA_TTF points elsewhere
HIMALAYA = os.environ.get('HIMALAYA_TTF') or "/Applications/Microsoft Word.app/Contents/Resources/DFonts/himalaya.ttf"
_him = None
def himalaya_cmap():
    global _him
    if _him is None: _him = cmap_map(open(HIMALAYA, 'rb').read())
    return _him

def monlam_nominal():
    m = {}
    for cp in range(0x0F00, 0x0F48): m[cp] = 99 + cp - 0x0F00
    for cp in range(0x0F49, 0x0F6B): m[cp] = 171 + cp - 0x0F49
    for cp in range(0x0F71, 0x0F8C): m[cp] = 205 + cp - 0x0F71
    for cp in range(0x0F90, 0x0F98): m[cp] = 232 + cp - 0x0F90
    for cp in range(0x0F99, 0x0FBD): m[cp] = 240 + cp - 0x0F99
    return m

def numglyphs(font):
    o = tables(font)['maxp'][0]; return struct.unpack('>H', font[o+4:o+6])[0]

def resolve(font, fontname, report):
    cm = cmap_map(font)
    ng = numglyphs(font)
    rev = {}
    for c, g in sorted(cm.items()): rev.setdefault(g, c)
    ref = himalaya_cmap() if 'Himalaya' in fontname else monlam_nominal() if 'Monlam' in fontname else {}
    conflicts = [(c, g, ref[c]) for c, g in cm.items() if 0x0F00 <= c <= 0x0FFF and c in ref and ref[c] != g]
    if conflicts: report.append(f"  !! {fontname}: reference disagrees with subset cmap on {len(conflicts)}: {conflicts[:5]}")
    else:
        for c, g in ref.items():
            if 0x0F00 <= c <= 0x0FFF and g < ng and g not in rev: rev[g] = c
    single, lig, mult = gsub_maps(font)
    memo = {}
    def uni(g, depth=0):
        if g in memo: return memo[g]
        if depth > 15: return None
        memo[g] = None; r = None
        if g in rev: r = chr(rev[g])
        if r is None and g in lig:
            cands = []
            for comps in lig[g]:
                parts = [uni(c, depth+1) for c in comps]
                if all(p is not None for p in parts): cands.append(''.join(parts))
            if cands: r = min(cands, key=lambda s: (len(s), s))
        if r is None and g in single:
            cands = [x for x in (uni(s, depth+1) for s in single[g]) if x is not None]
            if cands: r = min(cands, key=lambda s: (len(s), s))
        memo[g] = r; return r
    return uni

def parse_tounicode(cm):
    txt = cm.decode('latin1'); out = {}
    def hexstr(h):
        b = bytes.fromhex(h); return b.decode('utf-16-be', errors='replace')
    for blk in re.findall(r'beginbfchar(.*?)endbfchar', txt, re.S):
        for a, b in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>', blk): out[int(a, 16)] = hexstr(b)
    for blk in re.findall(r'beginbfrange(.*?)endbfrange', txt, re.S):
        for a, b, rest in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]+>)', blk):
            a, b = int(a, 16), int(b, 16)
            if rest.startswith('['):
                vals = re.findall(r'<([0-9A-Fa-f]*)>', rest)
                for i, v in enumerate(vals): out[a+i] = hexstr(v)
            else:
                base = bytes.fromhex(rest[1:-1])
                for i in range(b - a + 1):
                    v = int.from_bytes(base, 'big') + i
                    out[a+i] = v.to_bytes(len(base), 'big').decode('utf-16-be', errors='replace')
    return out

def build_cmap(m):
    lines = ["/CIDInit /ProcSet findresource begin", "12 dict begin", "begincmap",
             "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
             "/CMapName /Adobe-Identity-UCS def", "/CMapType 2 def",
             "1 begincodespacerange", "<0000> <FFFF>", "endcodespacerange"]
    items = sorted(m.items())
    for i in range(0, len(items), 100):
        chunk = items[i:i+100]
        lines.append(f"{len(chunk)} beginbfchar")
        for cid, s in chunk:
            lines.append(f"<{cid:04X}> <{s.encode('utf-16-be').hex().upper()}>")
        lines.append("endbfchar")
    lines += ["endcmap", "CMapName currentdict /CMap defineresource pop", "end", "end"]
    return "\n".join(lines).encode('latin1')

def main(src, dst, verbose=False):
    p = PDF(src); report = []; newobjs = {}
    stats = dict(same=0, fixed=0, kept=0)
    for n, dp in p.objs.items():
        if b'/Type0' not in dp or b'/ToUnicode' not in dp: continue
        name = re.search(rb'/BaseFont\s*/([^\s/>]+)', dp).group(1).decode().replace('#20', ' ')
        if 'Himalaya' not in name and 'Monlam' not in name: continue
        tu = p.ref(dp, b'ToUnicode')
        m = re.search(rb'/DescendantFonts\s+(\d+)\s+0\s+R', dp)
        arr = p.objs[int(m.group(1))] if m else re.search(rb'/DescendantFonts\s*(\[[^\]]*\])', dp).group(1)
        cf = int(re.search(rb'(\d+)\s+0\s+R', arr).group(1))
        if b'/Identity' not in p.objs[cf] and b'CIDToGIDMap' in p.objs[cf]:
            report.append(f"  !! {name} obj {n}: CIDToGIDMap not Identity, skipped"); continue
        fd = int(re.search(rb'/FontDescriptor\s+(\d+)\s+0\s+R', p.objs[cf]).group(1))
        ffm = re.search(rb'/FontFile2\s+(\d+)\s+0\s+R', p.objs[fd])
        if not ffm: report.append(f"  !! {name} obj {n}: no FontFile2"); continue
        font = p.decode(int(ffm.group(1)))
        uni = resolve(font, name, report)
        orig = parse_tounicode(p.decode(tu))
        new = {}
        for cid, t in orig.items():
            r = uni(cid)
            if r is None or r == '': new[cid] = t; stats['kept'] += 1
            elif r == t: new[cid] = t; stats['same'] += 1
            else:
                new[cid] = r; stats['fixed'] += 1
                if verbose: report.append(f"    {name[:12]} {cid:04X}: {t!r} -> {r!r}")
        newobjs[tu] = build_cmap(new)
    data = p.data
    out = bytearray(data)
    if not out.endswith(b'\n'): out += b'\n'
    offsets = {}
    for num, content in sorted(newobjs.items()):
        comp = zlib.compress(content)
        offsets[num] = len(out)
        out += b'%d 0 obj\n<</Filter/FlateDecode/Length %d>>\nstream\n' % (num, len(comp)) + comp + b'\nendstream\nendobj\n'
    # previous xref offset and trailer info
    prev = int(re.findall(rb'startxref\s+(\d+)', data)[-1])
    # trailer keys from last xref stream/trailer dict
    tail = data[prev:prev+2000]
    root = re.search(rb'/Root\s+(\d+\s+\d+\s+R)', tail) or re.search(rb'/Root\s+(\d+\s+\d+\s+R)', data[-4000:]) 
    info = re.search(rb'/Info\s+(\d+\s+\d+\s+R)', tail)
    size = max(max(p.objs) + 1, max(offsets) + 1 if offsets else 0)
    sm = re.search(rb'/Size\s+(\d+)', tail)
    if sm: size = max(size, int(sm.group(1)))
    xref_off = len(out)
    x = b'xref\n0 1\n0000000000 65535 f \n'
    for num in sorted(offsets):
        x += b'%d 1\n%010d 00000 n \n' % (num, offsets[num])
    out += x
    tr = b'trailer\n<</Size %d/Root %s' % (size, root.group(1))
    if info: tr += b'/Info ' + info.group(1)
    tr += b'/Prev %d>>\nstartxref\n%d\n%%%%EOF\n' % (prev, xref_off)
    out += tr
    open(dst, 'wb').write(out)
    print(f"{src.split('/')[-1]}: fonts patched {len(newobjs)}; glyph entries same={stats['same']} fixed={stats['fixed']} kept-original={stats['kept']}")
    for r in report: print(r)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], verbose='-v' in sys.argv)
