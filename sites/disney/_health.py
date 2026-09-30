"""Per-site health probe (called by control_server)."""


def health():
    try:
        from app import db, Movie, Show, ParkEntity, Product, IceEvent
        counts = {
            'movies': Movie.query.count(),
            'shows': Show.query.count(),
            'park_entities': ParkEntity.query.count(),
            'products': Product.query.count(),
            'ice_events': IceEvent.query.count(),
        }
        return {'ok': all(v > 0 for v in counts.values()),
                'site': 'disney', 'counts': counts}
    except Exception as exc:  # pragma: no cover
        return {'ok': False, 'site': 'disney', 'error': str(exc)}
