"""Per-site health probe (called by control_server)."""


def health():
    try:
        from app import db, Quote, BellEvent, IpoDeal, DirectoryRow
        counts = {
            'quotes': Quote.query.count(),
            'directory_rows': DirectoryRow.query.count(),
            'bell_events': BellEvent.query.count(),
            'ipo_deals': IpoDeal.query.count(),
        }
        return {'ok': all(v > 0 for v in counts.values()),
                'site': 'nyse', 'counts': counts}
    except Exception as exc:  # pragma: no cover
        return {'ok': False, 'site': 'nyse', 'error': str(exc)}
