import re
_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069]")
def clean(text, maxlen):
    t = _CTRL.sub(" ", text)                 # strip control / zero-width / bidi chars
    t = re.sub(r"\s+", " ", t).strip()       # collapse whitespace (kills newline tricks)
    return t[:maxlen]                        # length-limit
NAME_MAX, CMD_MAX = 32, 120
