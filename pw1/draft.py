import os
import re
ISSN_PATTERN = re.compile(r"[0-9]{7}[0-9X]")
def normalize_issn(value):
    if value == None:
        return None
    try:
        chars=value.upper().replace("-","").replace(" ","")
    except:
        return None
    l = len(chars)
    return chars if ISSN_PATTERN.fullmatch(chars) else None
