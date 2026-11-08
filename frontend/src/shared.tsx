import { useEffect, useMemo, useState } from "react"
import type { FormEvent, ReactNode } from "react"
import { useTheme } from "./context/ThemeContext"
import { selectedProfile, saveSelectedProfile } from "./services/session"
import type { SelectedProfile } from "./services/session"
import { api, getAdminHeaders } from "./services/api"
export { selectedProfile, saveSelectedProfile } from "./services/session"
export type { SelectedProfile } from "./services/session"
export { api, getAdminHeaders } from "./services/api"

export type ProfileType = "student" | "tutor"
export type Student = { id:number; full_name:string; email:string; education_level:string; subjects:string[] }
export type Tutor = { id:number; full_name:string; email:string; subjects:string[]; teaching_level:string; experience_years:number; hourly_rate:number; bio:string }
export type Profile = Student | Tutor
export type LearningPost = {
  id:number; post_type:ProfileType; author_name:string; author_profile_id:number|null; author_profile_type:ProfileType|null
  subjects:string[]; subject:string; level:string; experience:string; availability:string; location:string
  fee:number; description:string; status:string
}
export type InterestResponse = { id:number; post_id:number; profile_id:number; profile_type:ProfileType; response:"Interested"|"Not Interested"; review_status:string; created_at:string; updated_at:string }

export const emptyStudent = { full_name:"", email:"", education_level:"", subjects:[] as string[]¶»§q«^u¸1…å½ÕĞ¡í¡¥±‘É•¹ôéí¡¥±‘É•¸éI•…Ñ9½‘•ô¥íÉ•ÑÕÉ¸€ğøñ!•…‘•È¼øñµ…¥¸±…ÍÍ9…µ”ô‰Á…”ˆùí¡¥±‘É•¹ôğ½µ…¥¸øñ½½Ñ•È¼øğ¼ùô