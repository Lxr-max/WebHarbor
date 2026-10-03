"""Per-site health probe for the tumblr mirror.

Run standalone (`python3 _health.py [port]`) or import `health()` from the
control plane. Verifies the seed DB is populated and the key route families
render with real content.
"""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "tumblr"}


def probe(port: int) -> int:
    failures = []

    def get(path):
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',
                                    timeout=10) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    try:
        status, body = get('/_health')
        data = json.loads(body)
        if not data.get('ok'):
            failures.append(f"/_health not ok: {data}")
        if data.get('blogs', 0) < 400:
            failures.append(f"only {data.get('blogs')} blogs seeded")
        if data.get('posts', 0) < 1000:
            failures.append(f"only {data.get('posts')} posts seeded")
        if data.get('notes', 0) < 1000:
            failures.append(f"only {data.get('notes')} notes seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Trending today'),
        ('/explore', 'Explore Tumblr'),
        ('/tagged/photography', '43M'),
        ('/search/pixel%20art', 'Search results for'),
        ('/blog/nasa', '1,759 posts'),
        ('/blog/nasa/archive', 'Archive of NASA'),
        ('/blog/staff/811288138350821376', 'notes'),
        ('/login', 'Log in to Tumblr'),
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
    print(f'[health] tumblr healthy: {data}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40099))
