FIELDS = {
  "gross_salary": {
    "label": "Salaire brut",
    "type": "amount",
    "blocking": True,
    "sources": {
      "silae": [r"salaire\s+brut", r"SBT001"],
      "wagyz": [r"salaire\s+brut"],
    }
  },
  "net_payable": {
    "label": "Net à payer",
    "type": "amount",
    "blocking": True,
    "sources": {
      "silae": [r"net\s+à\s+payer", r"net\s+pay[ée]", r"NAP00[12]"],
      "wagyz": [r"net\s+pay[ée]"],
    }
  },
  "employee_contrib_total": {
    "label": "Cotisations salariales",
    "type": "amount",
    "blocking": True,
    "sources": {
      "silae": [r"total\s+des\s+retenues"],
      "wagyz": [r"cot\.?\s+salariales"],
    }
  },
  # … tu complètes progressivement
}
