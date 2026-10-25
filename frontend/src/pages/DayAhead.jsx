import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { useApi } from '../api'
import { Card, Kpi, Status } from '../components/ui'
import { COLORS, dateTime, gw, gwh, hhmm } from '../format'

const FIRST = '2026-01-02'
const LAST = '2026-02-01'

export default function DayAhead({ day, setDay }) {
  const { data, loading, error } = useApi(`/day/${day}`)

  const shift = (n) => {
    const d = new Date(`${day}T00:00:00Z`)
    d.setUTCDate(d.getUTCDate() + n)
    const next = d.toISOString().slice(0, 10)
    if (next >= FIRST && next <= LAST) setDay(next)
  }

  const controls = (
    <div className="controls">
      <button onClick={() => shift(-1)} disabled={day <= FIRST}>◀</button>
      <input type="date" value={day} min={FIRST} max={LAST} onChange={(e) => e.target.value && setDay(e.target.value)} />
      <button onClick={() => shift(1)} disabled={day >= LAST}>▶</button>
      <span className="muted">Delivery day (decision taken the day before)</span>
    </div>
  )

  if (!data) return <>{controls}<Status loading={loading} error={error} /></>

  // Show the decision forecast plus up to three earlier vintages, so the
  // trader can see how stable the forecast was in the run-up to the decision.
  const older = data.vintages.slice(-4, -1)
  const rows = data.hours.map((h) => {
    const row = { ...h, band: h.p90_low != null ? [h.p90_low, h.p10_high] : null }
    older.forEach((v, i) => {
      const p = v.points.find((x) => x.startTime === h.startTime)
      row[`v${i}`] = p ? p.forecast : null
    })
    return row
  })

  return (
    <>
      {controls}
      <div className="kpis">
        <Kpi label="Forecast used for decision" value={dateTime(data.decision_publish_time)} hint={`latest published before ${dateTime(data.cutoff)}`} />
        <Kpi label="Forecast wind energy" value={gwh(data.forecast_mwh)} />
        <Kpi label="Actual wind energy" value={gwh(data.actual_mwh)} />
        <Kpi
          label={data.shortfall_mwh >= 0 ? 'Shortfall to buy in' : 'Surplus wind'}
          value={gwh(Math.abs(data.shortfall_mwh))}
          tone={data.shortfall_mwh >= 0 ? 'warn' : 'good'}
        />
        <Kpi label="Mean hourly error" value={gw(data.summary.mae_mw)} hint={`${data.summary.nmae_pct}% of mean output`} />
      </div>

      <Card
        title="What was known at decision time, and what happened"
        subtitle="Shaded band: P10–P90 range of actual wind given the forecast level, from January's error distribution."
      >
        <ResponsiveContainer width="100%" height={380}>
          <ComposedChart data={rows} margin={{ left: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="startTime" tickFormatter={hhmm} />
            <YAxis tickFormatter={(v) => `${v / 1000}`} label={{ value: 'GW', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              labelFormatter={dateTime}
              formatter={(v) => (Array.isArray(v) ? `${gw(v[0])} – ${gw(v[1])}` : gw(v))}
            />
            <Legend />
            <Area isAnimationActive={false} dataKey="band" name="Likely range (P10–P90)" fill={COLORS.band} stroke="none" fillOpacity={0.35} />
            {older.map((v, i) => (
              <Line isAnimationActive={false} key={v.publishTime} dataKey={`v${i}`} name={`Earlier forecast ${dateTime(v.publishTime)}`}
                stroke={COLORS.persistence} strokeDasharray="4 3" dot={false} strokeWidth={1} />
            ))}
            <Line isAnimationActive={false} dataKey="forecast" name="Decision forecast" stroke={COLORS.forecast} dot={false} strokeWidth={2.5} />
            <Line isAnimationActive={false} dataKey="actual" name="Actual" stroke={COLORS.actual} dot={false} strokeWidth={2.5} />
          </ComposedChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Hour by hour">
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Hour</th><th>Forecast</th><th>Likely range</th><th>Actual</th><th>Error (F − A)</th></tr>
            </thead>
            <tbody>
              {data.hours.map((h) => (
                <tr key={h.startTime}>
                  <td>{hhmm(h.startTime)}</td>
                  <td>{gw(h.forecast)}</td>
                  <td>{h.p90_low != null ? `${gw(h.p90_low)} – ${gw(h.p10_high)}` : '–'}</td>
                  <td>{gw(h.actual)}</td>
                  <td className={h.error > 0 ? 'neg' : 'pos'}>{gw(h.error)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}
