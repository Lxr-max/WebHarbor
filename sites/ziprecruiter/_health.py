"""Per-site health probe for the ziprecruiter mirror."""
import json
import sys
import urllib.request


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
        if data.get('jobs', 0) < 250:
            failures.append(f"only {data.get('jobs')} jobs seeded")
        if data.get('companies', 0) < 250:
            failures.append(f"only {data.get('companies')} companies seeded")
        if data.get('salaries', 0) < 15:
            failures.append(f"expected 15+ salary pages, got {data.get('salaries')}")
        if data.get('articles', 0) < 10:
            failures.append(f"expected 10+ articles, got {data.get('articles')}")
        if data.get('titles', 0) != 14:
            failures.append(f"expected 14 title pages, got {data.get('titles')}")
        if data.get('users', 0) != 4:
            failures.append(f"expected 4 benchmark users, got {data.get('users')}")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'ZipRecruiter'),
        ('/jobs-search?search=software+engineer&location=San+Francisco%2C+CA',
         'Software engineer Jobs'),
        ('/jobs-search?search=registered+nurse&location=New+York%2C+NY',
         'Registered nurse Jobs'),
        ('/Jobs/Software-Engineer', 'Software Engineer Jobs'),
        ('/Salaries/Software-Engineer-Salary', 'Average Software Engineer salary'),
        ('/Salaries/Registered-Nurse-Salary-in-New-York,NY', 'Registered Nurse Salary'),
        ('/browse', 'Browse Jobs by Title'),
        ('/browse/titles/S', 'Job titles starting with'),
        ('/blog/', 'Career Advice'),
        ('/blog/category/career-advice/trends/', 'Trends'),
        ('/authn/login?realm=candidates', 'Job Seeker Login'),
        ('/authn/register?realm=candidates', 'Create a Free Account'),
    ]:
        try:
            status, body = get(path)
            if status != 200:
                failures.append(f'{path} -> {status}')
            elif marker not in body:
                failures.append(f'{path} missing marker {marker!r}')
        except Exception as e:
            failures.append(f'{path} raised {e}')

    if failures:
        for f in failures:
            print(f'[health] FAIL {f}')
        return 1
    print('[health] ziprecruiter all green')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40115))
