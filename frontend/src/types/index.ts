export type Student = {
  id: number
  full_name: string
  email: string
  education_level: string
  preferred_subjects: string
}

export type Tutor = {
  id: number
  full_name: string
  email: string
  subject: string
  teaching_level: string
  experience_years: number
  hourly_rate: number
  bio: string
}

export type Profile = Student | Tutor
export type Field = { name: string; label: string; type?: string; required?: boolean; placeholder?: string }
export type CurrentRole = "student" | "tutor" | "admin"

export type LearningPost = {
  id: number
  post_type: "tutor" | "student"
  author_name: string
  subject: string
  level: string
  experience: string
  availability: string
  location: string
  fee: number
  description: string
  status: "Pending" | "Accepted" | "Completed" | "Rejected"
  student_confirmed: boolean
  tutor_confirmed: boolean
  student_response: "No response" | "Interested" | "Not Interested"
  tutor_response: "No response" | "Interested" | "Not Interested"
}
