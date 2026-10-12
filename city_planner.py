"""Calendar-aware SF scoop planning. Private schedule/location never enter model prompts."""
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from math import radians, sin, cos, asin, sqrt, ceil, isfinite
import agent

SF = ZoneInfo('America/Los_Angeles')


def parse_time(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SF)
    return dt.astimezone(SF)


def gaps(busy, start, end):
    merged = []
    for item in sorted(busy, key=lambda b: b[0]):
        a, b = max(start, item[0]), min(end, item[1])
        if b <= a:
            continue
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(b, merged[-1][1])
        else:
            merged.append([a, b])
    cursor = start
    result = []
    for a, b in merged:
        if a > cursor:
            result.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < end:
        result.append((cursor, end))
    return result


def validate_location(location):
    lat, lon = float(location['lat']), float(location['lon'])
    if not isfinite(lat) or not isfinite(lon) or not 37.70 <= lat <= 37.83 or not -122.52 <= lon <= -122.35:
        raise ValueError('Choose a location within San Francisco.')
    return lat, lon


def walking_minutes(origin, destination):
    lat1, lon1 = map(radians, origin)
    lat2, lon2 = map(radians, destination)
    distance = 6371 * 2 * asin(min(1, sqrt(sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2)))
    # Approximate street detour, 4 km/h pace. No routing or elevation data.
    return max(1, ceil(distance * 1.4 / 4 * 60))


def fits_hours(place, arrival, duration=10):
    hours = place.get('weekly_hours')
    if hours is None:
        return False
    for opening, closing in hours[arrival.weekday()]:
        a = datetime.combine(arrival.date(), time.fromisoformat(opening), SF)
        b = datetime.combine(arrival.date(), time.fromisoformat(closing), SF)
        if a <= arrival and arrival + timedelta(minutes=duration) <= b:
            return True
    return False


def plan_day(data, busy, now=None):
    origin = validate_location(data['location'])
    destination = validate_location(data.get('destination') or data['location'])
    start, end = parse_time(data['start']), parse_time(data['end'])
    now = now or datetime.now(SF)
    start = max(start, now)
    if end <= start or end - start > timedelta(hours=24):
        raise ValueError('Choose a future planning window of no more than one day.')
    query = str(data.get('query', 'A daily scoop nearby')).strip()
    if not query or len(query) > 2000:
        raise ValueError('Enter a scoop preference under 2,000 characters.')
    options = []
    allowance, buffer = 10, 5
    checked_gaps = gaps(busy, start, end)
    for begin, finish in checked_gaps:
        for place in agent.CATALOG['places']:
            if 'coordinates' not in place:
                continue
            outward = walking_minutes(origin, place['coordinates'])
            onward = walking_minutes(place['coordinates'], destination)
            # Wait until opening if it is later in this calendar gap.
            for opening, closing in (place.get('weekly_hours') or [[]]*7)[begin.weekday()]:
                opens = datetime.combine(begin.date(), time.fromisoformat(opening), SF)
                leave = max(begin, opens - timedelta(minutes=outward))
                arrival = leave + timedelta(minutes=outward)
                back = arrival + timedelta(minutes=allowance+onward)
                if back + timedelta(minutes=buffer) <= finish and fits_hours(place, arrival):
                    p = dict(place)
                    p.update(walk_minutes_estimate=outward, onward_minutes=onward,
                             outing_minutes=outward+allowance+onward,
                             spare_minutes=int((finish-back).total_seconds()//60),
                             departure=leave.isoformat(), arrival=arrival.isoformat(),
                             return_at=back.isoformat(), gap_end=finish.isoformat())
                    options.append(p)
                    break
    # Give each shop its earliest feasible outing; then select a single daily scoop.
    unique = {}
    for p in sorted(options, key=lambda x: (x['departure'], x['outing_minutes'])):
        unique.setdefault(p['id'], p)
    options = list(unique.values())[:12]
    ranking = 'No feasible outing'
    if options:
        safe = [{k: p[k] for k in ['id', 'name', 'description', 'tags', 'outing_minutes']} for p in options]
        try:
            choice = agent.model_json([
                {'role': 'system', 'content': 'Rank the supplied ice cream shops for the preference. Return ONLY JSON {"ids":["id"]} including ALL supplied IDs best first. Favor shorter outings when preference matches are similar. Use only supplied facts.'},
                {'role': 'user', 'content': __import__('json').dumps({'request': query, 'shops': safe})}
            ])['ids']
            if not isinstance(choice, list) or any(not isinstance(i,str) for i in choice) or set(choice) != set(unique) or len(choice) != len(unique):
                raise ValueError('Invalid model ranking')
            options = [unique[i] for i in choice]
            ranking = 'Qwen ranked your preference'
        except Exception:
            options.sort(key=lambda p: (p['outing_minutes'], p['departure']))
            ranking = 'Model unavailable; ranked by shortest estimated outing'
    return {'places': options, 'checked': agent.CATALOG['checked'], 'ranking': ranking,
            'allowance_minutes': allowance, 'buffer_minutes': buffer,
            'origin': f'{origin[0]},{origin[1]}', 'destination': f'{destination[0]},{destination[1]}',
            'gaps': [{'start': a.isoformat(), 'end': b.isoformat(), 'minutes': int((b-a).total_seconds()//60)} for a,b in checked_gaps],
            'decisions': [f'Find free time around {len(busy)} busy intervals in the selected window.',
                          f'Search {len(agent.CATALOG["places"])} sourced San Francisco shops from your selected location.',
                          'Estimate travel at 4 km/h with a 40% street-detour allowance; hills and actual routes are not measured.',
                          'Reserve 10 minutes for a scoop plus a 5-minute arrival buffer before your next busy interval.',
                          'Require published hours to cover the scoop stop. Hours are a snapshot, not live availability.',
                          ranking],
            'message': 'Choose one outing for your daily scoop.' if options else 'No outing fits these gaps and published hours. Try a wider window or another location.'}
