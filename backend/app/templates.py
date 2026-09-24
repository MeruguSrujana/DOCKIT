# app/templates.py

STANDARD_TEMPLATES = {
    "fir": {
        "name": "First Information Report",
        "icon": "📄",
        "fields": [
            "complainant_name",
            "incident_date",
            "incident_location",
            "offence_details",
            "accused_details",
        ],
    },

    "witness_statement": {
        "name": "Witness Statement",
        "icon": "👤",
        "fields": [
            "witness_name",
            "statement_date",
            "statement",
            "investigating_officer",
        ],
    },

    "forensic_request": {
        "name": "Forensic Examination Request",
        "icon": "🔬",
        "fields": [
            "exhibit_number",
            "evidence_description",
            "examination_required",
            "forensic_laboratory",
            "sending_officer",
        ],
    },

    "seizure_memo": {
        "name": "Seizure Memo",
        "icon": "📦",
        "fields": [
            "seizure_date",
            "seizure_location",
            "item_description",
            "seized_by",
            "witness_details",
        ],
    },

    "forensic_report": {
        "name": "Forensic Report",
        "icon": "🧪",
        "fields": [
            "exhibit_number",
            "examination_method",
            "findings",
            "conclusion",
            "forensic_officer",
        ],
    },

    "charge_sheet": {
        "name": "Charge Sheet",
        "icon": "⚖️",
        "fields": [
            "accused_details",
            "charges",
            "evidence_summary",
            "witness_list",
            "investigating_officer",
        ],
    },

    "court_filing": {
        "name": "Court Filing",
        "icon": "🏛️",
        "fields": [
            "court_name",
            "filing_type",
            "document_details",
            "filed_by",
            "filing_date",
        ],
    },
}


def get_templates():
    return STANDARD_TEMPLATES


def get_template(template_type: str):
    return STANDARD_TEMPLATES.get(template_type)