import { useId, useState } from "react"
import type { KeyboardEvent } from "react"

type PasswordFieldProps = {
  label: string
  value: string
  onChange: (value: string) => void
  autoComplete: string
  required?: boolean
  minLength?: number
  maxLength?: number
  placeholder?: string
  showStrength?: boolean
  invalid?: boolean
}

function passwordStrength(value: string) {
  if (!value) return { score: 0, label: "Not entered", level: "empty" }
  const score = [
    value.length >= 12,
    value.length >= 16,
    /[a-z]/.test(value) && /[A-Z]/.test(value),
    /\d/.test(value),
    /[^A-Za-z0-9]/.test(value),
  ].filter(Boolean).length
  if (value.length < 12) return { score, label: "Too short", level: "weak" }
  if (score >= 5) return { score, label: "Strong", level: "strong" }
  if (score >= 4) return { score, label: "Good", level: "good" }
  if (score >= 3) return { score, label: "Fair", level: "fair" }
  return { score, label: "Weak", level: "weak" }
}

export function PasswordField({
  label, value, onChange, autoComplete, required, minLength, maxLength, placeholder, showStrength, invalid,
}: PasswordFieldProps) {
  const id = useId()
  const [capsLockOn, setCapsLockOn] = useState(false)
  const capsId = `password-caps-${id}`
  const strength = passwordStrength(value)
  const updateCapsLock = (event: KeyboardEvent<HTMLInputElement>) => setCapsLockOn(event.getModifierState("CapsLock"))

  return (
    <label className="field password-field" htmlFor={id}>
      {label}
      <input
        id={id}
        type="password"
        autoComplete={autoComplete}
        required={required}
        minLength={minLength}
        maxLength={maxLength}
        placeholder={placeholder}
        value={value}
        onChange={event => onChange(event.target.value)}
        onKeyDown={updateCapsLock}
        onKeyUp={updateCapsLock}
        onBlur={() => setCapsLockOn(false)}
        aria-invalid={invalid || undefined}
        aria-describedby={capsLockOn ? capsId : undefined}
      />
      {capsLockOn && <small id={capsId} className="password-caps-warning" role="status" aria-live="polite">Caps Lock is on.</small>}
      {showStrength && value && (
        <span className="password-strength" role="status" aria-live="polite">
          <span className="password-strength-heading">Password strength: <strong>{strength.label}</strong></span>
          <span className="password-strength-track" role="progressbar" aria-label="Password strength" aria-valuemin={0} aria-valuemax={5} aria-valuenow={strength.score}>
            <span className={`password-strength-fill strength-${strength.level}`} />
          </span>
          <small>Use at least 12 characters. A longer passphrase is even better.</small>
        </span>
      )}
    </label>
  )
}

export function PasswordMatchFeedback({ password, confirmation }: { password: string; confirmation: string }) {
  if (!confirmation) return null
  const matches = password === confirmation
  return (
    <small className={`password-match ${matches ? "is-match" : "is-mismatch"}`} role="status" aria-live="polite">
      {matches ? "Passwords match." : "Passwords do not match."}
    </small>
  )
}
