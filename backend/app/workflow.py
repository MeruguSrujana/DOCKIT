from fastapi import HTTPException, status

# Branching, event-driven lifecycle (per architecture §5): a document can
# return to review after being received (e.g. further investigation
# required) rather than only ever moving forward.
DOCUMENT_TRANSITIONS = {
    "draft":        {"register": "registered"},
    "registered":   {"submit_for_review": "under_review"},
    "under_review": {"approve": "approved", "reject": "draft"},
    "approved":     {"transfer": "transferred", "archive": "archived"},
    "transferred":  {"acknowledge_receipt": "received"},
    "received":     {"submit_for_review": "under_review",   # branch: further action required
                      "transfer": "transferred",              # branch: onward transfer (e.g. to court)
                      "archive": "archived"},
    "archived":     {},
}

ACTION_TO_EVENT_TYPE = {
    "register": "registered",
    "submit_for_review": "reviewed",
    "approve": "approved",
    "reject": "rejected",
    "transfer": "transferred",
    "acknowledge_receipt": "received",
    "archive": "archived",
}

EVIDENCE_TRANSITIONS = {
    "collected":        {"seal": "sealed"},
    "sealed":           {"transfer": "transferred"},
    "transferred":      {"receive": "received"},
    "received":         {"examine": "examined"},
    "examined":         {"generate_report": "report_generated"},
    "report_generated": {"use": "used"},
    "used":             {"archive": "archived"},
    "archived":         {},
}


def apply_transition(transitions: dict, current_state: str, action: str) -> str:
    """Validates a transition against the real state machine. Raises if
    the action isn't valid from the current state — invalid transitions
    are rejected by the backend, never silently accepted."""
    valid_actions = transitions.get(current_state, {})
    if action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Invalid transition: cannot perform '{action}' from state "
                f"'{current_state}'. Valid actions here: {list(valid_actions.keys()) or 'none'}."
            ),
        )
    return valid_actions[action]
