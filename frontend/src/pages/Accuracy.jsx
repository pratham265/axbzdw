import { useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { useApi } from '../api'
import { Card, Status } from '../components/ui'
import { COLORS, gw, pct } from '../format'

const FIRST = '2026-01-02'
const LAST = '2026-02-01'

function ModelTable({ a }) {
  const rows = [
    ['Decision forecast (WINDFOR, D-1)', a.forecast],
    ['Naive baseline (last known actual)', a.persistence],
    ['Bias-corrected forecast (past errors only)', a.bias_corrected],
  ]
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Method</th><th>MAE</th><th>RMSE</th><th>Bias</th><th>nMAE</th>
            <th>P10 error</th><th>P90 error</th><th>Max shortfall</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, s]) => (
            <tr key={name}>
              <td>{name}</td>
              <td>{gw(s.mae_mw)}</td>
              <td>{gw(s.rmse_mw)}</td>
              <td>{gw(s.bias_mw)}</td>
              <td>{pct(s.nmae_pct)}</td>
              <td>{gw(s.quantiles_mw?.p10)}</td>
              <td>{gw(s.quantiles_mw?.p90)}</td>
              <td>{gw(s.max_shortfall_mw)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Accuracy() {
  const [start, setStart] = useState(FIRST)
  const [end, setEnd] = useState(LAST)
  const acc = useApi('/accuracy', { start, end })
  const hor = useApi('/horizon')

  const controls = (
    <div className="controls">
      <label>From <input type="date" value={start} min={FIRST} max={end} onChange={(e) => e.target.value && setStart(e.target.value)} /></label>
      <label>To <input type="date" value={end} min={start} max={LAST} onChange={(e) => e.target.value && setEnd(e.target.value)} /></label>
      <span className="muted">Delivery days. Error = forecast − actual; positive means less wind than forecast.</span>
    </div>
  )
  if (!acc.data || !hor.data) return <>{controls}<Status {...(acc.error ? acc : hor)} /></>
  const a = acc.data
  const hist = a.histogram.map((b) => ({ ...b, mid: (b.from_mw + b.to_mw) / 2 }))

  return (
    <>
      {controls}
      <Card title="Forecast vs benchmarks" subtitle={`${a.forecast.n_hours} hours compared. Skill vs naive: ${pct(100 * a.skill_vs_persistence, 0)}; bias correction improves MAE by ${pct(100 * a.bias_corrected_skill_vs_forecast, 0)}.`}>
        <ModelTable a={a} />
      </Card>

      <div className="grid2">
        <Card title="Error distribution" subtitle="Hourly decision-forecast error. Red = wind under-delivered (shortfall).">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={hist}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="mid" tickFormatter={(v) => (v / 1000).toFixed(1)} label={{ value: 'GW', position: 'insideBottomRight', offset: -2 }} />
              <YAxis label={{ value: 'hours', angle: -90, position: 'insideLeft' }} />
              <Tooltip labelFormatter={(v, p) => p?.[0] ? `${gw(p[0].payload.from_mw)} to ${gw(p[0].payload.to_mw)}` : ''} />
              <Bar isAnimationActive={false} dataKey="count" name="Hours">
                {hist.map((b) => <Cell key={b.from_mw} fill={b.mid > 0 ? COLORS.shortfall : COLORS.surplus} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Error by forecast level" subtitle="Grouped by what the forecast said, which is known at decision time.">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={a.by_forecast_level}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="forecast_level" />
              <YAxis tickFormatter={(v) => (v / 1000).toFixed(1)} label={{ value: 'GW', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(v) => gw(v)} />
              <Legend />
              <Bar isAnimationActive={false} dataKey="bias_mw" name="Average error (bias)" fill={COLORS.forecast} />
              <Bar isAnimationActive={false} dataKey="p90_mw" name="P90 error (cover needed)" fill={COLORS.shortfall} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Accuracy vs how far ahead the forecast was made" subtitle="All WINDFOR vintages for January delivery hours. The decision forecasts fall in the 0–24h range.">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={hor.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="horizon" />
              <YAxis tickFormatter={(v) => (v / 1000).toFixed(1)} label={{ value: 'GW', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(v) => gw(v)} />
              <Legend />
              <Line isAnimationActive={false} dataKey="mae_mw" name="MAE" stroke={COLORS.forecast} strokeWidth={2} />
              <Line isAnimationActive={false} dataKey="rmse_mw" name="RMSE" stroke={COLORS.persistence} strokeWidth={2} />
              <Line isAnimationActive={false} dataKey="bias_mw" name="Bias" stroke={COLORS.shortfall} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Error by hour of day" subtitle="UTC, which equals UK time in January.">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={a.by_hour}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="hour" />
              <YAxis tickFormatter={(v) => (v / 1000).toFixed(1)} label={{ value: 'GW', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(v) => gw(v)} />
              <Legend />
              <Line isAnimationActive={false} dataKey="mae_mw" name="MAE" stroke={COLORS.forecast} strokeWidth={2} />
              <Line isAnimationActive={false} dataKey="p90_mw" name="P90 error" stroke={COLORS.shortfall} strokeWidth={2} />
              <Line isAnimationActive={false} dataKey="p10_mw" name="P10 error" stroke={COLORS.persistence} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </>
  )
}
