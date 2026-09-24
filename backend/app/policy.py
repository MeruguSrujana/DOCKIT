# app/policy.py

# DOCKIT Policy Engine
# Decides whether a role can perform an action
# based on the current document state.

POLICIES = {

    "investigating_officer": {
        "draft": ["register", "new_version"],
        "registered": ["submit_for_review", "new_version"],
        "under_review": ["new_version"],
        "approved": ["transfer", "new_version"],
        "transferred": [],
        "received": ["submit_for_review", "transfer", "new_version"],
        "archived": [],
    },

    "forensic_officer": {
        "draft": ["new_version"],
        "registered": ["submit_for_review", "new_version"],
        "under_review": ["approve", "reject", "new_version"],
        "approved": ["transfer", "new_version"],
        "transferred": ["acknowledge_receipt"],
        "received": ["submit_for_review", "transfer", "new_version"],
        "archived": [],
    },

    "prosecutor": {
        "draft": ["new_version"],
        "registered": ["submit_for_review", "new_version"],
        "under_review": ["approve", "reject", "new_version"],
        "approved": ["transfer", "new_version"],
        "transferred": ["acknowledge_receipt"],
        "received": ["submit_for_review", "transfer", "new_version"],
        "archived": [],
    },

    "court_clerk": {
        "under_review": ["approve", "reject"],
        "transferred": ["acknowledge_receipt"],
        "received": ["archive"],
        "archived": [],
    },

    "admin": {
        "*": [
            "register",
            "submit_for_review",
            "approve",
            "reject",
            "transfer",
            "acknowledge_receipt",
            "archive",
            "new_version",
        ]
    },
}


def is_allowed(role: str, document_state: str, action: str) -> bool:

    role_policy = POLICIES.get(role)

    if not role_policy:
        return False

    # Admin can perform the listed actions.
    if "*" in role_policy:
        return action in role_policy["*"]

    allowed_actions = role_policy.get(document_state, [])

    return action in allowed_actions