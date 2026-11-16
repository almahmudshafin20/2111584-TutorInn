import { useEffect, useRef, useState } from "react"
import type { FormEvent } from "react"
import { createPersonalTask,deletePersonalTask,getPersonalTaskSummary,listPersonalTasks,updatePersonalTask } from "../api/tasks"
import type { PersonalTask,PersonalTaskFilters,PersonalTaskInput,PersonalTaskSummary } from "../types/auth"

const emptyForm={title:"",description:"",category:"",due_date:""}
const uncategorized="__uncategorized__"
function initialFilters():PersonalTaskFilters {
  const p=new URLSearchParams(window.location.search), status=p.get("task_status")??"all"
  return {q:"",category:p.get("task_category")??"",status:["open","completed","overdue"].includes(status)?status as PersonalTaskFilters["status"]:"all"}
}
function dueLabel(value:string|null):string {
  if(!value)return "No due date"
  const due=new Date(`${value}T00:00:00`),today=new Date();today.setHours(0,0,0,0)
  const days=Math.round((due.getTime()-today.getTime())/86400000)
  if(days<0)return `Overdue by ${Math.abs(days)} day${Math.abs(days)===1?"":"s"}`
  if(days===0)return "Due today"
  if(days===1)return "Due tomorrow"
  return `Due ${due.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric"})}`
}
export default function PersonalTasksPanel(){
  const [filters,setFilters]=useState<PersonalTaskFilters>(initialFilters)
  const [tasks,setTasks]=useState<PersonalTask[]>([])
  const [summary,setSummary]=useState<PersonalTaskSummary>({total_count:0,open_count:0,completed_count:0,overdue_count:0,uncategorized_count:0,categories:[]})
  const [form,setForm]=useState(emptyForm),[editingId,setEditingId]=useState<number|null>(null)
  const [loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("")
  const searchRef=useRef<HTMLInputElement>(null)
  async function refresh(){
    setLoading(true);setError("")
    try{const [items,counts]=await Promise.all([listPersonalTasks(filters),getPersonalTaskSummary()]);setTasks(items);setSummary(counts)}
    catch(reason){setError(reason instanceof Error?reason.message:"Could not load personal tasks.")}
    finally{setLoading(false)}
  }
  useEffect(()=>{void refresh()},[filters])
  useEffect(()=>{
    const p=new URLSearchParams(window.location.search)
    if(filters.category)p.set("task_category",filters.category);else p.delete("task_category")
    if(filters.status&&filters.status!=="all")p.set("task_status",filters.status);else p.delete("task_status")
    const q=p.toString()
    window.history.replaceState(window.history.state,"",`${window.location.pathname}${q?`?${q}`:""}${window.location.hash}`)
  },[filters])
  useEffect(()=>{
    function shortcut(e:KeyboardEvent){
      if(e.key!=="/"||e.ctrlKey||e.metaKey||e.altKey)return
      const target=e.target
      if(target instanceof HTMLElement&&(target.isContentEditable||["INPUT","TEXTAREA","SELECT"].includes(target.tagName)))return
      e.preventDefault();searchRef.current?.focus()
    }
    window.addEventListener("keydown",shortcut);return()=>window.removeEventListener("keydown",shortcut)
  },[])
  function reset(){setForm(emptyForm);setEditingId(null)}
  function edit(task:PersonalTask){setForm({title:task.title,description:task.description,category:task.category??"",due_date:task.due_date??""});setEditingId(task.id)}
  async function save(e:FormEvent<HTMLFormElement>){
    e.preventDefault();setBusy(true);setError("");setNotice("")
    const payload:PersonalTaskInput={title:form.title.trim(),description:form.description.trim(),category:form.category.trim()||null,due_date:form.due_date||null,completed:editingId===null?false:tasks.find(t=>t.id===editingId)?.completed??false}
    try{if(editingId===null)await createPersonalTask(payload);else await updatePersonalTask(editingId,payload);setNotice(editingId===null?"Personal task created.":"Personal task updated.");reset();await refresh()}
    catch(reason){setError(reason instanceof Error?reason.message:"Could not save task.")}finally{setBusy(false)}
  }
  async function toggle(task:PersonalTask){
    setBusy(true);setError("");setNotice("")
    try{await updatePersonalTask(task.id,{title:task.title,description:task.description,category:task.category,due_date:task.due_date,completed:!task.completed});setNotice(task.completed?"Task marked open.":"Task marked completed.");await refresh()}
    catch(reason){setError(reason instanceof Error?reason.message:"Could not update task.")}finally{setBusy(false)}
  }
  async function remove(task:PersonalTask){
    if(!window.confirm(`Delete “${task.title}”?`))return
    setBusy(true);setError("");setNotice("")
    try{await deletePersonalTask(task.id);setNotice("Personal task deleted.");if(editingId===task.id)reset();await refresh()}
    catch(reason){setError(reason instanceof Error?reason.message:"Could not delete task.")}finally{setBusy(false)}
  }
  return <section id="personal-tasks" className="panel dashboard-panel personal-tasks-panel" aria-labelledby="personal-tasks-heading">
    <div className="panel-heading"><div><p className="eyebrow">YOUR LEARNING PLAN</p><h2 id="personal-tasks-heading">Personal learning tasks</h2><p>Organize your study goals. These tasks are private to your account.</p></div><span className="personal-task-shortcut">Press <kbd>/</kbd> to search</span></div>
    <div className="personal-task-summary" aria-label="Personal task summary">
      <article><strong>{summary.open_count}</strong><span>Open tasks</span></article><article><strong>{summary.completed_count}</strong><span>Completed tasks</span></article><article><strong>{summary.overdue_count}</strong><span>Overdue tasks</span></article>
    </div>
    <form className="personal-task-filters" onSubmit={e=>e.preventDefault()} aria-label="Search and filter personal tasks">
      <label className="field">Search tasks<input ref={searchRef} value={filters.q??""} onChange={e=>setFilters(f=>({...f,q:e.target.value}))} placeholder="Search titles or descriptions"/></label>
      <label className="field">Category<select value={filters.category??""} onChange={e=>setFilters(f=>({...f,category:e.target.value}))}><option value="">All categories</option><option value={uncategorized}>Uncategorized</option>{summary.categories.map(c=><option key={c} value={c}>{c}</option>)}</select></label>
      <label className="field">Status<select value={filters.status??"all"} onChange={e=>setFilters(f=>({...f,status:e.target.value as PersonalTaskFilters["status"]}))}><option value="all">All statuses</option><option value="open">Open</option><option value="completed">Completed</option><option value="overdue">Overdue</option></select></label>
    </form>
    {error&&<div className="alert error" role="alert">{error} <button type="button" className="small-button" onClick={()=>void refresh()}>Try again</button></div>}
    {notice&&<div className="alert success" role="status" aria-live="polite">{notice}</div>}
    <form className="personal-task-form" onSubmit={save}>
      <label className="field">Task title<input required maxLength={160} value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))} placeholder="e.g. Revise quadratic equations"/></label>
      <label className="field">Description<textarea rows={2} maxLength={2000} value={form.description} onChange={e=>setForm(f=>({...f,description:e.target.value}))} placeholder="Learning notes (optional)"/></label>
      <label className="field">Category (optional)<input maxLength={60} value={form.category} onChange={e=>setForm(f=>({...f,category:e.target.value}))} placeholder="Study, homework, revision…"/></label>
      <label className="field">Due date (optional)<input type="date" value={form.due_date} onChange={e=>setForm(f=>({...f,due_date:e.target.value}))}/></label>
      <div className="actions"><button className="button primary" disabled={busy}>{busy?"Saving…":editingId===null?"Add task":"Save task"}</button>{editingId!==null&&<button type="button" className="button secondary" disabled={busy} onClick={reset}>Cancel edit</button>}</div>
    </form>
    <div className="panel-heading" style={{marginTop:24}}><div><h3>Your tasks</h3><p>{summary.total_count} task{summary.total_count===1?"":"s"} in your learning plan.</p></div></div>
    <div aria-live="polite" aria-busy={loading}>{loading?<p className="dashboard-loading">Loading your personal tasks…</p>:tasks.length===0?<div className="empty-state"><h3>{summary.total_count===0?"No personal tasks yet":"No tasks match these filters"}</h3><p>{summary.total_count===0?"Add a learning task above to start organizing your study plan.":"Try changing your search, category or status filters."}</p></div>:<div className="personal-task-list">{tasks.map(task=><article className={`personal-task-card ${task.completed?"is-completed":task.status==="overdue"?"is-overdue":"is-open"}`} key={task.id}><div><div className="dashboard-card-top"><h4 className="personal-task-title">{task.title}</h4><span className={`status-pill status-${task.status}`}>{task.status}</span></div>{task.description&&<p className="personal-task-description">{task.description}</p>}<div className="personal-task-meta"><span className="personal-task-category">{task.category??"Uncategorized"}</span><span className="personal-task-due">{dueLabel(task.due_date)}</span></div></div><div className="personal-task-actions"><button type="button" className="small-button" disabled={busy} onClick={()=>void toggle(task)}>{task.completed?"Mark open":"Mark complete"}</button><button type="button" className="small-button" disabled={busy} onClick={()=>edit(task)}>Edit</button><button type="button" className="small-button danger-text" disabled={busy} onClick={()=>void remove(task)}>Delete</button></div></article>)}</div>}</div>
  </section>
}
