"""Per-site health probe for the virginia_dmv mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "virginia_dmv"}


def probe(port: int) -> int:
    failures = []

    def get(path):
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=10) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    try:
        status, body = get('/_health')
        data = json.loads(body)
        if not data.get('ok'):
            failures.append(f"/_health not ok: {data}")
        for key, floor in [('offices', 130), ('plates', 340), ('forms', 410),
                           ('news', 65), ('quiz_questions', 260),
                           ('manual_subsections', 20), ('fee_rows', 70),
                           ('online_services', 60), ('pages', 30),
                           ('users', 4), ('vehicles', 5)]:
            if data.get(key, 0) < floor:
                failures.append(f"only {data.get(key)} {key} seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Virginia Department of Motor Vehicles'),
        ('/vehicles/license-plates/search', 'Search/View Specialized License Plates'),
        ('/vehicles/license-plates/search/virginia-tech-go-hokies', 'Virginia Tech - Go Hokies'),
        ('/forms', 'Forms'),
        ('/vehicles/taxes-fees', 'DMV Fees'),
        ('/all-locations', 'Find a Location'),
        ('/locations/alexandria', '2681 Mill Road'),
        ('/drivers-manual', "Virginia Driver's Manual"),
        ('/drivers-manual/1/1', 'Two-Part Knowledge Exam'),
        ('/licenses-ids/exams/practice-exam/2', 'Traffic Signals'),
        ('/online-services-all', 'DMV Online Services'),
        ('/news', 'DMV News'),
        ('/account/login', 'DMV Online Account'),
    ]:
        try:
            status, body = get(path)
            if status != 200:
                failures.append(f"{path} -> {status}")
            elif marker not in body:
                failures.append(f"{path} missing marker {marker!r}")
        except Exception as e:
            failures.append(f"{path} failed: {e}")

    if failures:
        for f in failures:
            print(f'[health] {f}')
        return 1
    print('[health] virginia_dmv: all probes passed')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40112))
