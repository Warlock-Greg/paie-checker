from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles

from backend.parse import read_pdf_pages, split_payslips, pair_maps
from backend.metrics import extract_metrics

app = FastAPI(title="Paie Checker")

# -----------------------------
# Servir le front HTML
# -----------------------------
app.mount("/web", StaticFiles(directory="web", html=True), name="web")


@app.get("/")
def root():
    return {
        "status": "ok",
        "open_ui": "/web/"
    }


# -----------------------------
# API principale de comparaison
# -----------------------------
@app.post("/api/compare")
async def compare(
    silae: UploadFile = File(...),
    wagyz: UploadFile = File(...),
    mode: str = Form("auto"),  # auto | text | ocr
):
    # 1) Lecture des fichiers
    silae_bytes = await silae.read()
    wagyz_bytes = await wagyz.read()

    # 2) Lecture PDF (texte / OCR / auto)
    pages_s = read_pdf_pages(silae_bytes, mode=mode)
    pages_w = read_pdf_pages(wagyz_bytes, mode=mode)

    # 3) Split multi-salariés
    slips_s = split_payslips(pages_s)
    slips_w = split_payslips(pages_w)

    # 4) Appariement Silae ↔ Wagyz
    pairs = pair_maps(slips_s, slips_w)

    # 5) Extraction métriques + réponse
    rows = []

    for p in pairs:
        mS = (
            extract_metrics(p["s"]["text"], source="silae")
            if p.get("s") else
            {"values": {}, "missing": ["__no_bulletin__"], "missing_blocking": ["__no_bulletin__"]}
        )

        mW = (
            extract_metrics(p["w"]["text"], source="wagyz")
            if p.get("w") else
            {"values": {}, "missing": ["__no_bulletin__"], "missing_blocking": ["__no_bulletin__"]}
        )

        rows.append({
            "key": p["key"],
            "matched_by": p["matched_by"],

            "s": (
                {k: p["s"].get(k) for k in ["nom", "prenom", "nir", "mat"]}
                if p.get("s") else None
            ),
            "w": (
                {k: p["w"].get(k) for k in ["nom", "prenom", "nir", "mat"]}
                if p.get("w") else None
            ),

            "mS": mS,
            "mW": mW,

            # Debug : aperçu texte extrait
            "dbg": {
                "s_first_lines": "\n".join(pages_s[0].split("\n")[:20]) if pages_s else "",
                "w_first_lines": "\n".join(pages_w[0].split("\n")[:20]) if pages_w else "",
                "mode_used": mode,
            }
        })

    return {"rows": rows}

