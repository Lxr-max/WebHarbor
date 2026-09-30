"""Bind comparison values to their named entity, accepting prose and table rows."""
import re
from decimal import Decimal

def entity_numbers(judge, answer, name, aliases, other_aliases, expected):
    pattern = "|".join("(?:"+x+")" for x in aliases)
    stop = "|".join("(?:"+x+")" for x in other_aliases)
    chunks=[]
    for match in re.finditer(pattern, answer, re.I):
        tail=answer[match.end():]
        boundary=re.search(stop,tail,re.I) if stop else None
        chunks.append(tail[:boundary.start()] if boundary else tail)
    def numbers(s):
        return {Decimal(m.replace(",", "")) for m in re.findall(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?(?!\w|\.\d)",s)}
    want={Decimal(str(x).replace(",", "")) for x in expected}
    judge.check(name, any(want <= numbers(s) for s in chunks), "requested values must belong to the named comparison entity")
