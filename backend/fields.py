# Table canonique : noms standard + libellés/codes par source
FIELDS = {
    # ---- Financiers (bloquants) ----
    "gross_salary": {
        "label": "Salaire brut",
        "type": "amount",
        "blocking": True,
        "weight": 10,
        "sources": {
            "silae": [r"salaire\s+brut", r"\bSBT001\b"],
            "wagyz": [r"salaire\s+brut"],
        },
    },
    "net_taxable": {
        "label": "Net imposable",
        "type": "amount",
        "blocking": True,
        "weight": 10,
        "sources": {
            "silae": [r"montant\s+net\s+imposable", r"\bINI001\b", r"net\s+imposable"],
            "wagyz": [r"net\s+imposable"],
        },
    },
    "net_social": {
        "label": "Net social",
        "type": "amount",
        "blocking": True,
        "weight": 10,
        "sources": {
            "silae": [r"montant\s+net\s+social", r"\bNTS001\b"],
            "wagyz": [r"net\s+social"],
        },
    },
    "net_payable": {
        "label": "Net à payer",
        "type": "amount",
        "blocking": True,
        "weight": 10,
        "sources": {
            "silae": [r"net\s+à\s+payer", r"net\s+pay[ée]", r"\bNAP00[12]\b", r"\bNAP00[12]\b"],
            "wagyz": [r"net\s+pay[ée]", r"net\s+à\s+payer"],
        },
    },
    "employee_contrib_total": {
        "label": "Cotisations salariales",
        "type": "amount",
        "blocking": True,
        "weight": 10,
        "sources": {
            "silae": [r"total\s+des\s+retenues", r"cotisations\s+salariales"],
            "wagyz": [r"cot\.?\s*salariales", r"cotisations\s+salariales"],
        },
    },
    "employer_contrib_total": {
        "label": "Cotisations patronales",
        "type": "amount",
        "blocking": True,
        "weight": 10,
        "sources": {
            "silae": [r"charges?\s+patronales?", r"totalisation\s+cotisations"],
            "wagyz": [r"cot\.?\s*patronales", r"cotisations\s+patronales"],
        },
    },
    "employer_total_cost": {
        "label": "Coût total employeur",
        "type": "amount",
        "blocking": True,
        "weight": 10,
        "sources": {
            "silae": [r"co[uû]t\s+global", r"co[uû]t\s+total"],
            "wagyz": [r"co[uû]t\s+total", r"co[uû]t\s+employeur", r"co[uû]t\s+global"],
        },
    },

    # ---- Congés (non bloquants dans ce MVP) ----
    # Ici on détecte surtout la "zone congés" via metrics.py (fenêtre),
    # mais on garde les noms canoniques pour le scoring/affichage.
    "leave_n1_acquired": {"label": "Congés N-1 acquis", "type": "days", "blocking": False, "weight": 2, "sources": {"silae": [], "wagyz": []}},
    "leave_n1_taken":    {"label": "Congés N-1 pris",   "type": "days", "blocking": False, "weight": 2, "sources": {"silae": [], "wagyz": []}},
    "leave_n1_balance":  {"label": "Congés N-1 solde",  "type": "days", "blocking": False, "weight": 2, "sources": {"silae": [], "wagyz": []}},
    "leave_n_acquired":  {"label": "Congés N acquis",   "type": "days", "blocking": False, "weight": 2, "sources": {"silae": [], "wagyz": []}},
    "leave_n_taken":     {"label": "Congés N pris",     "type": "days", "blocking": False, "weight": 2, "sources": {"silae": [], "wagyz": []}},
    "leave_n_balance":   {"label": "Congés N solde",    "type": "days", "blocking": False, "weight": 2, "sources": {"silae": [], "wagyz": []}},
}
