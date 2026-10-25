import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { useApi } from '../api'
import { Card, Kpi, Status } from '../components/ui'
import { COLORS, dayLabel, dateTime, gw, gwh, pct, signedGw } from '../format'

export default function Overview({ onOpenDay }) {
  const acc = useApi('/accuracy')
  const ser = useApi('/series')
  if (!acc.data || !ser.data) return <Status {...(acc.error ? acc : ser)} />

  const a = acc.data
  const f = a.forecast
  const high = a.by_forecast_level.find((r) => r.forecast_level === '> 15 GW')
  const worst = [...a.by_day].sort((x, y) => y.mae_mw - x.mae_mw)[0]
  const daily = a.by_day.map((d) => ({
    day: d.day,
    label: dayLabel(d.day),
    forecast: d.forecast_mwh,
    actual: d.actual_mwh,
  }))

  return (
    <>
      <div className="kpis">
        <Kpi label="Typical hourly error (MAE)" value={gw(f.mae_mw)} hint={`${pct(f.nmae_pct)} of mean wind output`} />
        <Kpi label="Systematic bias" value={signedGw(f.bias_mw)} hint={`forecast too high in ${pct(f.share_over_forecast_pct, 0)} of hours`} tone="warn" />
        <Kpi label="90% shortfall cover" value={gw(f.quantiles_mw.p90)} hint="extra power that would have covered 9 in 10 hours" />
        <Kpi label="Worst single-hour shortfall" value={gw(f.max_shortfall_mw)} />
        <Kpi label="Skill vs naive baseline" value={pct(100 * a.skill_vs_persistence, 0)} hint="lower MAE than 'tomorrow = last known actual'" tone="good" />
      </div>

      <Card title="What the January pilot tells us">
        <ul className="findings">
          <li>
            The forecast available at decision time <b>over-predicted wind in {pct(f.share_over_forecast_pct, 0)} of hours</b>,
            on average by <b>{gw(f.bias_mw)}</b>. Relying on it as-is would have meant consistently under-buying.
          </li>
          <li>
            In 9 out of 10 hours, actual wind was no more than <b>{gw(f.quantiles_mw.p90)}</b> below the forecast.
            That is the size of the buffer needed to be covered 90% of the time.
          </li>
          {high && (
            <li>
              The error grows with wind level. When the forecast is above 15 GW, it was too high by
              <b> {gw(high.bias_mw)}</b> on average ({high.n_hours} hours), so high-wind days need the most caution.
            </li>
          )}
          <li>
            Even so, the forecast is far better than a naive guess: <b>{pct(100 * a.skill_vs_persistence, 0)} lower error</b> than
            assuming tomorrow looks like the last known actual.
          </li>
          <li>
            Because the bias is persistent, subtracting the average error of the previous days (data the team already
            has at decision time) cut the error by <b>{pct(100 * a.bias_corrected_skill_vs_forecast, 0)}</b>{' '}
            ({gw(f.mae_mw)} → {gw(a.bias_corrected.mae_mw)}).
          </li>
          <li>
            Hardest day: <a href="#" onClick={(e) => { e.preventDefault(); onOpenDay(worst.day) }}>{dayLabel(worst.day)}</a>,
            with an average error of {gw(worst.mae_mw)} ({gwh(worst.forecast_mwh - worst.actual_mwh)} less wind than forecast).
          </li>
        </ul>
      </Card>

      <Card title="Decision forecast vs actual wind, every hour" subtitle="Forecast = latest WINDFOR published before the delivery day began (D-1).">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={ser.data} margin={{ left: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="startTime" tickFormatter={dayLabel} minTickGap={40} />
            <YAxis tickFormatter={(v) => `${v / 1000}`} label={{ value: 'GW', angle: -90, position: 'insideLeft' }} />
            <Tooltip labelFormatter={dateTime} formatter={(v) => gw(v)} />
            <Legend />
            <Line isAnimationActive={false} dataKey="forecast" name="Decision forecast" stroke={COLORS.forecast} dot={false} strokeWidth={1.5} />
            <Line isAnimationActive={false} dataKey="actual" name="Actual" stroke={COLORS.actual} dot={false} strokeWidth={1.5} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Daily energy: forecast vs actual" subtitle="Click a day to see what the trader saw at decision time.">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={daily} onClick={(e) => e?.activePayload && onOpenDay(e.activePayload[0].payload.day)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="label" minTickGap={10} />
            <YAxis tickFormatter={(v) => `${Math.round(v / 1000)}`} label={{ value: 'GWh', angle: -90, position: 'insideLeft' }} />
            <Tooltip formatter={(v) => gwh(v)} />
            <Legend />
            <Bar isAnimationActive={false} dataKey="forecast" name="Forecast" fill={COLORS.forecast} cursor="pointer" />
            <Bar isAnimationActive={false} dataKey="actual" name="Actual" fill={COLORS.actual} cursor="pointer" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </>
  )
}
