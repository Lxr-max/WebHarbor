"""Frozen expectations for the refined research tasks; answers remain reviewer-only."""
import json
import re
from pathlib import Path
from verify_lib import (check_trajectory_identity, check_read_only, contains_phrase,
                        contains_amount, navigated_to_path, final_answer, normalize_text)
CONTRACT = json.loads(Path(__file__).with_name('refined_contract.json').read_text())

def fact_present(text, fact):
    if fact.isdigit():
        return contains_amount(text, int(fact))
    return contains_phrase(text, fact)

def entity_passages(answer, names):
    """Use entity mentions as boundaries, retaining prose, bullet and table syntax.

    This is a deterministic assertion matcher, not general semantic understanding.
    It rejects swapped facts across entities instead of matching an answer-wide bag.
    """
    text = normalize_text(answer)
    hits = []
    for name in names:
        needle = normalize_text(name)
        for m in re.finditer(re.escape(needle), text):
            hits.append((m.start(), m.end(), name))
    hits.sort()
    out = {name: [] for name in names}
    for i, (start, end, name) in enumerate(hits):
        stop = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        # Exclude mentions used merely in a negation or a list of candidates.
        prefix = re.split(r'[.;\n]', text[:start])[-1]
        if re.search(r'\b(?:not|incorrect|wrong|rather than)\s*$', prefix):
            continue
        out[name].append(text[start:stop])
    return out

def check(n, judge, traj, initial_db, after_db):
    spec = CONTRACT[str(n)]
    check_trajectory_identity(judge, traj, f'Chess.com--{n}')
    passages = entity_passages(final_answer(traj), [e['name'] for e in spec['entities']])
    for entity in spec['entities']:
        judge.check('visited_'+entity['path'], navigated_to_path(traj, entity['path']))
        text = ' '.join(passages[entity['name']])
        for fact in entity['facts']:
            judge.check(entity['name']+': '+fact, fact_present(text, fact))
    check_read_only(judge, initial_db, after_db)
