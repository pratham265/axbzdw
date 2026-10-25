export const mw = (v) => (v == null ? '–' : `${Math.round(v).toLocaleString('en-GB')} MW`)
export const gw = (v) => (v == null ? '–' : `${(v / 1000).toFixed(2)} GW`)
export const gwh = (v) => (v == null ? '–' : `${(v / 1000).toLocaleString('en-GB', { maximumFractionDigits: 1 })} GWh`)
export const pct = (v, d = 1) => (v == null ? '–' : `${v.toFixed(d)}%`)
export const signedGw = (v) => (v == null ? '–' : `${v > 0 ? '+' : ''}${(v / 1000).toFixed(2)} GW`)

export const hhmm = (iso) => iso?.slice(11, 16)
export const dayLabel = (iso) =>
  new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })
export const dateTime = (iso) =>
  iso ? `${dayLabel(iso)} ${hhmm(iso)}` : '–'

export const COLORS = {
  forecast: '#2563eb',
  actual: '#111827',
  corrected: '#059669',
  persistence: '#9ca3af',
  shortfall: '#dc2626',
  surplus: '#2563eb',
  band: '#93c5fd',
}
