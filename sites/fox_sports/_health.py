"""Per-site health probe (called by control_server)."""


def health():
    try:
        from app import db, Game, Player, Story, Team
        counts = {
            'teams': Team.query.count(),
            'games': Game.query.count(),
            'players': Player.query.count(),
            'stories': Story.query.count(),
        }
        return {'ok': all(v > 0 for v in counts.values()),
                'site': 'fox_sports', 'counts': counts}
    except Exception as exc:  # pragma: no cover
        return {'ok': False, 'site': 'fox_sports', 'error': str(exc)}
