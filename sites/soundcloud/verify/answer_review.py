"""Entity-bound music facts; accepts prose, bullets and table rows."""
import re
import unicodedata
from decimal import Decimal


def normalized(s):
    s = unicodedata.normalize("NFKC", s).casefold().replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s)


def bind_tracks(judge, answer, records):
    text = normalized(answer)
    titles = sorted({normalized(r[0]) for r in records}, key=len, reverse=True)
    pattern = "|".join(re.escape(t) for t in titles)
    mentions = list(re.finditer(pattern, text))
    for title, plays, duration, artist in records:
        key = normalized(title)
        segments = [text[m.end():mentions[i+1].start() if i+1 < len(mentions) else len(text)]
                    for i,m in enumerate(mentions) if m.group() == key]
        def correct(seg):
            nums = re.findall(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?(?!\w|\.\d)", seg)
            ok = any(Decimal(n.replace(",", "")) == Decimal(plays) for n in nums)
            # Numbers presented as a reference/ID or with unrelated units are not a play count.
            formatted = r"(?<!\d)" + r",?".join([str(plays)[:-3], str(plays)[-3:]]) if plays >= 1000 else str(plays)
            if re.search(r"\b(?:not|never)\b[^.;]{0,20}\d[\d,]*\s+plays", seg): return False
            if duration: ok = ok and duration in seg
            if artist: ok = ok and normalized(artist) in seg
            return ok
        judge.check("bound_track_" + title, any(correct(seg) for seg in segments),
                    f"{title}: {plays} plays" + (f", {duration}" if duration else ""))
