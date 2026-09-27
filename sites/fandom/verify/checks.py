"""Text helpers shared by graders and contract predicates."""

import re


def fold(text):
    text = (text or "").lower()
    text = (
        text.replace("—", "-")
        .replace("–", "-")
        .replace("’", "'")
        .replace("`", "'")
    )
    text = text.replace(",", "")
    text = re.sub(r"[$%]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def num_pat(value):
    if isinstance(value, float) and not float(value).is_integer():
        rendered = f"{value:.2f}"
        if rendered.endswith("0") and not rendered.endswith("00"):
            base = rendered[:-1]
            return re.compile(rf"(?<!\d){re.escape(base)}0?(?!\d)")
        return re.compile(rf"(?<!\d){re.escape(rendered)}(?!\d)")
    whole = int(value)
    return re.compile(rf"(?<!\d){whole}(?:\.0+)?(?!\d)")


def has_num(text, value):
    return num_pat(value).search(fold(text)) is not None


def has_phrase(text, phrase):
    return fold(phrase) in fold(text)


def near(text, anchor, value, window=240):
    folded = fold(text)
    needle = fold(anchor)
    if not needle:
        return False
    for match in re.finditer(re.escape(needle), folded):
        start = match.start()
        chunk = folded[max(0, start - window): start + len(needle) + window]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if num_pat(value).search(chunk):
                return True
        elif fold(str(value)) in chunk:
            return True
    return False
