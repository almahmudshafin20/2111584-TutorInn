import type { ReactNode } from "react"

export type DashboardTone = "accent" | "warning" | "success" | "neutral"

export function DashboardStat({ label, value, hint, tone = "accent" }: { label: string; value: ReactNode; hint?: string; tone?: DashboardTone }) {
  return (
    <article className={`dashboard-stat tone-${tone}`}>
      <span className="dashboard-stat-label">{label}</span>
      <strong className="dashboard-stat-value">{value}</strong>
      {hint && <span className="dashboard-stat-hint">{hint}</span>}
    </article>
  )
}

export function DashboardProgress({ label, done, total }: { label: string; done: number; total: number }) {
  const percent = total === 0 ? 0 : Math.round((done / total) * 100)
  return (
    <div className="dashboard-progress" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
      <div className="dashboard-progress-head">
        <span>{label}</span>
        <strong>{done} of {total} · {percent}%</strong>
      </div>
      <div className="dashboard-progress-track"><span style={{ width: `${percent}%` }} /></div>
    </div>
  )
}

export function DashboardCallout({ tone = "warning", children }: { tone?: DashboardTone; children: ReactNode }) {
  return <div className={`dashboard-callout tone-${tone}`} role="status">{children}</div>
}
