"""Per-site health probe (called by control_server)."""


def health():
    try:
        from app import db, Quote, NewsArticle, EarningsEvent, ChartPoint
        counts = {
            'quotes': Quote.query.count(),
            'news': NewsArticle.query.count(),
            'earnings': EarningsEvent.query.count(),
            'charts': ChartPoint.query.count(),
        }
        return {'ok': all(v > 0 for v in counts.values()),
                'site': 'yahoo_finance', 'counts': counts}
    except Exception as exc:  # pragma: no cover
        return {'ok': False, 'site': 'yahoo_finance', 'error': str(exc)}
