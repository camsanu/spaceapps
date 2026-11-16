// Astronaut health analytics page. Needs:  npm install recharts
// Usage:  <HealthDashboard apiBase="http://localhost:8000" userId={loggedInUser.id} />
// Styling reuses App.css: its :root variables (--purple, --surface, --line, ...) and its classes
// (widget-card, widget-section-header, widget-label, widget-button, text-button, todo-list, todo-item).
// Everything specific to this page is prefixed hd- and defined in the CSS string at the bottom.
import { useEffect, useMemo, useState } from "react";
import {
  Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

// SVG chart colours can't reliably use CSS variables, so these mirror App.css.
const PURPLE = "#6750a4", PURPLE_SOFT = "#e8def8", BLUE_CARD = "#b9bbdf", MUTED = "#716b7d", LINE = "#e4deed";
const STATUS = { good: "#2f8f6b", watch: "#d99a1e", alert: "#c9453f", info: MUTED };
const AXIS = { tick: { fill: MUTED, fontSize: 12 }, stroke: LINE };
const TIP = { contentStyle: { borderRadius: 10, border: `1px solid ${LINE}`, fontSize: 13 } };
const LABEL = (v) => ({ value: v, fontSize: 11, fill: MUTED });

const TABS = [
  ["All", null], ["Blood", ["blood"]], ["Biomarkers", ["biomarker"]], ["Bone & muscle", ["bone", "muscle", "body"]],
  ["Cardio", ["cardio"]], ["Sleep", ["sleep"]], ["Activity", ["activity"]], ["Nutrition", ["nutrition"]],
  ["Radiation", ["radiation"]],
];
const PHASE = { pre_flight: "Pre-flight", in_flight: "In flight", post_flight: "Post-flight" };

const fmt = (v, d = 1) => (v == null ? "–" : Number(v).toFixed(d));
const signed = (v, d = 1) => (v == null ? "–" : (v > 0 ? "+" : "") + Number(v).toFixed(d));
const hhmm = (m) => String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
const ordinal = (n) => {
  const r = Math.round(n), s = ["th", "st", "nd", "rd"], v = r % 100;
  return r + (s[(v - 20) % 10] || s[v] || s[0]);
};
const addDays = (iso, n) => {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};
const diffDays = (a, b) => Math.round((new Date(b + "T00:00:00Z") - new Date(a + "T00:00:00Z")) / 864e5);

// Fetch helper: keeps the previous data on screen while a new request is in flight.
function useApi(path, apiBase, userId) {
  const [s, setS] = useState({ data: null, error: null });
  useEffect(() => {
    let live = true;
    fetch(apiBase + path, { headers: { "X-User-Id": String(userId) } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
      .then((data) => live && setS({ data, error: null }))
      .catch((error) => live && setS((p) => ({ data: p.data, error })));
    return () => { live = false; };
  }, [path, apiBase, userId]);
  return s;
}

export default function HealthDashboard({ apiBase = "http://localhost:8000", userId = 1 }) {
  const [asOf, setAsOf] = useState(null);     // committed date; null = latest data
  const [slider, setSlider] = useState(null); // live slider position (days since first data)
  const [tab, setTab] = useState(0);
  const [selected, setSelected] = useState(null);
  const { data, error } = useApi(`/api/stats/summary${asOf ? `?as_of=${asOf}` : ""}`, apiBase, userId);
  const m = data?.mission;

  useEffect(() => { // debounce the timeline slider
    if (slider == null || !m) return;
    const t = setTimeout(() => setAsOf(addDays(m.first_date, slider)), 250);
    return () => clearTimeout(t);
  }, [slider, m?.first_date]);

  const cards = useMemo(() => {
    const cats = TABS[tab][1];
    return (data?.cards ?? []).filter((c) => !cats || cats.includes(c.category));
  }, [data, tab]);
  const attention = useMemo(
    () => (data?.cards ?? []).filter((c) => c.status === "alert" || c.status === "watch")
      .sort((a, b) => b.adverse - a.adverse).slice(0, 6), [data]);

  if (!data) {
    return (
      <div className="hd"><style>{CSS}</style>
        <section className="widget-card">{error ? `Could not load data: ${error.message}` : "Loading…"}</section>
      </div>
    );
  }

  const count = (s) => data.cards.filter((c) => c.status === s).length;
  const span = diffDays(m.first_date, m.last_date);
  const pos = slider ?? diffDays(m.first_date, m.as_of);

  return (
    <div className="hd">
      <style>{CSS}</style>

      <header className="widget-card hd-head">
        <div>
          <h1>{data.profile.name}</h1>
          <p className="hd-sub">{data.profile.role} · age {data.profile.age} · mission {m.name} ({m.environment})</p>
        </div>
        <div className="hd-phase" data-phase={m.phase}>
          {PHASE[m.phase]} · {m.mission_day < 0 ? `T${m.mission_day}` : `Day ${m.mission_day}`}
        </div>
      </header>

      <section className="widget-card hd-stack">
        <div className="widget-section-header">
          <h2>Mission timeline</h2><span className="hd-sub">viewing {m.as_of}</span>
        </div>
        <input type="range" min={0} max={span} value={pos} onChange={(e) => setSlider(Number(e.target.value))} />
        <div className="hd-row hd-sub">
          <span>{m.first_date}</span>
          <span>Launch {m.launch_date}{m.landing_date ? ` · Landing ${m.landing_date}` : ""}</span>
          <span>{m.last_date}</span>
        </div>
      </section>

      <div className="hd-grid2">
        <section className="widget-card hd-stack">
          <div className="hd-tiles">
            <Tile n={count("alert")} label="Alerts" color={STATUS.alert} />
            <Tile n={count("watch")} label="Watch" color={STATUS.watch} />
            <Tile n={count("good")} label="Normal" color={STATUS.good} />
            <Tile n={fmt(m.cumulative_msv, 1)} label="Radiation mSv" color={PURPLE} />
          </div>
          <div className="widget-section-header"><h2>Needs attention</h2></div>
          {attention.length === 0 && <p className="hd-sub">Everything is within the usual range for this astronaut.</p>}
          <div className="todo-list">
            {attention.map((c) => (
              <button key={c.metric} className="todo-item hd-attn" onClick={() => { setTab(0); setSelected(c.metric); }}>
                <span className="hd-dot" style={{ background: STATUS[c.status] }} />
                <span>{c.label}</span>
                <span className="hd-sub">{fmt(c.current, c.decimals)} {c.unit} · z {signed(c.z_baseline ?? c.pct_change / 5, 1)}</span>
              </button>
            ))}
          </div>
        </section>
        <RadiationPanel asOf={m.as_of} apiBase={apiBase} userId={userId} />
      </div>

      <HeartRatePanel date={m.as_of} apiBase={apiBase} userId={userId} />

      <nav className="hd-tabs">
        {TABS.map(([label], i) => (
          <button key={label} className={i === tab ? "on" : ""} onClick={() => setTab(i)}>{label}</button>
        ))}
      </nav>
      {selected && <MetricDetail key={selected + m.as_of} metric={selected} asOf={m.as_of} apiBase={apiBase}
        userId={userId} onClose={() => setSelected(null)} />}
      <div className="hd-cards">
        {cards.map((c) => (
          <MetricCard key={c.metric} c={c} active={c.metric === selected}
            onClick={() => setSelected((s) => (s === c.metric ? null : c.metric))} />
        ))}
      </div>
      <p className="hd-sub">Synthetic demo data. Not medical advice. z-score = distance from this astronaut's own
        pre-flight baseline; percentile = position within a healthy reference population.</p>
    </div>
  );
}

const Tile = ({ n, label, color }) => (
  <div className="hd-tile"><strong style={{ color }}>{n}</strong><span className="widget-label">{label}</span></div>
);

function MetricCard({ c, onClick, active }) {
  const color = STATUS[c.status];
  return (
    <button className={"widget-card hd-metric" + (active ? " on" : "")} onClick={onClick}
      style={{ borderTopColor: color }}>
      <div className="hd-row"><span className="hd-label">{c.label}</span>
        <span className="hd-dot" style={{ background: color }} title={c.status} /></div>
      <div className="hd-value">{fmt(c.current, c.decimals)} <small>{c.unit}</small></div>
      <ResponsiveContainer width="100%" height={34}>
        <LineChart data={c.spark.map((v, i) => ({ i, v }))}>
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      {c.percentile != null && (<>
        <div className="hd-bar"><div style={{ width: `${c.percentile}%`, background: color }} /></div>
        <div className="hd-sub">{ordinal(c.percentile)} percentile (reference)</div>
      </>)}
      <div className="hd-sub">
        {c.baseline_mean == null ? "no baseline" : `z ${signed(c.z_baseline, 2)} · ${signed(c.pct_change, 1)}% vs pre-flight`}
      </div>
    </button>
  );
}

function MetricDetail({ metric, asOf, apiBase, userId, onClose }) {
  const { data } = useApi(`/api/stats/metric/${metric}?as_of=${asOf}`, apiBase, userId);
  if (!data) return <section className="widget-card">Loading…</section>;
  const { definition: d, baseline: b, reference: r, points, landing_day: land } = data;
  const dec = d.decimals + 1;
  return (
    <section className="widget-card hd-stack">
      <div className="widget-section-header">
        <h2>{d.label} <small>({d.unit})</small></h2>
        <button className="text-button" onClick={onClose}>Close</button>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={points} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={LINE} />
          <XAxis {...AXIS} type="number" dataKey="mission_day" domain={["dataMin", "dataMax"]}
            tickFormatter={(v) => `D${v}`} />
          <YAxis {...AXIS} domain={["auto", "auto"]} width={52} tickFormatter={(v) => fmt(v, d.decimals)} />
          <Tooltip {...TIP} labelFormatter={(l) => `Mission day ${l}`} formatter={(v) => [fmt(v, dec), d.label]} />
          {b?.sd && <ReferenceArea y1={b.mean - b.sd} y2={b.mean + b.sd} fill={STATUS.good} fillOpacity={0.14} />}
          {b && <ReferenceLine y={b.mean} stroke={STATUS.good} strokeDasharray="4 4" />}
          {r?.normal_low != null && <ReferenceLine y={r.normal_low} stroke={STATUS.watch} strokeDasharray="2 4" />}
          {r?.normal_high != null && <ReferenceLine y={r.normal_high} stroke={STATUS.watch} strokeDasharray="2 4" />}
          <ReferenceLine x={0} stroke={MUTED} label={LABEL("Launch")} />
          {land != null && <ReferenceLine x={land} stroke={MUTED} label={LABEL("Landing")} />}
          <Line type="monotone" dataKey="value" stroke={PURPLE} strokeWidth={2} dot={points.length < 60}
            isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <p className="hd-sub">
        Green band: pre-flight baseline {b ? `${fmt(b.mean, dec)} ± ${fmt(b.sd, dec)} (${b.n} points, ${b.sd_source ?? "no"} spread)` : "n/a"}.
        {r && ` Amber lines: normal range ${r.normal_low ?? "–"} to ${r.normal_high ?? "–"} (reference mean ${r.ref_mean}).`}
      </p>
    </section>
  );
}

function segments(samples, state) {
  const out = [];
  let start = null;
  samples.forEach((s, i) => {
    const on = s.state === state;
    if (on && start === null) start = s.m;
    if ((!on || i === samples.length - 1) && start !== null) {
      out.push([start, on ? s.m : samples[i - 1].m]);
      start = null;
    }
  });
  return out;
}

function HeartRatePanel({ date, apiBase, userId }) {
  const { data } = useApi(`/api/stats/heart-rate?date=${date}`, apiBase, userId);
  if (!data) return <section className="widget-card">Loading heart rate…</section>;
  const s = data.summary;
  return (
    <section className="widget-card hd-stack">
      <div className="widget-section-header">
        <h2>Heart rate · {data.date}</h2>
        <span className="hd-sub">
          <i className="hd-key" style={{ background: BLUE_CARD }} />sleep
          <i className="hd-key" style={{ background: STATUS.watch }} />exercise
          <i className="hd-key" style={{ background: MUTED }} />typical pre-flight day
        </span>
      </div>
      <div className="hd-tiles">
        <Tile n={fmt(s.resting, 0)} label="Resting bpm" color={STATUS.good} />
        <Tile n={fmt(s.average, 0)} label="Average bpm" color={PURPLE} />
        <Tile n={fmt(s.max, 0)} label="Max bpm" color={STATUS.alert} />
        <Tile n={s.exercise_min} label="Exercise min" color={STATUS.watch} />
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data.samples} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={LINE} />
          <XAxis {...AXIS} type="number" dataKey="m" domain={[0, 1440]} ticks={[0, 240, 480, 720, 960, 1200, 1440]}
            tickFormatter={hhmm} />
          <YAxis {...AXIS} domain={[40, "auto"]} width={40} />
          <Tooltip {...TIP} labelFormatter={hhmm} formatter={(v) => [`${v} bpm`, "Heart rate"]} />
          {segments(data.samples, "sleep").map(([a, b], i) => <ReferenceArea key={"s" + i} x1={a} x2={b} fill={BLUE_CARD} fillOpacity={0.3} />)}
          {segments(data.samples, "exercise").map(([a, b], i) => <ReferenceArea key={"e" + i} x1={a} x2={b + 5} fill={STATUS.watch} fillOpacity={0.22} />)}
          <Line data={data.baseline_by_hour} dataKey="bpm" stroke={MUTED} strokeDasharray="5 4" dot={false}
            isAnimationActive={false} />
          <Line dataKey="bpm" stroke={STATUS.alert} strokeWidth={1.6} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}

function RadiationPanel({ asOf, apiBase, userId }) {
  const { data } = useApi(`/api/stats/radiation?as_of=${asOf}`, apiBase, userId);
  if (!data) return <section className="widget-card">Loading radiation…</section>;
  return (
    <section className="widget-card hd-stack">
      <div className="widget-section-header">
        <h2>Cumulative radiation dose</h2><strong>{fmt(data.total_msv, 1)} mSv</strong>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data.series} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={LINE} />
          <XAxis {...AXIS} type="number" dataKey="mission_day" domain={["dataMin", "dataMax"]}
            tickFormatter={(v) => `D${v}`} />
          <YAxis {...AXIS} width={44} />
          <Tooltip {...TIP} labelFormatter={(l) => `Mission day ${l}`} formatter={(v) => [`${fmt(v, 1)} mSv`, "Cumulative"]} />
          <ReferenceLine x={0} stroke={MUTED} />
          {data.landing_day != null && <ReferenceLine x={data.landing_day} stroke={MUTED} />}
          <Area type="monotone" dataKey="cumulative" stroke={PURPLE} fill={PURPLE_SOFT} fillOpacity={0.8}
            isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
      <p className="hd-sub">Steps in the curve are solar particle events.</p>
    </section>
  );
}

// Only what App.css doesn't already provide. Colours come from App.css variables (fallbacks = same values).
const CSS = `
.hd{display:flex;flex-direction:column;gap:20px;max-width:1280px;margin:0 auto;padding:20px 24px 32px;color:var(--ink,#282432)}
.hd h1{font-size:24px;line-height:1.2}
.hd small{color:var(--muted,#716b7d);font-weight:400;font-size:13px}
.hd-sub{color:var(--muted,#716b7d);font-size:13px}
.hd-stack{display:flex;flex-direction:column;gap:14px}
.hd-row{display:flex;justify-content:space-between;align-items:center;gap:8px}
.hd-head{display:flex;flex-direction:row;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.hd-head .hd-sub{margin-top:6px}
.hd-phase{padding:6px 14px;border-radius:999px;font-size:13px;font-weight:700;
  background:var(--purple-soft,#e8def8);color:var(--purple,#6750a4)}
.hd-phase[data-phase=in_flight]{background:var(--blue-card,#b9bbdf);color:var(--ink,#282432)}
.hd-phase[data-phase=post_flight]{background:#d9f0e6;color:#2f8f6b}
.hd input[type=range]{width:100%;accent-color:var(--purple,#6750a4)}
.hd-grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px}
.hd-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:12px}
.hd-tile{display:flex;flex-direction:column;gap:6px;padding:14px;border-radius:10px;background:var(--surface-muted,#f8f6fc)}
.hd-tile strong{font-size:22px}
.hd-attn{display:flex;align-items:center;gap:10px;width:100%;border:0;font-size:14px;color:inherit;text-align:left}
.hd-attn .hd-sub{margin-left:auto}
.hd-dot{width:11px;height:11px;border-radius:50%;flex:none}
.hd-key{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 5px 0 12px}
.hd-tabs{display:flex;gap:8px;flex-wrap:wrap}
.hd-tabs button{padding:8px 14px;border:1px solid var(--line,#e4deed);border-radius:999px;
  background:var(--surface,#fff);color:var(--ink,#282432);font-size:13px;font-weight:600}
.hd-tabs button.on{background:var(--purple,#6750a4);border-color:var(--purple,#6750a4);color:#fff}
.hd-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
.hd .hd-metric{display:block;width:100%;padding:16px;text-align:left;color:inherit;border-top-width:4px;
  transition:transform 150ms ease}
.hd .hd-metric:hover{transform:translateY(-1px)}
.hd .hd-metric.on{outline:2px solid var(--purple,#6750a4)}
.hd-label{font-size:13px;font-weight:600;color:var(--muted,#716b7d)}
.hd-value{font-size:26px;font-weight:700;margin:6px 0 2px}
.hd-bar{height:8px;border-radius:99px;background:var(--purple-soft,#e8def8);overflow:hidden;margin:8px 0 4px}
.hd-bar div{height:100%;border-radius:99px}
`;
