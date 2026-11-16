"""
Stats endpoints for the astronaut health dashboard (FastAPI router).

Wire it into your existing server:
    from stats import router as stats_router
    app.include_router(stats_router)
and make sure your CORS middleware has allow_headers=["*"] (the dashboard sends X-User-Id).

DB location: env var HEALTH_DB (default "app.db"); main.py also sets stats.DB_PATH. If your server already has a DB
dependency, replace get_conn(). Replace current_user_id() with your real login/session
lookup; for the prototype it trusts an X-User-Id header or ?user_id= query parameter.

Method (per metric):
  baseline  = mean/sd of the user's own PRE-FLIGHT values. With fewer than 5 pre-flight
              points the population reference sd is used instead (sd_source="reference").
  current   = mean of the last 7 days of data (a single value for sparse lab results).
  z_baseline= (current - baseline mean) / baseline sd     -> "how unusual for ME"
  percentile= normal CDF of (current - ref mean) / ref sd -> "how unusual vs. the population"
  status    = good / watch / alert from the z-score in the unhealthy direction
              (>=1 sd watch, >=2 sd alert; without a z-score, 5% / 10% change vs baseline).
"""
import math
import os
import sqlite3
import statistics as st
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

DB_PATH = os.environ.get("HEALTH_DB", "app.db")
router = APIRouter(prefix="/api/stats", tags=["stats"])
NO_BASELINE = {"radiation"}  # ground vs orbit comparison is meaningless; shown as cumulative dose
RECENT_DAYS = 7
FAR_FUTURE = date(9999, 12, 31)


# ------------------------------------------------------------------ dependencies
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def current_user_id(x_user_id: Optional[int] = Header(None), user_id: Optional[int] = Query(None)) -> int:
    uid = x_user_id if x_user_id is not None else user_id
    if uid is None:
        raise HTTPException(401, "Not logged in")
    return uid


# ------------------------------------------------------------------ helpers
def phi(z):  # standard normal CDF
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def parse_day(s, name="as_of"):
    if not s:
        return FAR_FUTURE
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise HTTPException(422, f"{name} must be YYYY-MM-DD")


def load_context(conn, uid):
    prof = conn.execute("SELECT * FROM astronaut_profile WHERE user_id = ?", (uid,)).fetchone()
    if not prof:
        raise HTTPException(404, "No health profile for this user")
    defs = {r["metric_key"]: dict(r) for r in conn.execute("SELECT * FROM metric_definitions")}
    refs = {}  # sex-specific rows override 'any'
    for r in conn.execute("SELECT * FROM reference_ranges WHERE sex IN (?, 'any') ORDER BY sex = 'any' DESC",
                          (prof["sex"],)):
        refs[r["metric_key"]] = dict(r)
    return prof, defs, refs


def landing_day(prof):
    if not prof["landing_date"]:
        return None
    return (date.fromisoformat(prof["landing_date"]) - date.fromisoformat(prof["launch_date"])).days


def fetch_rows(conn, uid, limit_day, metric=None):
    sql = "SELECT metric, ts, value, phase, mission_day FROM v_all_metrics WHERE user_id = ? AND date(ts) <= ?"
    args = [uid, limit_day.isoformat()]
    if metric:
        sql += " AND metric = ?"
        args.append(metric)
    return conn.execute(sql + " ORDER BY metric, ts", args).fetchall()


def make_baseline(pre_vals, ref):
    n = len(pre_vals)
    if n == 0:
        return None
    mean = st.fmean(pre_vals)
    if n >= 5:
        sd, src = st.stdev(pre_vals), "personal"
    elif ref:
        sd, src = ref["ref_sd"], "reference"
    else:
        sd, src = None, None
    return {"mean": mean, "sd": sd or None, "n": n, "sd_source": src}


def grade(z, pct_change, direction, value, ref):
    """-> (status, adverse): adverse = how many sd (or 5%-steps) the value sits in the unhealthy direction."""
    x = z if z is not None else (pct_change / 5 if pct_change is not None else None)
    if x is None:
        return "info", 0.0
    adverse = {"up": -x, "down": x}.get(direction, abs(x))
    status = "alert" if adverse >= 2 else "watch" if adverse >= 1 else "good"
    if status == "good" and ref and (
            (ref["normal_low"] is not None and value < ref["normal_low"]) or
            (ref["normal_high"] is not None and value > ref["normal_high"])):
        status = "watch"
    return status, adverse


def mission_info(conn, uid, prof, as_of_day):
    first, last = conn.execute("SELECT MIN(date(ts)), MAX(date(ts)) FROM v_all_metrics WHERE user_id = ?",
                               (uid,)).fetchone()
    day = min(as_of_day, date.fromisoformat(last))
    launch = date.fromisoformat(prof["launch_date"])
    landing = date.fromisoformat(prof["landing_date"]) if prof["landing_date"] else None
    phase = "pre_flight" if day < launch else ("in_flight" if landing is None or day < landing else "post_flight")
    cum = conn.execute("SELECT COALESCE(SUM(dose_msv), 0) FROM radiation_dose WHERE user_id = ? AND date <= ?",
                       (uid, day.isoformat())).fetchone()[0]
    return {"name": prof["mission_name"], "environment": prof["environment"], "launch_date": prof["launch_date"],
            "landing_date": prof["landing_date"], "landing_day": landing_day(prof), "first_date": first,
            "last_date": last, "as_of": day.isoformat(), "mission_day": (day - launch).days, "phase": phase,
            "cumulative_msv": round(cum, 2)}


# ------------------------------------------------------------------ endpoints
@router.get("/summary")
def summary(as_of: Optional[str] = None, uid: int = Depends(current_user_id), conn=Depends(get_conn)):
    """One card per metric: current value, baseline z-score, reference percentile, status, sparkline."""
    prof, defs, refs = load_context(conn, uid)
    limit = parse_day(as_of)
    by = {}
    for r in fetch_rows(conn, uid, limit):
        by.setdefault(r["metric"], []).append(r)
    cards = []
    for key, rows in by.items():
        d = defs.get(key)
        if not d:
            continue
        cutoff = (date.fromisoformat(rows[-1]["ts"][:10]) - timedelta(days=RECENT_DAYS - 1)).isoformat()
        current = st.fmean([r["value"] for r in rows if r["ts"][:10] >= cutoff])
        ref = refs.get(key)
        base = None if d["category"] in NO_BASELINE else make_baseline(
            [r["value"] for r in rows if r["phase"] == "pre_flight"], ref)
        z = (current - base["mean"]) / base["sd"] if base and base["sd"] else None
        pct_change = (current - base["mean"]) / abs(base["mean"]) * 100 if base and base["mean"] else None
        z_ref = (current - ref["ref_mean"]) / ref["ref_sd"] if ref else None
        status, adverse = grade(z, pct_change, d["good_direction"], current, ref)
        cards.append({
            "metric": key, "label": d["label"], "unit": d["unit"], "category": d["category"],
            "decimals": d["decimals"], "direction": d["good_direction"],
            "current": current, "as_of": rows[-1]["ts"], "n_points": len(rows),
            "baseline_mean": base and base["mean"], "baseline_sd": base and base["sd"],
            "baseline_n": base and base["n"], "sd_source": base and base["sd_source"],
            "z_baseline": z, "pct_change": pct_change,
            "ref_mean": ref and ref["ref_mean"], "ref_sd": ref and ref["ref_sd"],
            "normal_low": ref and ref["normal_low"], "normal_high": ref and ref["normal_high"],
            "z_ref": z_ref, "percentile": None if z_ref is None else round(100 * phi(z_ref), 1),
            "status": status, "adverse": adverse,
            "spark": [round(r["value"], d["decimals"] + 1) for r in rows[-30:]],
        })
    launch = date.fromisoformat(prof["launch_date"])
    return {
        "profile": {"name": prof["display_name"], "sex": prof["sex"], "role": prof["role"],
                    "age": (launch - date.fromisoformat(prof["birth_date"])).days // 365},
        "mission": mission_info(conn, uid, prof, limit),
        "cards": sorted(cards, key=lambda c: (c["category"], c["label"])),
    }


@router.get("/metric/{key}")
def metric_series(key: str, as_of: Optional[str] = None, uid: int = Depends(current_user_id),
                  conn=Depends(get_conn)):
    """Full time series for one metric, with baseline, reference band and per-point z-scores."""
    prof, defs, refs = load_context(conn, uid)
    if key not in defs:
        raise HTTPException(404, "Unknown metric")
    rows = fetch_rows(conn, uid, parse_day(as_of), key)
    base = None if defs[key]["category"] in NO_BASELINE else make_baseline(
        [r["value"] for r in rows if r["phase"] == "pre_flight"], refs.get(key))
    pts = [{"ts": r["ts"], "mission_day": r["mission_day"], "phase": r["phase"], "value": round(r["value"], 4),
            "z": (r["value"] - base["mean"]) / base["sd"] if base and base["sd"] else None} for r in rows]
    return {"definition": defs[key], "baseline": base, "reference": refs.get(key),
            "landing_day": landing_day(prof), "points": pts}


@router.get("/heart-rate")
def heart_rate(day: Optional[str] = Query(None, alias="date"), uid: int = Depends(current_user_id),
               conn=Depends(get_conn)):
    """One day of 5-minute heart-rate samples plus the user's typical pre-flight hourly curve."""
    prof, _, _ = load_context(conn, uid)
    if day:
        d = parse_day(day, "date")
    else:
        latest = conn.execute("SELECT MAX(substr(ts, 1, 10)) FROM heart_rate_samples WHERE user_id = ?",
                              (uid,)).fetchone()[0]
        if not latest:
            raise HTTPException(404, "No heart-rate data")
        d = date.fromisoformat(latest)
    rows = conn.execute("SELECT ts, bpm, state FROM heart_rate_samples WHERE user_id = ? AND ts >= ? AND ts < ? "
                        "ORDER BY ts", (uid, d.isoformat() + "T00:00:00",
                                        (d + timedelta(days=1)).isoformat() + "T00:00:00")).fetchall()
    samples = [{"m": int(r["ts"][11:13]) * 60 + int(r["ts"][14:16]), "bpm": r["bpm"], "state": r["state"]}
               for r in rows]
    sleep = [s["bpm"] for s in samples if s["state"] == "sleep"]
    base = conn.execute("SELECT CAST(substr(ts, 12, 2) AS INTEGER) h, AVG(bpm) FROM heart_rate_samples "
                        "WHERE user_id = ? AND substr(ts, 1, 10) < ? GROUP BY h ORDER BY h",
                        (uid, prof["launch_date"])).fetchall()
    return {"date": d.isoformat(), "samples": samples,
            "summary": {"resting": st.fmean(sleep) if sleep else None,
                        "average": st.fmean([s["bpm"] for s in samples]) if samples else None,
                        "max": max((s["bpm"] for s in samples), default=None),
                        "exercise_min": 5 * sum(1 for s in samples if s["state"] == "exercise")},
            "baseline_by_hour": [{"m": h * 60 + 30, "bpm": round(v, 1)} for h, v in base]}


@router.get("/radiation")
def radiation(as_of: Optional[str] = None, uid: int = Depends(current_user_id), conn=Depends(get_conn)):
    """Daily and cumulative radiation dose (mSv)."""
    prof, _, _ = load_context(conn, uid)
    launch = date.fromisoformat(prof["launch_date"])
    rows = conn.execute("SELECT date, dose_msv, cumulative_msv FROM v_radiation_cumulative "
                        "WHERE user_id = ? AND date <= ? ORDER BY date",
                        (uid, parse_day(as_of).isoformat())).fetchall()
    series = [{"date": r["date"], "mission_day": (date.fromisoformat(r["date"]) - launch).days,
               "dose": r["dose_msv"], "cumulative": round(r["cumulative_msv"], 3)} for r in rows]
    return {"series": series, "total_msv": series[-1]["cumulative"] if series else 0,
            "landing_day": landing_day(prof)}
