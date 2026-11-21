-- Recorded in the production migration ledger as create_tutorinn_profile_tables.
-- Restored verbatim so repo history matches the ledger. Production already has these tables;
-- this file runs only on a clean replay, before the catch-up migration adds the remaining columns.
CREATE TABLE public.students (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    education_level VARCHAR(255) NOT NULL,
    preferred_subjects VARCHAR(1000) NOT NULL
);

CREATE INDEX ix_students_email ON public.students (email);

CREATE TABLE public.tutors (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    subject VARCHAR(255) NOT NULL,
    teaching_level VARCHAR(255) NOT NULL,
    experience_years INTEGER NOT NULL,
    hourly_rate DOUBLE PRECISION NOT NULL,
    bio VARCHAR(2000) NOT NULL
);

CREATE INDEX ix_tutors_email ON public.tutors (email);
