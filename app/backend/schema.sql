-- Astronaut health monitoring prototype - SQLite schema
-- Safe to run repeatedly (CREATE ... IF NOT EXISTS; views are rebuilt).
-- Assumes your existing `users` table has an integer primary key called `id`.
-- If yours is named differently, change the REFERENCES userlog(id) clauses below.
--
-- Timestamps are ISO-8601 text in UTC ('2026-01-15T08:00:00'); dates are 'YYYY-MM-DD'.
-- Design idea: a few "wide" tables for high-volume wearable data (heart rate,
-- sleep, activity, nutrition, radiation), plus ONE narrow `measurements` table for
-- sparse clinical data (blood, bone, muscle, biomarkers). The view v_all_metrics
-- unions everything into (user, metric, value, ts, phase, mission_day) so a single
-- z-score / percentile / baseline endpoint works for every metric.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- catalogue
CREATE TABLE IF NOT EXISTS metric_definitions (
  metric_key     TEXT PRIMARY KEY,
  label          TEXT NOT NULL,
  unit           TEXT NOT NULL,
  category       TEXT NOT NULL,       -- blood, biomarker, bone, muscle, body, cardio, sleep, activity, nutrition, radiation
  decimals       INTEGER NOT NULL DEFAULT 1,
  good_direction TEXT NOT NULL DEFAULT 'range' CHECK (good_direction IN ('up','down','range'))
                                       -- drives UI colours: is higher better, lower better, or stay in range?
);

-- Population / ground reference statistics used for percentiles and z-scores.
-- Illustrative demo values: replace with NASA or clinical references before real use.
CREATE TABLE IF NOT EXISTS reference_ranges (
  metric_key  TEXT NOT NULL REFERENCES metric_definitions(metric_key),
  sex         TEXT NOT NULL CHECK (sex IN ('M','F','any')),
  ref_mean    REAL NOT NULL,
  ref_sd      REAL NOT NULL,
  normal_low  REAL,
  normal_high REAL,
  note        TEXT,
  PRIMARY KEY (metric_key, sex)
);

-- ---------------------------------------------------------------- "known" data
CREATE TABLE IF NOT EXISTS astronaut_profile (
  user_id                  INTEGER PRIMARY KEY REFERENCES userlog(id),
  display_name             TEXT NOT NULL,
  birth_date               TEXT NOT NULL,
  sex                      TEXT NOT NULL CHECK (sex IN ('M','F')),
  height_cm                REAL NOT NULL,
  baseline_weight_kg       REAL NOT NULL,
  role                     TEXT,
  mission_name             TEXT,
  launch_date              TEXT NOT NULL,  -- day 0 of the mission
  landing_date             TEXT,           -- NULL = mission still in progress
  environment              TEXT NOT NULL DEFAULT 'LEO' CHECK (environment IN ('LEO','lunar','deep_space')),
  known_conditions         TEXT,           -- JSON list of pre-existing conditions
  usual_workload_h_per_day REAL
);

-- ---------------------------------------------------------------- measured data
-- Sparse clinical results: blood counts, biomarkers, DXA bone density, lean mass,
-- grip strength, weight, blood pressure, daily resting HR / HRV summaries.
CREATE TABLE IF NOT EXISTS measurements (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES userlog(id),
  metric      TEXT NOT NULL REFERENCES metric_definitions(metric_key),
  value       REAL NOT NULL,
  measured_at TEXT NOT NULL,
  source      TEXT NOT NULL DEFAULT 'lab',  -- lab, dxa, wearable, scale, cuff, manual
  note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_meas_user_metric_time ON measurements(user_id, metric, measured_at);

-- Heart rate time series (5-minute resolution in the generator).
CREATE TABLE IF NOT EXISTS heart_rate_samples (
  user_id INTEGER NOT NULL REFERENCES userlog(id),
  ts      TEXT NOT NULL,
  bpm     INTEGER NOT NULL,
  state   TEXT NOT NULL DEFAULT 'rest' CHECK (state IN ('sleep','rest','exercise')),
  PRIMARY KEY (user_id, ts)
) WITHOUT ROWID;

-- One row per night. night_date = the date you WOKE UP.
CREATE TABLE IF NOT EXISTS sleep_sessions (
  user_id        INTEGER NOT NULL REFERENCES userlog(id),
  night_date     TEXT NOT NULL,
  start_at       TEXT NOT NULL,
  end_at         TEXT NOT NULL,
  total_min      REAL NOT NULL,   -- time actually asleep
  deep_min       REAL NOT NULL,
  rem_min        REAL NOT NULL,
  light_min      REAL NOT NULL,
  awake_min      REAL NOT NULL,
  efficiency_pct REAL NOT NULL,
  sleep_score    REAL NOT NULL,   -- 0-100 composite
  PRIMARY KEY (user_id, night_date)
);

CREATE TABLE IF NOT EXISTS activity_daily (
  user_id        INTEGER NOT NULL REFERENCES userlog(id),
  day            TEXT NOT NULL,
  resistance_min REAL NOT NULL,   -- e.g. ARED sessions (countermeasure for bone/muscle loss)
  cardio_min     REAL NOT NULL,   -- treadmill / cycle ergometer
  active_kcal    REAL NOT NULL,
  workload_hours REAL NOT NULL,   -- scheduled work hours that day
  PRIMARY KEY (user_id, day)
);

CREATE TABLE IF NOT EXISTS nutrition_daily (
  user_id      INTEGER NOT NULL REFERENCES userlog(id),
  day          TEXT NOT NULL,
  kcal_intake  REAL NOT NULL,
  protein_g    REAL NOT NULL,
  vitamin_d_iu REAL NOT NULL,
  calcium_mg   REAL NOT NULL,
  sodium_mg    REAL NOT NULL,
  water_ml     REAL NOT NULL,
  PRIMARY KEY (user_id, day)
);

-- Personal dosimeter, effective dose per day.
CREATE TABLE IF NOT EXISTS radiation_dose (
  user_id  INTEGER NOT NULL REFERENCES userlog(id),
  date     TEXT NOT NULL,
  dose_msv REAL NOT NULL,
  source   TEXT NOT NULL DEFAULT 'dosimeter',
  PRIMARY KEY (user_id, date)
);

-- ---------------------------------------------------------------- subjective / events
CREATE TABLE IF NOT EXISTS symptom_logs (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id   INTEGER NOT NULL REFERENCES userlog(id),
  logged_at TEXT NOT NULL,
  symptom   TEXT NOT NULL,
  severity  INTEGER NOT NULL CHECK (severity BETWEEN 0 AND 10),
  category  TEXT NOT NULL CHECK (category IN ('radiation','adaptation','sans','general')),
  note      TEXT
);
CREATE INDEX IF NOT EXISTS idx_sym_user_time ON symptom_logs(user_id, logged_at);

CREATE TABLE IF NOT EXISTS illness_events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES userlog(id),
  name       TEXT NOT NULL,
  category   TEXT,
  start_date TEXT NOT NULL,
  end_date   TEXT,
  severity   INTEGER CHECK (severity BETWEEN 1 AND 3),
  notes      TEXT
);

-- The written status-report log, readable by doctors / psychologists / an AI model.
CREATE TABLE IF NOT EXISTS journal_entries (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES userlog(id),
  written_at TEXT NOT NULL,
  mood       INTEGER NOT NULL CHECK (mood BETWEEN 1 AND 10),
  stress     INTEGER NOT NULL CHECK (stress BETWEEN 1 AND 10),
  text       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_journal_user_time ON journal_entries(user_id, written_at);

-- Output of the rules engine and/or the LLM layer.
CREATE TABLE IF NOT EXISTS recommendations (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        INTEGER NOT NULL REFERENCES userlog(id),
  created_at     TEXT NOT NULL,
  category       TEXT NOT NULL,   -- workload, sleep, exercise, nutrition, radiation, medical
  severity       TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('info','watch','alert')),
  title          TEXT NOT NULL,
  body           TEXT NOT NULL,
  source         TEXT NOT NULL DEFAULT 'rules' CHECK (source IN ('rules','ai')),
  related_metric TEXT REFERENCES metric_definitions(metric_key),
  acknowledged   INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------- views
-- Every numeric metric in one shape, tagged with mission phase and mission day.
-- Usage:  SELECT value FROM v_all_metrics
--         WHERE user_id=? AND metric='hemoglobin' AND phase='pre_flight';   -- personal baseline
DROP VIEW IF EXISTS v_all_metrics;
CREATE VIEW v_all_metrics AS
WITH raw AS (
  SELECT user_id, metric, value, measured_at AS ts, source FROM measurements
  UNION ALL SELECT user_id, 'sleep_total_min',      total_min,      night_date, 'wearable' FROM sleep_sessions
  UNION ALL SELECT user_id, 'sleep_deep_min',       deep_min,       night_date, 'wearable' FROM sleep_sessions
  UNION ALL SELECT user_id, 'sleep_rem_min',        rem_min,        night_date, 'wearable' FROM sleep_sessions
  UNION ALL SELECT user_id, 'sleep_efficiency_pct', efficiency_pct, night_date, 'wearable' FROM sleep_sessions
  UNION ALL SELECT user_id, 'sleep_score',          sleep_score,    night_date, 'wearable' FROM sleep_sessions
  UNION ALL SELECT user_id, 'exercise_min',    resistance_min + cardio_min, day, 'wearable' FROM activity_daily
  UNION ALL SELECT user_id, 'resistance_min',  resistance_min,  day, 'wearable' FROM activity_daily
  UNION ALL SELECT user_id, 'cardio_min',      cardio_min,      day, 'wearable' FROM activity_daily
  UNION ALL SELECT user_id, 'active_kcal',     active_kcal,     day, 'wearable' FROM activity_daily
  UNION ALL SELECT user_id, 'workload_hours',  workload_hours,  day, 'schedule' FROM activity_daily
  UNION ALL SELECT user_id, 'kcal_intake',     kcal_intake,     day, 'manual' FROM nutrition_daily
  UNION ALL SELECT user_id, 'protein_g',       protein_g,       day, 'manual' FROM nutrition_daily
  UNION ALL SELECT user_id, 'vitamin_d_iu',    vitamin_d_iu,    day, 'manual' FROM nutrition_daily
  UNION ALL SELECT user_id, 'calcium_mg',      calcium_mg,      day, 'manual' FROM nutrition_daily
  UNION ALL SELECT user_id, 'sodium_mg',       sodium_mg,       day, 'manual' FROM nutrition_daily
  UNION ALL SELECT user_id, 'water_ml',        water_ml,        day, 'manual' FROM nutrition_daily
  UNION ALL SELECT user_id, 'radiation_dose_msv', dose_msv,     date, source FROM radiation_dose
)
SELECT r.user_id, r.metric, r.value, r.ts, r.source,
       CASE WHEN date(r.ts) < p.launch_date THEN 'pre_flight'
            WHEN p.landing_date IS NULL OR date(r.ts) < p.landing_date THEN 'in_flight'
            ELSE 'post_flight' END AS phase,
       CAST(julianday(date(r.ts)) - julianday(p.launch_date) AS INTEGER) AS mission_day
FROM raw r
JOIN astronaut_profile p ON p.user_id = r.user_id;

DROP VIEW IF EXISTS v_radiation_cumulative;
CREATE VIEW v_radiation_cumulative AS
SELECT user_id, date, dose_msv,
       SUM(dose_msv) OVER (PARTITION BY user_id ORDER BY date) AS cumulative_msv
FROM radiation_dose;
