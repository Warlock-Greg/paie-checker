import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pdfplumber

RX_NIR = re.compile(r"\b(?:\d[ \u202f]?){13,17}\b")
RX_MAT = re.compile(r"\bMatricule\s*[:：]?\s*([A-Za-z0-9]+)\b", re.IGNORECASE)
RX_NAME = re.compile(
    r"\b(Monsieur|Madame)\s+([A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜ' -]{2,})\s+([A-Za-zÀ-ÿ' -]{2,})\b"
)

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
    pats = re.findall(r"\d{1,3}(?:[ \u202f.,]\d{3})*[.,]\d{2}|\d+[.,]\d{2}", line or "")
    out = []
    for p in pats:
        v = to_float(p)
        if v is not None:
            out.append(v)
    return out

def extract_key_and_name(text: str) -> dict:
    m_nir = RX_NIR.search(text or "")
    nir = re.sub(r"\D", "", m_nir.group(0)) if m_nir else None
    m_mat = RX_MAT.search(text or "")
    mat = m_mat.group(1) if m_mat else None

    nom = prenom = None
    m_name = RX_NAME.search(text or "")
    if m_name:
        nom = m_name.group(2).strip()
        prenom = m_name.group(3).strip()

    key = nir or mat or None
    return {"key": key, "nir": nir, "mat": mat, "nom": nom, "prenom": prenom}

def read_pdf_pages(pdf_bytes: bytes) -> List[str]:
    pages: List[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            pages.append(normalize_keep_nl(txt))
    return pages

# petit import local pour éviter warning si tu copies/colles
import io

def split_payslips(pages: List[str]) -> Dict[str, dict]:
    slips: Dict[str, dict] = {}
    current: Optional[str] = None

    for raw in pages:
        txt = normalize_keep_nl(raw)
        meta = extract_key_and_name(txt)
        key = meta["key"]

        if key:
            current = key
            if current not in slips:
                slips[current] = {"key": current, "nir": meta["nir"], "mat": meta["mat"], "nom": meta["nom"], "prenom": meta["prenom"], "text": ""}

        if not current:
            current = "__single__"
            if current not in slips:
                slips[current] = {"key": current, "nir": None, "mat": None, "nom": None, "prenom": None, "text": ""}

        slips[current]["text"] += "\n" + txt
        # backfill nom/prénom si découvert plus tard
        if not slips[current].get("nom") and meta.get("nom"):
            slips[current]["nom"] = meta["nom"]
        if not slips[current].get("prenom") and meta.get("prenom"):
            slips[current]["prenom"] = meta["prenom"]

    return slips

def find_after(lines: List[str], pos: int, look_ahead: int = 3) -> Optional[float]:
    for j in range(0, look_ahead + 1):
        k = pos + j
        if k < len(lines):
            nums = numbers_in(lines[k])
            if nums:
                return nums[-1]
    return None

def extract_metrics(text: str) -> dict:
    lines = [re.sub(r"\s+", " ", l).strip() for l in (text or "").split("\n")]
    lines = [l for l in lines if l]

    def first_pos(rx: re.Pattern) -> int:
        for i, l in enumerate(lines):
            if rx.search(l):
                return i
        return -1

    # mapping proche de ton JS
    map_rx = {
        "salaire_brut": [re.compile(r"\bsalaire\s+brut\b", re.I), re.compile(r"\bSBT001\b", re.I)],
        "net_imposable": [re.compile(r"\bmontant\s+net\s+imposable\b", re.I), re.compile(r"\bINI001\b", re.I), re.compile(r"\bnet\s+imposable\b", re.I)],
        "net_social": [re.compile(r"\bmontant\s+net\s+social\b", re.I), re.compile(r"\bNTS001\b", re.I)],
        "net_a_payer": [re.compile(r"\bnet\s+à\s+payer\b", re.I), re.compile(r"\bnet\s+pay[ée]\b", re.I), re.compile(r"\bNAP00[12]\b", re.I)],
    }

    m: Dict[str, Optional[float]] = {}
    for k, rxs in map_rx.items():
        pos = -1
        for rx in rxs:
            pos = first_pos(rx)
            if pos >= 0:
                break
        m[k] = find_after(lines, pos, 3) if pos >= 0 else None

    # Retenues
    pos_tr = first_pos(re.compile(r"\btotal\s+des\s+retenues\b", re.I))
    m["total_cotisations_salariales"] = find_after(lines, pos_tr, 0) if pos_tr >= 0 else None

    # Totalisation cotisations (2 montants)
    pos_tc = first_pos(re.compile(r"\btotalisation\s+cotisations\b", re.I))
    if pos_tc >= 0:
        nums = numbers_in(lines[pos_tc])
        if len(nums) >= 2:
            if m.get("total_cotisations_salariales") is None:
                m["total_cotisations_salariales"] = nums[0]
            m["total_charges_patronales"] = nums[1]

    if m.get("total_charges_patronales") is None:
        pos_cp = first_pos(re.compile(r"\bcharges?\s+patronales?\b", re.I))
        m["total_charges_patronales"] = find_after(lines, pos_cp, 0) if pos_cp >= 0 else None

    pos_cg = first_pos(re.compile(r"\bco[uû]t\s+global\b", re.I))
    m["cout_total_employeur"] = find_after(lines, pos_cg, 0) if pos_cg >= 0 else None

    # Congés (simple fenêtre)
    m["conges"] = {"n1": {}, "n": {}}
    pos_n1 = next((i for i,l in enumerate(lines) if re.search(r"cong[eé]s\s+n-?1", l, re.I)), -1)
    pos_n  = next((i for i,l in enumerate(lines) if re.search(r"cong[eé]s\s+n\b", l, re.I)), -1)

    def parse_conges(win: str) -> dict:
        def g(rx):
            mm = re.search(rx, win, re.I)
            return to_float(mm.group(1)) if mm else None
        return {
            "acquis": g(r"acquis\s*[:\-]?\s*(\d+(?:[.,]\d+)?)"),
            "pris":   g(r"pris\s*[:\-]?\s*(\d+(?:[.,]\d+)?)"),
            "solde":  g(r"solde\s*[:\-]?\s*(\d+(?:[.,]\d+)?)"),
        }

    if pos_n1 >= 0:
        win = " ".join(lines[pos_n1:pos_n1+8])
        m["conges"]["n1"] = parse_conges(win)
    if pos_n >= 0:
        win = " ".join(lines[pos_n:pos_n+8])
        m["conges"]["n"] = parse_conges(win)

    return m

def pair_maps(map_s: Dict[str, dict], map_w: Dict[str, dict]) -> List[dict]:
    def by_name(x: dict) -> str:
        return (x.get("nom") or "").upper().strip() + "|" + (x.get("prenom") or "").upper().strip()

    np_s = {by_name(v): v for v in map_s.values()}
    np_w = {by_name(v): v for v in map_w.values()}

    pairs = []
    all_keys = set(map_s.keys()) | set(map_w.keys())

    for key in all_keys:
        s = map_s.get(key)
        w = map_w.get(key)
        matched_by = None

        if s and w:
            if s.get("nir") and w.get("nir") and s["nir"] == w["nir"]:
                matched_by = "NIR"
            else:
                matched_by = "Clé exacte" if key != "__single__" else "Unique (__single__)"
        elif s and not w:
            cand = np_w.get(by_name(s))
            if cand:
                w = cand
                matched_by = "Nom+Prénom"
        elif w and not s:
            cand = np_s.get(by_name(w))
            if cand:
                s = cand
                matched_by = "Nom+Prénom"

        if not matched_by:
            matched_by = "Matricule" if key != "__single__" else "Unique (__single__)"

        pairs.append({"key": key, "s": s, "w": w, "matched_by": matched_by})

    return pairs
