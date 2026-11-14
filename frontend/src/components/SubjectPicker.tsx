import { useEffect, useState } from "react"
import { api } from "../services/api"

type SubjectPickerProps = {
  value: string[]
  onChange: (next: string[]) => void
  label?: string
}

export function SubjectPicker({ value, onChange, label = "Subjects" }: SubjectPickerProps) {
  const [draft, setDraft] = useState("")
  const [catalog, setCatalog] = useState<string[]>([])

  useEffect(() => {
    api<string[]>("/api/subjects").then(setCatalog).catch(() => setCatalog([]))
  }, [])

  function add(raw: string) {
    const next = raw.split(/[,;\n]/).map(item => item.trim()).filter(Boolean)
    if (next.length) {
      const unique = new Map<string, string>()
      for (const item of [...value, ...next]) {
        if (!unique.has(item.toLocaleLowerCase())) unique.set(item.toLocaleLowerCase(), item)
      }
      onChange(Array.from(unique.values()).slice(0, 20))
    }
    setDraft("")
  }

  return (
    <div className="field">
      <span>{label}</span>
      <div className="tag-list">
        {value.map(subject => (
          <button
            type="button"
            key={subject}
            className="subject-chip"
            onClick={() => onChange(value.filter(item => item !== subject))}
            aria-label={`Remove ${subject}`}
          >
            {subject} ×
          </button>
        ))}
      </div>
      <div className="search-form">
        <input
          list="tutorinn-subject-catalog"
          value={draft}
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => {
            if (event.key === "Enter" || event.key === ",") {
              event.preventDefault()
              add(draft)
            }
          }}
          placeholder="Type or choose a subject and press Enter"
        />
        <datalist id="tutorinn-subject-catalog">
          {catalog.map(item => <option key={item} value={item} />)}
        </datalist>
        <button type="button" className="button secondary" onClick={() => add(draft)} disabled={!draft.trim()}>
          Add
        </button>
      </div>
      <small className="muted">Add each subject separately. Duplicate subjects are ignored.</small>
    </div>
  )
}
