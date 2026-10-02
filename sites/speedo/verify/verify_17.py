"""Verify a source-grounded display about the four British Team Speedo swimmers."""
import re
from verify_lib import check_trajectory_identity, check_read_only, check_visited_path, final_answer, run_verifier
TASK_ID = "Speedo--17"
FACTS = {
    "adam-peaty": (r"Adam (?:Ramsay-Peaty|Peaty)", [r"Tokyo(?: 2020)?", r"retain|defend", r"title|gold"]),
    "alice-tai": (r"Alice Tai", [r"(?:seven|7) gold", r"2019", r"World Para"]),
    "duncan-scott": (r"Duncan Scott", [r"Tokyo(?: 2020)?", r"(?:one|1|a) gold", r"(?:three|3) silver"]),
    "matt-richards": (r"Matt Richards", [r"Tokyo(?: 2020)?", r"gold", r"4\s*[x×]\s*200\s*m", r"freestyle"]),
}

def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_team", r"/pages/team-speedo")
    names = "|".join(v[0] for v in FACTS.values())
    for slug, (name, facts) in FACTS.items():
        check_visited_path(judge, traj, "visited_" + slug, "/pages/team-speedo-" + slug)
        starts = list(re.finditer(name, answer, re.I))
        segments = []
        for m in starts:
            tail = answer[m.end():]
            other = re.search(names, tail, re.I)
            segments.append(tail[:other.start()] if other else tail)
        judge.check("achievement_" + slug, any(all(re.search(f, text, re.I) for f in facts)
                    and not re.search(r"\b(?:not|never|didn't)\b", text, re.I) for text in segments))
    check_read_only(judge, initial_db, after_db)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
