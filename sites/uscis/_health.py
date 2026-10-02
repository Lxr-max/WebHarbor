"""Per-site health probe for the uscis mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "uscis"}


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
        if data.get('forms', 0) < 90:
            failures.append(f"only {data.get('forms')} forms seeded")
        if data.get('fees', 0) < 120:
            failures.append(f"only {data.get('fees')} fee records seeded")
        if data.get('zips', 0) < 40000:
            failures.append(f"only {data.get('zips')} zip rows seeded")
        if data.get('news', 0) < 40:
            failures.append(f"only {data.get('news')} news items seeded")
        if data.get('glossary', 0) < 200:
            failures.append(f"only {data.get('glossary')} glossary terms seeded")
        if data.get('processing_times', 0) < 50:
            failures.append(f"only {data.get('processing_times')} processing times seeded")
        if data.get('wizard_states', 0) < 20:
            failures.append(f"only {data.get('wizard_states')} wizard states seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Manage Your Case'),
        ('/forms', 'All Forms'),
        ('/i-485', 'Application to Register Permanent Residence'),
        ('/n-400', 'Application for Naturalization'),
        ('/feecalculator', 'Select a Form for Fee Information'),
        ('/casestatus', 'Case Status Online'),
        ('/processing-times?form=N-400&office=SEA', 'Application for Naturalization'),
        ('/tools/find-a-civil-surgeon?zip=22202', 'VAN DORN PEDIATRICS'),
        ('/tools/glossary?q=adjustment', 'Adjustment of Status'),
        ('/about-us/find-a-uscis-office/field-offices/search?zip=60601', 'Ida B. Wells'),
        ('/newsroom/alerts', 'Alerts'),
        ('/citizenship-resource-center/learn-about-citizenship/naturalization-eligibility-tool-0', 'Naturalization Eligibility Tool'),
        ('/appointment', 'Requesting An Appointment'),
        ('/account/login', 'Sign in to your USCIS online account'),
        ('/tools/while-my-case-is-pending', 'While My Case is Pending'),
        ('/humanitarian/temporary-protected-status', 'Temporary Protected Status'),
        ('/green-card/green-card-eligibility-categories', 'Green Card Eligibility Categories'),
    ]:
        try:
            status, body = get(path)
            if status != 200:
                failures.append(f'{path} -> {status}')
            elif marker not in body:
                failures.append(f'{path} missing marker {marker!r}')
        except Exception as e:
            failures.append(f'{path} failed: {e}')

    if failures:
        for f in failures:
            print(f'[health] FAIL {f}')
        return 1
    print(f'[health] uscis healthy: {data}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 43109))
