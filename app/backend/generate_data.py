#!/usr/bin/env python3
"""
Synthetic astronaut health-data generator (NASA Space Apps prototype).

Creates a pre-flight -> in-flight -> post-flight timeline for ONE astronaut and
writes it into SQLite using schema.sql. All numbers are SYNTHETIC and only
loosely inspired by published spaceflight trends (space anemia, bone/muscle loss,
sleep restriction, radiation exposure, SANS). Not for medical use.

Hidden "story" variables drive the data so that the dashboard has real
correlations to show: workload -> stress -> poorer sleep, lower HRV, higher
resting HR, lower mood; solar particle events -> radiation symptoms and a dip in
lymphocytes; exercise adherence -> how much bone/muscle is lost.

Usage:
    python generate_data.py --db app.db --user-id 1 --reset
    python generate_data.py --sex M --env deep_space --mission-days 240 --seed 7 --reset
"""
import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
GROUND_DOSE = 0.008                                   # mSv/day on Earth
ENV_DOSE = {"LEO": 0.5, "lunar": 1.0, "deep_space": 1.8}  # mSv/day, illustrative

# key, label, unit, category, decimals, good_direction
METRICS = [
    ("rbc", "Red blood cells", "10^12/L", "blood", 2, "range"),
    ("hemoglobin", "Hemoglobin", "g/dL", "blood", 1, "range"),
    ("hematocrit", "Hematocrit", "%", "blood", 1, "range"),
    ("wbc", "White blood cells", "10^9/L", "blood", 1, "range"),
    ("lymphocyte_pct", "Lymphocytes", "%", "blood", 1, "range"),
    ("neutrophil_pct", "Neutrophils", "%", "blood", 1, "range"),
    ("platelets", "Platelets", "10^9/L", "blood", 0, "range"),
    ("crp", "C-reactive protein (inflammation)", "mg/L", "biomarker", 2, "down"),
    ("cortisol_am", "Morning cortisol (stress)", "ug/dL", "biomarker", 1, "range"),
    ("vitamin_d", "Vitamin D (25-OH)", "ng/mL", "biomarker", 1, "up"),
    ("ferritin", "Ferritin (iron stores)", "ng/mL", "biomarker", 0, "range"),
    ("ctx", "CTX (bone resorption)", "ng/mL", "biomarker", 2, "down"),
    ("p1np", "P1NP (bone formation)", "ng/mL", "biomarker", 0, "up"),
    ("glucose", "Fasting glucose", "mg/dL", "biomarker", 0, "range"),
    ("bmd_lumbar_spine", "Bone density - lumbar spine", "g/cm2", "bone", 3, "up"),
    ("bmd_femoral_neck", "Bone density - femoral neck", "g/cm2", "bone", 3, "up"),
    ("lean_mass_kg", "Lean body mass", "kg", "muscle", 1, "up"),
    ("grip_strength_kg", "Grip strength", "kg", "muscle", 1, "up"),
    ("weight_kg", "Body weight", "kg", "body", 1, "range"),
    ("resting_hr", "Resting heart rate", "bpm", "cardio", 1, "down"),
    ("hrv_rmssd", "Heart-rate variability (RMSSD)", "ms", "cardio", 1, "up"),
    ("systolic_bp", "Systolic blood pressure", "mmHg", "cardio", 0, "range"),
    ("diastolic_bp", "Diastolic blood pressure", "mmHg", "cardio", 0, "range"),
    ("sleep_total_min", "Sleep duration", "min", "sleep", 0, "up"),
    ("sleep_deep_min", "Deep sleep", "min", "sleep", 0, "up"),
    ("sleep_rem_min", "REM sleep", "min", "sleep", 0, "up"),
    ("sleep_efficiency_pct", "Sleep efficiency", "%", "sleep", 1, "up"),
    ("sleep_score", "Sleep score", "0-100", "sleep", 0, "up"),
    ("exercise_min", "Exercise (total)", "min", "activity", 0, "up"),
    ("resistance_min", "Resistance exercise", "min", "activity", 0, "up"),
    ("cardio_min", "Cardio exercise", "min", "activity", 0, "up"),
    ("active_kcal", "Active energy", "kcal", "activity", 0, "up"),
    ("workload_hours", "Workload", "h", "activity", 1, "down"),
    ("kcal_intake", "Calorie intake", "kcal", "nutrition", 0, "range"),
    ("protein_g", "Protein intake", "g", "nutrition", 0, "range"),
    ("vitamin_d_iu", "Vitamin D intake", "IU", "nutrition", 0, "up"),
    ("calcium_mg", "Calcium intake", "mg", "nutrition", 0, "range"),
    ("sodium_mg", "Sodium intake", "mg", "nutrition", 0, "down"),
    ("water_ml", "Water intake", "mL", "nutrition", 0, "up"),
    ("radiation_dose_msv", "Radiation dose (daily)", "mSv", "radiation", 3, "down"),
]
DECIMALS = {m[0]: m[4] for m in METRICS}

# metric, sex, mean, sd, normal_low, normal_high
REFS = [
    ("rbc", "M", 5.2, 0.40, 4.5, 5.9), ("rbc", "F", 4.6, 0.35, 4.1, 5.1),
    ("hemoglobin", "M", 15.0, 1.0, 13.5, 17.5), ("hemoglobin", "F", 13.5, 0.9, 12.0, 15.5),
    ("hematocrit", "M", 47.0, 3.0, 41.0, 53.0), ("hematocrit", "F", 41.0, 2.5, 36.0, 46.0),
    ("wbc", "any", 7.0, 1.5, 4.0, 11.0),
    ("lymphocyte_pct", "any", 30.0, 6.0, 20.0, 40.0),
    ("neutrophil_pct", "any", 58.0, 7.0, 40.0, 70.0),
    ("platelets", "any", 250.0, 50.0, 150.0, 400.0),
    ("crp", "any", 1.5, 1.2, 0.0, 3.0),
    ("cortisol_am", "any", 14.0, 4.0, 6.0, 23.0),
    ("vitamin_d", "any", 36.0, 8.0, 30.0, 50.0),
    ("ferritin", "M", 110.0, 55.0, 24.0, 336.0), ("ferritin", "F", 60.0, 40.0, 11.0, 307.0),
    ("ctx", "any", 0.35, 0.12, 0.10, 0.70),
    ("p1np", "any", 55.0, 18.0, 20.0, 100.0),
    ("glucose", "any", 90.0, 8.0, 70.0, 99.0),
    ("bmd_lumbar_spine", "any", 1.20, 0.12, 1.08, None),
    ("bmd_femoral_neck", "any", 0.93, 0.12, 0.81, None),
    ("resting_hr", "any", 62.0, 8.0, 50.0, 75.0),
    ("hrv_rmssd", "any", 50.0, 18.0, 25.0, 85.0),
    ("systolic_bp", "any", 118.0, 10.0, 95.0, 129.0),
    ("diastolic_bp", "any", 74.0, 8.0, 60.0, 84.0),
]
REF_NOTE = "Illustrative demo values - replace with NASA / clinical references."

JOURNAL = {
    "pre": {"hi": ["Training is going well and I feel prepared.", "Strong day in the simulator; the crew is in sync."],
            "mid": ["Packed schedule but manageable.", "Tired after the sim runs; early night planned."],
            "lo": ["Overloaded with training and checklists; sleeping badly."]},
    "in": {"hi": ["Rested and sharp. Exercise felt strong today.", "Great crew dinner; morale is high."],
           "mid": ["Busy day, manageable. Slept a bit broken.", "Missing home a little but staying focused."],
           "lo": ["Long hours and no downtime; I feel drained.", "Hard to focus and short-tempered with the crew."]},
    "post": {"hi": ["Getting stronger each day back in gravity."],
             "mid": ["Muscles feel heavy; balance is off when I stand up quickly."],
             "lo": ["Exhausted and dizzy; the rehab sessions are hard."]},
}


def iso(dt):
    return dt.isoformat(timespec="seconds")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default="app.db")
    p.add_argument("--user-id", type=int, default=1, help="id of an existing row in the userlog table")
    p.add_argument("--sex", choices=["M", "F"], default="F")
    p.add_argument("--env", choices=list(ENV_DOSE), default="LEO", help="radiation environment")
    p.add_argument("--launch", default="2026-01-15", help="launch date (day 0), YYYY-MM-DD")
    p.add_argument("--pre-days", type=int, default=30)
    p.add_argument("--mission-days", type=int, default=180)
    p.add_argument("--post-days", type=int, default=30, help="0 = mission still in progress")
    p.add_argument("--spe-count", type=int, default=2, help="solar particle events during the mission")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--reset", action="store_true", help="delete this user's existing health data first")
    a = p.parse_args()
    if a.mission_days < 30:
        p.error("--mission-days must be at least 30")
    return a


def main():
    a = parse_args()
    conn = sqlite3.connect(a.db)
    conn.execute("PRAGMA foreign_keys = ON")
    uid = a.user_id

    # The login table. If the database is brand new, create it (same columns as your old server)
    # plus a demo user, so this script alone can build the whole database.
    created_demo = False
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='userlog'").fetchone():
        conn.execute("""CREATE TABLE userlog (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password TEXT NOT NULL,
            legal TEXT NOT NULL, age INTEGER NOT NULL, weight REAL NOT NULL, height REAL NOT NULL)""")
    if not conn.execute("SELECT 1 FROM userlog WHERE id = ?", (uid,)).fetchone():
        if uid != 1 or conn.execute("SELECT COUNT(*) FROM userlog").fetchone()[0]:
            sys.exit(f"No user with id={uid} in the userlog table. Pass --user-id for an existing user.")
        conn.execute("INSERT INTO userlog (id, username, password, legal, age, weight, height) "
                     "VALUES (1, 'demo_astronaut', 'demo', 'Demo Astronaut', 0, 0, 0)")
        created_demo = True
        print("Created demo user: username demo_astronaut / password demo")

    conn.executescript(SCHEMA_PATH.read_text())

    tables = ["measurements", "heart_rate_samples", "sleep_sessions", "activity_daily", "nutrition_daily",
              "radiation_dose", "symptom_logs", "illness_events", "journal_entries", "recommendations",
              "astronaut_profile"]
    if conn.execute("SELECT 1 FROM astronaut_profile WHERE user_id = ?", (uid,)).fetchone():
        if not a.reset:
            sys.exit(f"User {uid} already has health data. Re-run with --reset to replace it.")
    if a.reset:
        for t in tables:
            conn.execute(f"DELETE FROM {t} WHERE user_id = ?", (uid,))

    generate(conn, a)
    if created_demo:  # keep the demo login row consistent with the generated profile
        h, wt, bd, ld = conn.execute("SELECT height_cm, baseline_weight_kg, birth_date, launch_date "
                                     "FROM astronaut_profile WHERE user_id = ?", (uid,)).fetchone()
        conn.execute("UPDATE userlog SET age = ?, weight = ?, height = ? WHERE id = ?",
                     ((date.fromisoformat(ld) - date.fromisoformat(bd)).days // 365, wt, h, uid))
    conn.commit()
    summary(conn, uid)
    conn.close()


def generate(conn, a):
    rng = np.random.default_rng(a.seed)
    uid, M, PRE, POST = a.user_id, a.mission_days, a.pre_days, a.post_days
    launch = date.fromisoformat(a.launch)
    days = np.arange(-PRE, M + POST)  # offsets from launch; day 0 = launch, day M = landing
    n = len(days)
    idx = lambda d: int(d) + PRE
    dt = lambda d: launch + timedelta(days=int(d))
    phase = lambda d: "pre" if d < 0 else ("in" if d < M else "post")
    ramp = lambda d, tau, rec: (0.0 if d < 0 else (1 - np.exp(-(d + 1) / tau)) if d < M
                                else (1 - np.exp(-M / tau)) * np.exp(-(d - M) / rec))
    months = lambda d, rec: 0.0 if d < 0 else (d / 30 if d < M else (M / 30) * np.exp(-(d - M) / rec))

    # ---- metric catalogue + reference ranges
    conn.executemany("INSERT OR REPLACE INTO metric_definitions VALUES (?,?,?,?,?,?)", METRICS)
    conn.executemany("INSERT OR REPLACE INTO reference_ranges VALUES (?,?,?,?,?,?,?)",
                     [(m, s, mu, sd, lo, hi, REF_NOTE) for m, s, mu, sd, lo, hi in REFS])
    ref = {(m, s): (mu, sd) for m, s, mu, sd, _, _ in REFS}
    B = {}  # this astronaut's personal baselines (slightly different from the population mean)
    for m in {r[0] for r in REFS}:
        mu, sd = ref.get((m, a.sex)) or ref[(m, "any")]
        B[m] = max(mu + sd * rng.normal(0, 0.4), 0.2 * mu)

    # ---- profile ("known" data)
    height = float(rng.normal(180 if a.sex == "M" else 167, 5))
    w0 = float(23.0 * (height / 100) ** 2 * rng.normal(1, 0.04))
    age = float(rng.normal(38, 4))
    legal_name = conn.execute("SELECT legal FROM userlog WHERE id = ?", (uid,)).fetchone()[0]
    conn.execute("INSERT INTO astronaut_profile VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        uid, legal_name, (launch - timedelta(days=int(age * 365.25))).isoformat(), a.sex,
        round(height, 1), round(w0, 1), "Flight Engineer", "DEMO-1", launch.isoformat(),
        dt(M).isoformat() if POST > 0 else None, a.env,
        json.dumps(["seasonal rhinitis"]), 8.0))

    # ---- latent daily "story" variables
    w = np.empty(n)  # workload h/day
    ar = 0.0
    for i, d in enumerate(days):
        ar = 0.7 * ar + rng.normal(0, 0.7)
        w[i] = {"pre": 7.0, "in": 9.0, "post": 5.0}[phase(d)] + ar
    for _ in range(max(1, M // 18)):  # busy episodes: docking, EVAs, experiments
        s = int(rng.integers(PRE + 5, PRE + M - 4))
        w[s:s + int(rng.integers(2, 5))] += rng.uniform(2.5, 4.0)
    w = np.clip(w, 3, 14)
    stress = np.clip((w - 8.0) / 3.0, -1.0, 1.5)

    spe, spe_days = np.zeros(n), []
    if M >= 40:
        for c in np.linspace(0.25, 0.8, a.spe_count) if a.spe_count > 0 else []:
            day = int(c * M) + int(rng.integers(-8, 9))
            spe_days.append(day)
            mag = rng.uniform(3, 9)  # extra mSv on the event day (exaggerated so it shows on charts)
            for k, f in enumerate([1.0, 0.4, 0.15]):
                spe[idx(day) + k] += mag * f
    spe_int = np.clip(spe / 6, 0, 1)
    spe_recent, acc = np.zeros(n), 0.0
    for i in range(n):
        acc = acc * 0.8 + spe_int[i]
        spe_recent[i] = acc

    ill, illness = np.zeros(n), []
    if M >= 60:
        s, L = int(rng.integers(30, M - 20)), int(rng.integers(4, 7))
        ill[idx(s):idx(s) + L] = 1
        illness.append(("Upper respiratory infection", "infection", dt(s).isoformat(),
                        dt(s + L - 1).isoformat(), 2, "Congestion and low-grade fatigue; resolved with rest."))
    if POST >= 4:
        illness.append(("Orthostatic intolerance", "cardiovascular", dt(M).isoformat(),
                        dt(M + 3).isoformat(), 2, "Lightheadedness on standing after landing."))
    conn.executemany("INSERT INTO illness_events (user_id,name,category,start_date,end_date,severity,notes) "
                     "VALUES (?,?,?,?,?,?,?)", [(uid, *e) for e in illness])

    # ---- daily tables: sleep, activity, nutrition, radiation
    sleep_rows, act_rows, nut_rows, rad_rows = [], [], [], []
    bed_prev, wake_h = np.zeros(n), np.zeros(n)
    res_d, car_d, adh_in = np.zeros(n), np.zeros(n), []
    for i, d in enumerate(days):
        ph, day0 = phase(d), datetime.combine(dt(d), datetime.min.time())
        # sleep
        total = float(np.clip({"pre": 440, "in": 390, "post": 425}[ph] - 9 * max(w[i] - 8, 0)
                              - 30 * ill[i] - 25 * spe_int[i] + rng.normal(0, 25), 240, 540))
        awake = float(np.clip(rng.normal(28, 9) + 8 * max(stress[i], 0) + 15 * ill[i], 8, 100))
        tib = total + awake
        wake_h[i] = float(np.clip(rng.normal(7.0 if ph == "in" else 6.8, 0.35), 5.5, 8.5))
        bed_prev[i] = wake_h[i] - tib / 60  # negative = evening before
        deep = total * float(np.clip(rng.normal({"pre": .18, "in": .155, "post": .17}[ph], .015), .08, .26))
        rem = total * float(np.clip(rng.normal({"pre": .22, "in": .205, "post": .21}[ph], .02), .10, .30))
        eff = 100 * total / tib
        score = 100 * (0.5 * min(total / 450, 1) + 0.2 * min(deep / 80, 1) + 0.15 * min(rem / 100, 1) + 0.15 * eff / 100)
        sleep_rows.append((uid, dt(d).isoformat(), iso(day0 + timedelta(hours=float(bed_prev[i]))),
                           iso(day0 + timedelta(hours=float(wake_h[i]))), round(total), round(deep), round(rem),
                           round(total - deep - rem), round(awake), round(eff, 1), round(score)))
        # activity
        if ph == "in":
            adh = float(np.clip(0.85 + rng.normal(0, 0.08) - 0.04 * max(w[i] - 9, 0), 0.3, 1.1))
            adh_in.append(adh)
            res, car = 60 * adh + rng.normal(0, 6), 60 * adh + rng.normal(0, 6)
        elif ph == "pre":
            res = 45 * (rng.random() < 0.6) + rng.normal(0, 5)
            car = 40 * (rng.random() < 0.7) + rng.normal(0, 5)
        else:
            pdays = d - M
            res = 25 + 20 * (1 - np.exp(-pdays / 20)) + rng.normal(0, 5)
            car = 25 + 15 * (1 - np.exp(-pdays / 20)) + rng.normal(0, 5)
        res_d[i], car_d[i] = max(res * (1 - 0.6 * ill[i]), 0), max(car * (1 - 0.6 * ill[i]), 0)
        act_rows.append((uid, dt(d).isoformat(), round(res_d[i]), round(car_d[i]),
                         round(4.5 * res_d[i] + 9 * car_d[i] + 220 + rng.normal(0, 40)), round(float(w[i]), 1)))
        # nutrition (astronauts typically under-eat in flight)
        need = 2600 if a.sex == "M" else 2100
        nut_rows.append((uid, dt(d).isoformat(),
                         round(need * {"pre": 1.0, "in": 0.82, "post": 0.98}[ph] * rng.normal(1, 0.07)),
                         round(w0 * rng.normal(1.15 if ph == "in" else 1.2, 0.12)),
                         round(max(rng.normal(800, 150) if ph == "in" else rng.normal(450, 250), 0)),
                         round(rng.normal(1000 if ph == "in" else 1100, 180)),
                         round(rng.normal(4200 if ph == "in" else 2900, 500)),
                         round(rng.normal(2300 if ph == "in" else 2600, 300))))
        # radiation
        rate = ENV_DOSE[a.env] if ph == "in" else GROUND_DOSE
        rad_rows.append((uid, dt(d).isoformat(), round(max(rng.normal(rate, rate * 0.12), 0) + float(spe[i]), 4),
                         "dosimeter"))
    adh_mean = float(np.mean(adh_in))
    conn.executemany("INSERT INTO sleep_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?)", sleep_rows)
    conn.executemany("INSERT INTO activity_daily VALUES (?,?,?,?,?,?)", act_rows)
    conn.executemany("INSERT INTO nutrition_daily VALUES (?,?,?,?,?,?,?,?)", nut_rows)
    conn.executemany("INSERT INTO radiation_dose VALUES (?,?,?,?)", rad_rows)

    # ---- heart rate (5-minute samples) + daily resting HR / HRV
    meas = []

    def put(metric, d, value, hour=8, source="lab", note=None):
        ts = datetime.combine(dt(d), datetime.min.time()) + timedelta(hours=hour)
        meas.append((uid, metric, round(float(value), DECIMALS[metric]), iso(ts), source, note))

    t = np.arange(288) * 5 / 60.0
    hr_rows = []
    for i, d in enumerate(days):
        ph, day0 = phase(d), datetime.combine(dt(d), datetime.min.time())
        rest = B["resting_hr"] + 2.0 * stress[i] + 6 * ill[i] + 3 * spe_int[i]
        if ph == "in":
            rest += 0.012 * d
        elif ph == "post":
            rest += 9 * np.exp(-(d - M) / 10)
        asleep = (t < wake_h[i]) | (t >= 24 + bed_prev[min(i + 1, n - 1)])
        hr = np.where(asleep, rest - 7 + 1.5 * np.sin(2 * np.pi * t / 3.0), rest + 10 + 4 * np.sin(2 * np.pi * (t - 9) / 24))
        hr = hr + rng.normal(0, np.where(asleep, 2.0, 3.5))
        state = np.where(asleep, "sleep", "rest").astype(object)
        for start_h, minutes, bump in ((10.0, res_d[i], 30), (17.0, car_d[i], 60)):
            nb = int(round(minutes / 5))
            if nb > 0:
                s = max(0, int(start_h * 12) + int(rng.integers(-6, 7)))
                e = min(s + nb, 288)
                hr[s:e] = rest + bump + rng.normal(0, 6, e - s)
                state[s:e] = "exercise"
        hr = np.clip(hr, 38, 195)
        hr_rows.extend((uid, iso(day0 + timedelta(minutes=5 * k)), int(hr[k]), state[k]) for k in range(288))
        put("resting_hr", d, hr[asleep].mean(), hour=7, source="wearable")
        hrv = B["hrv_rmssd"] * (1 - 0.10 * stress[i] - 0.15 * ill[i] - 0.10 * spe_int[i]
                                - (0.08 if ph == "in" else 0) - (0.10 * np.exp(-(d - M) / 10) if ph == "post" else 0))
        put("hrv_rmssd", d, max(hrv + rng.normal(0, 3), 10), hour=7, source="wearable")
    conn.executemany("INSERT INTO heart_rate_samples VALUES (?,?,?,?)", hr_rows)

    # ---- sparse clinical measurements
    last = int(days[-1])
    ok = lambda ds: sorted({int(d) for d in ds if days[0] <= d <= last})
    lab_days = ok([-30, -14] + list(range(7, M, 21)) + [M - 1] + [M + 1, M + 7, M + 14, M + 30])
    for d in lab_days:
        i, inf = idx(d), 1.0 if 0 <= d < M else 0.0
        # blood panel ("space anemia": red-cell mass falls in flight, recovers after landing)
        rb = 1 - 0.07 * ramp(d, 20, 25)
        put("rbc", d, B["rbc"] * rb + rng.normal(0, 0.08))
        put("hemoglobin", d, B["hemoglobin"] * rb + rng.normal(0, 0.25))
        put("hematocrit", d, B["hematocrit"] * rb + rng.normal(0, 0.8))
        put("wbc", d, B["wbc"] * (1 + 0.06 * inf + 0.30 * ill[i] + 0.04 * stress[i]) + rng.normal(0, 0.4))
        lym = B["lymphocyte_pct"] - 3.5 * spe_recent[i] - 1.5 * max(stress[i], 0) + rng.normal(0, 1.5)
        put("lymphocyte_pct", d, lym)
        put("neutrophil_pct", d, 100 - lym - rng.normal(8, 1))
        put("platelets", d, B["platelets"] + rng.normal(0, 15))
        # biomarkers
        put("crp", d, B["crp"] * np.exp(0.35 * inf + 0.3 * stress[i] + 1.1 * ill[i] + rng.normal(0, 0.25)))
        put("cortisol_am", d, B["cortisol_am"] * (1 + 0.08 * stress[i] + 0.05 * inf) + rng.normal(0, 1.2))
        put("vitamin_d", d, B["vitamin_d"] * (1 - 0.2 * ramp(d, 60, 45)) + rng.normal(0, 1.5))
        put("ferritin", d, B["ferritin"] * (1 + 0.45 * ramp(d, 45, 40)) + rng.normal(0, 8))
        put("ctx", d, B["ctx"] * (1 + 0.30 * ramp(d, 40, 20)) + rng.normal(0, 0.03))
        put("p1np", d, B["p1np"] * (1 - 0.05 * ramp(d, 40, 20)) + rng.normal(0, 3))
        put("glucose", d, B["glucose"] + rng.normal(0, 5))

    for d in ok(range(-PRE, M + POST, 7)):  # weekly weight + blood pressure
        i, inf = idx(d), 1.0 if 0 <= d < M else 0.0
        orth = 4.0 if M <= d < M + 4 else 0.0
        put("weight_kg", d, w0 * (1 - 0.025 * ramp(d, 45, 40)) + rng.normal(0, 0.35), hour=7, source="scale")
        put("systolic_bp", d, B["systolic_bp"] - 3 * inf + 2 * stress[i] - orth + rng.normal(0, 3), hour=7, source="cuff")
        put("diastolic_bp", d, B["diastolic_bp"] - 2 * inf + 1 * stress[i] + rng.normal(0, 2), hour=7, source="cuff")

    grip0 = (45.0 if a.sex == "M" else 29.0) * rng.normal(1, 0.05)
    for d in ok([-30, -10] + list(range(14, M, 28)) + [M + 3, M + 14, M + 30]):
        put("grip_strength_kg", d, grip0 * (1 - 0.009 * (1.6 - adh_mean) * months(d, 30)) + rng.normal(0, 0.5),
            hour=10, source="manual")

    lean0 = w0 * (0.72 if a.sex == "M" else 0.64) * rng.normal(1, 0.03)  # DXA scans: only on the ground
    for d in ok([-30, M + 5, M + 28]):
        put("bmd_lumbar_spine", d, B["bmd_lumbar_spine"] * (1 - 0.0042 * (1.6 - adh_mean) * months(d, 300))
            + rng.normal(0, 0.004), hour=9, source="dxa")
        put("bmd_femoral_neck", d, B["bmd_femoral_neck"] * (1 - 0.0060 * (1.6 - adh_mean) * months(d, 300))
            + rng.normal(0, 0.004), hour=9, source="dxa")
        put("lean_mass_kg", d, lean0 * (1 - 0.004 * (1.6 - adh_mean) * months(d, 200)) + rng.normal(0, 0.25),
            hour=9, source="dxa")
    conn.executemany("INSERT INTO measurements (user_id,metric,value,measured_at,source,note) VALUES (?,?,?,?,?,?)", meas)

    # ---- symptoms
    sym = []

    def log(d, hour, symptom, sev, cat, note=None):
        sev = int(np.clip(round(sev), 0, 10))
        if sev > 0 and days[0] <= d <= last:
            sym.append((uid, f"{dt(d).isoformat()}T{hour:02d}:00:00", symptom, sev, cat, note))

    for k in range(3):  # space adaptation, first 3 days in orbit
        for name, base in (("nausea", 6), ("headache", 5), ("dizziness", 5)):
            log(k, 18, name, base - 1.5 * k + rng.normal(0, 1), "adaptation", "space adaptation")
    for day in spe_days:  # radiation symptoms after solar particle events
        for k, f in enumerate([1.0, 0.7, 0.35]):
            log(day + k, 20, "nausea", 5 * f + rng.normal(0, 0.7), "radiation", "after solar particle alert")
            log(day + k, 20, "fatigue", 6 * f + rng.normal(0, 0.7), "radiation", "after solar particle alert")
            log(day + k, 20, "headache", 3 * f + rng.normal(0, 0.7), "radiation", "after solar particle alert")
    if M >= 60:  # SANS (spaceflight-associated neuro-ocular syndrome): slowly worsening vision complaints
        for d in range(45, M, 7):
            log(d, 9, "blurred_vision", 1 + 2 * (d - 45) / max(M - 45, 1) + rng.normal(0, 0.5), "sans")
    for i, d in enumerate(days):
        if rng.random() < 0.06:
            pool = ["headache", "back_pain", "congestion", "muscle_soreness"]
            if 0 <= d < 30:
                pool += ["back_pain"] * 3
            log(d, 19, str(rng.choice(pool)), 2 + rng.normal(0, 1), "general")
    conn.executemany("INSERT INTO symptom_logs (user_id,logged_at,symptom,severity,category,note) VALUES (?,?,?,?,?,?)", sym)

    # ---- journal (subjective status reports)
    jr = []
    for i in range(0, n, 3):
        d, ph = int(days[i]), phase(int(days[i]))
        mood = float(np.clip(7.4 - 0.5 * (w[i] - 8) - 1.5 * ill[i] - 1.0 * spe_int[i] + rng.normal(0, 0.7), 1, 10))
        bucket = "hi" if mood >= 7 else ("mid" if mood >= 5 else "lo")
        text = str(rng.choice(JOURNAL[ph][bucket]))
        if ill[i]:
            text += " Congested and run down."
        if spe_recent[i] > 0.5:
            text += " Radiation alert earlier; mild nausea, stayed in the shielded area."
        if ph == "in" and d >= 45 and rng.random() < 0.3:
            text += " Noticed some blurred vision when reading small text."
        jr.append((uid, f"{dt(d).isoformat()}T21:00:00", int(round(mood)),
                   int(np.clip(round(5 + 1.2 * stress[i] + rng.normal(0, 0.5)), 1, 10)), text))
    conn.executemany("INSERT INTO journal_entries (user_id,written_at,mood,stress,text) VALUES (?,?,?,?,?)", jr)


def summary(conn, uid):
    print("\nGenerated data for user", uid)
    for t in ["measurements", "heart_rate_samples", "sleep_sessions", "activity_daily", "nutrition_daily",
              "radiation_dose", "symptom_logs", "illness_events", "journal_entries"]:
        print(f"  {t:20s}{conn.execute(f'SELECT COUNT(*) FROM {t} WHERE user_id=?', (uid,)).fetchone()[0]:>8d} rows")
    keys = ["resting_hr", "hrv_rmssd", "sleep_total_min", "exercise_min", "workload_hours", "hemoglobin",
            "rbc", "crp", "ctx", "vitamin_d", "bmd_femoral_neck", "grip_strength_kg", "weight_kg"]
    rows = conn.execute(
        "SELECT metric, phase, AVG(value) FROM v_all_metrics WHERE user_id=? AND metric IN (%s) GROUP BY 1,2"
        % ",".join("?" * len(keys)), (uid, *keys)).fetchall()
    tbl = {(m, p): v for m, p, v in rows}
    print(f"\n  {'metric':20s}{'pre_flight':>12s}{'in_flight':>12s}{'post_flight':>12s}")
    for k in keys:
        cells = [f"{tbl[(k, p)]:12.2f}" if (k, p) in tbl else f"{'-':>12s}" for p in ("pre_flight", "in_flight", "post_flight")]
        print(f"  {k:20s}" + "".join(cells))
    total = conn.execute("SELECT MAX(cumulative_msv) FROM v_radiation_cumulative WHERE user_id=?", (uid,)).fetchone()[0]
    print(f"\n  cumulative radiation dose: {total:.1f} mSv")


if __name__ == "__main__":
    main()
