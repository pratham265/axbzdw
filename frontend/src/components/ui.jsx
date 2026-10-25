export function Kpi({ label, value, hint, tone }) {
  return (
    <div className={`kpi ${tone || ''}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  )
}

export function Card({ title, subtitle, children }) {
  return (
    <section className="card">
      {title && <h3>{title}</h3>}
      {subtitle && <p className="muted">{subtitle}</p>}
      {children}
    </section>
  )
}

export function Status({ loading, error }) {
  if (error) return <div className="status error">Could not load data: {error.message}</div>
  if (loading) return <div className="status">Loading…</div>
  return null
}
