from datetime import date, timedelta, datetime
import db


SERVICES_DAILY = ["guard", "restaurant", "kitchen", "cleaning"]


def _choose(candidates, usage):
    # candidates: list of squad ids; pick min usage, tie by list order
    best = None
    best_key = None
    for sid in candidates:
        key = (usage.get(sid, 0), candidates.index(sid))
        if best_key is None or key < best_key:
            best_key = key
            best = sid
    return best


def generate_week(conn, start_date_str, toilet_count=3, guard_count=0):
    # start_date_str: YYYY-MM-DD
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end = start + timedelta(days=6)
    # avoid duplicate week for same start? allow
    week_id = db.create_week(conn, start.isoformat(), end.isoformat())
    squads = db.list_squads(conn)
    squad_ids = [s["id"] for s in squads]
    if not squad_ids:
        raise RuntimeError("لا توجد أفواج. أنشئ الأفواج أولاً.")
    usage = {sid: 0 for sid in squad_ids}

    # daily assignments
    for d in range(7):
        day_date = (start + timedelta(days=d)).isoformat()
        # guard
        guard = _choose(squad_ids, usage)
        usage[guard] += 1
        db.upsert_assignment(conn, week_id, d, day_date, "guard", guard, guard_count, None)

        # restaurant: exclude guard
        rest_candidates = [s for s in squad_ids if s != guard]
        rest = _choose(rest_candidates, usage)
        usage[rest] += 1
        db.upsert_assignment(conn, week_id, d, day_date, "restaurant", rest, 0, None)

        # kitchen: exclude guard & restaurant
        kit_candidates = [s for s in squad_ids if s not in (guard, rest)]
        if not kit_candidates:
            kit_candidates = [s for s in squad_ids if s != guard]
        kitchen = _choose(kit_candidates, usage)
        usage[kitchen] += 1
        db.upsert_assignment(conn, week_id, d, day_date, "kitchen", kitchen, 0, None)

        # cleaning: exclude guard if possible; prefer not rest/kitchen
        clean_candidates = [s for s in squad_ids if s != guard]
        # prefer excluding rest & kitchen
        preferred = [s for s in clean_candidates if s not in (rest, kitchen)]
        if preferred:
            clean_candidates = preferred
        cleaning = _choose(clean_candidates, usage)
        usage[cleaning] += 1
        db.upsert_assignment(conn, week_id, d, day_date, "cleaning", cleaning, 0, None)

    # toilet squad: choose least used overall
    toilet_squad = _choose(squad_ids, usage)
    usage[toilet_squad] += 1  # one week duty
    for d in range(7):
        day_date = (start + timedelta(days=d)).isoformat()
        db.upsert_assignment(conn, week_id, d, day_date, "toilet", toilet_squad, toilet_count, None)

    return week_id
