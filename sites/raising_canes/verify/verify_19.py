#!/usr/bin/env python3
"""Company-profile research; frozen FAQ facts, read-only state."""
from verify_lib import Judge, parse_args, load_run, final_answer, navigated_to, contains_all, contains_any
import re

def main():
    a = parse_args(); j = Judge("Raising Cane's--19"); t = load_run(a.run_dir); answer = final_answer(t)
    j.check("nav_faq", navigated_to(t, "/faq"), "consult FAQ")
    j.check("founding", contains_all(answer, ["Todd Graves", "1996", "Baton Rouge"]), "founder, year and city")
    j.check("one_love", contains_all(answer, ["chicken finger"]), "quality chicken finger meals")
    j.check("ownership", contains_any(answer, ["privately owned", "private company", "private ownership"]), "private ownership")
    j.check("stock_unavailable", bool(re.search(r"(?:not|no|doesn't|does not|isn't|not available).{0,35}(?:public|stock)|(?:stock|shares).{0,35}(?:not available|not public|unavailable)", answer, re.I)), "no publicly available stock")
    j.check("franchising_unavailable", bool(re.search(r"(?:not|no|doesn't|does not).{0,45}franchis|franchis.{0,45}(?:unavailable|not available|not accept|closed)", answer, re.I)), "not accepting franchise applications")
    j.check("offices", contains_all(answer, ["Baton Rouge", "Plano", "769-3100"]), "office cities and Dallas-area phone")
    j.emit()

if __name__ == '__main__': main()
