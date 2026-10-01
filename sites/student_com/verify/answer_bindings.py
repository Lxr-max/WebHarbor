"""Natural-answer numeric associations shared by the student task checks."""
import re
from decimal import Decimal
def _number_pattern(value):
    """Standalone number. ``3.2`` does not match ``13.2``, ``3.22``, or ``32.38``,
    and ``3`` does not match ``67.3`` or ``2025``. Thousands commas are optional."""
    canon = re.sub(r"[,\s]", "", str(value)).strip(".,")
    if "." in canon:
        whole, frac = canon.split(".", 1)
    else:
        whole, frac = canon, None
    if not whole or not re.fullmatch(r"\d+", whole):
        raise ValueError(f"not a number: {value!r}")
    groups = []
    rest = whole
    while rest:
        groups.append(rest[-3:])
        rest = rest[:-3]
    groups.reverse()
    body = groups[0] + "".join(f",?{part}" for part in groups[1:])
    if frac is not None:
        if not re.fullmatch(r"\d+", frac):
            raise ValueError(f"not a number: {value!r}")
        body += r"\." + frac
    # A sentence-final period is not another decimal place. ``3.2.`` still
    # matches 3.2; ``3.22`` and ``3.2.5`` do not.
    return re.compile(rf"(?<![\d.]){body}(?!\d)(?!\.\d)")


def _term_pattern(label):
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])", re.I)


def _spans(text, labels):
    found = []
    for label in labels or []:
        if not label:
            continue
        for match in _term_pattern(label).finditer(text):
            found.append((match.start(), match.end()))
    return found


def _gap(left, right):
    a0, a1 = left
    b0, b1 = right
    if a1 <= b0:
        return b0 - a1
    if b1 <= a0:
        return a0 - b1
    return 0


def _nearest_is_subject(origin, subjects, competitors, window):
    anchors = [(span, True) for span in subjects] + [(span, False) for span in competitors]
    if not anchors:
        return False
    preceding = [(span, flag) for span, flag in anchors if span[1] <= origin[0]]
    if preceding:
        anchors = preceding
    distances = [(_gap(origin, span), is_subject) for span, is_subject in anchors]
    best = min(dist for dist, _ in distances)
    if best > window:
        return False
    return all(is_subject for dist, is_subject in distances if dist == best)


def _assertions(text):
    return re.split(r";|\n|(?<!\d)\.(?=\s|$)|(?<=\d)\.(?=\s+[A-Z])", text)


def _affirmed(text, start):
    prefix = text[:start]
    return not re.search(r"\b(?:not|never|incorrect|wrong|isn't|isnt)\b(?:\W+\w+){0,3}\W*$", prefix, re.I)


def number_bound(text, value, groups, window=220):
    pattern = _number_pattern(value)
    for segment in _assertions(text):
        for match in pattern.finditer(segment):
            origin = (match.start(), match.end())
            if _affirmed(segment, match.start()) and all(
                _nearest_is_subject(origin, _spans(segment, subjects), _spans(segment, competitors), window)
                for subjects, competitors in groups):
                return True
    return False


def phrase_bound(text, phrase, groups, window=220):
    for segment in _assertions(text):
        for match in _term_pattern(phrase).finditer(segment):
            origin = (match.start(), match.end())
            if _affirmed(segment, match.start()) and all(
                _nearest_is_subject(origin, _spans(segment, subjects), _spans(segment, competitors), window)
                for subjects, competitors in groups):
                return True
    return False


def context_window(text, anchor, must, must_not, window=80):
    for match in re.finditer(re.escape(anchor), text, re.I):
        segment = text[max(0, match.start() - window):match.end() + window]
        if all(_term_pattern(term).search(segment) for term in must) and all(
                not _term_pattern(term).search(segment) for term in must_not):
            return True
    return False


BINDINGS = {
1: {'answer_buffer': [(['buffer'], ['target', 'leftover', 'left over'])], 'answer_target': [(['target'], ['buffer','leftover','left over'])], 'answer_leftover': [(['left','remaining'], ['buffer','target'])]},
3: {'answer_gt1_price': [(['International House','I-House'], ['Eighth','Piedmont','Freeman'])], 'answer_gt2_price': [(['Eighth'], ['International House','Piedmont','Freeman'])]},
5: {'gainesville_count': [(['Gainesville'],['Austin'])], 'austin_count': [(['Austin'],['Gainesville'])]},
15: {'answer_min_price': [(['Moontower'],['Villas'])], 'answer_max_price': [(['Moontower'],['Villas'])], 'answer_rating': [(['Moontower'],['Villas'])], 'answer_reviews': [(['Moontower'],['Villas'])], 'answer_villas_rating': [(['Villas'],['Moontower'])], 'answer_villas_reviews': [(['Villas'],['Moontower'])]},
18: {'answer_rent_target': [(['target'],['cheapest','room'])], 'answer_cheapest_room': [(['cheapest','room'],['target'])]}
}
