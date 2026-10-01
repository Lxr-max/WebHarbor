"""Reviewer regressions; no external evidence directory required."""
import re
from urllib.parse import urlsplit, parse_qs
import pytest
import app as site

@pytest.mark.parametrize('target', ['http://[invalid', '//[invalid', 'https://example.org/', '//example.org/', '/\\example.org/', '/%2fexample.org/', '/%5cexample.org/', '/%0d%0aLocation:https://example.org/'])
def test_external_continuations_stay_local(target):
    with site.app.test_request_context('/'):
        assert site.local_redirect(target, '/').location == '/'

@pytest.mark.parametrize('target', ['/papers?q=hello', '/account', '/search/publ?year=2026&type=article'])
def test_internal_continuations_survive(target):
    with site.app.test_request_context('/'):
        assert site.local_redirect(target, '/').location == target
