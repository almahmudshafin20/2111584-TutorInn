export type ProfileType = "student" | "tutor"
export type CurrentRole = ProfileType | "admin"

export type Field = {
  name: string
  label: string
  type?: string
  required?: boolean
  placeholder?: string
}

export type Student = {
  id: number
  full_name: string
  email?: string
  phone_number?: string
  education_level: string
  subjects: string[]
}

export type Tutor = {
  id: number
  full_name: string
  email?: string
  phone_number?: string
  subjects: string[]
  teaching_level: string
  experience_years: number
  hourly_rate: number
  bio: string
}

export type Profile = Student | Tutor

export type LearningPost = {
  id: number
  post_type: ProfileType
  author_name: string
  author_profile_id: number | null
  author_profile_type: ProfileType | null
  subjects: string[]
  subject: string
  level: string
  experience: string
  availability: string
  location: string
  fee: number
  description: string
  status: string
}

export type InterestResponse = {
  id: number
  post_id: number
  profile_id: number
  profile_type: ProfileType
  response: "Interested" | "Not Interested"
  review_status: string
  created_at: string
  updated_at: string
}

export type SelectedProfile = { id: number; type: ProfileType }

export type AdminCandidate = {
  response: {
    id: number
    post_id: number
    profile_id: number
    profile_type: ProfileType
    response: string
    review_status: string
    created_at: string
    updated_at: string
  }
  post: {
    id: number
    post_type: ProfileType
    author_name: string
    subjects: string[]
    level: string
    experience: string
    availability: string
    location: string
    fee: number
    description: string
    status: string
  }
  tutor: null | {
    id: number
    full_name: string
    email: string
    phone_number: string
    subjects: string[]
    teaching_level: string
    experience_years: number
    hourly_rate: number
    bio: string
  }
  student: null | {
    id: number
    full_name: string
    email: string
    phone_number: string
    subjects: string[]
    education_level: string
  }
}

export const emptyStudent = {
  full_name: "",
  email: "",
  phone_number: "",
  education_level: "",
  subjects: [] as string[],
}

export const emptyTutor = {
  full_name: "",
  email: "",
  phone_number: "",
  subjects: [] as string[],
  teaching_level: "",
  experience_years: "0",
  hourly_rate: "500",
  bio: "",
}

export const emptyPost = {
  subjects: [] as string[],
  level: "",
  experience: "",
  availability: "",
  location: "",
  fee: "500",
  description: "",
}
