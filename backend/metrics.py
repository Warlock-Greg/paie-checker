import re
from typing import Dict, List, Optional

from backend.fields import FIELDS
from backend.parse_utils import find_after, numbers_in, to_float

def _clean_lines(text: str) -> List[str]:
    lines = (text or "").split("\n")
    out = []
    for l in lines:
        l = re.sub(r"\s+", " ", l).strip()
        if l:
            out.append(l)
    return out

def _extract_conges(lines: List[str]) -> Dict[str, Optional[float]]:
    """
    Reprend ta logique "fenêtre" : on cherche la zone Congés N-1 et Congés N,
    puis on extrait acquis / pris / solde.
    """
    def parse_bucket(start_index: int) -> Dict[str, Optional[float]]:
        win = " ".join(lines[start_index:start_index + 8])

        def grab(rx: str) -> Optional[float]:
            m = re.search(rx, win, re.I)
            return to_float(m.group(1)) if m else None

        return {
            "acquis": grab(r"acquis\s*[:\-]?\s*(\d+(?:[.,]\d+)?)"),
            "pris":   grab(r"pris\s*[:\-]?\s*(\d+(?:[.,]\d+)?)"),
            "solde":  grab(r"solde\s*[:\-]?\s*(\d+(?:[.,]\d+)?)"),
        }

    pos_n1 = next((i for i, l in enumerate(lines) if re.search(r"cong[eé]s\s+n-?1", l, re.I)), -1)
    pos_n  = next((i for i, l in enumerate(lines) if re.search(r"cong[eé]s\s+n\b", l, re.I)), -1)

    conges = {"n1": {"acquis": None, "pris": None, "solde": None},
              "n":  {"acquis": None, "pris": None, "solde": None}}

    if pos_n1 >= 0:
        conges["n1"] = parse_bucket(pos_n1)
    if pos_n >= 0:
        conges["n"] = parse_bucket(pos_n)

    return conges

def extract_metrics(text: str, source: str) -> Dict[str, object]:
    """
    Retourne :
      - values: dict des champs canoniques -> valeur (ou None)
      - missing: liste des champs non trouvés
      - missing_blocking: liste des champs bloquants non trouvés
    """
    if source not in ("silae", "wagyz"):
        raise ValueError("source must be 'silae' or 'wagyz'")

    lines = _clean_lines(text)

    values: Dict[str, Optional[float]] = {}
    missing: List[str] = []
    missing_blocking: List[str] = []

    # 1) champs "montants" via table canonique
    for field, cfg in FIELDS.items():
        # Congés : gérés plus bas via fenêtre
        if field.startswith("leave_"):
            continue

        value = None
        rx_list = cfg.get("sources", {}).get(source, [])

        for rx in rx_list:
            pattern = re.compile(rx, re.I)
            for i, line in enumerate(lines):
                if pattern.search(line):
                    # valeur = dernier montant trouvé sur la ligne ou quelques lignes après
                    value = find_after(lines, i, look_ahead=3)
                    if value is not None:
                        break
            if value is not None:
                break

        values[field] = value
        if value is None:
            missing.append(field)
            if cfg.get("blocking"):
                missing_blocking.append(field)

    # 2) Congés (fenêtre) -> on remplit les champs canoniques leave_*
    conges = _extract_conges(lines)

    leave_map = {
        "leave_n1_acquired": conges["n1"]["acquis"],
        "leave_n1_taken":    conges["n1"]["pris"],
        "leave_n1_balance":  conges["n1"]["solde"],
        "leave_n_acquired":  conges["n"]["acquis"],
        "leave_n_taken":     conges["n"]["pris"],
        "leave_n_balance":   conges["n"]["solde"],
    }

    for field, val in leave_map.items():
        values[field] = val
        # Congés : non bloquant dans ce MVP, mais on marque manquant si None
        if val is None:
            missing.append(field)

    return {
        "values": values,
        "missing": missing,
        "missing_blocking": missing_blocking,
    }
