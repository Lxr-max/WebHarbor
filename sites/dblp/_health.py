"""Per-site health probe for the dblp mirror."""
import json
import re
import sys
import urllib.request


def probe(port: int) -> int:
    failures = []

    def get(path):
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=15) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    try:
        status, body = get('/_health')
        data = json.loads(body)
        if not data.get('ok'):
            failures.append(f"/_health not ok: {data}")
        if data.get('publications', 0) < 5000:
            failures.append(f"only {data.get('publications')} publications seeded")
        if data.get('authors', 0) < 1000:
            failures.append(f"only {data.get('authors')} authors seeded")
        if data.get("venues", 0) != 21:
            failures.append(f"expected 21 venues, got {data.get('venues')}")
        if data.get('users', 0) != 4:
            failures.append(f"expected 4 benchmark users, got {data.get('users')}")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Welcome to dblp'),
        ('/search?q=sigmod', 'Venue search results'),
        ('/search/publ?q=attention+is+all+you+need', 'Tensor Product Attention Is All You Need'),
        ('/search/author?q=jiawei+han', 'Jiawei Han'),
        ('/search/venue?q=sigmod', 'ACM SIGMOD Conference'),
        ('/pid/h/JiaweiHan.html', 'Coauthor Index'),
        ('/db/conf/', 'ACM SIGMOD Conference'),
        ('/db/journals/', 'Proceedings of the VLDB Endowment'),
        ('/db/conf/sigmod/index.html', 'Venue statistics'),
        ('/db/journals/pvldb/index.html', 'Volume 19'),
        ('/rec/journals/pacmmod/0001LW24.html', 'BibTeX record'),
        ('/rec/journals/pacmmod/0001LW24.bib', 'DBLP:journals/pacmmod/0001LW24'),
        ('/authn/login', 'dblp login'),
        ('/authn/register', 'Create a dblp account'),
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
    print('[health] dblp all green')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40142))
