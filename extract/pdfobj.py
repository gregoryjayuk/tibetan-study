import re, zlib
class PDF:
    def __init__(self, path):
        self.data = open(path,'rb').read()
        self.objs = {}      # num -> bytes (dict part) ; streams stored separately
        self.streams = {}   # num -> raw stream bytes
        d = self.data
        for m in re.finditer(rb'(\d+)\s+(\d+)\s+obj\b', d):
            num = int(m.group(1)); start = m.end()
            end = d.find(b'endobj', start)
            body = d[start:end]
            si = body.find(b'stream')
            if si != -1 and re.search(rb'/Length', body[:si]):
                dictpart = body[:si]
                s = start + si + len('stream')
                if d[s:s+2] == b'\r\n': s += 2
                elif d[s:s+1] in (b'\n', b'\r'): s += 1
                lm = re.search(rb'/Length\s+(\d+)(\s+0\s+R)?', dictpart)
                if lm and not lm.group(2):
                    L = int(lm.group(1)); raw = d[s:s+L]
                else:
                    e = d.find(b'endstream', s); raw = d[s:e].rstrip(b'\r\n')
                self.objs[num] = dictpart; self.streams[num] = raw
            else:
                self.objs[num] = body
        # resolve indirect lengths
        for num, dp in list(self.objs.items()):
            if num in self.streams:
                lm = re.search(rb'/Length\s+(\d+)\s+0\s+R', dp)
                if lm:
                    ln = int(lm.group(1))
                    try:
                        L = int(self.objs[ln].strip())
                        m2 = re.search(rb'%d\s+0\s+obj\b' % num, d)
                        body_start = m2.end(); si = d.find(b'stream', body_start) + 6
                        if d[si:si+2] == b'\r\n': si += 2
                        elif d[si:si+1] in (b'\n', b'\r'): si += 1
                        self.streams[num] = d[si:si+L]
                    except Exception: pass
        # expand object streams
        for num, dp in list(self.objs.items()):
            if b'/ObjStm' in dp and num in self.streams:
                raw = self.decode(num)
                n = int(re.search(rb'/N\s+(\d+)', dp).group(1))
                first = int(re.search(rb'/First\s+(\d+)', dp).group(1))
                hdr = raw[:first].split()
                pairs = [(int(hdr[i]), int(hdr[i+1])) for i in range(0, 2*n, 2)]
                for i, (onum, off) in enumerate(pairs):
                    a = first + off; b = first + pairs[i+1][1] if i+1 < len(pairs) else len(raw)
                    if onum not in self.objs:
                        self.objs[onum] = raw[a:b]
    def decode(self, num):
        raw = self.streams[num]; dp = self.objs[num]
        if b'/FlateDecode' in dp:
            try: return zlib.decompress(raw)
            except Exception:
                return zlib.decompressobj().decompress(raw)
        return raw
    def ref(self, dp, key):
        m = re.search(rb'/' + key + rb'\s+(\d+)\s+0\s+R', dp)
        return int(m.group(1)) if m else None
