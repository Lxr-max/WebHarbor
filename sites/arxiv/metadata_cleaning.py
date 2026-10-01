"""Source-checked repairs for known arXiv scrape artifacts.

A repeated mathematical expression is not proof of a scrape error. Repairs match
both the paper identifier and the complete captured field, never a global regex.
Readable Unicode transcriptions and their original TeX titles are kept together
in metadata_corrections.json; unknown and subsequently edited values pass through.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Mapping

CORRECTIONS = json.loads(
    Path(__file__).with_name("metadata_corrections.json").read_text(encoding="utf-8")
)
_BY_ID = {entry["arxiv_id"]: entry for entry in CORRECTIONS}


def clean_paper_metadata_fields(paper_like) -> dict[str, str]:
    """Return only source-verified corrections for an exact captured paper."""
    if isinstance(paper_like, Mapping):
        get = paper_like.get
    else:
        get = lambda key: getattr(paper_like, key, None)
    correction = _BY_ID.get(get("arxiv_id"))
    if correction is None:
        return {}
    field = correction["field"]
    if get(field) != correction["captured"]:
        return {}
    return {field: correction["corrected"]}
