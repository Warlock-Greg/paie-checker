import io
import re
from typing import Dict, List, Optional

import pdfplumber

from backend.parse_utils import normalize_keep_nl
from backend.ocr import ocr_pdf_to_pages


# -------------------------------
# Regex identification salarié
# -------------------------------
RX_NIR = re.compile(r"\b(?:\d[ \u202f]?){13,17}\b")
RX_MAT = re.compile(r"\bMatricule\s*[:：]?\s*([A-Za-z0-9]+)\b", re.IGNORECASE)
RX_NAME = re.compile(
    r"\b(Monsieur|Madame)\s+([A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜ' -]{2,})\s+([A-Za-zÀ-ÿ' -]{2,})\b"
)


# -------------------------------
# Lecture PDF (texte / OCR / auto)
# -------------------------------
def read_pdf_pages(pdf_bytes: bytes, mode: str = "auto") -> List[str]:
    """
    Lit un PDF et retourne une liste de pages texte.

    mode :
      - "text" : pdfplumber uniquement
      - "ocr"  : OCR uniquement
      - "auto" : tente pdfplumber, sinon OCR
    """
    pages: List[str] = []

    # 1) Tentative lecture TEXTE
    if mode in ("auto", "text"):
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text(
                        x_tolerance=3,
                        y_tolerance=3,
                        layout=True
                    ) or ""
                    txt = normalize_keep_nl(txt)
                    pages.append(txt)
        except Exception:
            pages = []

    # 2) Fallback OCR si nécessaire
    has_text = any(p.strip() for p in pages)

    if mode == "ocr" or (mode == "auto" and not has_text):
        pages = ocr_pdf_to_pages(pdf_bytes)

    return pages


# -------------------------------
# Extraction clé salarié
# -------------------------------
def extract_key_and_name(text: str) -> dict:
    """
    Extrait NIR / matricule / nom / prénom depuis un texte.
    """
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
    return {
        "key": key,
        "nir": nir,
        "mat": mat,
        "nom": nom,
        "prenom": prenom,
    }


# -------------------------------
# Split multi-salariés
# -------------------------------
def split_payslips(pages: List[str]) -> Dict[str, dict]:
    """
    Regroupe les pages par salarié.
    Chaque nouvelle page contenant une clé (NIR ou matricule)
    démarre ou continue un bulletin.
    """
    slips: Dict[str, dict] = {}
    current: Optional[str] = None

    for raw in pages:
        txt = normalize_keep_nl(raw)
        meta = extract_key_and_name(txt)
        key = meta["key"]

        # Nouvelle clé détectée
        if key:
            current = key
            if current not in slips:
                slips[current] = {
                    "key": current,
                    "nir": meta["nir"],
                    "mat": meta["mat"],
                    "nom": meta["nom"],
                    "prenom": meta["prenom"],
                    "text": "",
                }

        # Cas bulletin unique (fallback)
        if not current:
            current = "__single__"
            if current not in slips:
                slips[current] = {
                    "key": current,
                    "nir": None,
                    "mat": None,
                    "nom": None,
                    "prenom": None,
                    "text": "",
                }

        slips[current]["text"] += "\n" + txt

        # Backfill nom / prénom si trouvé plus tard
        if not slips[current].get("nom") and meta.get("nom"):
            slips[current]["nom"] = meta["nom"]
        if not slips[current].get("prenom") and meta.get("prenom"):
            slips[current]["prenom"] = meta["prenom"]

    return slips


# -------------------------------
# Appariement Silae ↔ Wagyz
# -------------------------------
def pair_maps(map_s: Dict[str, dict], map_w: Dict[str, dict]) -> List[dict]:
    """
    Apparie les bulletins :
      1) clé exacte (NIR / matricule)
      2) fallback Nom + Prénom
    """
    def by_name(x: dict) -> str:
        return (
            (x.get("nom") or "").upper().strip()
            + "|"
            + (x.get("prenom") or "").upper().strip()
        )

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
                matched_by = "Nom + Prénom"

        elif w and not s:
            cand = np_s.get(by_name(w))
            if cand:
                s = cand
                matched_by = "Nom + Prénom"

        if not matched_by:
            matched_by = "Matricule" if key != "__single__" else "Unique (__single__)"

        pairs.append({
            "key": key,
            "s": s,
            "w": w,
            "matched_by": matched_by,
        })

    return pairs

