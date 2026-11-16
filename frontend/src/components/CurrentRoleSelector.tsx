import type { CurrentRole } from "../types"

export function CurrentRoleSelector({ role, onChange }: { role: CurrentRole; onChange: (role: CurrentRole) => void }) {
  return <div className="post-kind-switch" role="group" aria-label="Continue as role">
    <span className="muted">Continue as:</span>
    <button type="button" className={role === "student" ? "button primary" : "button secondary"} onClick={() => onChange("student")}>Student</button>
    <button type="button" className={role === "tutor" ? "button primary" : "button secondary"} onClick={() => onChange("tutor")}>Tutor</button>
    <button type="button" className={role === "admin" ? "button primary" : "button secondary"} onClick={() => onChange("admin")}>Admin</button>
  </div>
}
