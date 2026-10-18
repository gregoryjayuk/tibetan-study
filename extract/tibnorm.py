"""Clean up Tibetan text pulled from the repaired PDFs.

pdftotext places a few characters oddly (spaces inside syllables, a tsheg typed before a vowel),
and the books themselves occasionally drop the space after a ག-final syllable (འདུགཡག).
Every rule here removes something that is never valid Tibetan orthography.
"""
import re

CONS = 'ཀཁགངཅཆཇཉཏཐདནཔཕབམཙཚཛཝཞཟའཡརལཤསཧཨཊཋཌཎཥ'
LETTER = 'ཀ-ཬ'          # base consonants
VOWEL = 'ཱ-྄'           # vowel signs and other combining marks
SUBJ = 'ྐ-ྼ'            # subjoined consonants
SYL = re.compile(r'^[གདབམའ]?[' + CONS + r'][' + SUBJ + r']*[ཱིེོྀུ]*'
                 r'(?:[གངདནབམའརལས][སད]?)?(?:འ[ིོུ]|འམ|འང|ར|ས)?$')
FIXLOG = []


def valid(s):
    return bool(SYL.match(s))


def split_syl(s):
    """'འདུགཡག' is two syllables with the separator lost: split after the ག/ཀ if both halves are valid."""
    if valid(s) or len(s) < 4:
        return s
    for i in range(1, len(s) - 1):
        if s[i] in 'གཀ' and valid(s[:i + 1]) and valid(s[i + 1:]):
            FIXLOG.append((s, s[:i + 1] + ' ' + s[i + 1:]))
            return s[:i + 1] + ' ' + s[i + 1:]
    return s


def norm(s):
    s = s.replace('​', '')
    # the fixed-form ra (U+0F6A) prints like ར but would never match a search or a flashcard answer
    s = s.replace('\u0f6a', '\u0f62')
    # a space before a combining mark or subjoined letter
    s = re.sub(r'([' + LETTER + VOWEL + SUBJ + r']) (?=[' + VOWEL + SUBJ + r'])', r'\1', s)
    # a space before a tsheg
    s = re.sub(r' ་', '་', s)
    # a tsheg typed before the vowel it belongs after: མོའ་ི -> མོའི་
    s = re.sub(r'་ ?([' + VOWEL + r'])', r'\1་', s)
    # a space splitting a vowel from its final letter(s): ཡི ན་ -> ཡིན་
    s = re.sub(r'([' + VOWEL + r']) (?=[' + LETTER + r'][' + LETTER + r']?(?:[་།༔\s]|$))', r'\1', s)
    # genitive/terminative -འི -འོ -འུ followed by a space instead of a tsheg
    s = re.sub(r'(འ[ིོུ]) (?=[' + LETTER + r'])', r'\1་', s)
    # ཤ is set with a stray space after it in these PDFs
    s = re.sub(r'ཤ (?=[' + LETTER + r'])', 'ཤ', s)
    # digits split by a space
    s = re.sub(r'([༠-༩]) (?=[༠-༩])', r'\1', s)
    # a space after a tsheg inside running text
    s = re.sub(r'་ +(?=[' + LETTER + r'])', '་', s)
    # ང takes a tsheg before a shad (སོང་།), which the text layer sometimes loses
    s = re.sub(r'ང།', 'ང་།', s)
    s = re.sub(r'་་+', '་', s)
    s = re.sub(r'[ཀ-ྼ]+', lambda m: split_syl(m.group(0)), s)
    return s.rstrip()
