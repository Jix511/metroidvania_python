"""Persistent, validated counters for a player profile."""

STAT_DEFAULTS = {
    'play_time': 0.0,
    'damage_dealt': 0,
    'damage_taken': 0,
    'attacks': 0,
    'hits': 0,
    'critical_hits': 0,
    'blocked_hits': 0,
    'enemies_defeated': 0,
    'bosses_defeated': 0,
    'gold_earned': 0,
    'xp_earned': 0,
    'potions_used': 0,
    'deaths': 0,
    'highest_combo': 0,
    'perfect_parries': 0,
    'posture_breaks': 0,
    'executions': 0,
}


def normalize_stats(value=None):
    source = value if isinstance(value, dict) else {}
    result = dict(STAT_DEFAULTS)
    for key, default in STAT_DEFAULTS.items():
        raw = source.get(key, default)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        result[key] = max(0.0, float(raw)) if key == 'play_time' else max(0, int(raw))
    return result


def format_play_time(seconds):
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f'{hours:02d}:{minutes:02d}:{secs:02d}'
