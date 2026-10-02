"""Captured text should render Unicode without treating it as trusted HTML."""
from app import decode_source_text, NewsArticle


def test_double_escaped_source_text():
    assert decode_source_text(r'El Ni\u00f1o\u2019s') == 'El Niño’s'
    assert decode_source_text('already café') == 'already café'
    article = NewsArticle(body='["\\\\u003cscript\\\\u003e"]')
    assert article.body_list() == ['<script>']
    # The value remains an ordinary string, so Jinja autoescaping still applies.
    from markupsafe import escape
    assert str(escape(article.body_list()[0])) == '&lt;script&gt;'
