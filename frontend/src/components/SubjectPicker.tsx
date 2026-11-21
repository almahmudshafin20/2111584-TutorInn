import { useEffect, useState } from "react"
import { listSubjects } from "../api/subjects"

type SubjectPickerProps = { value: string[]; onChange: (next: string[]) => void; label?: string }

export function SubjectPicker({ value, onChange, label = "Subjects" }: SubjectPickerProps) {
  const [catalog, setCatalog] = useState<string[]>([])
  const [selected, setSelected] = useState("")
  const [error, setError] = useState("")
  useEffect(() => { listSubjects().then(setCatalog).catch(() => setError("The subject catalogue could not be loaded.")) }, [])
  function add() {
    if (!selected || value.some(item => item.toLocaleLowerCase() === selected.toLocaleLowerCase())) return
    onChange([...value, selected].slice(0, 20)); setSelected("")
  }
  return <div className="field"><span>{label}</span><div className="tag-list">{value.map(subject =>
    <button type="button" key={subject} className="subject-chip" onClick={() => onChange(value.filter(item => item !== subject))} aria-label={`Remove ${subject}`}>{subject} ×</button>)}</div>
    <div className="search-form"><select value={selected} onChange={event => setSelected(event.target.value)} aria-label={`Choose ${label.toLowerCase()}`}><option value="">Choose an active subject</option>{catalog.filter(item => !value.some(valueItem => valueItem.toLocaleLowerCase() === item.toLocaleLowerCase())).map(item => <option key={item} value={item}>{item}</option>)}</select><button type="button" className="button secondary" onClick={add} disabled={!selected || value.length >= 20}>Add</button></div>
    {error && <small className="muted">{error}</small>}<small className="muted">Choose from the Admin-managed subject catalogue. Duplicate subjects are ignored.</small>
  </div>
}
