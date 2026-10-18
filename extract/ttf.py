"""Minimal TrueType table directory reader."""
import struct
def tables(font):
    numTables = struct.unpack('>H', font[4:6])[0]
    t = {}
    for i in range(numTables):
        tag, cs, off, ln = struct.unpack('>4sIII', font[12+16*i:28+16*i])
        t[tag.decode('latin1')] = (off, ln)
    return t
