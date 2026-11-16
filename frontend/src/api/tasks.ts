import { api } from "./api"
import type { PersonalTask, PersonalTaskFilters, PersonalTaskInput, PersonalTaskSummary } from "../types/auth"

export function listPersonalTasks(filters:PersonalTaskFilters={}):Promise<PersonalTask[]> {
  const params=new URLSearchParams()
  if(filters.q?.trim()) params.set("q",filters.q.trim())
  if(filters.category==="__uncategorized__") params.set("uncategorized","true")
  else if(filters.category?.trim()) params.set("category",filters.category.trim())
  if(filters.status&&filters.status!=="all") params.set("status",filters.status)
  const query=params.toString()
  return api<PersonalTask[]>(`/api/me/tasks${query?`?${query}`:""}`)
}
export function getPersonalTaskSummary():Promise<PersonalTaskSummary>{return api<PersonalTaskSummary>("/api/me/tasks/summary")}
export function createPersonalTask(payload:PersonalTaskInput):Promise<PersonalTask>{return api<PersonalTask>("/api/me/tasks",{method:"POST",body:JSON.stringify(payload)})}
export function updatePersonalTask(id:number,payload:PersonalTaskInput):Promise<PersonalTask>{return api<PersonalTask>(`/api/me/tasks/${id}`,{method:"PUT",body:JSON.stringify(payload)})}
export function deletePersonalTask(id:number):Promise<void>{return api<void>(`/api/me/tasks/${id}`,{method:"DELETE"})}
