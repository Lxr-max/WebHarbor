"""Per-site health probe (called by control_server)."""


def health():
    try:
        from app import db, Event, Organizer, Paper, Sponsor
        counts = {
            'papers': Paper.query.count(),
            'events': Event.query.count(),
            'sponsors': Sponsor.query.count(),
            'organizers': Organizer.query.count(),
        }
        return {'ok': all(v > 0 for v in counts.values()),
                'site': 'iclr', 'counts': counts}
    except Exception as exc:  # pragma: no cover
        return {'ok': False, 'site': 'iclr', 'error': str(exc)}
