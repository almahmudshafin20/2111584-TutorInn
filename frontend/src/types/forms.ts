import type { Field } from "./index"

export const studentFields: Field[] = [
  { name: "full_name", label: "Full name", required: true, placeholder: "e.g. Ayesha Rahman" },
  { name: "email", label: "Email", type: "email", required: true, placeholder: "you@example.com" },
  { name: "education_level", label: "Education level", required: true, placeholder: "e.g. HSC, University" },
  { name: "preferred_subjects", label: "Preferred subjects", placeholder: "e.g. Mathematics, Physics" },
]

export const tutorFields: Field[] = [
  { name: "full_name", label: "Full name", required: true, placeholder: "e.g. Rahim Ahmed" },
  { name: "email", label: "Email", type: "email", required: true, placeholder: "you@example.com" },
  { name: "subject", label: "Subject", required: true, placeholder: "e.g. Mathematics" },
  { name: "teaching_level", label: "Teaching level", required: true, placeholder: "e.g. Secondary, HSC" },
  { name: "experience_years", label: "Experience (years)", type: "number", required: true, placeholder: "3" },
  { name: "hourly_rate", label: "Hourly rate (৳)", type: "number", required: true, placeholder: "500" },
  { name: "bio", label: "Short bio", type: "textarea", placeholder: "Briefly describe your teaching experience." },
]

export const emptyStudent = { full_name: "", email: "", education_level: "", preferred_subjects: "" }
export const emptyTutor = { full_name: "", email: "", subject: "", teaching_level: "", experience_years: "0", hourly_rate: "500", bio: "" }
export const emptyPost = { author_name: "", subject: "", level: "", experience: "", availability: "", location: "", fee: "500", description: "" }
