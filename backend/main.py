from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.parse import read_pdf_pages, split_payslips, extract_metrics, pair_maps

app = FastAPI(title="Paie Checker")

# servir le HTML
app.mount("/web", StaticFiles(directory="web", html=True), name="web")

@app.get("/")
def root():
    return {"status": "ok", "open_ui": "/web/"}

@app.post("/api/compare")
async def compare(
    silae: UploadFile = File(...),
    wagyz: UploadFile = File(...),
):
    silae_bytes = await silae.read()
    wagyz_bytes = await wagyz.read()

    pages_s = read_pdf_pages(silae_bytes)
    pages_w = read_pdf_pages(wagyz_bytes)

    slips_s = split_payslips(pages_s)
    slips_w = split_payslips(pages_w)

    pairs = pair_maps(slips_s, slips_w)

    rows = []
    for p in pairs:
        mS = extract_metrics(p["s"]["text"]) if p["s"] else {}
        mW = extract_metrics(p["w"]["text"]) if p["w"] else {}
        rows.append({
            "key": p["key"],
            "matched_by": p["matched_by"],
            "s": {k: p["s"].get(k) for k in ["nom","prenom","nir","mat"]} if p["s"] else None,
            "w": {k: p["w"].get(k) for k in ["nom","prenom","nir","mat"]} if p["w"] else None,
            "mS": mS,
            "mW": mW,
            # debug léger optionnel
            "dbg": {
                "s_first_lines": "\n".join(pages_s[0].split("\n")[:20]) if pages_s else "",
                "w_first_lines": "\n".join(pages_w[0].split("\n")[:20]) if pages_w else "",
            }
        })

    return {"rows": rows}
