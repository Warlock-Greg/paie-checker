import re
from typing import List, Optional

def normalize_keep_nl(s: str) -> str:
    return (s or "").replace("\u202f", " ").replace("\u00A0", " ")

def to_float(tok: str) -> Optional[float]:
    if not tok:
        return None
    t = re.sub(r"\s", "", tok).replace(",", ".")
    # si plusieurs points (séparateurs de milliers), on les retire
    if not re.search(r"\d+\.\d{2}$", t) and t.count(".") > 1:
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None

def numbers_in(line: str) -> List[float]:
    if not line:
        return []
    pats = re.findall(r"\d{1,3}(?:[ \u202f.,]\d{3})*[.,]\d{2}|\d+[.,]\d{2}", line)
    out: List[float] = []
    for p in pats:
        v = to_float(p)
        if v is not None:
            out.append(v)
    return out

def find_after(lines: List[str], pos: int, look_ahead: int = 3) -> Optional[float]:
    # cherche un montant dans la ligne pos puis les look_ahead suivantes
    for j in range(0, look_ahead + 1):
        k = pos + j
        if 0 <= k < len(lines):
            nums = numbers_in(lines[k])
            if nums:
                return nums[-1]
    return None
