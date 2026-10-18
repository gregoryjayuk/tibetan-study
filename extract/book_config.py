"""Settings that belong to a particular set of textbooks, with neutral defaults.

A private extract/book_config_local.py, if present, overrides any of these for the books you own:
    READER_PDF      file name of a level's graded-reader PDF in the data folder ('{level}' is replaced)
    FOOTER_MARKERS  text that marks a page-footer line to drop (the Tibetan page-number label is always dropped)
    LABEL_FIXES     {lesson id: [(misprinted speaker label, correct label), ...]}: a speaker label misprinted
                    once would merge two turns of the conversation, so the label (only) is corrected
"""
READER_PDF = '{level} readers.pdf'
FOOTER_MARKERS = ()
LABEL_FIXES = {}

try:
    import book_config_local as _local
except ImportError:
    _local = None
for _k in ('READER_PDF', 'FOOTER_MARKERS', 'LABEL_FIXES'):
    if _local is not None and hasattr(_local, _k):
        globals()[_k] = getattr(_local, _k)
