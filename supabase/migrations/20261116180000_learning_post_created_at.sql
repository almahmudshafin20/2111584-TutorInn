-- Keep new tutoring request creation timestamps aligned with the FastAPI model.
ALTER TABLE public.learning_posts
  ADD COLUMN IF NOT EXISTS created_at varchar(40);

CREATE INDEX IF NOT EXISTS ix_learning_posts_created_at
  ON public.learning_posts (created_at);
