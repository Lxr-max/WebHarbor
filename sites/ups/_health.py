"""Per-site health probe (called by the control plane)."""


def health():
    return {"ok": True, "site": "ups"}
