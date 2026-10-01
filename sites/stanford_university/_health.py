"""Per-site health probe (called by control_server)."""


def health():
    try:
        from app import db, Department, Course, Program, Faculty, \
            NewsArticle, CampusEvent, CalendarEntry, Library, User
        counts = {
            'departments': Department.query.count(),
            'courses': Course.query.count(),
            'programs': Program.query.count(),
            'faculty': Faculty.query.count(),
            'news': NewsArticle.query.count(),
            'events': CampusEvent.query.count(),
            'calendar': CalendarEntry.query.count(),
            'libraries': Library.query.count(),
            'users': User.query.count(),
        }
        return {'ok': all(v > 0 for v in counts.values()),
                'site': 'stanford_university', 'counts': counts}
    except Exception as exc:  # pragma: no cover
        return {'ok': False, 'site': 'stanford_university', 'error': str(exc)}
