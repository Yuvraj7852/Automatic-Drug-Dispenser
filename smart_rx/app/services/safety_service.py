import json
from pathlib import Path
from flask import current_app

def _normal(value):
    return (value or "").strip().lower()

def check_allergies(patient, prescription_items):
    allergy_text = _normal(patient.allergies)
    if not allergy_text:
        return []
    alerts = []
    terms = [term.strip() for term in allergy_text.replace(";", ",").split(",") if term.strip()]
    for item in prescription_items:
        names = {_normal(item.medicine.name), _normal(item.medicine.generic_name)}
        for term in terms:
            if any(term in name or name in term for name in names if name):
                alerts.append(f"Possible allergy match: {item.medicine.name} ({term})")
    return alerts

def check_interactions(prescription_items):
    path = Path(current_app.root_path) / "data" / "interactions.json"
    pairs = json.loads(path.read_text(encoding="utf-8")).get("pairs", [])
    names = set()
    for item in prescription_items:
        names.add(_normal(item.medicine.name))
        names.add(_normal(item.medicine.generic_name))
    alerts = []
    for pair in pairs:
        a, b = _normal(pair["medicine_a"]), _normal(pair["medicine_b"])
        if a in names and b in names:
            alerts.append(pair["warning"])
    return alerts
